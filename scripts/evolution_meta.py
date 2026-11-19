#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evolution_meta.py —— 持续进化闭环 meta 化：把运行经验反哺为可机读知识库条目（P2-⑨·对齐《AI Agent》Ch.8.2「从更新产物到更新更新方法」）

设计边界（诚实标注）：
  团长 §6.5 定期整理例程（睡眠学习）当前靠人工触发。本脚本把"经验→知识"做成**半自动提案器**：
  读取运行轨迹（runs/<pid>/<run_id>.jsonl，schema 同 ingest_run_log），识别可沉淀信号：
    1. 重复出现的失败类别（同 root_cause 多次）→ 提议新增 governance 铁律 / ver 自检项；
    2. 反复被引用的知识缺口（doc-in 抽取项无知识库条目）→ 提议新增 knowledge-index 条目（待核实）；
    3. 多次被采纳的变更 v<N> 模式 → 提议写回 SOP 确定性步骤。
  输出 **governance PR 就绪的 diff 提案**（markdown），交异源 Reviewer 审核，而非自动合入——
  严守 governance.md「锁版本、拒静默更新」纪律（本脚本只生成提案，不写主分支）。

用法：
  python evolution_meta.py --run-log <path> [--out proposals.md] [--json]

退出码：0 正常 ｜ 2 用法/格式错误
"""
import sys, os, json, argparse, re
from collections import Counter


def load_events(path):
    events = []
    if path.endswith(".json"):
        data = json.load(open(path, encoding="utf-8"))
        events = data if isinstance(data, list) else data.get("events", [])
    else:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def propose(events):
    """返回 (proposals, stats)。proposals 为治理 PR 就绪的 markdown 段落列表。"""
    # 1. 失败类别计数（复用 ingest 的归因逻辑精简版）
    rejects = [e for e in events if e["type"] == "reject"]
    reasons = Counter()
    for e in rejects:
        r = e.get("reason") or ""
        # 归并：取前 8 字作类别指纹
        key = re.sub(r"[：:。.].*$", "", r)[:8] or "未说明"
        reasons[key] += 1
    # 2. 知识缺口：doc-in 抽取但无对应 knowledge-index 引用标签
    gap_hits = [e for e in events if e["type"] == "note" and "缺口" in (e.get("reason") or "")]
    # 3. 已采纳变更次数
    changes = [e for e in events if e["type"] == "note" and "变更 v" in (e.get("reason") or "")]

    proposals = []
    for cat, cnt in reasons.most_common():
        if cnt >= 2:
            proposals.append(
                f"- **新增治理铁律候选**（失败类别「{cat}」复现 {cnt} 次）：\n"
                f"  建议写入 `governance.md` 或 `ver-agent.md` 自检清单，明确该类别的强制核查项与来源标注要求。\n"
                f"  证据：run-log 中 {cnt} 条 reject，reason 含「{cat}」。"
            )
    if gap_hits:
        proposals.append(
            f"- **新增 knowledge-index 条目候选**（{len(gap_hits)} 处知识缺口）：\n"
            f"  对 doc-in 反复抽到的无库条目主题，新增「待核实」索引项，走 PR 核验时效后入正文。"
        )
    if len(changes) >= 2:
        proposals.append(
            f"- **SOP 回写候选**（{len(changes)} 次变更 v<N> 被采纳）：\n"
            f"  提炼共性变更模式，写回团长 §6.2 版本纪律作为确定性步骤，减少重复判定成本。"
        )
    stats = {"reject_categories": dict(reasons), "gap_hits": len(gap_hits),
             "adopted_changes": len(changes), "proposals": len(proposals)}
    return proposals, stats


def main():
    ap = argparse.ArgumentParser(description="进化闭环 meta 化：经验→知识提案")
    ap.add_argument("--run-log", required=True)
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        events = load_events(args.run_log)
    except (ValueError, FileNotFoundError) as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 2
    props, stats = propose(events)
    md = "# 进化 meta 提案（governance PR 就绪·须异源审核）\n\n"
    md += f"> 来源 run-log：{os.path.basename(args.run_log)} ｜ 事件数 {len(events)}\n\n"
    md += "\n".join(props) if props else "_本次轨迹未识别到可沉淀信号（无需变更）。_"
    md += f"\n\n---\n**stats**：{json.dumps(stats, ensure_ascii=False)}"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[proposals] -> {args.out}")
    elif args.json:
        print(json.dumps({"stats": stats, "proposals": props}, ensure_ascii=False, indent=2))
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
