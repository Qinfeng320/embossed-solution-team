#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smart_table_layout.py — 表格智能布局（WPS「表格智能布局」的确定性等价实现）。

（references/document-format-standards.md §0.4 ③ 的确定性实现）

为什么需要本脚本
----------------
WPS / WPS Office 的「表格智能布局」（表格工具 → 自动调整 → 表格智能布局）是
**交互式会员功能，不对外暴露任何自动化接口**（无 COM ProgID、无命令行入口），
因此无法由脚本"点击"该按钮。本脚本实现其等效结果：

  1. **按内容智能分配列宽**：统计每列内容的显示宽度（中文/全角按 2 单位、西文与数字按 1 单位），
     据此按比例分配列宽，并施加最小/最大占比夹取，消除"等分列宽"导致的窄列挤爆、宽列留白。
  2. **铺满版心**：表格总宽 = 页面版心宽度（由 sectPr/pgMar 推算），`tblW` 置 100%。
  3. **表头跨页重复**：首行加 `w:tblHeader`，长表跨页时自动重复表头。
  4. **表头垂直居中**：首行单元格 `vAlign=center`。

何时运行
--------
必须作为**最后一步**后处理（在 ① 字体回写 apply_docx_fonts.py、② 样式清理
prune_docx_styles.py 之后）——本脚本用 python-docx 整体重写文档包。

用法:
    python smart_table_layout.py <file.docx> [file2.docx ...]

依赖: python-docx
注意: 目标文件被 Word/WPS/同步盘占用时，先写临时文件再 copyfile 覆盖；仍被占用须等待后重试。
"""
import copy
import os
import shutil
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# 版心总宽兜底值（A4 21cm - 左2.8 - 右2.6 = 15.6cm → 8844 twips）
DEFAULT_CONTENT_TWIPS = 8844
MIN_RATIO = 0.08   # 单列最小占比
MAX_RATIO = 0.62   # 单列最大占比


def display_width(text: str) -> int:
    """按显示宽度计权：CJK/全角按 2，其余按 1。"""
    w = 0
    for ch in text or "":
        cp = ord(ch)
        w += 2 if (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0xA4CF
                   or 0xAC00 <= cp <= 0xD7A3 or 0xF900 <= cp <= 0xFAFF
                   or 0xFE30 <= cp <= 0xFE6F or 0xFF00 <= cp <= 0xFF60
                   or 0xFFE0 <= cp <= 0xFFE6) else 1
    return w


def content_twips(doc) -> int:
    """由 sectPr 的 pgMar 推算版心宽度（twips）。"""
    try:
        sect = doc.sections[0]
        pg = sect._sectPr.find(qn("w:pgMar"))
        if pg is not None:
            left = int(pg.get(qn("w:left")) or 0)
            right = int(pg.get(qn("w:right")) or 0)
            w = int(pg.get(qn("w:w")) or sect.page_width.twips)
            return max(w - left - right, 2000)
    except Exception:
        pass
    return DEFAULT_CONTENT_TWIPS


def smart_table(table, total: int) -> dict:
    """对单个表格应用智能布局，返回统计信息。"""
    tbl = table._tbl
    grid = tbl.find(qn("w:tblGrid"))
    rows = tbl.findall(qn("w:tr"))
    if grid is None or not rows:
        return {"cols": 0, "changed": False}

    cols = grid.findall(qn("w:gridCol"))
    n = len(cols)
    if n == 0:
        return {"cols": 0, "changed": False}

    # ---- 1. 计算每列内容权重（取该列所有单元格的最大显示宽度）----
    weights = [1] * n
    for tr in rows:
        tcs = tr.findall(qn("w:tc"))
        if len(tcs) != n:      # 合并单元格行 → 不参与权重统计
            continue
        for j, tc in enumerate(tcs):
            txt = "".join(t.text or "" for t in tc.iter(qn("w:t")))
            weights[j] = max(weights[j], min(display_width(txt.strip()), 56))

    # ---- 2. 按比例分配列宽（含夹取与归一化）----
    total_w = sum(weights) or n
    widths = [total * (w / total_w) for w in weights]
    widths = [min(max(x, total * MIN_RATIO), total * MAX_RATIO) for x in widths]
    scale = total / (sum(widths) or 1)
    widths = [int(round(x * scale)) for x in widths]
    widths[-1] += total - sum(widths)          # 消除取整误差

    # ---- 3. 写回 tblGrid ----
    for j, gc in enumerate(cols):
        gc.set(qn("w:w"), str(widths[j]))

    # ---- 4. 写回各单元格 tcW ----
    for tr in rows:
        tcs = tr.findall(qn("w:tc"))
        if len(tcs) != n:
            continue
        for j, tc in enumerate(tcs):
            tcPr = tc.find(qn("w:tcPr"))
            if tcPr is None:
                tcPr = OxmlElement("w:tcPr")
                tc.insert(0, tcPr)
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.insert(0, tcW)
            tcW.set(qn("w:w"), str(widths[j]))
            tcW.set(qn("w:type"), "dxa")

    # ---- 5. 表头：首行跨页重复 + 垂直居中 ----
    first = rows[0].find(qn("w:trPr"))
    if first is None:
        first = OxmlElement("w:trPr")
        rows[0].insert(0, first)
    if first.find(qn("w:tblHeader")) is None:
        first.append(OxmlElement("w:tblHeader"))
    for tc in rows[0].findall(qn("w:tc")):
        tcPr = tc.find(qn("w:tcPr"))
        if tcPr is None:
            tcPr = OxmlElement("w:tcPr")
            tc.insert(0, tcPr)
        va = tcPr.find(qn("w:vAlign"))
        if va is None:
            va = OxmlElement("w:vAlign")
            tcPr.append(va)
        va.set(qn("w:val"), "center")

    # ---- 6. 表格宽度铺满版心 ----
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), "5000")
    tblW.set(qn("w:type"), "pct")
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "autofit")

    return {"cols": n, "changed": True, "widths": widths}


def process(path: str):
    doc = Document(path)
    total = content_twips(doc)
    stats = []
    for t in doc.tables:
        stats.append(smart_table(t, total))
    tmp = path + ".tmp"
    doc.save(tmp)
    try:
        shutil.copyfile(tmp, path)
    except PermissionError:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return total, stats


def main() -> None:
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(2)
    for p in sys.argv[1:]:
        if not os.path.isfile(p):
            sys.stderr.write(f"[smart_tables] 跳过（不存在）: {p}\n")
            continue
        total, stats = process(p)
        ok = [s for s in stats if s["changed"]]
        multi = [s for s in ok if s["cols"] > 1]
        print(
            f"[smart_tables] {os.path.basename(p)} | 版心 {total} twips | "
            f"处理表格 {len(ok)}/{len(stats)} 张（多列 {len(multi)} 张）"
        )


if __name__ == "__main__":
    main()
