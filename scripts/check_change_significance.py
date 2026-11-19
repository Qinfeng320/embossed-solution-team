#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_change_significance.py — 变更 v<N> 统计显著性闸（可执行版）

对齐《AI Agent》第 6 章 §6.7「统计显著性」：变更 / 版本切换 / 口径调整带来的"差异"
须先确认 **超过噪声带宽且可复现**（配对分析成立、非单次随机波动），才值得据此发布
改动或切换；低于噪声的微小差异标「待观察（NOISE）」而非立即采纳，避免把抽样噪声当改进。

设计意图：把团队 §6.2「噪声闸」从方法论声明变成可一键运行的决策器。团长在处理变更
v<N>、或 ver 在核验"版本一致性/数值漂移"时，先跑本脚本拿到 PASS / HOLD 判定，再决定
是否把变更合入交接物。与 `check_budget_consistency.py`（内部自洽闸）互为补充：
  - check_budget_consistency.py → 数字"对不对得上"
  - check_change_significance.py → 数字"变了多少、是不是真的变、能不能复现"

用法：
  python check_change_significance.py \
      --baseline baseline.json \
      --candidate candidate.json \
      [--samples-dir candidate_runs/]      # 内含 ≥2 个候选样本 → 可复现性检验
      [--noise-rel 0.01] [--noise-abs 0.0] [--cv-thresh 0.05] [--json]

输入格式（两种都接受）：
  - JSON：{"一期预算下限": 410, "一期预算上限": 1170, ...}
  - 行式 md/json：每行 "字段: 数字" 或 "字段 = 数字"（自动忽略单位与千分位逗号）

判定逻辑：
  SAMPLE 级（baseline vs candidate）：
    - 对每个共同字段计算 |Δ_rel| 与 |Δ_abs|
    - SIGNIFICANT  ⇔ |Δ_rel| > noise_rel  且  |Δ_abs| > noise_abs
    - NOISE        ⇔ 否则（差异落在噪声带内）
  REPRO 级（仅当 --samples-dir 提供且含 ≥2 样本）：
    - 对每个字段跨样本算变异系数 CV = stdev / |mean|
    - CV > cv_thresh → NOT_REPRODUCIBLE（单次波动，不可信）
  VERDICT：
    - 存在任一字段 SIGNIFICANT 且（无样本 OR 该字段 REPRODUCIBLE）→ PASS（采纳变更 v<N>）
    - 否则 → HOLD（待观察，不立即采纳）

退出码：
  0 = PASS（差异真实且可复现，可采纳变更 v<N>）
  1 = HOLD（差异在噪声内或不可复现，标「待观察」）
  2 = 用法 / 解析错误
"""
import sys
import os
import re
import argparse
import json
import statistics


# ---------- 解析：从文件读出 {field: float} ----------
_LINE_RE = re.compile(r"([^\n:=]+?)[\s:=]+(-?\d[\d,]*\.?\d*)")


def _load_pairs(path):
    """读取 JSON 或行式文本，返回 {字段: 浮点数}。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            out = {}
            for k, v in data.items():
                if isinstance(v, (int, float)):
                    out[str(k).strip()] = float(v)
            if out:
                return out
    except json.JSONDecodeError:
        pass
    # 行式回退：捕获 "字段: 数字" / "字段 = 数字"
    out = {}
    for m in _LINE_RE.finditer(raw):
        field = m.group(1).strip().rstrip("：:，,）。)】]")
        try:
            val = float(m.group(2).replace(",", ""))
        except ValueError:
            continue
        if field:
            out[field] = val
    return out


def _load_samples(dir_path):
    """读取 samples-dir 下所有 .json/.md/.txt，返回 [{field:float}, ...]。"""
    samples = []
    for fn in sorted(os.listdir(dir_path)):
        if fn.endswith((".json", ".md", ".txt")):
            fp = os.path.join(dir_path, fn)
            pairs = _load_pairs(fp)
            if pairs:
                samples.append(pairs)
    return samples


def _cv(values):
    """变异系数；样本不足 2 返回 None。"""
    if len(values) < 2:
        return None
    mean = statistics.fmean(values)
    if abs(mean) < 1e-9:
        return None
    return statistics.stdev(values) / abs(mean)


def main():
    ap = argparse.ArgumentParser(description="变更 v<N> 统计显著性闸")
    ap.add_argument("--baseline", required=True, help="基线版本数值文件 (json / 行式 md)")
    ap.add_argument("--candidate", required=True, help="候选版本数值文件 (json / 行式 md)")
    ap.add_argument("--samples-dir", default=None,
                    help="候选多次运行样本目录（≥2 个文件）→ 可复现性检验")
    ap.add_argument("--noise-rel", type=float, default=0.01,
                    help="相对噪声带宽，默认 0.01 (1%%)")
    ap.add_argument("--noise-abs", type=float, default=0.0,
                    help="绝对噪声带宽，默认 0.0（仅作下限，不单独阻断）")
    ap.add_argument("--cv-thresh", type=float, default=0.05,
                    help="变异系数阈值，默认 0.05 (5%%)，超则为不可复现")
    ap.add_argument("--json", action="store_true", help="同时输出 JSON 结果")
    args = ap.parse_args()

    try:
        base = _load_pairs(args.baseline)
        cand = _load_pairs(args.candidate)
    except OSError as e:
        sys.stderr.write(f"[ERROR] 无法读取文件: {e}\n")
        return 2

    if not base or not cand:
        sys.stderr.write("[ERROR] baseline 或 candidate 未解析出任何数值字段\n")
        return 2

    samples = _load_samples(args.samples_dir) if args.samples_dir else []
    has_repro = len(samples) >= 2

    fields = sorted(set(base) & set(cand))
    only_base = sorted(set(base) - set(cand))
    only_cand = sorted(set(cand) - set(base))

    rows = []
    pass_flag = False
    for fld in fields:
        b, c = base[fld], cand[fld]
        delta_abs = c - b
        delta_rel = (delta_abs / b) if abs(b) > 1e-9 else float("inf")
        significant = (abs(delta_rel) > args.noise_rel) and (abs(delta_abs) > args.noise_abs)
        # 可复现性
        reproducible = None
        cv = None
        if has_repro:
            vals = [s.get(fld) for s in samples if s.get(fld) is not None]
            cv = _cv(vals)
            reproducible = (cv is None) or (cv <= args.cv_thresh)
        # 该字段是否构成"可采纳的真实变更"
        adoptable = significant and (reproducible is not True if has_repro else True)
        # 注：无样本时 reproducible=None，视为"无反证即可采纳"
        if significant and (not has_repro or reproducible):
            pass_flag = True
        rows.append({
            "field": fld,
            "baseline": b,
            "candidate": c,
            "delta_abs": round(delta_abs, 4),
            "delta_rel": (round(delta_rel, 6) if abs(delta_rel) != float("inf") else None),
            "significant": significant,
            "reproducible": reproducible,
            "cv": (round(cv, 6) if cv is not None else None),
            "verdict": ("SIGNIFICANT" if significant else "NOISE")
                       + ("" if not has_repro else ("/REPRO" if reproducible else "/NON-REPRO")),
        })

    verdict = "PASS" if pass_flag else "HOLD"
    exit_code = 0 if pass_flag else 1

    # ---------- Markdown 报告 ----------
    lines = []
    lines.append("# 变更 v<N> 统计显著性闸报告")
    lines.append("")
    lines.append(f"- 判定（VERDICT）：**{verdict}** "
                 f"（{'可采纳变更 v<N>' if verdict == 'PASS' else '标「待观察」，暂不采纳'}）")
    lines.append(f"- 噪声带宽：相对 {args.noise_rel:.2%} / 绝对 {args.noise_abs}")
    lines.append(f"- 可复现检验：{'启用（'+str(len(samples))+' 个样本, CV≤'+str(args.cv_thresh)+'）' if has_repro else '未提供样本（仅单点配对）'}")
    lines.append(f"- 共同字段 {len(fields)} 个；仅 baseline {len(only_base)} 个；仅 candidate {len(only_cand)} 个")
    lines.append("")
    lines.append("| 字段 | 基线 | 候选 | Δ_abs | Δ_rel | 超噪声? | 可复现? | CV | 判定 |")
    lines.append("|------|------|------|-------|-------|---------|---------|-----|------|")
    for r in rows:
        lines.append(
            f"| {r['field']} | {r['baseline']} | {r['candidate']} | {r['delta_abs']} | "
            f"{('-' if r['delta_rel'] is None else r['delta_rel'])} | "
            f"{'是' if r['significant'] else '否'} | "
            f"{('-' if r['reproducible'] is None else ('是' if r['reproducible'] else '否'))} | "
            f"{('-' if r['cv'] is None else r['cv'])} | {r['verdict']} |"
        )
    if only_base:
        lines.append("")
        lines.append(f"- 仅 baseline 存在（候选缺失）：{', '.join(only_base)}")
    if only_cand:
        lines.append(f"- 仅 candidate 存在（新增字段）：{', '.join(only_cand)}")
    lines.append("")
    lines.append("> 依据《AI Agent》§6.7：低于噪声或不可复现的微小差异标「待观察」而非立即采纳。")
    report = "\n".join(lines)
    sys.stdout.write(report + "\n")

    if args.json:
        sys.stdout.write("\n---JSON---\n")
        sys.stdout.write(json.dumps({
            "verdict": verdict,
            "noise_rel": args.noise_rel,
            "noise_abs": args.noise_abs,
            "has_repro": has_repro,
            "fields": rows,
        }, ensure_ascii=False, indent=2) + "\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
