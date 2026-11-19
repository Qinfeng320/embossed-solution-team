#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""专家团标准模板 · 内容→样式落盘脚本（content_to_docx.py）

输入「已判断类别的结构化内容」（JSON），直接输出套好标准样式的 Word 文档：
标题自动编号、封面/目录/图表题注、图·表宽度顶满版心（图片高度按原图比例同步缩放）、页面设置终值。
标题与题注的手写编号自动清洗（编号一律由样式生成）。

用法：
  python content_to_docx.py --input content.json --out 交付物.docx [--base <模板路径>]

输入 JSON 结构（示例）：
{
  "cover": "示例解决方案名称",          // 可选：封面主标题
  "toc":   [["项目背景", "1"], ["建设需求分析", "1"]],   // 可选：目录条目 [文本, 页码, 级别(可选 1-3)]
  "blocks": [
    {"type": "h1",  "text": "一、项目背景"},             // 编号自动清洗 → 一 项目背景
    {"type": "h2",  "text": "1.1 建设需求分析"},
    {"type": "h3",  "text": "1.1.1 教学场景需求"},
    {"type": "p",   "text": "正文段落……（正文不清洗）"},
    {"type": "img", "src": "E:/path/img.png", "caption": "系统总体架构"},
    {"type": "tbl", "caption": "设备配置清单", "rows": [["设备名称","数量"],["数采手套","12"]]}
  ]
}
类型：cover / h1–h6 / toc1–toc3 / p / img / cap_img / cap_tbl / tbl
"""
import argparse
import json
import os
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_BASE = os.path.join(PLUGIN_DIR, 'assets', '样式模板.dotx')

# ---- 内容 → 样式映射（对应标准模板 styleId） ----
STYLE_MAP = {
    'cover': '41', 'h1': '2', 'h2': '3', 'h3': '4', 'h4': '5', 'h5': '6', 'h6': '7',
    'toc1': '15', 'toc2': '16', 'toc3': '13',
    'img': '36', 'cap_img': '37', 'cap_tbl': '38',
}
TBL_STYLE = '39'          # 居中-表格（表格内各段落）
PAGE_MAR = ('1440', '1800', '1440', '1800')   # 上右下左（缇）——输出终值
IMG_W = 5274310           # 图片显示宽 = 版心宽（EMU）

CLEAN_RULES = [
    (r'^[一二三四五六七八九十百]+[、．.，,：:]\s*', '汉字序号'),
    (r'^第[一二三四五六七八九十百\d]+[部分篇章节]+\s*[、．.]?\s*', '章节词'),
    (r'^（[一二三四五六七八九十]+）\s*', '括号汉字'),
    (r'^\d+(?:\.\d+)+[、．.]?\s*', '多级数字'),
    (r'^(?:\d{1,2})[、．.]\s+', '单级数字'),
    (r'^\d+）\s*', '圆括号数字'),
    (r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '带圈数字'),
    (r'^图\s?\d+\s*[、．.:：]?\s*', '图题前缀'),
    (r'^表\s?\d+\s*[、．.:：]?\s*', '表题前缀'),
]
AUTO_NUM_KINDS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'cap_img', 'cap_tbl'}


def clean(text):
    for pat, _ in CLEAN_RULES:
        text = re.sub(pat, '', text).strip()
    return text


def xml_escape(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def make_p(sid, text):
    style = f'<w:pStyle w:val="{sid}"/>' if sid else ''
    ppr = f'<w:pPr>{style}</w:pPr>' if style else ''
    if '\t' in text:
        a, b = text.split('\t', 1)
        runs = (f'<w:r><w:t xml:space="preserve">{xml_escape(a)}</w:t></w:r>'
                f'<w:r><w:tab/></w:r>'
                f'<w:r><w:t xml:space="preserve">{xml_escape(b)}</w:t></w:r>')
    else:
        runs = f'<w:r><w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r>'
    return f'<w:p>{ppr}{runs}</w:p>'


def make_img_p(r_id, cx, cy):
    return ('<w:p><w:pPr><w:pStyle w:val="36"/></w:pPr><w:r><w:drawing '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            '<wp:docPr id="1" name="图片 1"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:nvPicPr><pic:cNvPr id="1" name="img"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{r_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


def make_tbl(rows, widths=None):
    n = max(len(r) for r in rows)
    if not widths:
        w = 8306 // n
        widths = [w] * n
    def cell(t, w):
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="{TBL_STYLE}"/></w:pPr><w:r><w:t>{xml_escape(t)}</w:t></w:r></w:p></w:tc>')
    borders = ('<w:tblBorders>' + ''.join(
        f'<w:{s} w:val="single" w:sz="4" w:color="BFBFBF"/>' for s in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV'])
        + '</w:tblBorders>')
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    trs = ''
    for ri, r in enumerate(rows):
        # 表头跨页重复：首行 trPr 加 tblHeader（§0.14 模板规范要求）
        trpr = '<w:trPr><w:tblHeader/></w:trPr>' if ri == 0 else ''
        trs += '<w:tr>' + trpr + ''.join(cell(str(c), widths[i] if i < len(widths) else widths[-1]) for i, c in enumerate(r)) + '</w:tr>'
    return ('<w:tbl><w:tblPr><w:tblW w:w="8306" w:type="dxa"/><w:jc w:val="center"/>'
            + borders + '</w:tblPr><w:tblGrid>' + grid + '</w:tblGrid>' + trs + '</w:tbl>')


def img_size(src):
    """返回 (cx, cy)（EMU）；高度按原图比例，宽=版心宽。读取失败时按 3:1 估算。"""
    try:
        from PIL import Image
        with Image.open(src) as im:
            iw, ih = im.size
        return IMG_W, int(IMG_W * ih / iw)
    except Exception:
        return IMG_W, IMG_W // 3


def build(data, base, out):
    with zipfile.ZipFile(base) as z:
        doc = z.read('word/document.xml').decode('utf-8')
        parts_src = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}

    # ---- 组装段落 ----
    paras = []
    if data.get('cover'):
        paras.append(make_p(STYLE_MAP['cover'], clean(data['cover'])))
    for item in data.get('toc', []):
        text, page = item[0], str(item[1])
        lvl = int(item[2]) if len(item) > 2 else 1
        paras.append(make_p(STYLE_MAP.get(f'toc{lvl}', '15'), f'{text}\t{page}'))

    media = {}
    rid = 100
    n_img = 0
    skipped_imgs = 0
    for b in data.get('blocks', []):
        t = b.get('type')
        if t == 'tbl':
            if b.get('caption'):
                paras.append(make_p(STYLE_MAP['cap_tbl'], clean(b['caption'])))
            paras.append(make_tbl(b['rows'], b.get('widths')))
            continue
        if t == 'img':
            src = b.get('src')
            n_img += 1
            if src and os.path.exists(src):
                cx, cy = img_size(src)
                key = f'word/media/image{n_img}.png'
                media[key] = open(src, 'rb').read()
                paras.append(make_img_p(f'rId{rid}', cx, cy))
                rid += 1
            else:
                skipped_imgs += 1
                paras.append(make_p('36', f'[图片素材未提供：{src or "无"} ]'))
            if b.get('caption'):
                paras.append(make_p(STYLE_MAP['cap_img'], clean(b['caption'])))
            continue
        text = b.get('text', '')
        sid = STYLE_MAP.get(t)
        if t in AUTO_NUM_KINDS:
            text = clean(text)
        paras.append(make_p(sid, text))

    # ---- 替换 body（保留原 sectPr；页边距强制终值） ----
    m = re.search(r'<w:body>(.*)</w:body>', doc, re.S)
    body = m.group(1)
    sm = re.search(r'<w:sectPr.*?</w:sectPr>', body, re.S)
    sectpr = sm.group(0)
    if re.search(r'<w:pgMar[^>]*/>', sectpr):
        sectpr = re.sub(r'<w:pgMar[^>]*/>',
                        f'<w:pgMar w:top="{PAGE_MAR[0]}" w:right="{PAGE_MAR[1]}" w:bottom="{PAGE_MAR[2]}" w:left="{PAGE_MAR[3]}" w:header="720" w:footer="720" w:gutter="0"/>',
                        sectpr)
    doc2 = doc[:m.start(1)] + ''.join(paras) + sectpr + doc[m.end(1):]

    # ---- 打包（.dotx → .docx；含图片部件与关系） ----
    content_types = parts_src['[Content_Types].xml'].decode('utf-8')
    if 'Extension="png"' not in content_types:
        content_types = content_types.replace('<Default Extension="wmf"',
                                              '<Default Extension="png" ContentType="image/png"/><Default Extension="wmf"')
    content_types = content_types.replace(
        'application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml')
    rels = parts_src['word/_rels/document.xml.rels'].decode('utf-8')
    add_rels = ''
    for i in range(n_img - skipped_imgs):
        add_rels += (f'<Relationship Id="rId{100 + i}" '
                     'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                     f'Target="media/image{i + 1}.png"/>')
    rels = rels.replace('</Relationships>', add_rels + '</Relationships>')

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data_b in parts_src.items():
            if name == 'word/document.xml':
                data_b = doc2.encode('utf-8')
            elif name == '[Content_Types].xml':
                data_b = content_types.encode('utf-8')
            elif name == 'word/_rels/document.xml.rels':
                data_b = rels.encode('utf-8')
            zout.writestr(name, data_b)
        for name, blob in media.items():
            zout.writestr(name, blob)

    # ---- 自检 ----
    with zipfile.ZipFile(out) as zv:
        d = zv.read('word/document.xml').decode('utf-8')
    bad = sum(d.count(x) for x in ['一、项目', '1.1 建设', '图1 系统', '表1 设备'])  # 常见手写编号形态
    print(f'生成完成：{out}')
    print(f'段落数：{len(paras)} | 图片：{n_img - skipped_imgs} 张（跳过 {skipped_imgs}）| 手写编号残留检查：{bad}（应关注 0）')
    return out


def main():
    ap = argparse.ArgumentParser(description='内容 → 标准样式 Word 文档')
    ap.add_argument('--input', required=True, help='内容 JSON 路径')
    ap.add_argument('--out', required=True, help='输出 .docx 路径')
    ap.add_argument('--base', default=DEFAULT_BASE, help='基底模板（默认=专家团标准模板）')
    args = ap.parse_args()

    with open(args.input, encoding='utf-8') as f:
        data = json.load(f)
    if not os.path.exists(args.base):
        print('!! 基底模板不存在：', args.base)
        sys.exit(1)
    build(data, args.base, os.path.abspath(args.out))


if __name__ == '__main__':
    main()
