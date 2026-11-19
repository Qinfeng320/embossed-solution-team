#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_docx.py - 读回 build_docx.py 的渲染产物，供 LLM 做 QA 核验（只读，不渲染）。

设计边界：本脚本**只抽取** .docx 的结构化内容（标题/层级/表格/红线信号/页码域/乱码），
不替 LLM 做"是否合格"的语义判断——判断权在 docx-agent（大模型）。
这样落实「文档渲染不依赖脚本做结论，脚本完毕后大模型启动检查工作」。

用法:
    python inspect_docx.py <file.docx> [--json]
依赖: python-docx（与 build_docx.py 共用 managed venv，缺则自动自举）
"""
import sys
import os
import re
import json
import argparse
import zipfile

try:
    from docx import Document
except ImportError:  # 依赖自举：建 managed venv 安装后重执行
    import subprocess
    VENV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))), "binaries", "python", "envs", "default")
    py = os.path.join(VENV, "Scripts", "python.exe")
    if os.path.exists(py):
        subprocess.run([py, "-m", "pip", "install", "--quiet", "python-docx"], check=False)
        from docx import Document
    else:
        raise

# 红线信号关键词（用于 LLM 核验时快速定位诚实边界是否落位）
REDLINE_KEYWORDS = [
    "诚实边界", "红线", "不得", "仅对样品", "不代表批量", "示意", "假设",
    "科研性质", "内部参考", "无社会证明", "强制认证", "司法维权", "有效期",
    "已部署", "已降本", "已应用",
]


def inspect(path: str) -> dict:
    doc = Document(path)

    headings = []
    double_numbering = []
    para_nonempty = 0
    callout_texts = []

    for p in doc.paragraphs:
        text = p.text
        if not text.strip():
            continue
        para_nonempty += 1
        style_name = (p.style.name if p.style else "") or ""
        m = re.match(r"Heading (\d)", style_name)
        if m:
            lvl = int(m.group(1))
            # 双重编号检测：仅当标题开头出现 >=2 个编号标记才算异常
            # （脚本自动加的单一"一、"或"1."是正常显示，不算重复）
            lead = text
            cnt = 0
            for pat in (r"^[一二三四五六七八九十百零]+、", r"^\d+[\.、]", r"^\(?\d+\)"):
                if re.match(pat, lead):
                    cnt += 1
                    lead = re.sub(pat, "", lead, count=1)
            if cnt >= 2:
                double_numbering.append(text)
            headings.append({"level": lvl, "text": text})
        # callout 红框检测：段落底纹含红色调（w:shd fill 接近红）
        shd = p._p.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd')
        if shd is not None:
            fill = shd.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill', '')
            if fill and (fill.upper() in ("FF0000", "C00000", "E74C3C", "F4CCCC", "FFC7CE", "FCE4E4")):
                callout_texts.append(text)

    tables = []
    for ti, tb in enumerate(doc.tables):
        rows = [[c.text for c in r.cells] for r in tb.rows]
        empty = sum(1 for r in rows for c in r if not c.strip())
        tables.append({
            "index": ti,
            "rows": len(tb.rows),
            "cols": len(tb.columns),
            "header": rows[0] if rows else [],
            "empty_cells": empty,
        })
        # callout 红框以单格表格渲染，底色在单元格 tcPr 而非段落 pPr，须扫 cell._tc
        for row in tb.rows:
            for cell in row.cells:
                shd = cell._tc.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd')
                if shd is not None:
                    fill = shd.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill', '')
                    if fill and (fill.upper() in ("FF0000", "C00000", "E74C3C", "F4CCCC", "FFC7CE", "FCE4E4")):
                        callout_texts.append(cell.text)

    # 页码域 PAGE
    has_page_field = False
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".xml"):
                    data = z.read(n).decode("utf-8", "ignore")
                    if "PAGE" in data and "w:fldChar" in data:
                        has_page_field = True
                        break
    except Exception:
        pass

    # 乱码检测（替换字符）
    full_text = "\n".join(p.text for p in doc.paragraphs)
    for tb in doc.tables:
        for r in tb.rows:
            for c in r.cells:
                full_text += "\n" + c.text
    garbled = "\ufffd" in full_text

    # 红线信号命中（供 LLM 重点核对诚实边界是否落位）
    redline_hits = {}
    for kw in REDLINE_KEYWORDS:
        cnt = full_text.count(kw)
        if cnt:
            redline_hits[kw] = cnt

    # 空章节检测：标题后无内容
    empty_sections = []
    paras = doc.paragraphs
    for i, p in enumerate(paras):
        if not p.text.strip():
            continue
        if re.match(r"Heading \d", (p.style.name if p.style else "") or ""):
            nxt = ""
            for q in paras[i + 1:]:
                if q.text.strip():
                    nxt = q.text
                    break
                if re.match(r"Heading \d", (q.style.name if q.style else "") or ""):
                    break
            if not nxt or re.match(r"Heading \d", (q.style.name if q.style else "") or ""):
                empty_sections.append(p.text)

    return {
        "path": path,
        "paragraphs_nonempty": para_nonempty,
        "headings": headings,
        "double_numbering": double_numbering,
        "tables": tables,
        "red_callouts": callout_texts,
        "has_page_field": has_page_field,
        "garbled_chars": garbled,
        "redline_signal_hits": redline_hits,
        "empty_sections": empty_sections,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="渲染后的 .docx 路径")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（便于 LLM 解析）")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print(f"ERROR: 文件不存在 {args.path}", file=sys.stderr)
        sys.exit(2)

    rep = inspect(args.path)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"文件: {rep['path']}")
        print(f"非空段落数: {rep['paragraphs_nonempty']}")
        print(f"标题数: {len(rep['headings'])}")
        for h in rep["headings"]:
            print(f"  H{h['level']}  {h['text']}")
        print(f"双重编号(异常): {rep['double_numbering'] or '无'}")
        print(f"表格数: {len(rep['tables'])}")
        for t in rep["tables"]:
            print(f"  表{t['index']} {t['rows']}x{t['cols']} 空单元格={t['empty_cells']} 表头={t['header']}")
        print(f"红框 callout 数: {len(rep['red_callouts'])}")
        for c in rep["red_callouts"]:
            print(f"  红框> {c[:80]}")
        print(f"页码域(PAGE): {rep['has_page_field']}")
        print(f"乱码字符: {rep['garbled_chars']}")
        print(f"空章节: {rep['empty_sections'] or '无'}")
        print(f"红线信号命中: {rep['redline_signal_hits'] or '无'}")


if __name__ == "__main__":
    main()
