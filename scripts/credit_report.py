#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会话积分消耗报告（PR-031）：按模型归集团员积分与全链 token 用量。

数据来源（本地第一手，无需联网）：
  ~/.workbuddy/projects/<项目目录>/<会话ID>.jsonl          主会话转录
  ~/.workbuddy/projects/<项目目录>/<会话ID>/subagents/*.jsonl  各团员转录

归属规则：
  1. 团员识别：主转录中 providerData.teammateMessage.from 的消息事件＝各团员完成标记（带时间戳）；
  2. 转录关联：每个团员转录按时间窗（上一团员完成标记之后、本团员完成标记之前＋宽限期）对应到团员；
  3. 积分归属：credit-usage 事件（来源=team_member，带数值与时间戳）按同样的时间窗归到团员，
     团员所用模型取自其转录的 requestModelName；
  4. 团员顺序运行时归属精确；并行运行的记「未归属」，如实呈现不猜。

已知边界（如实标注，不掩盖）：
  - 平台对团员请求逐笔记账（credit-usage 事件），但团长自身请求的积分不逐笔写入会话转录——
    团长自身消耗以账单为准，本工具只统计 token 用量供参考；
  - credit-usage 事件不带模型名，模型信息来自团员转录关联（上述规则 2/3）。

用法：
  python scripts/credit_report.py                      # 自动定位当前项目的最新会话
  python scripts/credit_report.py --transcript <path>  # 指定主转录 jsonl
  python scripts/credit_report.py --json               # 机器可读输出
  python scripts/credit_report.py --all                # 项目下全部会话汇总
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime

GRACE_SECONDS = 90  # 完成标记后的宽限（尾笔计费晚于最后消息）


def _pdir_to_project_dir(cwd):
    """把 Windows 工作目录映射为 .workbuddy/projects 下的项目目录名。
    例：E:\\BaiduSyncdisk\\示例客户名\\售前专家团 -> e-BaiduSyncdisk-示例客户名-售前专家团
    """
    cwd = cwd.replace("\\", "/").rstrip("/")
    drive, _, rest = cwd.partition(":")
    if not rest:
        return None
    return (drive.lower() + "-" + rest.lstrip("/")).replace("/", "-")


def resolve_transcripts(args):
    home = os.path.expanduser("~/.workbuddy/projects")
    if args.transcript:
        return [args.transcript]
    proj = _pdir_to_project_dir(os.getcwd())
    cand = os.path.join(home, proj) if proj else None
    sessions = []
    if cand and os.path.isdir(cand):
        sessions = sorted(glob.glob(os.path.join(cand, "*.jsonl")), key=os.path.getmtime)
    if not sessions:
        # 兜底：全项目目录找最近修改的会话
        sessions = sorted(glob.glob(os.path.join(home, "*", "*.jsonl")), key=os.path.getmtime)
    if not sessions:
        sys.exit("未找到任何会话转录；请用 --transcript 指定路径。")
    if args.all:
        return sessions
    return [sessions[-1]]


def parse_file(path):
    """读取一个转录文件，返回 (teammate_msg_markers, credit_events, token_by_model, req_ids)"""
    markers, credits, tokens = [], [], {}
    req_models = {}
    with open(path, encoding="utf-8") as f:
        for ln in f:
            try:
                d = json.loads(ln)
            except Exception:
                continue
            pd = d.get("providerData") or {}
            ts = d.get("timestamp")
            tm = pd.get("teammateMessage")
            if isinstance(tm, dict) and tm.get("from") and d.get("type") == "message":
                markers.append((ts, tm["from"]))
            if d.get("type") == "credit-usage":
                credits.append((ts, float(pd.get("credit") or 0), pd.get("source") or ""))
            rid = pd.get("conversationRequestId")
            if rid and pd.get("requestModelName"):
                req_models[rid] = pd["requestModelName"]
            u = pd.get("usage")
            if u and pd.get("requestModelName"):
                m = pd["requestModelName"]
                t = tokens.setdefault(m, {"in": 0, "out": 0, "cached": 0, "reqs": 0, "msgs": 0})
                t["in"] += u.get("inputTokens", 0)
                t["out"] += u.get("outputTokens", 0)
                for det in (u.get("inputTokensDetails") or []):
                    t["cached"] += det.get("cached_tokens", 0)
                t["reqs"] += u.get("requests", 0)
                t["msgs"] += 1
    return markers, credits, tokens, req_models


def build_report(main_path):
    sess_dir = os.path.splitext(main_path)[0]
    sub_files = sorted(glob.glob(os.path.join(sess_dir, "subagents", "*.jsonl")))
    markers, credits, lead_tokens, _ = parse_file(main_path)
    markers.sort()

    # 团员时间窗：[上一完成标记, 本完成标记 + 宽限]
    windows = []
    prev = 0
    for ts, name in markers:
        windows.append({"name": name, "start": prev, "end": ts + GRACE_SECONDS * 1000})
        prev = ts

    # 团员转录 -> 团员（按其时间范围落进哪个窗口）
    sub_info = {}  # name -> {model, tokens}
    for sf in sub_files:
        _, _, tokens, req_models = parse_file(sf)
        # 该文件的时间范围：用 markers 无、直接读时间戳范围
        ts_list = []
        with open(sf, encoding="utf-8") as f:
            for ln in f:
                try:
                    d = json.loads(ln)
                except Exception:
                    continue
                if d.get("timestamp"):
                    ts_list.append(d["timestamp"])
        if not ts_list:
            continue
        lo, hi = min(ts_list), max(ts_list)
        owner = None
        for w in windows:
            if lo >= w["start"] and hi <= w["end"]:
                owner = w["name"]
                break
        if owner is None:  # 兜底：取完成标记晚于其最后消息的最近窗口
            later = [w for w in windows if w["end"] >= hi]
            owner = later[0]["name"] if later else "未归属"
        models = sorted(set(req_models.values()))
        model = models[0] if len(models) == 1 else ("+".join(models) if models else "未知")
        info = sub_info.setdefault(owner, {"model": model, "tokens": {}, "file": os.path.basename(sf)})
        for m, t in tokens.items():
            acc = info["tokens"].setdefault(m, {"in": 0, "out": 0, "cached": 0, "reqs": 0, "msgs": 0})
            for k in ("in", "out", "cached", "reqs", "msgs"):
                acc[k] += t[k]
        if models and info["model"] in ("未知",):
            info["model"] = model

    # 积分归团：时间窗归属
    credit_by_member = {}
    unassigned = []
    for ts, c, src in credits:
        owner = None
        for w in windows:
            if w["start"] <= ts <= w["end"]:
                owner = w["name"]
                break
        if owner is None:
            unassigned.append((ts, c))
            continue
        e = credit_by_member.setdefault(owner, {"credit": 0.0, "n": 0})
        e["credit"] += c
        e["n"] += 1

    # 积分按模型聚合
    credit_by_model = {}
    for name, e in credit_by_member.items():
        m = sub_info.get(name, {}).get("model", "未知")
        a = credit_by_model.setdefault(m, {"credit": 0.0, "n": 0, "members": []})
        a["credit"] += e["credit"]
        a["n"] += e["n"]
        a["members"].append(f"{name}（{e['credit']:.2f}/{e['n']}笔）")
    total = sum(a["credit"] for a in credit_by_model.values()) + sum(c for _, c in unassigned)

    return {
        "session": os.path.basename(main_path),
        "session_mtime": datetime.fromtimestamp(os.path.getmtime(main_path)).strftime("%Y-%m-%d %H:%M"),
        "members": sub_info,
        "credit_by_model": credit_by_model,
        "unassigned": unassigned,
        "lead_tokens": lead_tokens,
        "total_credit": total,
    }


def fmt_tokens(t):
    cin = t["in"] / 1e6
    cout = t["out"] / 1e3
    ccache = t["cached"] / 1e6
    return f"输入 {cin:.2f}M（缓存命中 {ccache:.2f}M）· 输出 {cout:.1f}K · {t['reqs']} 次请求"


def render_text(r):
    L = []
    L.append(f"积分消耗报告 · 会话 {r['session'][:18]}…（最后活动 {r['session_mtime']}）")
    L.append("=" * 56)
    if r["credit_by_model"]:
        L.append("团员积分（平台逐笔记账 · 时间窗归属）")
        for m, a in sorted(r["credit_by_model"].items(), key=lambda x: -x[1]["credit"]):
            L.append(f"  {m:<22} {a['credit']:>8.2f} 积分（{a['n']} 笔）｜{'、'.join(a['members'])}")
        if r["unassigned"]:
            L.append(f"  未归属（并行期）        {sum(c for _, c in r['unassigned']):>8.2f} 积分（{len(r['unassigned'])} 笔）")
        L.append(f"  合计                    {r['total_credit']:>8.2f} 积分")
    else:
        L.append("本会话无团员积分记录（未派发成员或平台未记账）。")
    L.append("")
    L.append("Token 用量（按模型）")
    for m, t in sorted(r["lead_tokens"].items(), key=lambda x: -x[1]["in"]):
        L.append(f"  [团长] {m:<18} {fmt_tokens(t)}")
    for name, info in r["members"].items():
        for m, t in sorted(info["tokens"].items(), key=lambda x: -x[1]["in"]):
            L.append(f"  [{name}] {m:<17} {fmt_tokens(t)}")
    L.append("")
    L.append("说明：团长自身请求的积分平台不逐笔记入会话转录，以账单为准；"
             "并行运行期的积分无法按时间窗唯一归属时记「未归属」，不猜。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="会话积分消耗报告（按模型归集团员积分与 token 用量）")
    ap.add_argument("--transcript", help="主转录 jsonl 路径（默认自动定位当前项目最新会话）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--all", action="store_true", help="项目下全部会话逐个报告")
    args = ap.parse_args()
    for path in resolve_transcripts(args):
        r = build_report(path)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(render_text(r))
            print()


if __name__ == "__main__":
    main()
