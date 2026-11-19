# -*- coding: utf-8 -*-
"""export_pdf.py —— 用 Word COM 导出保真 PDF（顺序正确版）

为什么要有这个脚本：手工写 COM 调用时，最常见的错是**先 Close 再取页数/统计**，
这会抛 `RPC_E_DISCONNECTED (0x80010108)`；或者在只读打开后直接 Save 而静默失败。
本脚本把正确顺序固化下来：

    Open → Fields.Update（正文域）→ 各节 Footers/Headers 域更新 →
    Repaginate → ComputeStatistics（取页数，**必须在 Close 之前**）→
    Save（可选）→ ExportAsFixedFormat → Close → Quit

用法：
    python scripts/export_pdf.py <file.docx> [--no-save] [--out x.pdf]

输出一行摘要：`pages=N sections=M pdf=路径 exists=True`。
"""
import argparse, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--out", default=None, help="输出 PDF 路径（默认同名 .pdf）")
    ap.add_argument("--no-save", action="store_true", help="不写回 docx（只更新内存结果并导出）")
    a = ap.parse_args()

    docx = os.path.abspath(a.docx)
    pdf = os.path.abspath(a.out or os.path.splitext(docx)[0] + ".pdf")
    if not os.path.exists(docx):
        print(f"[export_pdf] 文件不存在：{docx}")
        return 2
    if os.path.exists(pdf):
        try:
            os.remove(pdf)
        except OSError as e:
            print(f"[export_pdf] 旧 PDF 无法删除（可能被占用）：{e}")
            return 3

    import win32com.client as win32
    wd = win32.DispatchEx("Word.Application")
    wd.Visible = False
    wd.DisplayAlerts = 0
    doc = None
    try:
        doc = wd.Documents.Open(docx, False, False)   # ConfirmConversions, ReadOnly
        doc.Fields.Update()
        for s in doc.Sections:
            for part in (s.Footers, s.Headers):
                for item in part:
                    try:
                        item.Range.Fields.Update()
                    except Exception:
                        pass
        doc.Repaginate()
        pages = doc.ComputeStatistics(2)              # ★ 必须在 Close 之前
        sections = doc.Sections.Count
        if not a.no_save:
            doc.Save()
        doc.ExportAsFixedFormat(pdf, 17)               # 17 = wdExportFormatPDF
        doc.Close(0)
        doc = None
        print(f"[export_pdf] pages={pages} sections={sections} pdf={pdf} exists={os.path.exists(pdf)}")
        return 0 if os.path.exists(pdf) else 4
    except Exception as e:
        print(f"[export_pdf] 失败：{type(e).__name__}: {e}")
        return 1
    finally:
        try:
            if doc is not None:
                doc.Close(0)
        except Exception:
            pass
        try:
            wd.Quit()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
