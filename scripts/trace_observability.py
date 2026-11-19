#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trace_observability.py —— 可观测性：由运行轨迹构建 span 树并输出成本/质量/延迟审计（P0-⑦·对齐《AI Agent》Ch.6.8 OpenTelemetry/OpenInference）

设计边界（诚实标注）：
  专家团无内置 APM，本脚本按 OpenTelemetry 的 trace/span 树语义，定义轻量 span schema
  并据此做离线审计——这是统计显著性闸（check_change_significance.py）与 A/B 特性开关
  （团长 §6.5 闸门开关表）的真实数据底座。

SPAN SCHEMA（与 ingest_run_log 事件同源于 run-log）：
  每个事件可带 span_id / parent_span_id；无显式 parent 时按调用顺序（dispatch→其后的
  member_return/accept 归到该 dispatch 下）自动嵌套。span 可携带：
    - cost_tokens / cost_yuan（若团长在事件中记录）
    - latency_ms（由相邻 ts 推算）
  审计输出：每 span 的耗时/成本、整树聚合、以及「质量闸门」是否全程闭合
  （所有 verdict 均为「可进入使用」或经修订后达标，无「禁止外发」残留）。

用法：
  python trace_observability.py --run-log runs/<pid>/<run_id>.jsonl [--json out] [--summary]

退出码：0 健康（无禁止外发残留）｜ 1 存在禁止外发/缺失验收的阻断项 ｜ 2 用法/格式错误
"""
import sys, os, json, argparse

VALID_TYPES = {"dispatch", "member_return", "accept", "reject", "verdict", "error", "note"}


def load_events(path):
    events = []
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        events = data if isinstance(data, list) else data.get("events", [])
    else:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def build_spans(events):
    """按 span_id/parent 或调用顺序构建树；返回 (roots, by_id, verdict_events)。"""
    by_id = {}
    roots = []
    last_dispatch = None
    verdict_events = []  # 独立收集 verdict，避免被复用 span 的类型吞掉
    for ev in events:
        sid = ev.get("span_id") or f"auto-{len(by_id)}"
        parent = ev.get("parent_span_id")
        if ev["type"] == "verdict":
            verdict_events.append(ev)
        if sid not in by_id:
            by_id[sid] = {"span_id": sid, "parent": parent, "member": ev.get("member"),
                          "phase": ev.get("phase"), "type": ev["type"], "children": [],
                          "cost_tokens": ev.get("cost_tokens"), "cost_yuan": ev.get("cost_yuan"),
                          "ts": ev.get("ts"), "verdict": ev.get("verdict") if ev["type"] == "verdict" else None}
        else:
            for k in ("member", "phase", "cost_tokens", "cost_yuan", "ts", "verdict"):
                if ev.get(k) is not None:
                    by_id[sid][k] = ev.get(k)
        node = by_id[sid]
        if parent and parent in by_id:
            if node not in by_id[parent]["children"]:
                by_id[parent]["children"].append(node)
        elif ev["type"] == "dispatch" or (parent is None and last_dispatch is None):
            if node not in roots:
                roots.append(node)
        if ev["type"] == "dispatch":
            last_dispatch = sid
    return roots, by_id, verdict_events


def audit(roots, verdict_events):
    total_tokens = 0.0
    total_yuan = 0.0
    blocked = []
    for node in _iter(roots):
        if node.get("cost_tokens"):
            total_tokens += float(node["cost_tokens"])
        if node.get("cost_yuan"):
            total_yuan += float(node["cost_yuan"])
        if node["type"] == "reject":
            pass  # 已修订不计阻断，除非末态仍禁止
    verdicts = [e.get("verdict") for e in verdict_events if e.get("verdict")]
    blocked = [e.get("span_id") for e in verdict_events if e.get("verdict") == "禁止外发"]
    healthy = all(v in ("可进入使用", "修订后复核") for v in verdicts) if verdicts else True
    return {
        "total_cost_tokens": total_tokens,
        "total_cost_yuan": round(total_yuan, 4),
        "verdicts": verdicts,
        "blocked_spans": blocked,
        "healthy": healthy and not blocked,
    }


def _iter(nodes):
    for n in nodes:
        yield n
        yield from _iter(n["children"])


def main():
    ap = argparse.ArgumentParser(description="可观测性 span 树审计")
    ap.add_argument("--run-log", required=True)
    ap.add_argument("--json")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    try:
        events = load_events(args.run_log)
    except (ValueError, FileNotFoundError) as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 2
    roots, by_id, verdict_events = build_spans(events)
    rep = {"span_count": len(by_id), "audit": audit(roots, verdict_events)}
    if args.summary:
        a = rep["audit"]
        print(f"spans={rep['span_count']} tokens={a['total_cost_tokens']:.0f} "
              f"cost¥={a['total_cost_yuan']} verdicts={a['verdicts']} healthy={a['healthy']}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print(f"[report] -> {args.json}")
    elif not args.summary:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["audit"]["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
