# -*- coding: utf-8 -*-
"""make_docx.py —— 一条命令从文档树 JSON 出成品 .docx（标准模板体系）

用途：把「内容」与「出文档」彻底分开。内容阶段只改 md/JSON；定稿后跑本脚本**一次**，
产出符合 §0.14 模板体系的 Word，不再手工补丁、不再反复重渲。

用法：
    python scripts/make_docx.py <tree.json> -o <out.docx> [--template <dotx>] [--header "页眉"] [--no-toc] [--no-pdf]

内置（依次执行，全部幂等）：
  1 模板基底渲染（复用 build_docx.build）
  2 清理模板自带示例内容（"123123"/"阿斯蒂芬" 等演示段）
  3 封面标题套「封面」样式、副标题与信息行居中、正文首章分页
  4 标题编号：附录整体不编号；其余沿用模板自动编号（无双重编号）
  5 表格：表题套「角标-表格」（表 N）、单元格段套「居中-表格」并剥离直设字体字号（PR-034，
          让样式真正生效）、按内容分配列宽、表头跨页重复、行不跨页
  6 图片：含图片对象的段落统一套「居中-图片」（PR-034）
  7 列表：统一左缩进 0.9cm + 悬挂
  7 目录：封面后插入 toc 1–3 域（Word 打开可更新）
  8 分节：封面 / 目录 / 正文三节；封面与目录不显示页码，正文页码从 1 起；页眉右对齐

输出：docx + 一条自检摘要（节数 / 表数 / 表题数 / 单元格样式数），便于不打开文件也能核对。
"""
import argparse, datetime, json, os, re, sys, copy

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.table import Table

HERE = os.path.dirname(os.path.abspath(__file__))
TOTAL_W = 8306          # 版心宽度（缇）
MIN_COL = 1050          # 单列保底宽度
RED_TONE = ("🔴", "⚠️", "❌", "禁止", "禁用", "不能说", "不可说", "不得", "不要")


# ---------------------------------------------------------------- 基础工具
def _norm(s):
    return re.sub(r"\s", "", s or "")


def set_style(par, name):
    try:
        par.style = name
        return True
    except Exception:
        return False


# PR-034：样式套上不等于生效。文字级 rFonts/sz/szCs 会盖掉样式定义，
# 必须在套样式后剥离；图片段只设居中对齐也不算，必须套「居中-图片」。
DIRECT_FONT_TAGS = ("w:rFonts", "w:sz", "w:szCs")


def strip_direct_font(par):
    n = 0
    for run in par.runs:
        rpr = run._element.rPr
        if rpr is None:
            continue
        for tag in DIRECT_FONT_TAGS:
            for old in rpr.findall(qn(tag)):
                rpr.remove(old)
                n += 1
    ppr = par._element.pPr
    rpr = ppr.find(qn('w:rPr')) if ppr is not None else None
    if rpr is not None:
        for tag in DIRECT_FONT_TAGS:
            for old in rpr.findall(qn(tag)):
                rpr.remove(old)
                n += 1
    return n


def style_images(doc):
    """所有含真实图片对象的段落套「居中-图片」；幂等。"""
    n = 0
    for par in doc.paragraphs:
        if par._element.findall(".//" + qn('w:drawing')):
            if par.style.name != "居中-图片" and set_style(par, "居中-图片"):
                n += 1
    return n


def strip_caption_fonts(doc):
    """PR-036：角标类（角标-表格/角标-图片）只由样式决定字体字号，剥离直接格式。

    与 PR-034 的「居中-表格」同类问题：旧 build_docx 给题注写死黑体 10.5pt，
    套样式后直接格式仍在，样式定义的仿宋 12pt 不生效。
    """
    n, cnt = 0, 0
    for par in doc.paragraphs:
        if par.style.name in ("角标-表格", "角标-图片"):
            cnt += 1
            n += strip_direct_font(par)
    return cnt, n


def zero_num(par):
    """取消某段的自动编号（numId=0 覆盖样式）。"""
    pPr = par._p.get_or_add_pPr()
    for old in pPr.findall(qn('w:numPr')):
        pPr.remove(old)
    numPr = OxmlElement('w:numPr')
    nid = OxmlElement('w:numId')
    nid.set(qn('w:val'), '0')
    numPr.append(nid)
    pPr.append(numPr)


def _clear_par(par):
    for child in list(par._p):
        if child.tag != qn('w:pPr'):
            par._p.remove(child)


# ---------------------------------------------------------------- 1 渲染
def render_tree(tree_path, out_path, template=None):
    sys.path.insert(0, HERE)
    import build_docx
    tree = json.load(open(tree_path, encoding="utf-8"))
    build_docx.build(tree, out_path, template)
    return tree


# ---------------------------------------------------------------- 2 清模板残留
def strip_template_demo(doc, title):
    body = doc.element.body
    kids = list(body.iterchildren())
    idx = None
    nt = _norm(title)
    for i, el in enumerate(kids):
        if el.tag.endswith('}p'):
            tx = _norm(Paragraph(el, doc).text)
            if tx and nt[:8] in tx and len(tx) <= len(nt) + 6:
                idx = i
                break
    if idx:
        for el in kids[:idx]:
            body.remove(el)
    return idx or 0


# ---------------------------------------------------------------- 3 封面
def style_cover(doc, title):
    ps = list(doc.paragraphs)
    idx = None
    for i, p in enumerate(ps):
        if _norm(p.text) and _norm(p.text) in _norm(title):
            idx = i
            break
    if idx is None:
        return False
    set_style(ps[idx], "封面")
    for p in ps[idx + 1: idx + 9]:
        if p.text.strip():
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return True


# ---------------------------------------------------------------- 4 编号
def fix_numbering(doc):
    in_app = False
    for par in doc.paragraphs:
        if par.style.name in ('Heading 1', 'heading 1'):
            in_app = par.text.strip().startswith("附录")
            if in_app:
                zero_num(par)
        elif par.style.name in ('Heading 2', 'heading 2') and in_app:
            zero_num(par)


# ---------------------------------------------------------------- 5 表格
def _dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in str(s))


def style_tables(doc, captions):
    caps, cells = 0, 0
    body = doc.element.body
    for el in list(body.iterchildren()):
        if not el.tag.endswith('}tbl'):
            continue
        prev = el.getprevious()
        if prev is not None and prev.tag.endswith('}p'):
            pp = Paragraph(prev, doc)
            if pp.text.strip() and pp.text.strip() in captions:
                if set_style(pp, "角标-表格"):
                    caps += 1
                pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        t = Table(el, doc)
        for row in t.rows:
            for cell in row.cells:
                for cp in cell.paragraphs:
                    if set_style(cp, "居中-表格"):
                        cells += 1
                    # PR-034：剥离直设字体字号，否则样式字体字号不生效
                    strip_direct_font(cp)

        ncol = len(t.columns)
        if ncol < 2:
            continue
        raw = []
        for j in range(ncol):
            mx = 1
            for r in t.rows[:12]:
                if j < len(r.cells):
                    for seg in str(r.cells[j].text).split('\n'):
                        mx = max(mx, _dw(seg))
            raw.append(mx)
        if ncol * MIN_COL >= TOTAL_W:
            w = [TOTAL_W // ncol] * ncol
        else:
            rem = TOTAL_W - ncol * MIN_COL
            extra = [max(0, x - 8) for x in raw]
            se = sum(extra) or 1
            w = [MIN_COL + int(rem * e / se) for e in extra]
        w[-1] += TOTAL_W - sum(w)

        tblPr = t._tbl.tblPr
        for tag in ('w:tblLayout', 'w:tblW'):
            for old in tblPr.findall(qn(tag)):
                tblPr.remove(old)
        lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
        tw = OxmlElement('w:tblW'); tw.set(qn('w:w'), str(TOTAL_W)); tw.set(qn('w:type'), 'dxa'); tblPr.append(tw)
        grid = t._tbl.find(qn('w:tblGrid'))
        if grid is not None:
            for gc, val in zip(grid.findall(qn('w:gridCol')), w):
                gc.set(qn('w:w'), str(val))

        # PR-034：删除旧的"宽表降字号"直设逻辑（原 fs=8/9 会写死字号覆盖「居中-表格」样式，
        # 是"套了样式但字体字号没变过去"的根因）。列宽已按内容分配并铺满版心（L-20），
        # 字号一律交由样式决定，不得再写 run.font.size / rFonts。
        for ri, row in enumerate(t.rows):
            trPr = row._tr.get_or_add_trPr()
            if trPr.find(qn('w:cantSplit')) is None:
                trPr.append(OxmlElement('w:cantSplit'))
            if ri == 0 and trPr.find(qn('w:tblHeader')) is None:
                trPr.append(OxmlElement('w:tblHeader'))
            for j, c in enumerate(row.cells):
                if j >= ncol:
                    break
                tcPr = c._tc.get_or_add_tcPr()
                for old in tcPr.findall(qn('w:tcW')):
                    tcPr.remove(old)
                e = OxmlElement('w:tcW'); e.set(qn('w:w'), str(w[j])); e.set(qn('w:type'), 'dxa')
                tcPr.insert(0, e)
    return caps, cells


# ---------------------------------------------------------------- 6 列表
def fix_lists(doc):
    n = 0
    for par in doc.paragraphs:
        if par.style.name in ('List Bullet', 'List Number'):
            pf = par.paragraph_format
            pf.left_indent = Cm(0.9)
            pf.first_line_indent = Cm(-0.45)
            pf.space_before = Pt(0)
            pf.space_after = Pt(1)
            n += 1
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for par in c.paragraphs:
                    if par.style.name in ('List Bullet', 'List Number'):
                        par.paragraph_format.left_indent = Cm(0)
                        par.paragraph_format.first_line_indent = Cm(0)
    return n


# ---------------------------------------------------------------- 7 目录
def insert_toc(doc, heading="目　录"):
    first_h1 = None
    for par in doc.paragraphs:
        if par.style.name in ('Heading 1', 'heading 1') and not par.text.strip().startswith("附录"):
            first_h1 = par
            break
    if first_h1 is None:
        return False
    h = first_h1.insert_paragraph_before(heading)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run("")
    rPr = r._r.get_or_add_rPr()
    rf = OxmlElement('w:rFonts'); rf.set(qn('w:eastAsia'), "黑体"); rPr.append(rf)
    r.font.size = Pt(16); r.font.bold = True

    p = first_h1.insert_paragraph_before("")
    parts = []
    c1 = OxmlElement('w:r'); f1 = OxmlElement('w:fldChar')
    f1.set(qn('w:fldCharType'), 'begin'); f1.set(qn('w:dirty'), 'true'); c1.append(f1)
    c2 = OxmlElement('w:r'); it = OxmlElement('w:instrText')
    it.set(qn('xml:space'), 'preserve'); it.text = ' TOC \\o "1-3" \\h \\z \\u '; c2.append(it)
    c3 = OxmlElement('w:r'); f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'separate'); c3.append(f2)
    c4 = OxmlElement('w:r'); t4 = OxmlElement('w:t'); t4.text = "（在 Word 中 Ctrl+A 后 F9 刷新目录）"; c4.append(t4)
    c5 = OxmlElement('w:r'); f3 = OxmlElement('w:fldChar'); f3.set(qn('w:fldCharType'), 'end'); c5.append(f3)
    for e in (c1, c2, c3, c4, c5):
        p._p.append(e)
    return True


# ---------------------------------------------------------------- 8 分节与页码
def split_sections(doc, toc_text="目录"):
    body = doc.element.body
    toc_h = None
    first_h1 = None
    for par in doc.paragraphs:
        t = _norm(par.text)
        if t == _norm(toc_text):
            toc_h = par
        if par.style.name in ('Heading 1', 'heading 1') and not par.text.strip().startswith("附录"):
            first_h1 = par
            break
    if toc_h is None or first_h1 is None:
        return 1

    pPr = first_h1._p.get_or_add_pPr()
    for old in pPr.findall(qn('w:pageBreakBefore')):
        pPr.remove(old)

    sectPr = body.find(qn('w:sectPr'))

    def split_before(par):
        prev = par._p.getprevious()
        if prev is None or not prev.tag.endswith('}p'):
            newp = OxmlElement('w:p')
            par._p.addprevious(newp)
            prev = newp
        tp = Paragraph(prev, par._parent)
        tpPr = tp._p.get_or_add_pPr()
        new = copy.deepcopy(sectPr)
        for tag in ('w:footerReference', 'w:headerReference'):
            for old in new.findall(qn(tag)):
                new.remove(old)
        for old in tpPr.findall(qn('w:sectPr')):
            tpPr.remove(old)
        tpPr.append(new)

    split_before(toc_h)
    split_before(first_h1)
    return 3


def setup_pages(doc, header_text):
    for i, s in enumerate(doc.sections):
        s.footer.is_linked_to_previous = False
        s.header.is_linked_to_previous = False
        fp = s.footer.paragraphs[0]
        _clear_par(fp)
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if i == len(doc.sections) - 1:      # 正文节：页码从 1 起
            r1 = fp.add_run("— "); r1.font.size = Pt(9); r1.font.name = "仿宋"
            run = OxmlElement('w:r'); f1 = OxmlElement('w:fldChar')
            f1.set(qn('w:fldCharType'), 'begin'); f1.set(qn('w:dirty'), 'true'); run.append(f1); fp._p.append(run)
            run2 = OxmlElement('w:r'); it = OxmlElement('w:instrText')
            it.set(qn('xml:space'), 'preserve'); it.text = ' PAGE '; run2.append(it); fp._p.append(run2)
            run3 = OxmlElement('w:r'); f2 = OxmlElement('w:fldChar')
            f2.set(qn('w:fldCharType'), 'separate'); run3.append(f2); fp._p.append(run3)
            run4 = OxmlElement('w:r'); tt = OxmlElement('w:t'); tt.text = '1'; run4.append(tt); fp._p.append(run4)
            run5 = OxmlElement('w:r'); f3 = OxmlElement('w:fldChar')
            f3.set(qn('w:fldCharType'), 'end'); run5.append(f3); fp._p.append(run5)
            r3 = fp.add_run(" —"); r3.font.size = Pt(9); r3.font.name = "仿宋"

            sp = s._sectPr
            for old in sp.findall(qn('w:pgNumType')):
                sp.remove(old)
            pn = OxmlElement('w:pgNumType'); pn.set(qn('w:start'), '1')
            cols = sp.find(qn('w:cols'))
            (cols.addprevious(pn) if cols is not None else sp.append(pn))

        hp = s.header.paragraphs[0]
        if i == 0:
            _clear_par(hp)                   # 封面不设页眉
        else:
            hp.text = header_text            # 分节会清空，须重设
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for r in hp.runs:
                r.font.size = Pt(9); r.font.name = "仿宋"


# ---------------------------------------------------------------- 主流程
def _is_writable(path):
    """目标不存在或可独占写入 → True。用于避免覆盖被 WPS / Word 打开的文件。"""
    if not os.path.exists(path):
        return True
    try:
        with open(path, "r+b"):
            return True
    except OSError:
        return False


def resolve_out_path(out):
    """目标被占用时自动改用带时间戳的新文件名，保证出件不被中断。

    PR-037：覆盖同名文件时，只要该文件正被 WPS / Word 打开就必然写失败，
    迫使用户先手动关闭、打断任务。改为「占用即改名」——旧文件原样保留，
    新文件另起带时间戳的名字，任务照常跑完，清理交给 sweep_outputs.py。
    返回 (实际输出路径, 是否改名)。
    """
    if _is_writable(out):
        return out, False
    stem, ext = os.path.splitext(out)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    cand = f"{stem}_{ts}{ext}"
    i = 1
    while not _is_writable(cand):
        cand = f"{stem}_{ts}_{i}{ext}"
        i += 1
    return cand, True


def make(tree_path, out_path, template=None, header=None, toc=True):
    out_path, renamed = resolve_out_path(out_path)
    if renamed:
        print(f"[make_docx] 目标文件被占用，改输出到新文件（旧文件保持不动）：{out_path}")
    tree = render_tree(tree_path, out_path, template)
    meta = tree.get("meta", {})
    title = meta.get("title", "")
    hdr = header or f"{title}（{meta.get('classification', '')}）".strip()

    captions = []
    for sec in tree.get("sections", []):
        for b in sec.get("blocks", []):
            if isinstance(b, dict) and b.get("type") == "table" and b.get("caption"):
                captions.append(b["caption"])

    doc = Document(out_path)
    removed = strip_template_demo(doc, title)
    style_cover(doc, title)
    fix_numbering(doc)
    caps, cells = style_tables(doc, captions)
    pics = style_images(doc)
    capn, capclr = strip_caption_fonts(doc)
    lists = fix_lists(doc)
    has_toc = insert_toc(doc) if toc else False
    nsec = split_sections(doc) if has_toc else 1
    setup_pages(doc, hdr)
    doc.save(out_path)

    print(f"[make_docx] 输出：{out_path}")
    print(f"[make_docx] 自检：清理模板演示段 {removed} · 表题 {caps} · 表格内段落 {cells} · "
          f"图片段补套样式 {pics} · 角标段 {capn} 剥离直接字体字号 {capclr} 处 · "
          f"列表 {lists} · 目录 {'有' if has_toc else '无'} · 节 {nsec} · 表 {len(doc.tables)}")
    print(f"[make_docx] 下一步：Word 打开后 Ctrl+A → F9 更新目录，另存 PDF")


def main():
    ap = argparse.ArgumentParser(description="文档树 JSON → 标准模板 Word（一步出成品）")
    ap.add_argument("tree", help="文档树 JSON 路径")
    ap.add_argument("-o", "--out", required=True, help="输出 .docx 路径")
    ap.add_argument("--template", default=None, help="基底模板（默认=专家团标准模板）")
    ap.add_argument("--header", default=None, help="页眉文字（默认=标题（密级））")
    ap.add_argument("--no-toc", action="store_true", help="不生成目录（短文档用）")
    a = ap.parse_args()
    tpl = a.template or os.path.join(HERE, "..", "assets", "样式模板.dotx")
    make(a.tree, a.out, tpl, a.header, not a.no_toc)


if __name__ == "__main__":
    main()
