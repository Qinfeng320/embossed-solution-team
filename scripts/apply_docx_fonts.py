#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_docx_fonts.py — 转换后按段落角色回写中文字体（黑体 / 楷体 / 宋体）。

（document-format-standards.md §0.4 ① 「字体回写」的确定性实现）

为什么需要本脚本
----------------
html-to-docx 在 Phase 2c 会执行 `apply_cjk_run_properties`，把文档中**所有含中文的
run 统一强制为 body 的 CJK 字体**（本项目为宋体），从而覆盖标题应有的黑体、以及
二级小标题应有的楷体。因此转换完成后必须按"段落角色"把字体回写回去。

角色判定规则（与 document-format-standards.md §0.1 对应）
--------------------------------------------------------
  1. `Heading *` 段落                             → 黑体
  2. 首个 `Heading 2` 之前的段落（封面区）
       · 字号 ≥ 12pt                              → 黑体
       · 其余（编制单位/日期等）                   → 宋体
  3. 正文区（首个 Heading 2 之后）字号 ≥ 15pt 的段落 → 楷体（（一）级小标题）
  4. 其余                                        → 保持宋体（不动）

同一次运行内对所有 run 显式写入 ascii / hAnsi / eastAsia / cs + hint=eastAsia，
并清除主题字体引用，确保 Word 中中文走东亚字体槽。

用法:
    python apply_docx_fonts.py <file.docx> [file2.docx ...]

依赖: python-docx
注意: 目标 .docx 可能被 Word / 预览面板占用——本脚本先写临时文件、再 shutil.copyfile
      覆盖原文件（rename 在文件被占用时会报 PermissionError），失败则回退 os.replace。
"""
import os
import shutil
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HEI, KAI, SONG = "黑体", "楷体", "宋体"
_ATTRS = ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs")
_THEME = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")


def set_font(run, name: str) -> None:
    """把 run 的中西文字体统一设为 name，并声明 hint=eastAsia。"""
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for a in _ATTRS:
        rFonts.set(qn(a), name)
    rFonts.set(qn("w:hint"), "eastAsia")
    for t in _THEME:
        if rFonts.get(qn(t)) is not None:
            del rFonts.attrib[qn(t)]


def max_size(par) -> float:
    """段落中 run 的最大直接字号（pt）；无直接字号返回 0。"""
    sizes = [r.font.size.pt for r in par.runs if r.font.size is not None]
    return max(sizes) if sizes else 0.0


def process(path: str) -> dict:
    doc = Document(path)
    paras = doc.paragraphs
    # 封面区 = 首个「章级标题（Heading 2）」之前的所有段落
    # （封面主标题本身是 Heading 1，不能用"首个 Heading"作边界）
    first_h2 = next(
        (i for i, p in enumerate(paras) if p.style.name == "Heading 2"), len(paras)
    )
    stats = {HEI: 0, KAI: 0, SONG: 0}
    for i, p in enumerate(paras):
        st = p.style.name
        if st.startswith("Heading"):
            target = HEI
        elif i < first_h2:
            target = HEI if max_size(p) >= 12 else SONG
        else:
            target = KAI if max_size(p) >= 15 else None
        if target is None:
            continue
        for r in p.runs:
            set_font(r, target)
            stats[target] += 1

    tmp = path + ".tmp"
    doc.save(tmp)
    try:
        shutil.copyfile(tmp, path)
    except PermissionError:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return stats


def main() -> None:
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(2)
    for p in sys.argv[1:]:
        if not os.path.isfile(p):
            sys.stderr.write(f"[apply_docx_fonts] 跳过（不存在）: {p}\n")
            continue
        s = process(p)
        print(
            f"[apply_docx_fonts] {os.path.basename(p)} | "
            f"黑体 {s[HEI]} run · 楷体 {s[KAI]} run · 宋体 {s[SONG]} run"
        )


if __name__ == "__main__":
    main()
