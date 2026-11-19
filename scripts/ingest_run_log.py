#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_run_log.py —— 端到端编排质量评估：解析团长运行轨迹并产出失败归因（P0-⑥·对齐《AI Agent》Ch.6.5.2 轨迹前缀回归 / Ch.6.9「先看评测系统本身」）

设计边界（诚实标注）：
  专家团运行时由 WorkBuddy 编排，本脚本不直接重放 LLM，而是定义**运行轨迹 schema** 并据此做
  离线评估。接入方式：团长在派发/验收每个成员时，向 `runs/<project_id>/<run_id>.jsonl` 追加一条
  结构化事件（schema 见下方 EVENT_SCHEMA）。本脚本读取该轨迹，完成两件事：
    1. 重建结构化轨迹（phase 树 + 成员轮次 + 验收结论），供 trace_observability.py 复用；
    2. 按「首个错误步骤」做失败归因（呼应团长 §1.2 回路的 JSON 结构化失败归因），输出
       ver-agent 可消费的归因 JSON。
  端到端 LLM 编排质量 = 本轨迹 + sop_eval.py 的 golden cases 共用同一标注集（书 6.9 评测系统自检）。

EVENT_SCHEMA（每行一条 JSON）：
  {"ts":<float>,"span_id":<str>,"parent_span_id":<str|null>,"type":<str>,"member":<str|null>,
   "phase":<str|null>,"ok":<bool|null>,"reason":<str|null>,"payload":<obj|null>}
  type ∈ {dispatch, member_return, accept, reject, verdict, error, note}
    - dispatch: 团长下发交接物给某成员（parent=团长 root span）
    - member_return: 成员回传（ok 表示是否自报完成）
    - accept/reject: 团长四维度验收结论（reject 须带 reason）
    - verdict: ver 外发判定（可进入使用/修订后复核/禁止外发）
    - error: 任意环节显式错误（含异常/卡住/超轮次）
    - note: 其它观测（如变更 v<N>、派新即关旧）

退出码：0 解析成功且无阻断错误 ｜ 1 轨迹含阻断错误（error 事件或连续 reject 超限）｜ 2 用法/格式错误
"""
import sys, os, json, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_RUNS = os.path.join(PKG_ROOT, "runs")

VALID_TYPES = {"dispatch", "member_return", "accept", "reject", "verdict", "error", "note"}


def load_events(path):
    """读取 JSONL 运行轨迹，返回事件列表；格式错误抛 ValueError。"""
    events = []
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        events = data if isinstance(data, list) else data.get("events", [])
    else:
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"第 {ln} 行非合法 JSON：{e}")
                events.append(ev)
    for i, ev in enumerate(events):
        if not isinstance(ev, dict) or "type" not in ev:
            raise ValueError(f"事件 #{i} 缺少 type 字段")
        if ev["type"] not in VALID_TYPES:
            raise ValueError(f"事件 #{i} type={ev['type']} 非法，须 ∈ {sorted(VALID_TYPES)}")
    return events


def build_trajectory(events):
    """重建 phase/成员轮次树，返回 {spans, phases, member_turns, order}。"""
    spans = {}
    for ev in events:
        sid = ev.get("span_id")
        if sid:
            spans.setdefault(sid, {"span_id": sid, "parent": ev.get("parent_span_id"),
                                   "member": ev.get("member"), "phase": ev.get("phase"),
                                   "events": []})["events"].append(ev)
    phases, member_turns, order = [], {}, []
    for ev in events:
        if ev["type"] == "dispatch":
            order.append(ev)
            if ev.get("phase") and ev["phase"] not in phases:
                phases.append(ev["phase"])
        if ev["type"] in ("member_return", "accept", "reject"):
            m = ev.get("member")
            if m:
                member_turns.setdefault(m, []).append(ev)
    return {"spans": spans, "phases": phases, "member_turns": member_turns,
            "dispatch_order": [e.get("member") for e in order]}


def attribute_failure(events, max_reject_per_member=2):
    """
    失败归因：返回首个错误步骤定位（呼应团长 §1.2 / ver §6 失败归因从首个错误）。
    规则：
      - 任一 type=error 事件 → 首个即为主因；
      - 无 error 但存在 reject → 取最早 reject，并校验是否超「同成员修订 ≤2 轮」熔断；
      - 否则无失败（轨迹健康）。
    输出结构与团长回路 JSON 失败归因对齐：首个错误步骤 / 根因类别 / 证据引用 / 是否可恢复 / 置信度。
    """
    for idx, ev in enumerate(events):
        if ev["type"] == "error":
            return {
                "has_failure": True,
                "first_error_step": idx + 1,
                "root_cause": "explicit_error",
                "evidence": ev.get("reason") or ev.get("payload"),
                "recoverable": None,
                "confidence": "high",
                "kind": "error_event",
            }
    earliest_reject = None
    for idx, ev in enumerate(events):
        if ev["type"] == "reject":
            earliest_reject = (idx, ev)
            break
    if earliest_reject:
        idx, ev = earliest_reject
        m = ev.get("member")
        turns = len([e for e in events if e.get("member") == m and e["type"] in ("accept", "reject")])
        over_cap = turns > max_reject_per_member
        return {
            "has_failure": True,
            "first_error_step": idx + 1,
            "root_cause": "acceptance_reject",
            "evidence": ev.get("reason"),
            "recoverable": not over_cap,
            "confidence": "medium" if over_cap else "high",
            "kind": "reject_over_cap" if over_cap else "reject",
            "member": m,
            "reject_rounds": turns,
            "breach_fuse_cap": over_cap,
        }
    return {"has_failure": False, "first_error_step": None, "root_cause": None,
            "evidence": None, "recoverable": None, "confidence": "high", "kind": "healthy"}


def main():
    ap = argparse.ArgumentParser(description="端到端运行轨迹解析 + 失败归因")
    ap.add_argument("--run-log", required=True, help="运行轨迹 .jsonl 或 .json 路径")
    ap.add_argument("--json", help="输出轨迹+归因 JSON 路径")
    ap.add_argument("--attrib-only", action="store_true", help="仅输出失败归因")
    args = ap.parse_args()
    try:
        events = load_events(args.run_log)
    except (ValueError, FileNotFoundError) as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 2
    traj = build_trajectory(events)
    attrib = attribute_failure(events)
    if args.attrib_only:
        out = attrib
    else:
        out = {"events": len(events), "trajectory": traj, "attribution": attrib}
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"[report] -> {args.json}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    blocked = attrib["has_failure"] and (attrib["kind"] == "error_event"
                                          or attrib.get("breach_fuse_cap"))
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
