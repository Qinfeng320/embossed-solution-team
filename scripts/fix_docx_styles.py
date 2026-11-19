# -*- coding: utf-8 -*-
"""fix_docx_styles.py —— 已有 .docx 的表格/图片/角标样式归位（PR-034 / PR-036）

适用：文档已生成后，又通过编辑器/脚本批量插图或改表，导致：
  ① 单元格文字残留直接字体字号（rFonts/sz/szCs），盖掉「居中-表格」样式；
  ② 图片段只做了视觉居中，样式仍是正文，未套「居中-图片」；
  ③ 表题/图题残留直接字体字号（旧渲染写死黑体 10.5pt），盖掉
     「角标-表格」/「角标-图片」样式定义的仿宋 12pt；或题注根本没套角标样式。

本脚本做三件事，均幂等：
  1 对所有「居中-表格」段（含段落级 rPr 与文字 run）剥离直接字体字号；
  2 对所有含真实图片对象的段落套「居中-图片」；
  3 对所有「角标-表格」/「角标-图片」段剥离直接字体字号。

**不做题注补套**：无法从版面可靠区分"表题"与"表前引导句"（实测把
"…如下表。收口判据全部为可数条件"误判为表题并加上表编号）。题注未套样式
请从文档树重新渲染；本脚本只负责清除覆盖样式的直接格式。

不改正文语义、不改图片本体、不改列宽，只归位样式。
建议先备份原文件，再执行；执行后用 doc_selfcheck.py 读回核验。

用法：
    python scripts/fix_docx_styles.py <file.docx> [<file2.docx> ...]
"""
import os
import shutil
import sys

from docx import Document
from docx.oxml.ns import qn

DIRECT_FONT_TAGS = ("w:rFonts", "w:sz", "w:szCs")


def strip_direct_font(rpr):
    if rpr is None:
        return 0
    n = 0
    for tag in DIRECT_FONT_TAGS:
        for el in rpr.findall(qn(tag)):
            rpr.remove(el)
            n += 1
    return n


def process(path):
    doc = Document(path)

    cells, cleared = 0, 0
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if p.style.name != "居中-表格":
                        continue
                    cells += 1
                    for run in p.runs:
                        cleared += strip_direct_font(run._element.rPr)
                    ppr = p._element.pPr
                    if ppr is not None:
                        cleared += strip_direct_font(ppr.find(qn("w:rPr")))

    pics, restyled = 0, 0
    for p in doc.paragraphs:
        if p._element.findall(".//" + qn("w:drawing")):
            pics += 1
            if p.style.name != "居中-图片":
                try:
                    p.style = doc.styles["居中-图片"]
                    restyled += 1
                except KeyError:
                    pass  # 该文档模板无「居中-图片」样式，跳过

    # PR-036：角标类剥离直接字体字号（残留会盖掉样式定义的仿宋 12pt）
    caps, cap_cleared = 0, 0
    for p in doc.paragraphs:
        if p.style.name in ("角标-表格", "角标-图片"):
            caps += 1
            for run in p.runs:
                cap_cleared += strip_direct_font(run._element.rPr)
            ppr = p._element.pPr
            if ppr is not None:
                cap_cleared += strip_direct_font(ppr.find(qn("w:rPr")))

    if cleared or restyled or cap_cleared:
        tmp = path + ".tmp"
        doc.save(tmp)
        try:
            shutil.copyfile(tmp, path)
        except PermissionError:
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    return cells, cleared, pics, restyled, caps, cap_cleared


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    for path in sys.argv[1:]:
        if not os.path.isfile(path):
            print(f"[fix_docx_styles] 跳过（不存在）: {path}")
            continue
        cells, cleared, pics, restyled, caps, cap_cleared = process(path)
        print(f"[fix_docx_styles] {os.path.basename(path)} | "
              f"表格段 {cells} 剥离直接字体字号 {cleared} 处 | "
              f"图片段 {pics} 补套「居中-图片」 {restyled} 个 | "
              f"角标段 {caps} 剥离直接字体字号 {cap_cleared} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
