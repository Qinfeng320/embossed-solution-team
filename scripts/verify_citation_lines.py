#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_citation_lines.py —— 行号—原文重合度机器闸（governance §二.2「回原文铁律」的自动化实现）

背景
----
PR-001 异源复核中，B 组 Reviewer 捕获一处「张冠李戴」阻断项：
`mat-agent.md` §9-⑥「演示诚实契约」引用原文行 11781–11804，
但该区间实为「世界模型路线对比表」，与演示诚实毫无关系（真锚点 10783–10800）。

这类错误靠比对上游摘要永远发现不了，只有回原文逐条比对才抓得到。
governance.md §二.2 据此立「回原文铁律」，并登记本脚本把这道闸从人力降为机器。

判别原理（确定性，不依赖模型）
------------------------------
对每条形如「行 N–M」的引用：
  1. 取引用所在 markdown 行作为「声称的主题文本」；
  2. 取原文 N..M 行作为「实际被引内容」；
  3. 两者各自抽取 中文字符 2-gram + 英文/数字术语 token，算覆盖率
     coverage = |主题特征 ∩ 原文特征| / |主题特征|
  4. 覆盖率过低 = 声称主题与实际内容不相干 = 张冠李戴嫌疑。

同时校验结构性错误（越界 / 起止倒置 / 区间过宽吞并邻条）。

退出码
------
  0  全部 PASS（可合入）
  1  存在 ERROR（阻断级，禁止合入）
  2  仅存在 WARN（需人工判读）
  3  用法/环境错误

用法
----
  python scripts/verify_citation_lines.py --source <原文.txt> --scan <目录或文件> [...]
  python scripts/verify_citation_lines.py --self-test        # 用 B-1 已知正反例自检本脚本
  python scripts/verify_citation_lines.py ... --json out.json --calibrate
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from typing import Iterable

# ---- Windows 控制台 UTF-8 ----
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_SOURCE = "<项目目录>/archive/ai_agents_zh_text.txt"

# ---- 阈值（可由 --calibrate 依产线分布重新标定，勿拍脑袋改）----
PASS_COVERAGE = 0.18   # ≥ 判 PASS
WARN_COVERAGE = 0.08   # [WARN, PASS) 判 WARN；< 判 ERROR（张冠李戴嫌疑）
WIDE_SPAN = 130        # 区间跨度 > 此值判 WARN（过宽易吞并邻条，参见 PR-001 F4）
MIN_FEATURES = 4       # 主题特征少于此数则无法可靠判别，降级为 SKIP

# 覆盖率判别的最小样本量。span 小于此值时，被引原文仅 1~4 行（约 40~200 字），
# 而 markdown 主题句常是整条 bullet（含我方引申与落点说明），特征基数严重不对等，
# 覆盖率必然趋零 —— 此时的低覆盖率是「样本不足」而非「张冠李戴」。
# 首轮标定实测：single 引用 134/140 落入 ERROR，range 仅 16/125，证实为系统性伪阳性。
# 故 span < 此值者只做结构校验与弱信号提示，不判阻断（同「差异低于噪声带宽不采纳」纪律）。
MIN_SPAN_FOR_COVERAGE = 5

# 主引用：「行 12456–12540」「行 2211-2225」「行 6013—6018」
# 尾部 (?!\d) 必须保留：否则 \d{2,5} 贪婪失败后会回溯截断出错误数字。
RE_RANGE = re.compile(r"行\s*(\d{2,5})(?!\d)\s*[–—\-~]\s*(\d{2,5})(?!\d)")
# 单行引用：「行 10800」
#   (?!\d)                 —— 防回溯截断：曾因缺此断言，「行 13167–13171」被截出假引用 1316，
#                             再拿 1316 去比对原文（内容完全无关）而误报阻断。
#   (?!\s*[–—\-~]\s*\d)    —— 防把区间起点当单行引用。
RE_SINGLE = re.compile(r"行\s*(\d{2,5})(?!\d)(?!\s*[–—\-~]\s*\d)")
# 支撑子行：括号内裸行号「（10785–10786）」「(10800)」——仅在该行已有主引用时启用
RE_SUBLINE = re.compile(r"[（(]\s*(\d{4,5})(?:\s*[–—\-~]\s*(\d{4,5}))?\s*[）)]")

# 噪声：markdown 语法、章节锚点、版本号等，参与特征抽取前剔除
RE_NOISE = re.compile(
    r"§\s*\d+[\-–][①②③④⑤⑥⑦⑧⑨⑩a-zA-Z]*"   # §9-⑥ / §4-⑤a
    r"|v\d+\.\d+"                                # v1.1
    r"|Ch\.?\s*\d+(\.\d+)?"                      # Ch.5.1
    r"|行\s*\d[\d–—\-~\s]*"                      # 行号引用本体
    r"|\d+"                                      # 其余裸数字
    r"|[\*`_\[\]\(\)（）【】<>#|~]"               # markdown 标记
)

# 高频虚词 bigram：几乎在任何中文段落都命中，计入会虚高覆盖率
STOP_BIGRAMS = {
    "的的", "是的", "了的", "在的", "和的", "与的", "对应", "以及", "或者", "并且",
    "本团", "须在", "应当", "可以", "不得", "必须", "如果", "由于", "因此", "所以",
    "这个", "那个", "一个", "进行", "使用", "通过", "作为", "对于", "关于", "根据",
}

LEVEL_ORDER = {"ERROR": 0, "WARN": 1, "SKIP": 2, "PASS": 3}

# 行内豁免标记：用于「教学性反例引用」——即刻意引用一个错误锚点来作反面教材
# （如 governance §二.2 引 11781–11804 说明何为张冠李戴）。此类引用若被判错，
# 闸门就会逼着人删掉正确的教学内容，属典型的度量反噬。
RE_IGNORE = re.compile(r"<!--\s*cite-ignore\s*-->|〔反例引用〕")

# 自检清单条目：设计目标是「具体动作 + 可判定否决条件」，措辞必然是我方作业语言，
# 且常与原文隔着一层跨域引申（例：原文讲 TTS 填充词 → 我方落点为"不确定性显式标注"）。
# 对其套用与理论依据条目相同的覆盖率阈值必然伪阳性，故单列一档、只提示不阻断。
RE_CHECKLIST = re.compile(r"^\s*[-*]\s*\[[ xX]\]")


@dataclass
class Citation:
    file: str
    md_line: int
    kind: str            # "range" | "single" | "subline"
    start: int
    end: int
    context: str
    coverage: float = 0.0
    n_features: int = 0
    n_hit: int = 0
    term_total: int = 0        # 英文/数字术语数
    term_hit: int = 0
    level: str = "PASS"
    reason: str = ""
    sample_src: str = ""
    missing_terms: list = field(default_factory=list)


# ---------------- 特征抽取 ----------------

def _cjk_bigrams(text: str) -> set[str]:
    out: set[str] = set()
    for seg in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        for i in range(len(seg) - 1):
            bg = seg[i:i + 2]
            if bg not in STOP_BIGRAMS:
                out.add(bg)
    return out


def _terms(text: str) -> set[str]:
    """英文/数字术语 token（mock、fallback、Whisper、RTP、LoCoMo、Mem0 …）"""
    return {
        t.lower()
        for t in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}", text)
        if len(t) >= 3
    }


def extract_features(text: str, strip_noise: bool = False) -> tuple[set[str], set[str]]:
    src = RE_NOISE.sub(" ", text) if strip_noise else text
    return _cjk_bigrams(src), _terms(src)


# ---------------- 原文加载 ----------------

def load_source(path: str) -> list[str]:
    if not os.path.isfile(path):
        print(f"[ERR] 原文证据文件不存在：{path}", file=sys.stderr)
        sys.exit(3)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def slice_source(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1:end])


# ---------------- 引用扫描 ----------------

def scan_file(path: str, include_sublines: bool = True) -> list[Citation]:
    cits: list[Citation] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln, raw in enumerate(f.read().splitlines(), start=1):
            has_primary = False
            for m in RE_RANGE.finditer(raw):
                cits.append(Citation(path, ln, "range", int(m.group(1)), int(m.group(2)), raw.strip()))
                has_primary = True
            for m in RE_SINGLE.finditer(raw):
                v = int(m.group(1))
                cits.append(Citation(path, ln, "single", v, v, raw.strip()))
                has_primary = True
            if include_sublines and has_primary:
                for m in RE_SUBLINE.finditer(raw):
                    s = int(m.group(1))
                    e = int(m.group(2)) if m.group(2) else s
                    cits.append(Citation(path, ln, "subline", s, e, raw.strip()))
    return cits


# PR 归档目录：其中的行号引用是「某处曾引错」的审计留痕（如 PR-001 保留 B-1 的错锚点
# 11781–11804 作为历史记录），属正确存档而非引用主张，默认排除以免制造伪阳性。
DEFAULT_EXCLUDES = ("references/prs",)


def iter_md_files(targets: Iterable[str], excludes: Iterable[str] = ()) -> list[str]:
    ex = tuple(e.replace("\\", "/").rstrip("/") for e in excludes)

    def excluded(p: str) -> bool:
        n = os.path.normpath(p).replace("\\", "/")
        return any(e and (e in n) for e in ex)

    out: list[str] = []
    for t in targets:
        if os.path.isfile(t):
            if not excluded(t):
                out.append(t)
        elif os.path.isdir(t):
            for root, _dirs, files in os.walk(t):
                if "__pycache__" in root or os.sep + "." in root:
                    continue
                for fn in files:
                    if not fn.endswith(".md"):
                        continue
                    fp = os.path.join(root, fn)
                    if not excluded(fp):
                        out.append(fp)
    return sorted(set(out))


# ---------------- 评估 ----------------

def evaluate(cit: Citation, src_lines: list[str],
             pass_cov: float, warn_cov: float, wide_span: int) -> Citation:
    if RE_IGNORE.search(cit.context):
        cit.level, cit.reason = "SKIP", "行内标记豁免（教学性反例引用）"
        return cit

    total = len(src_lines)

    if cit.start < 1 or cit.end > total:
        cit.level, cit.reason = "ERROR", f"行号越界（原文共 {total} 行，引用 {cit.start}–{cit.end}）"
        return cit
    if cit.start > cit.end:
        cit.level, cit.reason = "ERROR", f"起止倒置（{cit.start} > {cit.end}）"
        return cit

    # 子行必须落在同一 markdown 行的主引用语境内，仅做越界校验，不重复算覆盖率
    if cit.kind == "subline":
        cit.level, cit.reason = "PASS", "支撑子行·范围有效"
        return cit

    ref_bg, ref_tm = extract_features(cit.context, strip_noise=True)
    ref_feat = ref_bg | ref_tm
    cit.n_features = len(ref_feat)
    cit.term_total = len(ref_tm)

    if cit.n_features < MIN_FEATURES:
        cit.level, cit.reason = "SKIP", f"主题特征过少（{cit.n_features}），无法可靠判别"
        return cit

    body = slice_source(src_lines, cit.start, cit.end)
    src_bg, src_tm = extract_features(body, strip_noise=False)
    src_feat = src_bg | src_tm

    hit = ref_feat & src_feat
    cit.n_hit = len(hit)
    cit.term_hit = len(ref_tm & src_tm)
    cit.coverage = cit.n_hit / cit.n_features
    cit.missing_terms = sorted(ref_tm - src_tm)[:6]
    cit.sample_src = re.sub(r"\s+", " ", body)[:110]

    span = cit.end - cit.start + 1

    # ---- 小样本降级：被引原文过短时，覆盖率不具统计判别力，只给弱信号 ----
    if span < MIN_SPAN_FOR_COVERAGE:
        if cit.coverage <= 0.0 and cit.term_total > 0 and cit.term_hit == 0:
            cit.level = "WARN"
            cit.reason = (f"单/短行引用（{span} 行）零命中：主题术语 "
                          f"{', '.join(cit.missing_terms[:3])} 均未出现，锚点可能偏移（需人工回原文）")
        else:
            cit.level = "PASS"
            cit.reason = (f"短行引用（{span} 行）·样本不足不做覆盖率阻断"
                          f"（实测重合 {cit.coverage:.0%}，术语 {cit.term_hit}/{cit.term_total}）")
        return cit

    is_checklist = bool(RE_CHECKLIST.match(cit.context))

    # ---- 张冠李戴判定：需 bigram 与术语「双低」才阻断 ----
    # 只要有任一专有术语在区间内命中，锚点大概率正确，降级为存疑交人工。
    if cit.coverage < warn_cov and cit.term_hit == 0:
        if is_checklist:
            cit.level = "WARN"
            cit.reason = (f"自检条目重合度 {cit.coverage:.0%} 极低。自检条目为作业动作描述，"
                          f"措辞脱离原文属预期；但若系跨域引申，须在条目内显式标注〔引申〕"
                          f"（与 PR-001 F1「引申与原文分离」同纪律），否则读者顺行号回查会不知所云")
        else:
            cit.level = "ERROR"
            cit.reason = (f"重合度 {cit.coverage:.0%} < {warn_cov:.0%} 且术语零命中"
                          f"（{cit.term_total} 个）—— 张冠李戴嫌疑：声称主题与该行区间实际内容不相干")
    elif cit.coverage < warn_cov:
        cit.level = "WARN"
        cit.reason = (f"重合度 {cit.coverage:.0%} 极低，但术语命中 {cit.term_hit}/{cit.term_total}"
                      f"，锚点疑似偏移而非错位，需人工回原文确认")
    elif cit.coverage < pass_cov:
        cit.level = "WARN"
        cit.reason = f"重合度 {cit.coverage:.0%} 偏低（阈值 {pass_cov:.0%}），锚点可能偏移或过宽"
    elif span > wide_span:
        cit.level = "WARN"
        cit.reason = f"区间跨度 {span} 行 > {wide_span}，易吞并邻条（参见 PR-001 F4），建议收窄"
    else:
        cit.level = "PASS"
        cit.reason = f"重合度 {cit.coverage:.0%}，术语命中 {cit.term_hit}/{cit.term_total}"
    return cit


# ---------------- 自检（评测系统自身可信度）----------------

SELF_TEST_CASES = [
    # (描述, 上下文, start, end, 期望等级)
    ("B-1 真锚点（应 PASS）",
     "演示诚实契约：实验验收禁用 mock、禁用连接提示音冒充真实链路、fallback 失败须如实暴露而非静默兜底、"
     "只记录用户确认、不虚构诊所已完成预约",
     10783, 10800, "PASS"),
    ("B-1 错锚点（应 ERROR，历史阻断项）",
     "演示诚实契约：实验验收禁用 mock、禁用连接提示音冒充真实链路、fallback 失败须如实暴露而非静默兜底、"
     "只记录用户确认、不虚构诊所已完成预约",
     11781, 11804, "ERROR"),
    ("越界（应 ERROR）", "任意主题文本用于越界校验测试内容", 99000, 99100, "ERROR"),
    ("倒置（应 ERROR）", "任意主题文本用于倒置校验测试内容", 900, 800, "ERROR"),
    # —— 以下为首轮标定后新增的伪阳性回归用例（防止修正误报时把真问题一并放过）——
    ("单行引用不得因样本不足被误判阻断（应 PASS/WARN，不得 ERROR）",
     "三级预算优先级阶梯：先问需要后训练吗，Harness 工程能解决就不训练；再 SFT 教格式与流程；"
     "最后 RL 提成效。旁路：缺事实性知识走继续预训练或 RAG。",
     9254, 9254, "PASS"),
    ("宽区间真锚点（应 PASS）",
     "虚拟文件系统四区：Scratchpad、Shared、Mounted、Built-in，按可见性与生命周期、读写权限、"
     "并发控制划分",
     12456, 12540, "PASS"),
]

# 单行用例允许 PASS 或 WARN（两者皆非阻断），只要不是 ERROR 即达成目的
SELF_TEST_NON_BLOCKING = {"单行引用不得因样本不足被误判阻断（应 PASS/WARN，不得 ERROR）"}


# 解析层回归用例：(原始文本, 期望解析出的 (kind, start, end) 集合)
PARSER_TEST_CASES = [
    ("行 13167–13171", {("range", 13167, 13171)}),          # 回溯 bug 会多出 ("single",1316,1316)
    ("行 12588–12594、7236–7238", {("range", 12588, 12594)}),
    ("（§9-⑥，行 10800）", {("single", 10800, 10800)}),
    ("行 2211-2225 与 行 3032—3036",
     {("range", 2211, 2225), ("range", 3032, 3036)}),
    ("禁用 mock（10800）、提示音（10785–10786）",              # 无主引用时不启用子行规则
     set()),
]


def run_parser_test() -> int:
    """校验行号解析器本身 —— 解析错了，后面所有比对都建立在幻觉引用上。"""
    print("-" * 78)
    print("解析层回归（防正则回溯截断出幻觉行号）")
    failed = 0
    for text, expect in PARSER_TEST_CASES:
        got = set()
        has_primary = False
        for m in RE_RANGE.finditer(text):
            got.add(("range", int(m.group(1)), int(m.group(2))))
            has_primary = True
        for m in RE_SINGLE.finditer(text):
            got.add(("single", int(m.group(1)), int(m.group(1))))
            has_primary = True
        if has_primary:
            for m in RE_SUBLINE.finditer(text):
                s = int(m.group(1))
                e = int(m.group(2)) if m.group(2) else s
                got.add(("subline", s, e))
        ok = got == expect
        failed += 0 if ok else 1
        print(f"  {'✓' if ok else '✗'} {text!r}")
        if not ok:
            print(f"      期望 {sorted(expect)}")
            print(f"      实得 {sorted(got)}")
    return failed


def run_self_test(src_lines: list[str]) -> int:
    print("=" * 78)
    print("自检：用 PR-001 已知正反例验证本脚本的判别力（评测系统自身也要被评测）")
    print("=" * 78)
    failed = run_parser_test()
    print("-" * 78)
    print("判别层回归（真锚点 / 张冠李戴 / 结构错误 / 小样本伪阳性）")
    for desc, ctx, s, e, expect in SELF_TEST_CASES:
        c = evaluate(Citation("<self-test>", 0, "range", s, e, ctx),
                     src_lines, PASS_COVERAGE, WARN_COVERAGE, WIDE_SPAN)
        ok = (c.level != "ERROR") if desc in SELF_TEST_NON_BLOCKING else (c.level == expect)
        failed += 0 if ok else 1
        mark = "✓" if ok else "✗"
        print(f"  {mark} {desc}")
        print(f"      行 {s}–{e} → {c.level}（期望 {expect}）｜ 重合度 {c.coverage:.1%}｜ {c.reason}")
    print("-" * 78)
    if failed:
        print(f"自检未通过：{failed} 项不符预期 —— 阈值或特征抽取需重新标定，此时脚本结论不可采信")
        return 1
    print("自检通过：脚本能稳定区分真锚点与已知张冠李戴案例")
    return 0


# ---------------- 标定辅助 ----------------

def print_calibration(cits: list[Citation]) -> None:
    vals = sorted(c.coverage for c in cits if c.kind != "subline" and c.level != "SKIP")
    if not vals:
        return
    def pct(p: float) -> float:
        return vals[min(len(vals) - 1, int(len(vals) * p))]
    print("\n【覆盖率分布 · 阈值标定依据（阈值须来自产线数据，不拍脑袋）】")
    print(f"  样本 {len(vals)} 条｜min {vals[0]:.1%}｜P5 {pct(.05):.1%}｜P25 {pct(.25):.1%}｜"
          f"中位 {pct(.5):.1%}｜P75 {pct(.75):.1%}｜max {vals[-1]:.1%}")
    print(f"  当前阈值：ERROR < {WARN_COVERAGE:.0%} ≤ WARN < {PASS_COVERAGE:.0%} ≤ PASS")


# ---------------- 主流程 ----------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="行号—原文重合度机器闸（governance §二.2 回原文铁律的自动化实现）")
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="原始证据文本文件")
    ap.add_argument("--scan", nargs="*", default=["agents", "references"],
                    help="待扫描的 .md 文件或目录")
    ap.add_argument("--json", dest="json_out", help="结果写入 JSON（供 CI 消费）")
    ap.add_argument("--pass-coverage", type=float, default=PASS_COVERAGE)
    ap.add_argument("--warn-coverage", type=float, default=WARN_COVERAGE)
    ap.add_argument("--wide-span", type=int, default=WIDE_SPAN)
    ap.add_argument("--no-sublines", action="store_true", help="不校验括号内支撑子行")
    ap.add_argument("--exclude", nargs="*", default=list(DEFAULT_EXCLUDES),
                    help="排除的路径片段（默认排除 references/prs 审计留痕）")
    ap.add_argument("--calibrate", action="store_true", help="输出覆盖率分布，用于标定阈值")
    ap.add_argument("--self-test", action="store_true", help="用已知正反例自检脚本判别力")
    ap.add_argument("--quiet-pass", action="store_true", help="只打印非 PASS 条目")
    args = ap.parse_args()

    src_lines = load_source(args.source)

    if args.self_test:
        return run_self_test(src_lines)

    files = iter_md_files(args.scan, args.exclude)
    if not files:
        print(f"[ERR] 未找到待扫描 .md：{args.scan}", file=sys.stderr)
        return 3

    cits: list[Citation] = []
    for fp in files:
        cits.extend(scan_file(fp, include_sublines=not args.no_sublines))

    for c in cits:
        evaluate(c, src_lines, args.pass_coverage, args.warn_coverage, args.wide_span)

    errors = [c for c in cits if c.level == "ERROR"]
    warns = [c for c in cits if c.level == "WARN"]
    skips = [c for c in cits if c.level == "SKIP"]
    passes = [c for c in cits if c.level == "PASS"]

    print("=" * 78)
    print(f"行号—原文重合度核验 ｜ 原文 {os.path.basename(args.source)}（{len(src_lines)} 行）")
    print(f"扫描 {len(files)} 个 .md，检出 {len(cits)} 处行号引用")
    print("=" * 78)

    cits_sorted = sorted(cits, key=lambda c: (LEVEL_ORDER[c.level], c.file, c.md_line))
    for c in cits_sorted:
        if args.quiet_pass and c.level == "PASS":
            continue
        rel = os.path.relpath(c.file).replace("\\", "/")
        tag = {"ERROR": "[阻断]", "WARN": "[存疑]", "SKIP": "[跳过]", "PASS": "[通过]"}[c.level]
        print(f"\n{tag} {rel}:{c.md_line}  行 {c.start}–{c.end}"
              + (f"  ({c.kind})" if c.kind != "range" else ""))
        print(f"    {c.reason}")
        if c.level in ("ERROR", "WARN"):
            print(f"    声称：{c.context[:96]}")
            print(f"    实际：{c.sample_src}")
            if c.missing_terms:
                print(f"    未命中术语：{', '.join(c.missing_terms)}")

    print("\n" + "=" * 78)
    print(f"汇总：阻断 {len(errors)} ｜ 存疑 {len(warns)} ｜ 跳过 {len(skips)} ｜ 通过 {len(passes)}")

    if args.calibrate:
        print_calibration(cits)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({
                "source": args.source,
                "source_lines": len(src_lines),
                "files_scanned": len(files),
                "thresholds": {"pass": args.pass_coverage, "warn": args.warn_coverage,
                               "wide_span": args.wide_span},
                "summary": {"error": len(errors), "warn": len(warns),
                            "skip": len(skips), "pass": len(passes)},
                "citations": [asdict(c) for c in cits_sorted],
            }, f, ensure_ascii=False, indent=2)
        print(f"JSON 已写入：{args.json_out}")

    if errors:
        print("判定：**FAIL** —— 存在张冠李戴/越界级引用，禁止合入，须回原文修正后重跑")
        return 1
    if warns:
        print("判定：**HOLD** —— 无阻断项，但存在需人工判读的存疑引用")
        return 2
    print("判定：**PASS** —— 全部行号引用与原文内容相符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
