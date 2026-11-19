#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_docx_text.py — .docx 文本规范化（三项，幂等，安全写入）

依据 references/style-guide.md §六 与 document-format-standards.md §九：
  1) 全角空格 U+3000 → 半角空格×2（黑体无 U+3000 字形，会渲染为方框）
  2) 数字/英文紧邻空格清理（"100 N"→"100N"；纯中文间隔不动；迭代至收敛）
  3) 关闭自动中西文间距（docDefaults 与段落样式 pPr 注入 autoSpaceDE/DN=0）

覆盖范围：正文 body（含表格、文本框）+ 页眉页脚；每次 Word/WPS 保存后须重跑。
依赖自举：缺 python-docx 时自动使用 managed venv 安装后重执行。

用法：
  python normalize_docx_text.py <file.docx> [--dry-run] [--no-u3000] [--no-latin] [--no-autospace]
"""
import sys, os, re, subprocess, argparse

MANAGED_PY = "<Python 解释器>"
VENV_PY = "<Python 环境>/Scripts/python.exe"


def _bootstrap():
    try:
        import docx  # noqa: F401
        return
    except ImportError:
        pass
    try:
        subprocess.run([VENV_PY, "-m", "pip", "install", "-q", "python-docx"], check=True)
        os.execv(VENV_PY, [VENV_PY, *sys.argv])
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"[normalize_docx_text] 依赖自举失败: {e}\n")
        sys.exit(2)


_bootstrap()

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

# pPr 子元素 schema 顺序（节选，覆盖常用项；autoSpaceDE/DN 位于 topLinePunct 与 bidi 之间）
PPR_ORDER = [
    "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
    "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs",
    "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct", "w:topLinePunct",
    "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
    "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap",
    "w:jc", "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl",
    "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange",
]


def _strip_latin_spaces(s):
    """删除与数字/字母紧邻的空格（迭代至收敛）；纯中文间隔不动。"""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"(?<=[0-9A-Za-z])[ \u00a0]+|[ \u00a0]+(?=[0-9A-Za-z])", "", s)
    return s


def _iter_text_nodes(doc):
    """正文（含表格/文本框）+ 各节页眉页脚（非链接态）的全部 w:t 节点。"""
    for t in doc.element.body.iter(qn("w:t")):
        yield t
    for section in doc.sections:
        for hf in (section.header, section.footer,
                   section.first_page_header, section.first_page_footer,
                   section.even_page_header, section.even_page_footer):
            try:
                if hf.is_linked_to_previous:
                    continue
                for t in hf._element.iter(qn("w:t")):
                    yield t
            except Exception:
                continue


def _insert_autospace(pPr):
    """向 pPr 注入 autoSpaceDE/DN=0（按 schema 顺序插入）。返回是否发生了注入。"""
    changed = False
    for tag in ("w:autoSpaceDE", "w:autoSpaceDN"):
        existing = pPr.find(qn(tag))
        if existing is not None:
            if existing.get(qn("w:val")) not in ("0", "false"):
                existing.set(qn("w:val"), "0")
                changed = True
            continue
        el = OxmlElement(tag)
        el.set(qn("w:val"), "0")
        idx = PPR_ORDER.index(tag)
        anchor = None
        for child in pPr:
            ctag = child.tag.replace("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}", "w:")
            if ctag in PPR_ORDER and PPR_ORDER.index(ctag) > idx:
                anchor = child
                break
        if anchor is not None:
            anchor.addprevious(el)
        else:
            pPr.append(el)
        changed = True
    return changed


def _ensure_autospace_styles(doc):
    """docDefaults 与全部段落样式注入 autoSpaceDE/DN=0；返回处理计数。"""
    n = 0
    styles_el = doc.styles.element
    # docDefaults > pPrDefault > pPr
    dd = styles_el.find(qn("w:docDefaults"))
    if dd is not None:
        pprd = dd.find(qn("w:pPrDefault"))
        if pprd is None:
            pprd = OxmlElement("w:pPrDefault")
            dd.append(pprd)
        pPr = pprd.find(qn("w:pPr"))
        if pPr is None:
            pPr = OxmlElement("w:pPr")
            pprd.append(pPr)
        if _insert_autospace(pPr):
            n += 1
    # 全部段落样式
    for style in doc.styles:
        try:
            if style.type != 1:  # 1 = PARAGRAPH
                continue
            pPr = style.element.get_or_add_pPr()
            if _insert_autospace(pPr):
                n += 1
        except Exception:
            continue
    return n


def _safe_save(doc, path, retries=6, interval=1.5):
    import time, shutil
    tmp = path + ".navtmp"
    doc.save(tmp)
    last = None
    for _ in range(retries):
        try:
            shutil.copyfile(tmp, path)
            os.remove(tmp)
            return True
        except Exception as e:  # 文件被占用/同步盘瞬时锁
            last = e
            time.sleep(interval)
    raise RuntimeError(f"写回失败（原文件可能被 Word/WPS/同步盘占用）：{last}；中间件保留在 {tmp}")


def main():
    ap = argparse.ArgumentParser(description="docx 文本规范化（U+3000 / 拉丁空格 / autoSpace）")
    ap.add_argument("file", help="目标 .docx 路径")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写出")
    ap.add_argument("--no-u3000", action="store_true", help="跳过全角空格替换")
    ap.add_argument("--no-latin", action="store_true", help="跳过数字/英文邻接空格清理")
    ap.add_argument("--no-autospace", action="store_true", help="跳过 autoSpace 注入")
    args = ap.parse_args()

    doc = Document(args.file)
    c_u3000 = c_latin = 0
    touched = 0

    for t in _iter_text_nodes(doc):
        s = t.text or ""
        orig = s
        if not args.no_u3000 and "\u3000" in s:
            c_u3000 += s.count("\u3000")
            s = s.replace("\u3000", "  ")
        if not args.no_latin:
            s2 = _strip_latin_spaces(s)
            c_latin += (len(s) - len(s2))
            s = s2
        if s != orig:
            t.text = s
            t.set(XML_SPACE, "preserve")
            touched += 1

    n_styles = 0
    if not args.no_autospace:
        n_styles = _ensure_autospace_styles(doc)

    print(f"文件: {args.file}")
    print(f"  U+3000 替换: {c_u3000} 处 | 拉丁邻接空格删除: {c_latin} 个 | 改动文本节点: {touched}")
    print(f"  autoSpace 注入/校正: {n_styles} 处（docDefaults + 段落样式）")
    if args.dry_run:
        print("  [dry-run] 未写出")
        return
    _safe_save(doc, args.file)
    print("  已写回（安全写入）。")


if __name__ == "__main__":
    main()
