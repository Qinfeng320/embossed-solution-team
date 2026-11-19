#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dynamic_router.py —— 评估驱动动态选型：工作流 ↔ 自主 降级/升级路由（P1-①·对齐《AI Agent》Ch.1.2 编排模式 / Ch.10.2 多 Agent 优于单 Agent 判据 / Ch.6.6 评估驱动选型）

设计边界（诚实标注）：
  团长 §6.5 已有「评估驱动动态选型」占位（前置依赖 SOP 评估数据集）。本脚本把该决策做成
  **可独立调用的确定性路由**，使团长在调度前先算一次：简单单点任务走「自主单 Agent」、
  复杂/高后果/含外部承诺任务走「Manager 工作流 + 双 ver」。

  判据（呼应 Ch.10.2：协作仅在引入新信息时才优于单 Agent）：
    - 路由=workflow 触发信号：① 含对外承诺/报价/红线（高后果）；② 多维交叉（≥2 成员事实底座）；
      ③ 含数字一致性/预算；④ 客户未确认前提多；⑤ 经 sop_eval 历史表示该成员在高后果场景错误率高。
    - 路由=autonomous 触发信号：单角色、纯格式/解析/单点研判、无对外承诺、无数字。

用法：
  python dynamic_router.py --member <id> --task "..." [--history-error-rate 0.0] [--json]

退出码：0 正常 ｜ 2 用法错误（路由结果走 stdout/JSON）
"""
import sys, os, json, argparse, re

# 高后果/承诺类信号
HIGH_STAKES = [r"报价", r"预算", r"承诺", r"外发", r"投标", r"发信", r"红线", r"合规",
               r"客户版", r"定稿", r"不可撤回", r"法律", r"合同"]
# 弱信号（可自主）
LOW_STAKES = [r"解析", r"结构化", r"读懂", r"趋势", r"判断", r"画像", r"行业", r"政策依据"]


def route(member, task, history_error_rate=0.0):
    t = task or ""
    hits_high = [p for p in HIGH_STAKES if re.search(p, t)]
    # 多维交叉：任务提及多个成员事实底座关键词
    cross_dims = len(re.findall(r"(预算|架构|案例|产品|政策|行业|客户|数据|文档)", t))
    multi_dim = cross_dims >= 2
    high_history = history_error_rate >= 0.15
    workflow = bool(hits_high) or multi_dim or high_history
    if workflow:
        reason = []
        if hits_high:
            reason.append(f"含高后果信号：{hits_high}")
        if multi_dim:
            reason.append(f"多维交叉（{cross_dims} 维事实底座）")
        if high_history:
            reason.append(f"历史错误率 {history_error_rate:.0%}≥15%")
        return {"route": "workflow", "ver_required": True, "member": member,
                "reason": "；".join(reason), "dual_ver": bool(hits_high)}
    return {"route": "autonomous", "ver_required": False, "member": member,
            "reason": "单点/低后果任务，按 Ch.10.2 单 Agent 更优（无新信息需协作）",
            "dual_ver": False}


def main():
    ap = argparse.ArgumentParser(description="动态选型路由决策")
    ap.add_argument("--member", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--history-error-rate", type=float, default=0.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = route(args.member, args.task, args.history_error_rate)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"[route] {res['route']} ｜ ver={res['ver_required']} ｜ dual_ver={res['dual_ver']}")
        print(f"  原因：{res['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
