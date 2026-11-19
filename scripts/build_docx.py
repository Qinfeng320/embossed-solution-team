#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_docx.py — 文档树(JSON) -> .docx (+ 可选 PDF) 确定性渲染脚本

契约见 references/doc-tree-spec.md。脚本只渲染、不篡改内容；
LLM(docx-agent) 负责把上游验收结论组织成符合规范的 JSON 文档树。

依赖自举：若当前 python 缺 python-docx / pywin32，自动建 managed venv 安装并重执行。
PDF：--pdf 时用 MS Word COM 导出；不可用时降级提示手动导出。
"""
import sys, os, json, subprocess, argparse, zipfile, tempfile

MANAGED_PY = "<Python 解释器>"
VENV_DIR = "<Python 环境>"
VENV_PY = os.path.join(VENV_DIR, "Scripts", "python.exe")


def _bootstrap():
    """确保依赖可用；缺失则自举到 managed venv 并重执行本脚本。"""
    try:
        import docx  # noqa: F401
        return
    except ImportError:
        pass
    try:
        if not os.path.exists(VENV_PY):
            subprocess.run([MANAGED_PY, "-m", "venv", VENV_DIR], check=True)
        subprocess.run([VENV_PY, "-m", "pip", "install", "-q", "python-docx", "pywin32"], check=True)
        os.execv(VENV_PY, [VENV_PY, *sys.argv])
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"[build_docx] 依赖自举失败: {e}\n请手动执行: {VENV_PY} -m pip install python-docx pywin32\n")
        sys.exit(2)


_bootstrap()

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _normalize_template(path):
    """将 .dotx 复制为临时 .docx 并翻转 [Content_Types].xml 的 main content-type，
    使 python-docx 可正常打开（脚本默认 Document(template) 直接打开 .dotx 会因
    content-type 校验失败）。返回可打开路径；非 .dotx 直接返回原路径。"""
    if not path:
        return None
    if path.lower().endswith(".dotx"):
        tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp.close()
        _flip_dotx_to_docx(path, tmp.name)
        return tmp.name
    return path


def _flip_dotx_to_docx(src, dst):
    """读 .dotx zip，把 word/document.xml 的 content-type 由 template.main 翻转为
    document.main，写回新 .docx（其余部分不动）。"""
    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        data = {n: zin.read(n) for n in names}
    ct = data.get("[Content_Types].xml", b"")
    ct = ct.replace(
        b"application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml",
        b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
    )
    data["[Content_Types].xml"] = ct
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, data[n])


def _ensure_list_styles(doc):
    """若模板缺 List Bullet / List Number 样式（python-docx 渲染列表会 KeyError/回退），
    注入 built-in 样式定义。

    PR-024（2026-11-17）：注入时必须剥离样式自带的 numPr——默认模板样式引用的
    numId 在目标模板 numbering.xml 中可能指向标题多级编号（本包模板 numId=1 即
    heading 1-6 的中文多级编号），导致 List Bullet 与章节标题共享同一计数器。

    PR-025（2026-11-17）：注入的样式默认模板里**无 basedOn 且 rPr 引用主题字体**
    （minorHAnsi/minorEastAsia），在正式模板中会脱离正文字体体系——Word 实际
    渲染出字号偏小、符号变形（"·"渲成短横线观感），与 LibreOffice 渲染成图的
    回退效果不一致，导致渲染核验漏检。根治＝清除注入样式携带的全部本地
    pPr/rPr 覆盖，改挂 basedOn Normal，字体字号行距完全继承正文口径。"""
    from copy import deepcopy
    existing = {s.name for s in doc.styles}
    for name in ("List Bullet", "List Number"):
        if name not in existing:
            base = Document()  # 默认模板含这些 built-in 样式
            src = next((s for s in base.styles if s.name == name), None)
            if src is not None:
                el = deepcopy(src.element)
                # 清除默认模板带来的本地覆盖（numPr / autoSpaceDE/DN /
                # contextualSpacing / 主题 rFonts）与既有 basedOn（其指向
                # 默认模板的 Normal，在目标模板中是悬空引用），全部交给 Normal 继承
                for tag in ("w:pPr", "w:rPr", "w:basedOn"):
                    sub = el.find(qn(tag))
                    if sub is not None:
                        el.remove(sub)
                # 挂 basedOn Normal，继承正文字体字号与行距
                try:
                    normal_id = doc.styles["Normal"].style_id
                except (KeyError, AttributeError):
                    normal_id = None
                if normal_id:
                    based = OxmlElement("w:basedOn")
                    based.set(qn("w:val"), normal_id)
                    name_el = el.find(qn("w:name"))
                    if name_el is not None:
                        name_el.addnext(based)
                doc.styles.element.append(el)


RED = RGBColor(0xC0, 0x00, 0x00)
BLUE = RGBColor(0x1F, 0x4E, 0x79)
AMBER = RGBColor(0x9C, 0x65, 0x00)  # 琥珀色


def _set_cell_shading(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def _add_page_number_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fldStart = OxmlElement("w:fldChar"); fldStart.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = "PAGE"
    fldEnd = OxmlElement("w:fldChar"); fldEnd.set(qn("w:fldCharType"), "end")
    run._r.append(fldStart); run._r.append(instr); run._r.append(fldEnd)


def _add_callout(doc, block):
    tone = block.get("tone", "info")
    color = {"redline": RED, "info": BLUE, "warning": AMBER}.get(tone, BLUE)
    fill = {"redline": "FCE4E4", "info": "E7F0F9", "warning": "FFF4D6"}.get(tone, "E7F0F9")
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    _set_cell_shading(cell, fill)
    # 左边框加色
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single"); left.set(qn("w:sz"), "24")
    left.set(qn("w:space"), "0"); left.set(qn("w:color"), "%02X%02X%02X" % (color[0], color[1], color[2]))
    borders.append(left)
    tcPr.append(borders)
    if block.get("title"):
        tp = cell.paragraphs[0]
        tr = tp.add_run(block["title"]); tr.bold = True; tr.font.color.rgb = color; tr.font.size = Pt(10.5)
        _set_run_font(tr, "SimHei", "黑体")
    bp = cell.add_paragraph()
    br = bp.add_run(block.get("text", ""))
    br.font.size = Pt(10.5)
    doc.add_paragraph()


def _layout_table(tbl, ncol):
    """表格列宽按内容分配（铺满 8306 缇）+ 表头跨页重复 + 行不跨页 + 宽表降字号。

    2026-10-26 新增：原先列宽等分，长表头会被挤成竖排（16 字分 6 行）。下沉到渲染层，
    任何调用 build_docx 的场景都自动正确。
    """
    TOTAL, MINW = 8306, 1050

    def dw(s):
        return sum(2 if ord(c) > 127 else 1 for c in str(s))

    raw = []
    for j in range(ncol):
        mx = 1
        for r in tbl.rows[:12]:
            if j < len(r.cells):
                for seg in str(r.cells[j].text).split("\n"):
                    mx = max(mx, dw(seg))
        raw.append(mx)
    if ncol * MINW >= TOTAL:
        w = [TOTAL // ncol] * ncol
    else:
        rem = TOTAL - ncol * MINW
        extra = [max(0, x - 8) for x in raw]
        se = sum(extra) or 1
        w = [MINW + int(rem * e / se) for e in extra]
    w[-1] += TOTAL - sum(w)

    tblPr = tbl._tbl.tblPr
    for tag in ('w:tblLayout', 'w:tblW'):
        for old in tblPr.findall(qn(tag)):
            tblPr.remove(old)
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    tw = OxmlElement('w:tblW'); tw.set(qn('w:w'), str(TOTAL)); tw.set(qn('w:type'), 'dxa'); tblPr.append(tw)

    grid = tbl._tbl.find(qn('w:tblGrid'))
    if grid is not None:
        for gc, val in zip(grid.findall(qn('w:gridCol')), w):
            gc.set(qn('w:w'), str(val))

    fs = 8 if ncol >= 5 else (9 if ncol == 4 else None)
    for ri, row in enumerate(tbl.rows):
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
            if fs:
                for cp in c.paragraphs:
                    for run in cp.runs:
                        run.font.size = Pt(fs)


def _disable_numbering(paragraph):
    """段落级直接格式 numId=0，禁用样式继承的任何 Word 自动编号。
    与 _ensure_list_styles 的样式级剥离构成双保险（PR-024）。"""
    pPr = paragraph._p.get_or_add_pPr()
    old = pPr.find(qn("w:numPr"))
    if old is not None:
        pPr.remove(old)
    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl"); ilvl.set(qn("w:val"), "0")
    numId = OxmlElement("w:numId"); numId.set(qn("w:val"), "0")
    numPr.append(ilvl); numPr.append(numId)
    pStyle = pPr.find(qn("w:pStyle"))
    if pStyle is not None:
        pStyle.addnext(numPr)
    else:
        pPr.insert(0, numPr)


def _render_list_item(doc, text, prefix):
    """列表条目：符号/编号由脚本确定性生成（PR-024），不依赖模板 numbering；
    悬挂缩进由 make_docx.fix_lists 统一设置。"""
    p = doc.add_paragraph(f"{prefix}{text}", style="List Bullet")
    _disable_numbering(p)
    return p


def _render_block(doc, block):
    t = block.get("type")
    if t == "paragraph":
        doc.add_paragraph(block.get("text", ""))
    elif t == "bullet":
        for item in block.get("items", []):
            _render_list_item(doc, str(item), "· ")
    elif t == "numbered":
        for i, item in enumerate(block.get("items", []), 1):
            _render_list_item(doc, str(item), f"{i}. ")
    elif t == "table":
        headers = block.get("headers", [])
        rows = block.get("rows", [])
        if block.get("caption"):
            cap = doc.add_paragraph()
            cr = cap.add_run(block["caption"])
            # PR-036：题注的字体字号一律由「角标-表格」样式决定（含自动编号"表 N"），
            # 不得写直接格式——直设黑体 10.5pt 会盖掉样式定义的仿宋 12pt，
            # 造成"套了样式但字体没改过来"。仅当模板缺该样式时降级为直设。
            try:
                cap.style = "角标-表格"
            except Exception:
                cr.bold = True; cr.font.size = Pt(10.5)
                _set_run_font(cr, "SimHei", "黑体")
        tbl = doc.add_table(rows=1, cols=max(len(headers), 1))
        tbl.style = "Table Grid"
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        hdr = tbl.rows[0].cells
        for i, h in enumerate(headers):
            hdr[i].text = ""
            rr = hdr[i].paragraphs[0].add_run(str(h)); rr.bold = True
            _set_run_font(rr, "SimHei", "黑体")
            _set_cell_shading(hdr[i], "D9E2F3")
        for r in rows:
            cells = tbl.add_row().cells
            for i, v in enumerate(r):
                cells[i].text = str(v)
        # 2026-10-26：列宽由"等分"改为"按内容分配 + 铺满版心 8306 缇"，
        # 并补 tblHeader（跨页重复表头）与 cantSplit（行不跨页）。
        # 此前等分会把长表头挤成竖排（16 字分 6 行）；下沉到本函数后，
        # 任何直接调用 build_docx 的场景也自动正确，不必依赖 make_docx 后处理。
        _layout_table(tbl, max(len(headers), 1))
        doc.add_paragraph()
    elif t == "callout":
        _add_callout(doc, block)
    elif t == "image":
        caption = block.get("caption")
        src = block.get("src")
        if caption:
            cap = doc.add_paragraph()
            cr = cap.add_run(caption)
            # PR-036：图片题注字体字号由「角标-图片」样式决定（含自动编号"图 N"），
            # 不写直接格式；仅模板缺样式时降级为直设。
            try:
                cap.style = "角标-图片"
            except Exception:
                cr.bold = True; cr.font.size = Pt(10.5)
                _set_run_font(cr, "SimHei", "黑体")
        if src and os.path.exists(src):
            try:
                w = block.get("width")
                pic_width = Inches(w) if w is not None else Emu(5274310)
                # 只传 width：python-docx 自动按原图比例缩放高度（不变形；§6.8）
                doc.add_picture(src, width=pic_width)
                # PR-034：图片段必须套「居中-图片」，只做视觉居中不算样式合规。
                # add_picture 会把图片写进一个新段落，取最后一个段落套样式（幂等）。
                try:
                    doc.paragraphs[-1].style = "居中-图片"
                except Exception:
                    pass  # 非标准模板（无该样式）时降级：仍保住图片与视觉居中
            except Exception as e:
                pp = doc.add_paragraph()
                pp.add_run(f"[图片渲染失败: {src} | {e}]").italic = True
        else:
            pp = doc.add_paragraph()
            pp.add_run(f"[图片素材未提供: {caption or src or '无说明'} — 请补全后重渲]").italic = True
        doc.add_paragraph()
    elif t == "pagebreak":
        doc.add_page_break()
    else:
        sys.stderr.write(f"[build_docx] 未知 block type 跳过: {t}\n")


def _add_cover(doc, meta):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(120)
    r = p.add_run(meta.get("title", "未命名方案")); r.bold = True; r.font.size = Pt(26)
    _set_run_font(r, "SimHei", "黑体")
    if meta.get("subtitle"):
        p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(meta["subtitle"]); r2.font.size = Pt(15); r2.font.color.rgb = BLUE
    doc.add_paragraph()
    info = [
        ("客户", meta.get("client", "—")),
        ("版本", meta.get("version", "—")),
        ("日期", meta.get("date", "—")),
        ("编制", meta.get("author", "售前专家团")),
    ]
    if meta.get("classification"):
        info.append(("密级", meta["classification"]))
    for k, v in info:
        pp = doc.add_paragraph(); pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rk = pp.add_run(f"{k}："); rk.bold = True; rk.font.size = Pt(11)
        rv = pp.add_run(str(v)); rv.font.size = Pt(11)
    doc.add_page_break()


def _cn_num(n):
    nums = "零一二三四五六七八九十"
    if n <= 10:
        return nums[n]
    if n < 20:
        return "十" + (nums[n - 10] if n > 10 else "")
    if n < 100:
        t, o = divmod(n, 10)
        return nums[t] + "十" + (nums[o] if o else "")
    return str(n)


def _set_style_font(style, ascii_name, ea_name):
    """设置样式的中英文字体（含 eastAsia），确保中文公文仿宋/黑体生效。"""
    style.font.name = ascii_name
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), ascii_name)
    rFonts.set(qn("w:hAnsi"), ascii_name)
    rFonts.set(qn("w:eastAsia"), ea_name)


def _set_run_font(run, ascii_name, ea_name):
    """设置单个 run 的中英文字体（含 eastAsia）。"""
    run.font.name = ascii_name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), ascii_name)
    rFonts.set(qn("w:hAnsi"), ascii_name)
    rFonts.set(qn("w:eastAsia"), ea_name)


def _heading_has_numbering(doc, level):
    """检测 heading 样式是否绑定了 Word 自动编号（numPr），避免与脚本手动前缀叠加成“一、一、”。"""
    name = f"heading {level}"
    try:
        style = doc.styles[name]
    except KeyError:
        return False
    pPr = style.element.find(qn("w:pPr"))
    if pPr is None:
        return False
    return pPr.find(qn("w:numPr")) is not None


import re as _re

_MANUAL_NUM_RE = [
    # ⚠️ 必须放在最前：多层编号（1.1 / 3.2.1 / 7.8b / 7.10）。
    # 若先走单层规则，"7.10 标题" 只会被削成 "10 标题"，造成 "1.1 1 标题" 的双重编号。
    _re.compile(r'^\s*\d+(?:\.\d+)+[bc]?(?=[\s、.．])\s*[、.．]?\s*'),
    # 一、 二、 1. 2. （一）（二） (1)(2) ① ② 等前缀，含全半角括号/顿号/点
    _re.compile(r'^\s*[(（]?[一二三四五六七八九十百零\d]+[、．.)\）]\s*'),
    _re.compile(r'^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*'),
    _re.compile(r'^\s*第[一二三四五六七八九十百零\d]+[、．.]\s*'),
    _re.compile(r'^\s*\d+[、.．]\s*'),
]

def _strip_manual_number(title):
    """剥离 JSON 标题里可能残留的手写编号前缀，编号权完全交给模板 heading
    样式的 Word 自动编号（numPr）。覆盖：一、/（一）/1./(1)/①/第一、 等。
    这是防御性兜底——docx-agent 生成的 JSON title 本就不含编号。"""
    t = title or ""
    for rx in _MANUAL_NUM_RE:
        t = rx.sub("", t)
    return t.strip()


def _remove_numpr(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    numPr = pPr.find(qn("w:numPr"))
    if numPr is not None:
        pPr.remove(numPr)


def _add_heading_like(doc, title, style_name, with_number=True):
    """套用模板 heading 样式（继承其 numPr 自动编号）。模板缺该级样式时兜底。"""
    try:
        p = doc.add_paragraph(title, style=style_name)
    except KeyError:
        lvl = int(style_name.split()[-1]) if style_name.split()[-1].isdigit() else 1
        prefix = f"{_cn_num(1)}、" if with_number else ""
        return doc.add_heading(f"{prefix}{title}", level=lvl)
    if not with_number:
        _remove_numpr(p)
    return p


def _render_section(doc, sec, idx):
    level = sec.get("level", 1)
    # 关键铁律：标题不得带手写编号，编号权完全交给模板 heading 样式的 Word
    # 自动编号（numPr）。先剥离 JSON 里可能残留的手写编号前缀。
    title = _strip_manual_number(sec.get("title", ""))
    auto_num = sec.get("numbering", "auto")
    style_name = f"heading {level}"
    if auto_num == "none":
        # 不需要编号的章节（如附录标题）套用模板 heading 样式但禁用自动编号
        _add_heading_like(doc, title, style_name, with_number=False)
    else:
        # 默认：套用模板 heading 样式，其 numPr 自动编号生效，绝不手动加前缀
        _add_heading_like(doc, title, style_name, with_number=True)
    for b in sec.get("blocks", []):
        _render_block(doc, b)


def _render_redlines(doc, tree):
    redlines = tree.get("redlines", [])
    if not redlines:
        sys.stderr.write("[build_docx] 错误：redlines 为空，红线是外发闸门，不可缺失。\n")
        sys.exit(3)
    placement = tree.get("redline_placement", "appendix")
    appendix = tree.get("appendix", {}) or {}
    show_appendix = appendix.get("redlines", True)
    # 脚注版（精简，置于封面后）
    if placement in ("footnote", "both"):
        fp = doc.add_paragraph()
        fr = fp.add_run("诚实边界与声明："); fr.bold = True; fr.font.size = Pt(9); fr.font.color.rgb = RED
        fr2 = fp.add_run(" ".join(f"({i+1}){t}" for i, t in enumerate(redlines)))
        fr2.font.size = Pt(9); fr2.font.color.rgb = RED
    # 附录版
    if placement in ("appendix", "both") and show_appendix:
        doc.add_page_break()
        doc.add_heading("附录：诚实边界与免责声明", level=1)
        for i, t in enumerate(redlines):
            p = doc.add_paragraph()
            rr = p.add_run(f"{i+1}. "); rr.bold = True; rr.font.color.rgb = RED
            p.add_run(t)
        sources = appendix.get("sources")
        if sources:
            doc.add_heading("资料来源", level=2)
            for s in sources:
                _render_list_item(doc, str(s), "· ")


def build(tree, out_docx, template=None):
    tpl = _normalize_template(template)
    doc = Document(tpl) if tpl else Document()
    _ensure_list_styles(doc)
    # 字体：正文宋体、标题黑体（沿用体系惯例；随标准模板口径演进）。
    # 重要：字号 / 行距 / 页边距一律继承所用模板（标准模板为 assets/样式模板.dotx，§0.14），脚本
    # 不再硬覆盖，确保“严格按模板输出”。模板未设中文字体时才补宋体/黑体。
    # 2026-10-26（用户确认·方案 A）：正文中文恢复仿宋口径，与模板 Normal 的
    # rFonts eastAsia="仿宋" 一致；西文仍走 SimSun（宋体）。此前此处硬写"宋体"，
    # 会把模板的仿宋覆盖掉，是"按模板输出却是宋体"的根因。
    normal = doc.styles["Normal"]
    _set_style_font(normal, "SimSun", "仿宋")
    for _lvl in (1, 2, 3):
        try:
            _set_style_font(doc.styles[f"heading {_lvl}"], "SimHei", "黑体")
        except KeyError:
            pass
    _add_cover(doc, tree.get("meta", {}))
    for i, sec in enumerate(tree.get("sections", []), start=1):
        _render_section(doc, sec, i)
    _render_redlines(doc, tree)
    _add_page_number_footer(doc.sections[0])
    doc.save(out_docx)
    if tpl and template and tpl != template:
        try:
            os.remove(tpl)
        except OSError:
            pass
    return out_docx


def export_pdf(docx_path):
    try:
        import win32com.client
    except ImportError:
        sys.stderr.write("[build_docx] 未装 pywin32，跳过 PDF 导出（请手动用 Word 另存为 PDF）。\n")
        return None
    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(os.path.abspath(docx_path))
        doc.SaveAs2(os.path.abspath(pdf_path), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close()
        word.Quit()
        print(f"[build_docx] PDF 已导出: {pdf_path}")
        return pdf_path
    except Exception as e:
        sys.stderr.write(f"[build_docx] PDF 导出失败（{e}）；docx 已生成，请手动用 Word 另存为 PDF。\n")
        return None


def main():
    ap = argparse.ArgumentParser(description="文档树 JSON -> .docx (+PDF)")
    ap.add_argument("input", help="文档树 JSON 路径")
    ap.add_argument("-o", "--output", help="输出 .docx 路径")
    ap.add_argument("--pdf", action="store_true", help="导出 PDF（MS Word COM）")
    ap.add_argument("--template", help="基于 .dotx/.docx 模板创建（保留其样式）")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        tree = json.load(f)
    out = args.output or (os.path.splitext(args.input)[0] + ".docx")
    build(tree, out, template=args.template)
    print(f"[build_docx] DOCX 已生成: {out}")
    if args.pdf:
        export_pdf(out)


if __name__ == "__main__":
    main()
