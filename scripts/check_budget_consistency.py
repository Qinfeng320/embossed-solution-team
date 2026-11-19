#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_budget_consistency.py — 预算数字一致性自动闸

针对预算文档(如 dat_budget.md)做：
  1. 内部自洽：一期 + 二期 [+ 三期] == 合计（上/下限分别校验）
     - 自动识别「两期项目」(医疗：仅一期+二期)与「三期项目」(教育/制造)
  2. 合规前置专项提示（信息级，不阻断）
  3. (可选)跨文件比对：扫描 --compare 文件中的预算数字，与权威 dat 不一致则提示
     （比对文件可能故意保留旧数作为告警，故仅提示、不计入 passed）

设计意图：落实"以磁盘 dat_budget.md 为唯一事实底座"。本次曾出现子 agent 后台落盘覆盖
预算、团长 prompt 内旧值未刷新的版本冲突，靠人工重读磁盘救回。本脚本作为 ver 阶段前的
自动闸，把"人工核对"变成"机器校验"。

提取可靠性原则（避免误报）：
  - 只认「带万区间」(如 "410 – 1170 万元")，排除周期"6–9 月"、年份、分项无万数字。
  - 兼容 markdown 表格小计/合计行（如 "| **一期小计** | | **410** | **1170** |"）。
  - 两期项目无独立"合计"行时，由一期+二期求和派生合计再校验。

用法：
  python check_budget_consistency.py --dat <dat_budget.md> \
      [--compare mat_narrative.md arc_architecture.md] [--json]
退出码：0 = 内部自洽通过，1 = 内部自洽存在告警
"""
import sys
import os
import re
import argparse
import json

PHASES = ["一期", "二期", "三期"]
WAN = r"(\d[\d,]*)\s*[–\-~]\s*(\d[\d,]*)"  # 范围（不带单位）


def _to_int(s):
    return int(str(s).strip("*").replace(",", ""))


def _extract_all_ranges(text):
    """返回 {phase: [(lo, hi), ...]}，含行内带万区间 + markdown 表格小计/合计行。"""
    result = {p: [] for p in PHASES + ["合计"]}
    lines = text.splitlines()
    # 1) 行内区间带「万」——仅当阶段词与"预算区间/合计区间"同现时提取，
    #    排除分项行(如"二期...注册 300–700 万")、周期、年份的干扰
    for ph in PHASES + ["合计"]:
        kw = "预算区间" if ph != "合计" else "合计区间"
        for line in lines:
            if ph in line and kw in line:
                m = re.search(WAN + r"\s*万", line)
                if m:
                    result[ph].append((_to_int(m.group(1)), _to_int(m.group(2))))
                    break
    # 2) markdown 表格小计/合计行：取该行最后两个纯数字单元格
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        label = cells[0]
        nums = [c for c in cells if re.fullmatch(r"\*{0,2}\d[\d,]*\*{0,2}", c)]
        matched = None
        for ph in PHASES:
            if ph in label and ("小计" in label or "合计" in label):
                matched = ph
                break
        if matched is None and "合计" in label and "小计" not in label:
            matched = "合计"
        if matched and len(nums) >= 2:
            lo = _to_int(nums[-2])
            hi = _to_int(nums[-1])
            if (lo, hi) not in result[matched]:
                result[matched].append((lo, hi))
    return result


def _authoritative(ranges_all):
    """每个阶段取第一个候选作为权威范围。"""
    return {k: v[0] for k, v in ranges_all.items() if v}


def _derive_total(ranges):
    """两期项目无独立合计时，由一期+二期求和派生（标记 _derived_total）。"""
    if "合计" not in ranges and "一期" in ranges and "二期" in ranges:
        ranges["合计"] = (
            ranges["一期"][0] + ranges["二期"][0],
            ranges["一期"][1] + ranges["二期"][1],
        )
        ranges["_derived_total"] = True
    return ranges


def _check_internal(ranges):
    issues = []
    has3 = "三期" in ranges
    if has3 and all(p in ranges for p in ["一期", "二期", "三期", "合计"]):
        lo = ranges["一期"][0] + ranges["二期"][0] + ranges["三期"][0]
        hi = ranges["一期"][1] + ranges["二期"][1] + ranges["三期"][1]
        if lo != ranges["合计"][0]:
            issues.append(f"合计下限 {ranges['合计'][0]} ≠ 一期+二期+三期下限 {lo}")
        if hi != ranges["合计"][1]:
            issues.append(f"合计上限 {ranges['合计'][1]} ≠ 一期+二期+三期上限 {hi}")
    elif not has3 and all(p in ranges for p in ["一期", "二期", "合计"]):
        lo = ranges["一期"][0] + ranges["二期"][0]
        hi = ranges["一期"][1] + ranges["二期"][1]
        if lo != ranges["合计"][0]:
            issues.append(f"合计下限 {ranges['合计'][0]} ≠ 一期+二期下限 {lo}")
        if hi != ranges["合计"][1]:
            issues.append(f"合计上限 {ranges['合计'][1]} ≠ 一期+二期上限 {hi}")
    else:
        missing = [p for p in (["一期", "二期"] + (["三期"] if has3 else []) + ["合计"]) if p not in ranges]
        issues.append(f"[信息] 未能完整提取阶段范围，缺失: {missing}；请人工确认预算数字。")
    return issues


def _check_crossfile(dat_ranges, compare_paths):
    """弱校验：仅确认 dat 权威数字是否被比对文件引用（出现在任意带万区间中）。
    比对文件可能故意保留旧数作告警，故不做严格按阶段对齐，避免误报；仅信息提示。"""
    info = []
    for p in compare_paths:
        if not os.path.exists(p):
            info.append(f"比对文件不存在: {p}")
            continue
        with open(p, "r", encoding="utf-8") as f:
            txt = f.read()
        all_ranges = _extract_all_ranges(txt)
        union = set()
        for v in all_ranges.values():
            union.update(v)
        for ph in PHASES + ["合计"]:
            if ph not in dat_ranges:
                continue
            dat_v = dat_ranges[ph]
            if dat_v in union:
                info.append(f"{p} 中含与权威 dat 一致的 {ph} 数字 {dat_v}（弱校验通过，归属由人工确认）")
            else:
                info.append(f"{p} 中未找到与权威 dat 一致的 {ph} 数字 {dat_v}（请人工确认）")
    return info


def main():
    ap = argparse.ArgumentParser(description="预算数字一致性自动闸")
    ap.add_argument("--dat", required=True, help="权威预算文档(dat_budget.md)路径")
    ap.add_argument("--compare", nargs="*", help="需比对一致性的其他产物(mat_narrative.md / arc_architecture.md 等)")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    with open(args.dat, "r", encoding="utf-8") as f:
        dat_text = f.read()
    dat_all = _extract_all_ranges(dat_text)
    dat_ranges = _derive_total(_authoritative(dat_all))
    issues = _check_internal(dat_ranges)
    info = []
    if args.compare:
        info = _check_crossfile(dat_ranges, args.compare)

    # passed 仅取决于 dat 内部自洽；跨文件比对仅信息提示
    report = {
        "dat": args.dat,
        "phase_model": "三期" if "三期" in dat_ranges else "两期",
        "extracted_ranges": {k: v for k, v in dat_ranges.items() if k != "_derived_total"},
        "derived_total": dat_ranges.get("_derived_total", False),
        "internal_issues": issues,
        "crossfile_info": info,
        "passed": len([x for x in issues if not x.startswith("[信息]")]) == 0,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[check_budget] 期数模型: {report['phase_model']}"
              f"{' (合计由两期求和派生)' if report['derived_total'] else ''}")
        print(f"[check_budget] 提取范围: {report['extracted_ranges']}")
        if issues:
            print("[check_budget] 内部告警:")
            for x in issues:
                print("  - " + x)
        else:
            print("[check_budget] 内部自洽通过。")
        if info:
            print("[check_budget] 跨文件比对提示(需人工确认):")
            for x in info:
                print("  - " + x)
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
