#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_style_words.py — 交付件文风终扫（三类禁用词＋符号规范 + 可选工作痕迹辅助检查 + AI 生成腔弱化提示）

依据 references/style-guide.md（词表与符号规范唯一真相源；本脚本内置表为其镜像，修订须同步）：
  · 第一档（BANNED，§1.1 + §七.4）：三类禁用词与符号规范——终扫**清零口径**，命中即需逐条判读，影响退出码；
  · 第二档（WEAK，§1.5，PR-008 新增）：AI 生成腔弱化清单（E1–E6，镜像 academic-humanizer 汉化改造）——**提示级**，
    默认输出计数摘要、`--weak` 输出明细；不影响退出码（判读权在 ver，配套 references/claim-evidence-discipline.md §四）；
  · 辅助档（WORKTRACE，§二）：工作痕迹提示词（`--worktraces`）。
方法沿用 ver-agent M1/M2 铁律：docx/xlsx 遍历全部 .xml/.rels 部件去标签拼接、html.unescape 解码；
md/txt 直读。命中项为"疑似"清单——脚本是筛子不是法官，判读权在 ver（按上下文区分违规与例外）。

用例：
  python check_style_words.py --paths "<样例目录>/交付件目录"
  python check_style_words.py --paths "报告.docx" --worktraces --weak --json
  python check_style_words.py --paths "目录" --exclude "规范文档.md" "素材底稿.md"

输出：逐文件命中明细（词/组别/次数/上下文）；退出码 0=第一档无命中、1=第一档有命中、2=执行错误。
"""
import sys, os, re, html, zipfile, argparse, json

# ---- 词表（镜像 references/style-guide.md §1.1；修订须同步） ----
BANNED = {
    "A 军事化/狼性类": ["作战地图", "作战", "打法", "主战场", "卡位", "硬仗", "铁军", "狼性"],
    "B 互联网黑话类": ["抓手", "钩子", "赋能", "对齐", "拉通", "颗粒度", "复盘", "沙盘", "压舱石", "翻车", "闭环"],
    "C 市侩/江湖气类": ["通吃", "搞定", "拿下", "卖点", "爆款", "抢窗口", "占位", "抢占"],
    "D 符号规范（style-guide §七.4）": ["§"],  # 学术符号禁用；引文原文中的 § 由 ver 判读例外
}

# ---- 弱化清单（镜像 references/style-guide.md §1.5；PR-008 新增；提示级、不清零） ----
WEAK = {
    "E1 意义拔高（无具体依据时）": ["注入新的活力", "注入新活力", "迈上新台阶", "开启新篇章", "里程碑意义", "填补空白", "颠覆性的", "革命性的"],
    "E2 空泛程度宣称（无支撑时）": ["极大地", "全方位地", "多维度地", "深层次地", "助力"],
    "E3 回避系动词": ["起到了", "扮演着", "发挥着"],  # 候选词，须按上下文判"能否直接写 是/承担/负责"
    "E4 空洞收尾": ["具有广阔的应用前景", "未来发展可期", "大有可为"],
    "E6 三段式填充": [],  # 三项目排比属结构判据，机械扫描误报高，不做词表（由 ver 人工判读）
}
# E5 升华式成对结构（正则）："不仅是……更是 / 不仅……更是" 近距离同现
WEAK_REGEX = {
    "E5 升华式成对结构": r"不仅(?:是)?[^。；\n]{0,40}?更是",
}
# 密度控制项（style-guide §1.5）：合计计数 + 每千字密度，超阈值仅提示
DENSITY = {
    "模板化强调（值得注意的是/需要指出的是/应当强调的是）": ["值得注意的是", "需要指出的是", "应当强调的是"],
}
DENSITY_LIMIT_PER_1K = 2.0  # 每千字上限（参考值，超限提示）

# 白名单短语（style-guide §1.2）：先等长遮蔽，再计数——避免"左对齐"误报"对齐"、"整改闭环"误报"闭环"
WHITELIST = [
    "左对齐", "右对齐", "居中对齐", "两端对齐", "垂直对齐", "水平对齐", "垂直居中",
    "整改闭环", "闭环管理", "验收闭环", "闭环控制",
]

# 语境排除规则（正则）：遮蔽技术语境用法，避免误报——
# "占位符/占位文本/占位图"为排版技术词（placeholder），非"占位"进取腔
CONTEXT_EXCLUDE = [
    r"占位[符文图页]",
]


def mask_whitelist(text):
    """等长遮蔽白名单短语与语境排除项（保索引对齐，便于从原文摘上下文）。"""
    for w in WHITELIST:
        text = text.replace(w, "○" * len(w))
    for pat in CONTEXT_EXCLUDE:
        text = re.sub(pat, lambda m: "○" * len(m.group(0)), text)
    return text

# 工作痕迹辅助短语（style-guide §2；--worktraces 时启用，提示级）
WORKTRACE = [
    "经逐页核验", "经核查", "经交叉核实", "经核实", "本次调研", "梳理过程中", "需说明的是",
    "待补", "暂未获取", "待核实", "可信度中等", "来源有限", "初稿", "修订版", "勘误", "纠偏",
    "（一句话讲透）", "（本页核心交付）",  # 自述式元描述（style-guide §二 第 8 类 · PR-007）
]


def text_of_ooxml(fp):
    """docx/xlsx 全 XML 部件去标签拼接（M1）+ html.unescape 解码（M2）。"""
    z = zipfile.ZipFile(fp)
    s = ""
    for n in [x for x in z.namelist() if x.endswith(".xml") or x.endswith(".rels")]:
        s += re.sub(r"<[^>]+>", "", z.read(n).decode("utf8", "ignore"))
    return html.unescape(s)


def read_text(fp):
    """读取任意目标文件文本；zip 格式按 OOXML 处理，其余按文本。"""
    low = fp.lower()
    if low.endswith((".docx", ".xlsx")):
        return text_of_ooxml(fp)
    if low.endswith(".bak") or low.endswith((".doc", ".xls", ".ppt", ".pptx")):
        # 先探测是否 zip 格式（.bak 常为 docx 备份）
        try:
            with open(fp, "rb") as f:
                if f.read(2) == b"PK":
                    return text_of_ooxml(fp)
        except Exception:
            pass
    with open(fp, encoding="utf-8", errors="ignore") as f:
        return f.read()


def iter_files(paths, excludes):
    exts = (".docx", ".xlsx", ".doc", ".xls", ".ppt", ".pptx", ".pdf", ".md", ".txt", ".bak")
    for p in paths:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                for f in fs:
                    if f.lower().endswith(exts) and not any(e in f for e in excludes):
                        yield os.path.join(root, f)
        else:
            if not any(e in os.path.basename(p) for e in excludes):
                yield p


def scan(text):
    """返回 {组别: {词: [(次数, [上下文...])]}}；上下文取命中处 ±16 字。"""
    masked = mask_whitelist(text)
    result = {}
    for group, words in BANNED.items():
        g = {}
        for w in words:
            hits = [m.start() for m in re.finditer(re.escape(w), masked)]
            if hits:
                ctx = []
                for i in hits[:6]:
                    seg = text[max(0, i - 16): i + len(w) + 16].replace("\n", " ")
                    ctx.append(seg)
                g[w] = (len(hits), ctx)
        if g:
            result[group] = g
    return result


def scan_worktraces(text):
    out = {}
    for w in WORKTRACE:
        c = text.count(w)
        if c:
            out[w] = c
    return out


def scan_weak(text, detail=False):
    """第二档：AI 生成腔弱化清单（§1.5）。detail=True 时附上下文摘录。返回 (组别词计数, 密度项)。"""
    masked = mask_whitelist(text)
    result = {}
    for group, words in WEAK.items():
        g = {}
        for w in words:
            hits = [m.start() for m in re.finditer(re.escape(w), masked)]
            if hits:
                if detail:
                    ctx = []
                    for i in hits[:6]:
                        seg = text[max(0, i - 16): i + len(w) + 16].replace("\n", " ")
                        ctx.append(seg)
                    g[w] = {"count": len(hits), "context": ctx}
                else:
                    g[w] = {"count": len(hits)}
        if g:
            result[group] = g
    for group, pat in WEAK_REGEX.items():
        hits = [m.start() for m in re.finditer(pat, masked)]
        if hits:
            g = {}
            if detail:
                ctx = [text[max(0, i - 16): i + 40].replace("\n", " ") for i in hits[:6]]
                g[group] = {"count": len(hits), "context": ctx}
            else:
                g[group] = {"count": len(hits)}
            result[group] = g
    # 密度控制项：合计计数 + 每千字密度
    density = {}
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text)) or 1
    for label, words in DENSITY.items():
        c = sum(text.count(w) for w in words)
        if c:
            per1k = round(c / (cjk / 1000.0), 2)
            density[label] = {"count": c, "per_1k": per1k,
                              "over_limit": per1k > DENSITY_LIMIT_PER_1K}
    return result, density


def main():
    ap = argparse.ArgumentParser(description="交付件文风终扫（禁用词清零档 + 弱化清单提示档 + 工作痕迹；筛子定位，判读在 ver）")
    ap.add_argument("--paths", nargs="+", required=True, help="文件或目录（目录递归扫描常见格式）")
    ap.add_argument("--worktraces", action="store_true", help="附加扫描工作痕迹辅助词（提示级）")
    ap.add_argument("--weak", action="store_true", help="弱化清单（§1.5）输出明细与上下文；默认仅输出计数摘要")
    ap.add_argument("--exclude", nargs="*",
                    default=["style-guide.md", "claim-evidence-discipline.md", "proposal-structure-guide.md",
                             "redlines.md", "evidence-spec.md", "governance.md", "input-spec.md",
                             "knowledge-index.md", "doc-tree-spec.md", "document-format-standards.md"],
                    help="文件名排除片段（默认排除规范文件自身——规范中含词表举例，扫描会产生大量已知命中）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    report = []
    total_hits = 0
    for fp in iter_files(args.paths, args.exclude):
        try:
            t = read_text(fp)
        except Exception as e:
            report.append({"file": fp, "error": str(e)})
            continue
        item = {"file": fp, "banned": {}, "worktraces": {}, "weak": {}, "density": {}}
        r = scan(t)
        for group, g in r.items():
            item["banned"][group] = {w: {"count": c, "context": ctx} for w, (c, ctx) in g.items()}
            total_hits += sum(c for c, _ in g.values())
        if args.worktraces:
            item["worktraces"] = scan_worktraces(t)
        item["weak"], item["density"] = scan_weak(t, detail=args.weak)
        if item["banned"] or item["worktraces"] or item["weak"] or item["density"]:
            report.append(item)

    if args.json:
        print(json.dumps({"files": report, "total_banned_hits": total_hits}, ensure_ascii=False, indent=2))
    else:
        print("=" * 68)
        print("文风终扫（禁用词/工作痕迹/弱化清单）—— 命中为疑似清单，须按上下文判读")
        print("=" * 68)
        if not report:
            print("未扫描到任何命中（扫描范围：%s）" % "、".join(args.paths))
        for item in report:
            if "error" in item:
                print(f"[跳过] {item['file']} —— {item['error']}")
                continue
            print(f"\n▸ {item['file']}")
            for group, g in item["banned"].items():
                for w, d in g.items():
                    print(f"   [第一档·禁止] [{group[0]}] {w}  ×{d['count']}")
                    for c in d["context"][:3]:
                        print(f"        …{c}…")
            for w, c in item.get("worktraces", {}).items():
                print(f"   [工作痕迹·提示] {w}  ×{c}")
            for group, g in item.get("weak", {}).items():
                for w, d in g.items():
                    print(f"   [第二档·弱化提示] {w}  ×{d['count']}")
                    for c in d.get("context", [])[:3]:
                        print(f"        …{c}…")
            for label, d in item.get("density", {}).items():
                flag = "（超密度参考值）" if d["over_limit"] else ""
                print(f"   [密度控制·提示] {label}：×{d['count']}，每千字 {d['per_1k']} 次{flag}")
        print(f"\n合计：第一档禁用词命中 {total_hits} 处（含例外候选；请逐条判读）；"
              f"第二档为提示级、不影响退出码，判读与处理见 references/claim-evidence-discipline.md §四")
    sys.exit(1 if total_hits else 0)


if __name__ == "__main__":
    main()
