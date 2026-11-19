#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_docx.py — 多份 .docx 顺序合并（骨架复用 + 样式ID映射 + 图片重映射）

依据文档合并工程实践（PR-006）：取第一份为骨架（完整保留其部件与版式），
将后续文档的正文元素顺序追加（章间插入分页），并处理：
  ① styleId 冲突映射（同步重写引用）
  ② 图片 rId 重映射 + media 复制（防重名）
  ③ [Content_Types].xml 扩展名补全（jpg/jpeg/png 互认）
边界（v1）：适配"同管线产出/样式相近"的文档合并；numbering 以骨架为准
（若后续文档含骨架没有的编号定义，编号可能回退为正文样式——合并后须重跑
文本规范化与编校检查并渲染核对）。

用法：
  python merge_docx.py <out.docx> <in1.docx> <in2.docx> [in3.docx ...]
"""
import sys, os, re, zipfile, argparse

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_zip(fp):
    with zipfile.ZipFile(fp) as z:
        return {n: z.read(n) for n in z.namelist()}


def style_ids(styles_xml):
    return dict(re.findall(r'<w:style [^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>', styles_xml, re.S))


def style_name(style_body):
    m = re.search(r'<w:name w:val="([^"]+)"', style_body)
    return m.group(1) if m else ""


def merge(out_path, inputs):
    base = read_zip(inputs[0])
    doc = base["word/document.xml"].decode("utf-8", "ignore")
    styles = base.get("word/styles.xml", b"").decode("utf-8", "ignore")
    rels = base.get("word/_rels/document.xml.rels", b"").decode("utf-8", "ignore")
    ctypes = base.get("[Content_Types].xml", b"").decode("utf-8", "ignore")
    base_styles = style_ids(styles)

    body_open = re.search(r"(<w:body[^>]*>)", doc).group(1)
    body_close = "</w:body>"
    head = doc[: doc.index(body_open) + len(body_open)]
    tail = doc[doc.index(body_close):]
    base_body = doc[len(head): doc.index(body_close)]
    sect = re.search(r"(<w:sectPr.*?</w:sectPr>)", base_body, re.S)
    sect_xml = sect.group(1) if sect else ""
    base_body_main = base_body.replace(sect_xml, "") if sect_xml else base_body

    merged_body = base_body_main
    stats = {"docs": 1, "elements": 0, "images": 0, "styles_added": 0, "rid_base": 9000}
    rid_next = stats["rid_base"]
    new_rel_parts, new_media, new_styles_xml = [], {}, []

    for idx, fp in enumerate(inputs[1:], 2):
        z = read_zip(fp)
        d = z["word/document.xml"].decode("utf-8", "ignore")
        b = re.search(r"<w:body[^>]*>(.*)</w:body>", d, re.S).group(1)
        b = re.sub(r"<w:sectPr.*?</w:sectPr>", "", b, flags=re.S)

        # ① 样式映射：冲突 styleId → 新ID
        mapping = {}
        other_styles = z.get("word/styles.xml", b"").decode("utf-8", "ignore")
        for sid, body in style_ids(other_styles).items():
            if sid in base_styles:
                if style_name(body) != style_name(base_styles[sid]):
                    new_sid = f"{sid}_d{idx}"
                    mapping[sid] = new_sid
                    new_styles_xml.append(body.replace(f'w:styleId="{sid}"', f'w:styleId="{new_sid}"', 1))
                    stats["styles_added"] += 1
            else:
                new_styles_xml.append(body)
                stats["styles_added"] += 1
        if mapping:
            for old, new in mapping.items():
                b = re.sub(r'(w:val=")%s(")' % re.escape(old), r"\g<1>%s\g<2>" % new, b)

        # ② 图片重映射：收集本文档 rels 中图片 → 新 rId
        rels_xml = z.get("word/_rels/document.xml.rels", b"").decode("utf-8", "ignore")
        for rm in re.finditer(r'<Relationship [^>]*Id="([^"]+)"[^>]*Type="[^"]*image[^"]*"[^>]*Target="([^"]+)"[^>]*/>', rels_xml):
            old_rid, target = rm.group(1), rm.group(2)
            new_rid = f"rId{rid_next}"; rid_next += 1
            b = re.sub(r'(r:embed=")%s(")' % re.escape(old_rid), r"\g<1>%s\g<2>" % new_rid, b)
            b = re.sub(r'(r:id=")%s(")' % re.escape(old_rid), r"\g<1>%s\g<2>" % new_rid, b)
            src = "word/" + target.lstrip("/")
            if src.startswith("word/media/"):
                media_name = "media/m%d_%s" % (idx, os.path.basename(target))
                new_media["word/" + media_name] = z.get(src, b"")
                new_rel_parts.append(
                    f'<Relationship Id="{new_rid}" Type="{R}/image" Target="{media_name}"/>')
                stats["images"] += 1

        # ③ 追加正文（章间分页）
        merged_body += '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + b
        stats["docs"] += 1
        stats["elements"] += len(re.findall(r"<w:p[ >]", b))

    # 组装
    merged_body += sect_xml
    new_doc = head + merged_body + tail

    if new_styles_xml:
        styles = styles.replace("</w:styles>", "".join(new_styles_xml) + "</w:styles>")
    if new_rel_parts:
        rels = rels.replace("</Relationships>", "".join(new_rel_parts) + "</Relationships>")
    # Content_Types：确保图片扩展名（jpg/png 等）已声明
    for ext in ("jpg", "jpeg", "png"):
        if f'Extension="{ext}"' not in ctypes:
            ctypes = ctypes.replace(
                "</Types>",
                f'<Default Extension="{ext}" ContentType="image/{"jpeg" if ext in ("jpg","jpeg") else "png"}"/></Types>')

    base["word/document.xml"] = new_doc.encode("utf-8")
    base["word/styles.xml"] = styles.encode("utf-8")
    base["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    base["[Content_Types].xml"] = ctypes.encode("utf-8")
    base.update(new_media)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for n, data in base.items():
            zout.writestr(n, data)

    print(f"合并完成：{out_path}")
    print(f"  文档数 {stats['docs']} ｜ 追加段落元素 {stats['elements']} ｜ 迁移图片 {stats['images']} ｜ 新增样式 {stats['styles_added']}")
    print("  提示：合并后须重跑 `normalize_docx_text.py` 与 `lint_docx_text.py`，并渲染核对分页与编号。")


def main():
    ap = argparse.ArgumentParser(description="多份 docx 顺序合并（骨架复用）")
    ap.add_argument("output")
    ap.add_argument("inputs", nargs="+", help="至少 2 个输入文件（第一个为骨架）")
    args = ap.parse_args()
    if len(args.inputs) < 1:
        print("需要输入文件"); sys.exit(2)
    if os.path.abspath(args.output) in [os.path.abspath(p) for p in args.inputs]:
        print("输出不能覆盖输入文件"); sys.exit(2)
    merge(args.output, args.inputs)


if __name__ == "__main__":
    main()
