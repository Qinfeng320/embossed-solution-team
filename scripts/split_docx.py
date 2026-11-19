#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_docx.py — 按一级标题拆分 .docx（章节分组 + 引用筛选）

依据文档拆分工程实践（PR-006）：以"一级标题"为界把正文分组，
每组生成一个独立文档；媒体按实际引用筛选（防孤儿资源），
其余部件（样式/设置/编号）原样保留在每份产出中。

判定"一级标题"：段落样式名匹配 heading 1 / 标题 1，或样式 outlineLvl=0。
文首内容（首个标题前）非空时归入 `00_前置内容.docx`。

用法：
  python split_docx.py <in.docx> --outdir <dir>
  输出：<dir>/01_<标题>.docx、02_<标题>.docx …

边界（v1）：适配标准结构文档（正文由一级标题分节）；编号定义整包保留（各分册
独立可用）；拆分后如再交付，建议对目标分册重跑规范化与编校检查。
"""
import sys, os, re, zipfile, argparse, html

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

ILLEGAL = re.compile(r'[\\/:*?"<>|\s]+')


def read_zip(fp):
    with zipfile.ZipFile(fp) as z:
        return {n: z.read(n) for n in z.namelist()}


def heading_levels(styles_xml):
    """styleId -> heading level（1-based）或 None。"""
    out = {}
    for m in re.finditer(r'<w:style [^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>', styles_xml, re.S):
        sid, body = m.groups()
        lvl = None
        nm = re.search(r'<w:name w:val="([^"]*)"', body)
        if nm:
            mh = re.search(r'(?:heading|标题)\s*(\d)', nm.group(1), re.I)
            if mh:
                lvl = int(mh.group(1))
        if lvl is None:
            ol = re.search(r'<w:outlineLvl w:val="(\d)"', body)
            if ol:
                lvl = int(ol.group(1)) + 1
        out[sid] = lvl
    return out


def split_body_elements(doc_xml):
    """返回 (head, elements, tail, sectpr)：body 顶层元素串列表（含表格）。"""
    bm = re.search(r"(<w:body[^>]*>)(.*)(</w:body>)", doc_xml, re.S)
    head = doc_xml[: bm.start(2)]
    inner, tail = bm.group(2), doc_xml[bm.end(2):]
    # 顶层切分：用非贪婪+标签配对近似（w:p / w:tbl / w:sectPr 顶层元素）
    elements = []
    pos = 0
    pat = re.compile(r"<w:(p|tbl|sectPr)[ >]")
    while True:
        m = pat.search(inner, pos)
        if not m:
            break
        tag = m.group(1)
        close = f"</w:{tag}>"
        end = inner.find(close, m.start())
        if end == -1:
            break
        end += len(close)
        elements.append(inner[m.start():end])
        pos = end
    sect = ""
    for i, e in enumerate(elements):
        if e.startswith("<w:sectPr"):
            sect = e
            elements.pop(i)
            break
    return head, elements, tail, sect


def para_style(elem):
    if not elem.startswith("<w:p"):
        return None
    m = re.search(r'<w:pStyle w:val="([^"]+)"', elem)
    return m.group(1) if m else None


def para_text(elem):
    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", elem, re.S)
    t = html.unescape("".join(texts))
    return t.strip()


def refs_of(elements):
    ids = set()
    for e in elements:
        ids.update(re.findall(r'r:(?:embed|id|link)="([^"]+)"', e))
    return ids


def main():
    ap = argparse.ArgumentParser(description="按一级标题拆分 docx")
    ap.add_argument("file")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    parts = read_zip(args.file)
    doc = parts["word/document.xml"].decode("utf-8", "ignore")
    styles = parts.get("word/styles.xml", b"").decode("utf-8", "ignore")
    rels = parts.get("word/_rels/document.xml.rels", b"").decode("utf-8", "ignore")
    levels = heading_levels(styles)

    head, elements, tail, sect = split_body_elements(doc)

    groups, current = [], None
    for e in elements:
        sid = para_style(e)
        if sid is not None and levels.get(sid) == 1:
            current = {"title": para_text(e) or "未命名", "elements": [e]}
            groups.append(current)
        else:
            if current is None:
                current = {"title": None, "elements": [e]}
                groups.append(current)
            else:
                current["elements"].append(e)
    if groups and groups[0]["title"] is None and not any(x.strip() for x in groups[0]["elements"]):
        groups.pop(0)

    os.makedirs(args.outdir, exist_ok=True)
    made = []
    for i, g in enumerate(groups, 1):
        used = refs_of(g["elements"])
        # rels 筛选：保留非图片关系；图片关系按引用保留
        kept_rels = []
        kept_media = set()
        for rm in re.finditer(r"<Relationship [^>]*/>", rels):
            r = rm.group(0)
            if "image" in r:
                rid = re.search(r'Id="([^"]+)"', r).group(1)
                if rid not in used:
                    continue
                tgt = re.search(r'Target="([^"]+)"', r).group(1)
                kept_media.add("word/" + tgt.lstrip("/"))
            kept_rels.append(r)
        new_rels = re.sub(
            r"<Relationships[^>]*>.*?</Relationships>",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(kept_rels) + "</Relationships>",
            rels, flags=re.S)

        new_doc = head + "".join(g["elements"]) + sect + tail

        title = g["title"] or "前置内容"
        fname = f"{i:02d}_{ILLEGAL.sub('_', title)[:30]}.docx"
        out = os.path.join(args.outdir, fname)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for n, data in parts.items():
                if n == "word/document.xml":
                    zout.writestr(n, new_doc.encode("utf-8"))
                elif n == "word/_rels/document.xml.rels":
                    zout.writestr(n, new_rels.encode("utf-8"))
                elif n.startswith("word/media/") and n not in kept_media:
                    continue
                else:
                    zout.writestr(n, data)
        made.append(fname)
        print(f"  产出：{fname}（段落级元素 {len(g['elements'])}）")

    print(f"拆分完成：共 {len(made)} 份 → {args.outdir}")
    print("  提示：对拟交付的分册须重跑 `normalize_docx_text.py` / `lint_docx_text.py` 并渲染核对。")


if __name__ == "__main__":
    main()
