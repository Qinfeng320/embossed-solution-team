#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_docx.py — 渲染成图验证链路（docx → PDF → 逐页 PNG）

依据 docx-agent「QA Gate」（PR-005 新增"渲染成图核验"环节）：
结构化读回（inspect_docx.py）发现不了中文排版的视觉问题（方框、折行、分页、列宽），
关键交付（对外件/上会件）须在本链路渲染成图后逐页读图核对。

链路：MS Word COM 导出 PDF（只读打开）→ pypdfium2 渲染 PNG。
Word 组件不可用时降级提示（可改用 tencent-local-office-edit 预览或手动导出）。
依赖自举：缺 pywin32 / pypdfium2 时自动用 managed venv 安装后重执行。

用法：
  python render_docx.py <file.docx> [--out <目录>] [--scale 2.0] [--pages "1,4,10"]
  输出：<out 目录>/<name>.pdf + page01.png、page02.png …
"""
import sys, os, subprocess, argparse

MANAGED_PY = "<Python 解释器>"
VENV_PY = "<Python 环境>/Scripts/python.exe"


def _bootstrap():
    ok = True
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        ok = False
    try:
        import pypdfium2  # noqa: F401
    except ImportError:
        ok = False
    if ok:
        return
    try:
        subprocess.run([VENV_PY, "-m", "pip", "install", "-q", "pywin32", "pypdfium2"], check=True)
        os.execv(VENV_PY, [VENV_PY, *sys.argv])
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"[render_docx] 依赖自举失败: {e}\n")
        sys.exit(2)


_bootstrap()


def to_pdf_with_word(docx, pdf):
    """Word COM 只读导出 PDF；失败返回 False。用 DispatchEx 独立实例，避免干扰用户已开的 Word。"""
    try:
        import win32com.client
    except ImportError:
        return False
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(os.path.abspath(docx), ReadOnly=True)
        try:
            doc.ExportAsFixedFormat(os.path.abspath(pdf), 17)  # 17 = wdExportFormatPDF
        finally:
            doc.Close(False)
        return True
    except Exception as e:
        sys.stderr.write(f"[render_docx] Word 导出失败（请检查 WINWORD 残留进程）：{e}\n")
        return False
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser(description="docx 渲染成图验证（PDF + 逐页 PNG）")
    ap.add_argument("file", help="目标 .docx")
    ap.add_argument("--out", default=None, help="输出目录（默认 <docx同目录>/<name>_render/）")
    ap.add_argument("--scale", type=float, default=2.0, help="PNG 渲染倍率（默认 2.0）")
    ap.add_argument("--pages", default=None, help='指定页（如 "1,4,10"；默认全部）')
    args = ap.parse_args()

    docx = os.path.abspath(args.file)
    outdir = args.out or os.path.join(os.path.dirname(docx),
                                      os.path.splitext(os.path.basename(docx))[0] + "_render")
    os.makedirs(outdir, exist_ok=True)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(docx))[0] + ".pdf")

    if not to_pdf_with_word(docx, pdf):
        print("降级提示：Word 组件不可用，PDF 未生成。")
        print("可选路径：① 用 tencent-local-office-edit 预览人工核对；② 手动在 Word 中导出 PDF 后运行本脚本的渲染部分。")
        sys.exit(2)

    import pypdfium2 as pdfium
    pdfdoc = pdfium.PdfDocument(pdf)
    n = len(pdfdoc)
    if args.pages:
        idxs = [int(x.strip()) - 1 for x in args.pages.split(",") if x.strip()]
        idxs = [i for i in idxs if 0 <= i < n]
    else:
        idxs = list(range(n))

    pngs = []
    for i in idxs:
        img = pdfdoc[i].render(scale=args.scale).to_pil()
        png = os.path.join(outdir, "page%02d.png" % (i + 1))
        img.save(png)
        pngs.append(png)

    print(f"PDF: {pdf}（共 {n} 页）")
    for p in pngs:
        print("  " + p)
    print(f"渲染完成：{len(pngs)} 张 PNG，请逐页读图核对版式（方框/折行/分页/列宽）。")


if __name__ == "__main__":
    main()
