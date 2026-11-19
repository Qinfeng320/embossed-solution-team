#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_docs.py - 确定性文档解析管线（输入侧）

把客户/用户提供的 Word / PDF / PPT / Excel 解析为「带自动溯源标签的结构化中间态 JSON」，
并做红线正则预检。LLM(doc-in-agent) 只负责把本脚本产出**语义归类**为七维度，
不重复做格式识别 / 页码标注等确定性活。

设计镜像输出侧 build_docx.py：脚本干确定性活，大模型干语义判断。
- 格式识别（扩展名 + 魔数）
- 文本/版面提取，并在提取时**自动注入溯源标签**（p.N / S.N / ¶N / Sheet!B3）
- 红线正则预检（"已部署/已降本/未验证数字/第三方科研测试报告类证明"等六红线相关信号）
- 图片/网页因需 OCR/网络，本脚本不处理，交由 doc-in-agent 走降级路径

依赖自举：缺 pypdf / python-pptx / openpyxl / python-docx 时自动装到 managed venv 重执行。

用法:
    python parse_docs.py <file1> [file2 ...] [-o out.json] [--json]
"""
import sys, os, json, subprocess, argparse, re

MANAGED_PY = "<Python 解释器>"
VENV_DIR = "<Python 环境>"
VENV_PY = os.path.join(VENV_DIR, "Scripts", "python.exe")


def _bootstrap():
    """确保依赖可用；缺失则自举到 managed venv 并重执行本脚本。"""
    try:
        import docx  # noqa: F401
        import pypdf  # noqa: F401
        import pptx  # noqa: F401
        import openpyxl  # noqa: F401
        return
    except ImportError:
        pass
    try:
        if not os.path.exists(VENV_PY):
            subprocess.run([MANAGED_PY, "-m", "venv", VENV_DIR], check=True)
        subprocess.run([VENV_PY, "-m", "pip", "install", "-q",
                        "python-docx", "pypdf", "python-pptx", "openpyxl"], check=True)
        os.execv(VENV_PY, [VENV_PY, *sys.argv])
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"[parse_docs] 依赖自举失败: {e}\n"
                         f"请手动执行: {VENV_PY} -m pip install python-docx pypdf python-pptx openpyxl\n")
        sys.exit(2)


_bootstrap()

from docx import Document as DocxDocument          # noqa: E402
from pypdf import PdfReader                         # noqa: E402
from pptx import Presentation                       # noqa: E402
from openpyxl import load_workbook                 # noqa: E402


# 六红线相关信号（输入预检，仅预警不裁定）
REDLINE_KEYWORDS = [
    "已部署", "已落地", "已上线", "已应用", "已降本", "已降低",
    "未验证", "检测报告", "第三方检测", "科研报告", "认证", "强制认证", "保证", "承诺",
    "准确率99", "精度±", "99.9%",
]


def detect_format(path: str):
    ext = os.path.splitext(path)[1].lower()
    legacy = {".doc": "doc_legacy", ".ppt": "ppt_legacy", ".xls": "xls_legacy"}
    if ext in (".pdf", ".docx", ".pptx", ".xlsx"):
        return ext.lstrip(".")
    if ext in legacy:
        return legacy[ext]
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff"):
        return "image"
    if ext in (".html", ".htm", ".url", ".webloc"):
        return "web"
    # 魔数兜底
    try:
        with open(path, "rb") as f:
            head = f.read(8)
        if head.startswith(b"%PDF"):
            return "pdf"
        if head.startswith(b"PK\x03\x04"):
            return "zip_unknown"  # docx/pptx/xlsx 之一，但扩展名缺失
    except Exception:
        pass
    return "unknown"


def parse_pdf(path):
    units, notes = [], []
    try:
        reader = PdfReader(path)
    except Exception as e:
        return units, notes + [f"PDF 解析失败: {e}"]
    if getattr(reader, "is_encrypted", False):
        notes.append("加密·未解析（不破解，请用户提供可解析版本）")
        return units, notes
    any_text = False
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt.strip():
            any_text = True
            for line in txt.splitlines():
                line = line.strip()
                if line:
                    units.append({"label": f"p.{i}", "type": "paragraph",
                                   "page": i, "text": line})
        else:
            notes.append(f"p.{i} 无可选中文本·疑似扫描件·需OCR")
    if not any_text:
        notes.append("全文无可选中文本·扫描件·需OCR（置信度低·待澄清）")
    return units, notes


def parse_docx(path):
    units, notes = [], []
    d = DocxDocument(path)
    for i, p in enumerate(d.paragraphs, start=1):
        t = p.text.strip()
        if not t:
            continue
        style = (p.style.name if p.style else "") or ""
        u = {"label": f"¶{i}", "type": "paragraph", "para": i, "text": t}
        if style.startswith("Heading"):
            u["heading"] = style
        units.append(u)
    for ti, tb in enumerate(d.tables, start=1):
        for ri, row in enumerate(tb.rows, start=1):
            for ci, cell in enumerate(row.cells, start=1):
                ct = cell.text.strip()
                if ct:
                    units.append({"label": f"表{ti}!{ri},{ci}", "type": "cell",
                                   "table": ti, "row": ri, "col": ci, "text": ct})
    notes.append("Word 修订痕迹/批注/分页符本脚本不解析，需 LLM 单独判别（仅'已接受态'正文入事实）")
    return units, notes


def parse_pptx(path):
    units, notes = [], []
    prs = Presentation(path)
    for si, slide in enumerate(prs.slides, start=1):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = "".join(r.text for r in para.runs).strip()
                    if t:
                        texts.append(t)
            if shape.has_table:
                tbl = shape.table
                for ri, row in enumerate(tbl.rows, start=1):
                    for ci, cell in enumerate(row.cells, start=1):
                        ct = cell.text.strip()
                        if ct:
                            units.append({"label": f"S.{si}表{ri},{ci}", "type": "cell",
                                           "slide": si, "row": ri, "col": ci, "text": ct})
        if texts:
            units.append({"label": f"S.{si}", "type": "slide", "slide": si,
                          "title": texts[0], "text": " ".join(texts[1:])})
        if slide.has_notes_slide:
            nt = slide.notes_slide.notes_text_frame.text.strip()
            if nt:
                units.append({"label": f"S.{si}备注", "type": "note",
                               "slide": si, "text": nt})
    return units, notes


def parse_xlsx(path):
    units, notes = [], []
    wb = load_workbook(path, data_only=True)
    merged_val = {}
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            notes.append(f"隐藏Sheet {ws.title}·可能非对外口径·不混入对外结论")
        for rng in ws.merged_cells.ranges:
            top = next(rng.cells)
            val = ws.cell(row=top.row, column=top.column).value
            for c in rng.cells:
                merged_val[(c.row, c.column)] = val
        for row in ws.iter_rows():
            for cell in row:
                v = merged_val.get((cell.row, cell.column), cell.value)
                if v is None:
                    continue
                s = str(v)
                if s.strip():
                    units.append({"label": f"{ws.title}!{cell.coordinate}", "type": "cell",
                                   "sheet": ws.title, "cell": cell.coordinate, "text": s})
    wb.close()
    notes.append("公式已取显示值（data_only）；隐藏行列未展开·标未计入；单位据表头补")
    return units, notes


def redline_precheck(units):
    hits = []
    for u in units:
        t = u.get("text", "")
        for kw in REDLINE_KEYWORDS:
            idx = t.find(kw)
            if idx >= 0:
                snippet = t[max(0, idx - 12): idx + len(kw) + 12]
                hits.append({"keyword": kw, "label": u.get("label", ""),
                             "snippet": snippet})
    return hits


def parse_one(path):
    fmt = detect_format(path)
    result = {"file": path, "format": fmt, "unit_count": 0,
              "units": [], "redline_precheck": [], "notes": [], "errors": []}
    try:
        if fmt == "pdf":
            units, notes = parse_pdf(path)
        elif fmt == "docx":
            units, notes = parse_docx(path)
        elif fmt == "pptx":
            units, notes = parse_pptx(path)
        elif fmt == "xlsx":
            units, notes = parse_xlsx(path)
        elif fmt in ("doc_legacy", "ppt_legacy", "xls_legacy", "zip_unknown"):
            notes = [f"旧格式/未知压缩包({fmt})·本脚本不解析·交由 LLM 降级（导出为 docx/xlsx 或贴文本）"]
        elif fmt in ("image", "web"):
            notes = [f"{fmt} 格式需 OCR/网络抓取·本脚本不处理·交由 doc-in-agent 走降级路径"]
        else:
            result["errors"].append(f"无法识别格式: {path}")
            notes = ["格式未知·请确认文件扩展名或提供文本"]
        result["units"] = units
        result["notes"] = notes
        result["unit_count"] = len(units)
        result["redline_precheck"] = redline_precheck(units)
    except Exception as e:
        result["errors"].append(f"解析异常: {e}")
    return result


def main():
    ap = argparse.ArgumentParser(description="文档 -> 带溯源标签的结构化中间态 JSON")
    ap.add_argument("inputs", nargs="+", help="输入文件（可多个）")
    ap.add_argument("-o", "--output", help="输出 JSON 路径（默认 stdout）")
    ap.add_argument("--json", action="store_true", help="强制 JSON 输出")
    args = ap.parse_args()

    files = [parse_one(p) for p in args.inputs]
    out = {"files": files} if len(files) > 1 else files[0]

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[parse_docs] 已生成: {args.output}（{len(files)} 个文件）", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
