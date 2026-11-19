# -*- coding: utf-8 -*-
"""doc_selfcheck.py —— 交付前自检：一条命令替代「导 PDF + 逐页看图」

用法：
    python scripts/doc_selfcheck.py <file.docx> [--expect "必须出现的串" ...] [--json]

检查项（全部读回真实文件，不信任生成过程）：
  1 节数（封面 / 目录 / 正文 应为 3；短文档 --no-toc 为 1）
  2 标题：H1/H2 计数、**标题文本是否仍带手写编号**（双重编号征兆）、**标题是否重复**
  3 正文字体：Normal 的 eastAsia 与字号（标准：仿宋 / 14pt）
  4 表格：表数、表题数（角标-表格）、单元格样式数（居中-表格）、
         每表是否设置 tblHeader（跨页重复）、列宽合计是否≈8306（顶满版心）、
         「居中-表格」段是否残留直接字体字号（残留会覆盖样式，PR-034）
  4.5 角标：表题「角标-表格」、图题「角标-图片」段是否残留直接字体字号
         （残留会盖掉样式的仿宋 12pt，PR-036）
  5 图片：含图片对象的段落是否套「居中-图片」（PR-034）
  6 红线：附录红线段是否存在
  7 关键串：--expect 给定的字符串是否都在正文或表格中

退出码：0=全部通过；1=存在 FAIL（供 CI / 团长闸门使用）
"""
import argparse, json, re, sys
from collections import Counter

from docx import Document
from docx.oxml.ns import qn

TOTAL_W = 8306
EXPECT_EA = "仿宋"
EXPECT_SZ = 14.0
# 直接字体字号会覆盖样式定义（PR-034）：套了样式的段落不许再带这些直设属性
DIRECT_FONT_TAGS = ("w:rFonts", "w:sz", "w:szCs")


def _has_direct_font(rpr):
    if rpr is None:
        return False
    return any(rpr.find(qn(tag)) is not None for tag in DIRECT_FONT_TAGS)

MANUAL_NUM = re.compile(r'^\s*(?:\d+(?:\.\d+)+[bc]?|[一二三四五六七八九十]+|[（(]?[一二三四五六七八九十\d]+[）)、.．]|[①②③④⑤⑥⑦⑧⑨⑩])\s*[、.．）)]?\s*\S')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--expect", nargs="*", default=[], help="必须出现的关键串")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    d = Document(a.docx)
    checks, fails = [], 0

    def add(name, ok, detail=""):
        nonlocal fails
        if not ok:
            fails += 1
        checks.append({"item": name, "ok": ok, "detail": detail})

    # 1 节数
    nsec = len(d.sections)
    add("节数", nsec in (1, 3), f"{nsec} 节（1=无目录，3=封面/目录/正文）")

    # 2 标题
    h1 = [p for p in d.paragraphs if p.style.name in ('Heading 1', 'heading 1')]
    h2 = [p for p in d.paragraphs if p.style.name in ('Heading 2', 'heading 2')]
    add("H1/H2 数量", len(h1) > 0, f"H1={len(h1)} H2={len(h2)}")

    bad = [p.text for p in h1 + h2 if p.text.strip() and _looks_manual(p.text)]
    add("标题无手写编号", not bad, "残留：" + "；".join(bad[:3]) if bad else "无")

    dup = [k for k, v in Counter(_norm(p.text) for p in h1 + h2).items() if v > 1 and k]
    add("标题不重复", not dup, "重复：" + "；".join(x[:14] for x in dup[:3]) if dup else "无")

    # 3 字体
    try:
        st = d.styles["Normal"]
        rPr = st.element.find(qn('w:rPr'))
        rf = rPr.find(qn('w:rFonts')) if rPr is not None else None
        ea = rf.get(qn('w:eastAsia')) if rf is not None else None
        sz = st.font.size.pt if st.font.size else None
        add("正文字体=仿宋", ea == EXPECT_EA, f"eastAsia={ea}")
        add("正文字号=14pt", sz is not None and abs(sz - EXPECT_SZ) < 0.6, f"{sz} pt")
    except KeyError:
        add("正文字体", False, "无 Normal 样式")

    # 4 表格
    caps = [p for p in d.paragraphs if p.style.name == "角标-表格"]
    cellp = sum(1 for t in d.tables for r in t.rows for c in r.cells
                for p in c.paragraphs if p.style.name == "居中-表格")
    no_hdr, bad_w = [], []
    for i, t in enumerate(d.tables, 1):
        if len(t.columns) < 2:
            continue
        trPr = t.rows[0]._tr.find(qn('w:trPr'))
        if trPr is None or trPr.find(qn('w:tblHeader')) is None:
            no_hdr.append(i)
        grid = t._tbl.find(qn('w:tblGrid'))
        if grid is not None:
            total = sum(int(gc.get(qn('w:w')) or 0) for gc in grid.findall(qn('w:gridCol')))
            if abs(total - TOTAL_W) > 6:
                bad_w.append(f"表{i}={total}")
    n_multi = len([t for t in d.tables if len(t.columns) >= 2])
    # PR-036：由"≥"收紧为严格相等——题注多套（把引导句误判成表题）
    # 会凭空给正文加"表 N"编号，必须拦下
    add("表题数=表数", len(caps) == n_multi,
        f"表题 {len(caps)} / 多列表 {n_multi}" + ("（题注多套或漏套）" if len(caps) != n_multi else ""))
    # 无多列表格时该判据不适用（避免把"没表格"误判为不合格）
    add("单元格套「居中-表格」", cellp > 0 or n_multi == 0, f"{cellp} 段 / 多列表 {n_multi}")
    add("表头跨页重复", not no_hdr, "缺 tblHeader：" + str(no_hdr[:5]) if no_hdr else "全部已设")
    add("列宽顶满版心", not bad_w, "异常：" + "；".join(bad_w[:3]) if bad_w else f"合计≈{TOTAL_W}")
    # PR-034：样式套上不等于生效——文字级直接字体字号会盖掉样式
    overrun = []
    for ti, t in enumerate(d.tables, 1):
        for r in t.rows:
            for c in r.cells:
                for p in c.paragraphs:
                    if p.style.name != "居中-表格":
                        continue
                    hits = sum(1 for run in p.runs if _has_direct_font(run._element.rPr))
                    ppr = p._element.pPr
                    if ppr is not None and _has_direct_font(ppr.find(qn("w:rPr"))):
                        hits += 1
                    if hits:
                        overrun.append(f"表{ti}:{p.text[:8]}")
    add("表格样式字体字号生效", not overrun,
        "直接字体字号残留：" + "；".join(overrun[:5]) if overrun else "无直接字体字号残留")

    # 4.5 角标类（PR-036）：表题/图题字体字号只由样式决定，直接格式会盖掉样式
    def _caption_overrun(style_name):
        bad = []
        for p in d.paragraphs:
            if p.style.name != style_name:
                continue
            hits = sum(1 for run in p.runs if _has_direct_font(run._element.rPr))
            ppr = p._element.pPr
            if ppr is not None and _has_direct_font(ppr.find(qn("w:rPr"))):
                hits += 1
            if hits:
                bad.append(p.text.strip()[:10] or style_name)
        return bad

    for style_name, label in (("角标-表格", "表题角标"), ("角标-图片", "图题角标")):
        bad = _caption_overrun(style_name)
        n_this = sum(1 for p in d.paragraphs if p.style.name == style_name)
        add(f"{label}字体字号生效", not bad,
            "直接字体字号残留：" + "；".join(bad[:5]) if bad else
            (f"{n_this} 段全部由样式决定" if n_this else "无此类角标"))

    # 5 图片（PR-034）：含图片对象的段落必须套「居中-图片」，仅手动居中不算
    pics = [p for p in d.paragraphs if p._element.findall(".//" + qn("w:drawing"))]
    bad_pic = [p.text.strip()[:12] or "图片段" for p in pics if p.style.name != "居中-图片"]
    add("图片段套「居中-图片」", not bad_pic,
        "未套样式：" + "；".join(bad_pic[:5]) if bad_pic else
        (f"{len(pics)} 张全部套用" if pics else "无图片"))

    # 6 红线
    txt_all = "\n".join(p.text for p in d.paragraphs)
    add("红线（附录）", ("诚实边界" in txt_all) or ("红线" in txt_all), "")

    # 7 关键串
    tb = "\n".join(c.text for t in d.tables for r in t.rows for c in r.cells)
    hay = txt_all + "\n" + tb
    miss = [s for s in a.expect if s not in hay]
    if a.expect:
        add("关键串齐全", not miss, "缺：" + "；".join(miss[:5]) if miss else f"{len(a.expect)} 项全在")

    if a.json:
        print(json.dumps({"file": a.docx, "fails": fails, "checks": checks},
                         ensure_ascii=False, indent=1))
    else:
        print(f"自检：{a.docx.split('/')[-1]}")
        for c in checks:
            print(f"  [{'OK  ' if c['ok'] else 'FAIL'}] {c['item']}" + (f"　{c['detail']}" if c['detail'] else ""))
        print(f"结果：{'通过' if fails == 0 else str(fails) + ' 项未通过'}")
    return 0 if fails == 0 else 1


def _norm(s):
    return re.sub(r"\s", "", s or "")


def _looks_manual(t):
    """标题里是否还带手写编号（如 '1.1 xxx' '一、xxx' '（一）xxx'）。"""
    s = t.strip()
    return bool(re.match(r'^\d+(?:\.\d+)+[bc]?\s', s) or
                re.match(r'^[一二三四五六七八九十]{1,3}[、.．]\s*\S', s) or
                re.match(r'^[（(][一二三四五六七八九十\d]{1,3}[）)]\s*\S', s) or
                re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', s))


if __name__ == "__main__":
    sys.exit(main())
