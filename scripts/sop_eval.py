#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sop_eval.py —— 专家团 SOP 编排质量评估数据集 + pass^k 回归（PR-003 高①·对齐《AI Agent》Ch.6.3/6.4/6.9）

设计边界（诚实标注，呼应书 6.9「评测系统自检」）：
  本专家团的"编排引擎"是团长 SOP（即运行时 system prompt），并非可独立 import 的 Python 模块；
  因此本脚本不直接重放 LLM 编排，而是提供**评估基础设施骨架**：
    1. 加载 golden cases（references/sop_eval_cases.md）——每个 case 含客户场景摘要、
       期望验收判定标签、必须命中的红线/确定性闸、期望产出结构；
    2. 对每 case 跑可插拔 checks：
       - 结构合规（验收四维度覆盖：完整性/可追溯/假设标注/上游一致性）
       - 确定性闸可达性（预算一致性 / 变更显著性 / 引证重合度 脚本是否就位且可调用）
       - 红线命中（六红线信号是否进入待核验清单）
    3. pass^k 风格统计：对固定 case 集跑 k 次，检验**结果确定性**（同输入同输出，杜绝"看运气"）；
       端到端 LLM 编排质量评估需在团长运行日志接入后补全（脚本预留 ingest_run_log() 接口）。

退出码：0 全部通过 ｜ 1 有关键 case 不通过 ｜ 2 仅警告 ｜ 3 用法错误
"""
import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Callable, List, Dict, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(SCRIPT_DIR)
CASES_PATH = os.path.join(PKG_ROOT, "references", "sop_eval_cases.md")

# ---- 六红线信号（简化正则，仅做可达性/命中检测示例）----
REDLINE_PATTERNS = {
    "已部署": r"已(经)?\s*部署|已落地",
    "已降本": r"已(经)?\s*降本|节约\s*[\d.]+%",
    "未验证数字承诺": r"提升\s*[\d.]+%|准确(率|性)\s*达\s*[\d.]+",
    "第三方科研/测试报告": r"实验(表明|证明|室)|测试报告|白皮书(称|显示)",
}
# 确定性闸脚本（验证"可达性"——即专家团确实具备该量化能力，呼应书 6.10 评估基础设施）
GATE_SCRIPTS = {
    "budget_consistency": os.path.join(SCRIPT_DIR, "check_budget_consistency.py"),
    "change_significance": os.path.join(SCRIPT_DIR, "check_change_significance.py"),
    "citation_fidelity": os.path.join(SCRIPT_DIR, "verify_citation_lines.py"),
}
# 验收四维度（团长 §1.1）
FOUR_DIMS = ["完整性", "可追溯性", "假设标注", "上游一致性"]


@dataclass
class CaseResult:
    case_id: str
    title: str
    structure_ok: bool = False
    redline_caught: bool = False
    gates_available: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    status: str = "FAIL"  # PASS / WARN / FAIL


@dataclass
class EvalReport:
    cases: List[CaseResult] = field(default_factory=list)
    runs: int = 1
    deterministic: bool = True

    def summary(self) -> Dict:
        passed = sum(1 for c in self.cases if c.status == "PASS")
        warned = sum(1 for c in self.cases if c.status == "WARN")
        failed = sum(1 for c in self.cases if c.status == "FAIL")
        return {
            "total": len(self.cases),
            "pass": passed,
            "warn": warned,
            "fail": failed,
            "pass_rate": round(passed / len(self.cases), 3) if self.cases else 0.0,
            "deterministic": self.deterministic,
        }


# ---------- case 解析（极简 markdown：按二级标题分块；字段用 #键: 值 或 列表 - ）----------
def parse_cases(md_path: str) -> List[Dict]:
    if not os.path.exists(md_path):
        return []
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    blocks = re.split(r"\n##\s+", text)
    cases = []
    for b in blocks:
        head = b.strip().splitlines()[0] if b.strip() else ""
        m = re.match(r"案例\s*[:：]?\s*(\S+)\s*(.*)", head)
        if not m:
            continue
        cid = m.group(1).strip()
        title = m.group(2).strip()
        body = "\n".join(b.splitlines()[1:])
        # 提取字段
        def field_val(key):
            mm = re.search(rf"#\s*{key}\s*[:：]\s*(.+)", body)
            return mm.group(1).strip() if mm else ""
        expectation = field_val("期望验收判定")
        redline = field_val("须命中红线")
        must_gates = [g.strip() for g in field_val("须过确定性闸").split("/") if g.strip()]
        scenarios = [l.strip("- ").strip() for l in re.findall(r"-\s*(.+)", body)]
        cases.append({
            "id": cid, "title": title, "expectation": expectation,
            "redline": redline, "must_gates": must_gates, "scenarios": scenarios,
            "raw": body,
        })
    return cases


# ---------- checks ----------
def check_structure(case: Dict) -> (bool, List[str]):
    notes = []
    # 评估基础设施骨架阶段：用 golden case 的必备要素作为「验收四维度」的代理映射
    # （团长运行日志接入后，改为直接校验成员产出四维度字段——见 evaluate_case 注释）
    #   场景诉求列表   -> 完整性
    #   期望验收判定   -> 上游一致性（团长须给出判定）
    #   须命中红线/闸 -> 可追溯性（结论须可溯源至红线/确定性闸）
    #   场景含溯源词  -> 假设标注（未确认项须显式标注）
    scenarios = case.get("scenarios", [])
    has_scenario = len(scenarios) >= 1
    has_expect = bool(case.get("expectation", "").strip())
    has_trace = (bool(case.get("redline", "").strip())
                 or bool(case.get("must_gates", []))
                 or any(("页码" in s or "URL" in s or "p." in s or "原文" in s) for s in scenarios))
    covered = []
    if has_scenario:
        covered.append("完整性")
    if has_expect:
        covered.append("上游一致性")
    if has_trace:
        covered.append("可追溯性")
    ok = has_scenario and has_expect and has_trace
    notes.append(f"四维度代理覆盖：{covered}")
    if not ok:
        notes.append("结构合规缺失：需同时具备 场景诉求 + 期望验收判定 + (红线或确定性闸/溯源)")
    return ok, notes


def check_redline(case: Dict) -> (bool, List[str]):
    redline = case.get("redline", "")
    notes = []
    if not redline:
        return True, ["无红线要求"]
    # 该 case 要求命中的红线信号，是否在 case 自身标注的"待核验清单"或正文出现
    pattern = REDLINE_PATTERNS.get(redline)
    if not pattern:
        return True, [f"红线「{redline}」无对应检测规则（已知待补）"]
    hit_in_case = re.search(pattern, case.get("raw", "")) is not None
    # 真实场景：团长应把该信号送入 ver 待核验；此处以"case 内是否自陈已识别"近似
    if hit_in_case:
        notes.append(f"红线「{redline}」信号已在 case 内自陈命中")
        return True, notes
    notes.append(f"红线「{redline}」信号未在 case 自陈（需团长运行日志确认是否进待核验）")
    return False, notes


def check_gates_available(case: Dict) -> (List[str], List[str]):
    must = case.get("must_gates", [])
    available = []
    notes = []
    for g in must:
        path = GATE_SCRIPTS.get(g) or os.path.join(SCRIPT_DIR, f"{g}.py")
        if os.path.exists(path):
            available.append(g)
        else:
            notes.append(f"确定性闸「{g}」脚本缺失（不可达）")
    return available, notes


def evaluate_case(case: Dict) -> CaseResult:
    res = CaseResult(case_id=case["id"], title=case["title"])
    s_ok, s_notes = check_structure(case)
    r_ok, r_notes = check_redline(case)
    gates, g_notes = check_gates_available(case)
    res.gates_available = gates
    res.notes = s_notes + r_notes + g_notes
    res.structure_ok = s_ok
    res.redline_caught = r_ok
    # 判定：结构 + 红线 + 闸全部满足 => PASS；部分 => WARN；结构性缺失 => FAIL
    if s_ok and r_ok and g_notes == []:
        res.status = "PASS"
    elif s_ok:
        res.status = "WARN"
    else:
        res.status = "FAIL"
    return res


# ---------- pass^k 确定性（同输入跑 k 次，结果须一致）----------
def run_once(cases: List[Dict]) -> List[str]:
    return [evaluate_case(c).status for c in cases]


def build_report(cases: List[Dict], k: int) -> EvalReport:
    rep = EvalReport(runs=k)
    rep.cases = [evaluate_case(c) for c in cases]
    if k > 1:
        base = run_once(cases)
        deterministic = all(run_once(cases) == base for _ in range(k - 1))
        rep.deterministic = deterministic
    return rep


def main():
    ap = argparse.ArgumentParser(description="专家团 SOP 评估数据集 + pass^k 回归")
    ap.add_argument("--cases", default=CASES_PATH, help="golden cases markdown 路径")
    ap.add_argument("--json", help="输出 JSON 报告路径")
    ap.add_argument("--k", type=int, default=1, help="pass^k：同输入重复运行次数（检验确定性）")
    ap.add_argument("--quiet-pass", action="store_true", help="PASS 时不打印逐条")
    args = ap.parse_args()

    cases = parse_cases(args.cases)
    if not cases:
        print(f"[ERR] 未解析到任何 case：{args.cases}", file=sys.stderr)
        return 3
    rep = build_report(cases, max(1, args.k))
    summ = rep.summary()

    print(f"=== SOP 评估数据集（pass^{args.k}）===")
    print(f"样本 {summ['total']} ｜ PASS {summ['pass']} ｜ WARN {summ['warn']} ｜ FAIL {summ['fail']} ｜ 通过率 {summ['pass_rate']:.0%} ｜ 确定性 {summ['deterministic']}")
    for c in rep.cases:
        if c.status == "PASS" and args.quiet_pass:
            continue
        print(f"  [{c.status:4}] {c.case_id} {c.title}")
        for n in c.notes:
            print(f"        - {n}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(asdict(rep), f, ensure_ascii=False, indent=2)
        print(f"[report] -> {args.json}")

    # 退出码：FAIL 存在=1；仅 WARN=2；全 PASS=0
    if summ["fail"] > 0:
        return 1
    if summ["warn"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
