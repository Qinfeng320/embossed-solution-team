#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docmd.py —— 售前专家团 · 文档↔Markdown 双向批量转换（团队共享引擎）
=================================================================================
归属：doc-in-agent（入向：文档→MD）/ docx-agent（出向：MD→文档）共用。
规范：references/docmd-guide.md

正向（文档 -> Markdown）:  依赖 Microsoft markitdown[all]
                         覆盖 docx / xlsx / pptx / pdf / html / csv / txt
反向（Markdown -> 文档）:
   - docx / pptx : 依赖 pandoc
   - xlsx        : 依赖 openpyxl（从 MD 表格提取，每表一个工作表）

用法示例:
  # 文档转 MD（可多个）
  python docmd.py 报告.docx 数据.xlsx 演示.pptx 论文.pdf

  # MD 转 Word / PPT / Excel
  python docmd.py 笔记.md --to docx
  python docmd.py 笔记.md --to pptx
  python docmd.py 笔记.md --to xlsx

  # 递归处理整个目录
  python docmd.py --dir ./docs --to docx

输出规则: 与源文件同目录、同名（仅扩展名不同）。

引擎路径可用环境变量覆盖（便于跨环境复用）：
  DOCMD_VENV_PY     markitdown 所在 venv 的 python.exe（默认：隔离 managed venv）
  DOCMD_PANDOC       pandoc.exe 绝对路径（直接指定即优先）
  DOCMD_PANDOC_DIR   pandoc-* 目录所在父目录（默认：用户 workspace/tools）
"""

import argparse
import os
import shutil
import subprocess
import sys

# ---- 引擎路径（环境变量可覆盖，便于跨环境复用）----
VENV_PY = os.environ.get(
    "DOCMD_VENV_PY",
    r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe",
)
PANDOC_DIR = os.environ.get(
    "DOCMD_PANDOC_DIR",
    r"D:\BaiduSyncdisk\AI-agent\2026-08-17-18-08-51\tools",
)

DOC_EXTS = {".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".pdf",
            ".html", ".htm", ".txt", ".csv"}


def find_pandoc():
    """环境变量 DOCMD_PANDOC 优先；否则在 DOCMD_PANDOC_DIR/pandoc-* 下定位；最后回退 PATH。"""
    env = os.environ.get("DOCMD_PANDOC")
    if env and os.path.isfile(env):
        return env
    base = PANDOC_DIR
    if os.path.isdir(base):
        for d in sorted(os.listdir(base)):
            if d.startswith("pandoc-"):
                for sub in ("pandoc.exe", os.path.join("bin", "pandoc.exe")):
                    cand = os.path.join(base, d, sub)
                    if os.path.isfile(cand):
                        return cand
    return shutil.which("pandoc") or ""


def markitdown_runner():
    """优先使用隔离 venv 中的 markitdown，否则回退到当前 python。"""
    if os.path.isfile(VENV_PY):
        return [VENV_PY, "-m", "markitdown"]
    return [sys.executable, "-m", "markitdown"]


def to_markdown(src, pandoc, runner):
    """文档 -> Markdown（Office/PDF 走 markitdown，其余走 pandoc）。"""
    out = os.path.splitext(src)[0] + ".md"
    ext = os.path.splitext(src)[1].lower()
    if ext in DOC_EXTS:
        with open(out, "w", encoding="utf-8") as f:
            subprocess.run(runner + [src], stdout=f, check=True)
    else:
        subprocess.run([pandoc, src, "-o", out], check=True)
    return out


def _is_sep_row(row):
    """判断是否为 Markdown 表格分隔行（如 |---|:--:|）。"""
    if not row:
        return False
    for c in row:
        s = c.strip()
        if s and not set(s) <= set("-:"):
            return False
    return any("-" in c for c in row)


def md_to_xlsx(src, venv_py):
    """Markdown -> Excel：提取文档中的 Markdown 表格写入 xlsx（每表一工作表）。"""
    out = os.path.splitext(src)[0] + ".xlsx"
    code = (
        "import sys\n"
        "from openpyxl import Workbook\n"
        "src, out = sys.argv[1], sys.argv[2]\n"
        "text = open(src, encoding='utf-8').read()\n"
        "def is_sep(row):\n"
        "    if not row: return False\n"
        "    for c in row:\n"
        "        s = c.strip()\n"
        "        if s and not set(s) <= set('-:'): return False\n"
        "    return any('-' in c for c in row)\n"
        "wb = Workbook(); wb.remove(wb.active)\n"
        "blocks, cur, inf = [], [], False\n"
        "for ln in text.splitlines():\n"
        "    s = ln.strip()\n"
        "    if s.startswith('|'):\n"
        "        cur.append(s); inf = True\n"
        "    else:\n"
        "        if inf: blocks.append(cur); cur = []; inf = False\n"
        "if cur: blocks.append(cur)\n"
        "if not blocks:\n"
        "    ws = wb.create_sheet('\\u5185\\u5bb9')\n"
        "    for i, ln in enumerate(text.splitlines(), 1): ws.cell(row=i, column=1, value=ln)\n"
        "else:\n"
        "    for idx, tbl in enumerate(blocks, 1):\n"
        "        rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in tbl]\n"
        "        data = [r for r in rows if not is_sep(r)]\n"
        "        ws = wb.create_sheet('\\u8868\\u683c%d' % idx)\n"
        "        for row in data: ws.append(row)\n"
        "wb.save(out)\n"
        "print('XLSX \\u751f\\u6210:', out)\n"
    )
    subprocess.run([venv_py, "-c", code, src, out], check=True)
    return out


def from_markdown(src, fmt, pandoc, venv_py):
    """Markdown -> Office 文档（docx/pptx 用 pandoc，xlsx 用 openpyxl 表格提取）。"""
    if fmt == "xlsx":
        return md_to_xlsx(src, venv_py)
    out = os.path.splitext(src)[0] + "." + fmt
    subprocess.run([pandoc, src, "-o", out], check=True)
    return out


def collect_inputs(files, directory):
    inputs = list(files or [])
    if directory:
        for root, _, names in os.walk(directory):
            for n in names:
                inputs.append(os.path.join(root, n))
    return inputs


def main():
    ap = argparse.ArgumentParser(description="文档 <-> Markdown 双向批量转换（团队共享引擎）")
    ap.add_argument("files", nargs="*", help="待转换的文件（可多个）")
    ap.add_argument("--dir", help="递归处理整个目录")
    ap.add_argument("--to", choices=["docx", "xlsx", "pptx"], default="docx",
                    help="当输入为 .md 时指定的目标格式，默认 docx")
    args = ap.parse_args()

    pandoc = find_pandoc()
    runner = markitdown_runner()

    if not pandoc:
        sys.exit("✗ 未找到 pandoc，请先完成安装（见 references/docmd-guide.md）。")
    try:
        subprocess.run(runner + ["--help"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
    except Exception:
        sys.exit("✗ 未找到 markitdown，请先完成安装（pip install 'markitdown[all]'）。")

    inputs = collect_inputs(args.files, args.dir)
    if not inputs:
        sys.exit("✗ 没有可处理的文件，请用 files 或 --dir 指定。")

    ok = 0
    for src in inputs:
        ext = os.path.splitext(src)[1].lower()
        try:
            if ext == ".md":
                out = from_markdown(src, args.to, pandoc, VENV_PY)
                print(f"  MD  -> {args.to.upper()}: {out}")
            elif ext in DOC_EXTS:
                out = to_markdown(src, pandoc, runner)
                print(f"  文档 -> MD : {out}")
            else:
                print(f"  跳过不支持: {src}")
                continue
            ok += 1
        except subprocess.CalledProcessError:
            print(f"  ✗ 失败: {src}")

    print(f"\n完成: 成功 {ok} 个，失败 {len(inputs) - ok} 个。")


if __name__ == "__main__":
    main()
