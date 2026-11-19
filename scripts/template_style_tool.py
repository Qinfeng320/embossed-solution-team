#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""专家团标准模板 · 样式操作工具（template_style_tool.py）

将"模板设置内容"脚本化：以后修改模板样式/页面，一条命令完成。
每次写操作：自动备份（.bak_时间戳）→ 修改 → 读回验证 → 写回（文件被占用时自动重试）。

用法（默认目标 = 专家团标准模板 assets/样式模板.dotx）：
  python template_style_tool.py list   [--filter 关键字]        # 列出样式概览
  python template_style_tool.py show   --style "toc 1"          # 查看单一样式完整 XML
  python template_style_tool.py set    --style "toc 1" [--sz 26] [--line 360]
                                       [--font-ea 黑体] [--font-ascii 黑体]
                                       [--bold on|off] [--align center|left|right|both]
                                       [--first-line N] [--left N] [--before N] [--after N]
  python template_style_tool.py hide   --style "heading 7"      # 隐藏样式（hidden+semiHidden，去推荐标记）
  python template_style_tool.py remove --style "List Number" [--no-cascade]   # 删除样式（自动级联清理专属编号）
  python template_style_tool.py page   [--top 1440] [--right 1800] [--bottom 1440] [--left 1800]

单位：整数 = 缇（twips）；带 cm 后缀（如 2.54cm）= 厘米（1 cm ≈ 567 缇）。
样式定位：--style 接受样式名（w:name，如 "heading 2"、"封面"）或 styleId。
通用参数：--doc <路径>（默认 = 插件 assets/样式模板.dotx）
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_DOC = os.path.join(PLUGIN_DIR, 'assets', '样式模板.dotx')

# ---- 元素顺序表（用于合规插入） ----
RPR_ORDER = ['rStyle', 'rFonts', 'b', 'bCs', 'i', 'iCs', 'caps', 'smallCaps', 'strike',
             'dstrike', 'outline', 'shadow', 'emboss', 'imprint', 'noProof', 'snapToGrid',
             'vanish', 'webHidden', 'color', 'spacing', 'w', 'kern', 'position', 'sz', 'szCs',
             'highlight', 'u', 'effect', 'bdr', 'shd', 'fitText', 'vertAlign', 'rtl', 'cs',
             'em', 'lang', 'eastAsianLayout', 'specVanish', 'oMath']
PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl',
             'numPr', 'suppressLineNumbers', 'pBdr', 'shd', 'tabs', 'suppressAutoHyphens',
             'kinsoku', 'wordWrap', 'overflowPunct', 'topLinePunct', 'autoSpaceDE',
             'autoSpaceDN', 'bidi', 'adjustRightInd', 'snapToGrid', 'spacing', 'ind',
             'contextualSpacing', 'mirrorIndents', 'suppressOverlap', 'jc', 'textDirection',
             'textAlignment', 'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle', 'rPr',
             'sectPr', 'pPrChange']
STYLE_ORDER = ['name', 'aliases', 'basedOn', 'next', 'link', 'autoRedefine', 'hidden',
               'uiPriority', 'semiHidden', 'unhideWhenUsed', 'qFormat', 'locked', 'personal',
               'personalCompose', 'personalReply', 'rsid', 'pPr', 'rPr', 'tblPr', 'trPr',
               'tcPr', 'tblStylePr']


def _idx(tag, order):
    return order.index(tag) if tag in order else len(order) + 1


def _insert_ordered(xml, new_el, order):
    """按元素顺序表把自闭合元素插入到 xml 内合规位置。"""
    tag = re.match(r'<w:([A-Za-z0-9]+)', new_el).group(1)
    want = _idx(tag, order)
    pos = len(xml)
    for m in re.finditer(r'<w:([A-Za-z0-9]+)[ />]', xml):
        if _idx(m.group(1), order) > want:
            pos = m.start()
            break
    return xml[:pos] + new_el + xml[pos:]


def _set_attr(attrs, name, value):
    if re.search(r'\b' + re.escape(name) + r'="[^"]*"', attrs):
        return re.sub(r'\b' + re.escape(name) + r'="[^"]*"', f'{name}="{value}"', attrs)
    return (attrs + f' {name}="{value}"').strip()


def _parse_len(v):
    """解析长度：整数=缇；xx cm=厘米（×567 取整）。"""
    v = str(v).strip()
    if v.endswith('cm'):
        return int(round(float(v[:-2]) * 567))
    return int(v)


# ---- 读/写 ----
def _read_parts(path):
    """读取全部部件（读完立即关闭句柄——避免自锁导致后续写回失败）。"""
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
    return parts


def _save_with_retry(src, parts, verify_names):
    """写临时 → 读回验证 → 独占预检 + 重试写回（全程无自持句柄）。"""
    tmp = src + '.tmp_style_tool'
    with zipfile.ZipFile(src) as z0:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in z0.infolist():
                data = parts.get(item.filename)
                if data is None:
                    data = z0.read(item.filename)
                zout.writestr(item, data)
    for n in verify_names:
        with zipfile.ZipFile(tmp) as zv:
            ET.fromstring(zv.read(n))
    for i in range(1, 61):
        try:
            f = open(src, 'r+b'); f.close()
            os.replace(tmp, src)
            return True
        except PermissionError:
            if i % 15 == 0:
                print(f'  文件被占用，重试中（第 {i} 次）…')
            time.sleep(1)
    print('!! 写回失败：文件持续被占用；临时文件保留于', tmp)
    return False


def _backup(src):
    bak = f'{src}.bak_{int(time.time())}'
    shutil.copy2(src, bak)
    return bak


def _find_style(styles, key):
    for m in re.finditer(r'<w:style ([^>]*)>(.*?)</w:style>', styles, re.S):
        attrs, body = m.groups()
        sid = re.search(r'w:styleId="([^"]+)"', attrs)
        name = re.search(r'<w:name w:val="([^"]+)"', body)
        if (sid and sid.group(1) == key) or (name and name.group(1) == key):
            return m
    return None


# ---- 属性编辑 ----
def _edit_rpr(body, tag, value):
    m = re.search(r'<w:rPr>(.*?)</w:rPr>', body, re.S)
    new_el = f'<w:{tag} w:val="{value}"/>'
    if m:
        rpr = m.group(1)
        if re.search(r'<w:' + tag + r'[ />]', rpr):
            rpr2 = re.sub(r'<w:' + tag + r'[^>]*/>', new_el, rpr)
        else:
            rpr2 = _insert_ordered(rpr, new_el, RPR_ORDER)
        return body.replace(m.group(0), f'<w:rPr>{rpr2}</w:rPr>')
    return body.replace('</w:style>', f'<w:rPr>{new_el}</w:rPr></w:style>')


def _edit_ppr_simple(body, tag, value):
    m = re.search(r'<w:pPr>(.*?)</w:pPr>', body, re.S)
    new_el = f'<w:{tag} w:val="{value}"/>'
    if m:
        ppr = m.group(1)
        if re.search(r'<w:' + tag + r'[ />]', ppr):
            ppr2 = re.sub(r'<w:' + tag + r'[^>]*/>', new_el, ppr)
        else:
            ppr2 = _insert_ordered(ppr, new_el, PPR_ORDER)
        return body.replace(m.group(0), f'<w:pPr>{ppr2}</w:pPr>')
    return body.replace('</w:style>', f'<w:pPr>{new_el}</w:pPr></w:style>')


def _edit_spacing(body, line=None, before=None, after=None):
    m = re.search(r'<w:spacing([^>]*)/>', body)
    if m:
        attrs = m.group(1)
        if line is not None:
            attrs = _set_attr(attrs, 'w:line', line)
            attrs = _set_attr(attrs, 'w:lineRule', 'auto')
        if before is not None:
            attrs = _set_attr(attrs, 'w:before', before)
        if after is not None:
            attrs = _set_attr(attrs, 'w:after', after)
        return body.replace(m.group(0), f'<w:spacing{attrs}/>')
    parts = []
    if line is not None:
        parts.append(f'w:line="{line}" w:lineRule="auto"')
    if before is not None:
        parts.append(f'w:before="{before}"')
    if after is not None:
        parts.append(f'w:after="{after}"')
    new_el = f'<w:spacing {" ".join(parts)}/>'
    m2 = re.search(r'<w:pPr>(.*?)</w:pPr>', body, re.S)
    if m2:
        ppr2 = _insert_ordered(m2.group(1), new_el, PPR_ORDER)
        return body.replace(m2.group(0), f'<w:pPr>{ppr2}</w:pPr>')
    return body.replace('</w:style>', f'<w:pPr>{new_el}</w:pPr></w:style>')


def _edit_ind(body, first_line=None, left=None):
    m = re.search(r'<w:ind([^>]*)/>', body)
    if m:
        attrs = m.group(1)
        if first_line is not None:
            attrs = _set_attr(attrs, 'w:firstLine', first_line)
            attrs = _set_attr(attrs, 'w:firstLineChars', '0')
        if left is not None:
            attrs = _set_attr(attrs, 'w:left', left)
        return body.replace(m.group(0), f'<w:ind{attrs}/>')
    parts = []
    if first_line is not None:
        parts.append(f'w:firstLine="{first_line}" w:firstLineChars="0"')
    if left is not None:
        parts.append(f'w:left="{left}"')
    new_el = f'<w:ind {" ".join(parts)}/>'
    m2 = re.search(r'<w:pPr>(.*?)</w:pPr>', body, re.S)
    if m2:
        ppr2 = _insert_ordered(m2.group(1), new_el, PPR_ORDER)
        return body.replace(m2.group(0), f'<w:pPr>{ppr2}</w:pPr>')
    return body.replace('</w:style>', f'<w:pPr>{new_el}</w:pPr></w:style>')


def _edit_fonts(body, ea=None, ascii_=None):
    m = re.search(r'<w:rFonts([^>]*)/>', body)
    if m:
        attrs = m.group(1)
        if ea:
            attrs = _set_attr(attrs, 'w:eastAsia', ea)
        if ascii_:
            attrs = _set_attr(attrs, 'w:ascii', ascii_)
            attrs = _set_attr(attrs, 'w:hAnsi', ascii_)
        return body.replace(m.group(0), f'<w:rFonts{attrs}/>')
    parts = []
    if ascii_:
        parts.append(f'w:ascii="{ascii_}" w:hAnsi="{ascii_}"')
    if ea:
        parts.append(f'w:eastAsia="{ea}"')
    new_el = f'<w:rFonts {" ".join(parts)}/>'
    m2 = re.search(r'<w:rPr>(.*?)</w:rPr>', body, re.S)
    if m2:
        rpr2 = _insert_ordered(m2.group(1), new_el, RPR_ORDER)
        return body.replace(m2.group(0), f'<w:rPr>{rpr2}</w:rPr>')
    return body.replace('</w:style>', f'<w:rPr>{new_el}</w:rPr></w:style>')


def do_set(styles, key, args):
    m = _find_style(styles, key)
    if not m:
        print(f'!! 未找到样式：{key}')
        return None
    body = m.group(0)
    changes = []
    if args.sz is not None:
        body = _edit_rpr(body, 'sz', args.sz)
        body = _edit_rpr(body, 'szCs', args.sz)
        changes.append(f'sz/szCs={args.sz}')
    if args.line is not None or args.before is not None or args.after is not None:
        body = _edit_spacing(body, args.line, args.before, args.after)
        changes.append(f'spacing(line={args.line}, before={args.before}, after={args.after})')
    if args.font_ea or args.font_ascii:
        body = _edit_fonts(body, args.font_ea, args.font_ascii)
        changes.append(f'fonts(ea={args.font_ea}, ascii={args.font_ascii})')
    if args.bold is not None:
        on = args.bold == 'on'
        m2 = re.search(r'<w:rPr>(.*?)</w:rPr>', body, re.S)
        if m2:
            rpr = m2.group(1)
            el = '<w:b/>' if on else '<w:b w:val="0"/>'
            if re.search(r'<w:b[ />]', rpr):
                rpr2 = re.sub(r'<w:b[^>]*/>', el, rpr)
            else:
                rpr2 = _insert_ordered(rpr, el, RPR_ORDER)
            body = body.replace(m2.group(0), f'<w:rPr>{rpr2}</w:rPr>')
        else:
            body = body.replace('</w:style>', f'<w:rPr>{"<w:b/>" if on else "<w:b w:val=\"0\"/>"}</w:rPr></w:style>')
        changes.append(f'bold={args.bold}')
    if args.align:
        body = _edit_ppr_simple(body, 'jc', args.align)
        changes.append(f'align={args.align}')
    if args.first_line is not None or args.left is not None:
        body = _edit_ind(body, args.first_line, args.left)
        changes.append(f'ind(firstLine={args.first_line}, left={args.left})')
    if not changes:
        print('（未指定任何修改参数，未做变更。可用 --sz/--line/--font-ea/--bold/--align 等）')
        return None
    print(f'样式「{key}」修改：' + '；'.join(changes))
    return styles.replace(m.group(0), body)


def do_hide(styles, key):
    m = _find_style(styles, key)
    if not m:
        print(f'!! 未找到样式：{key}')
        return None
    body = m.group(0)
    body = body.replace('<w:qFormat/>', '').replace('<w:unhideWhenUsed/>', '')
    if '<w:uiPriority' in body:
        body = re.sub(r'<w:uiPriority w:val="\d+"/>', '<w:uiPriority w:val="99"/>', body)
    else:
        body = _insert_ordered(body, '<w:uiPriority w:val="99"/>', STYLE_ORDER)
    if '<w:hidden/>' not in body:
        body = _insert_ordered(body, '<w:hidden/>', STYLE_ORDER)
    if '<w:semiHidden/>' not in body:
        body = _insert_ordered(body, '<w:semiHidden/>', STYLE_ORDER)
    print(f'样式「{key}」已隐藏（hidden + semiHidden，qFormat/unhideWhenUsed 已移除）')
    return styles.replace(m.group(0), body)


def do_remove(styles, numbering, key, cascade=True):
    m = _find_style(styles, key)
    if not m:
        print(f'!! 未找到样式：{key}')
        return None, numbering
    body = m.group(0)
    numid = re.search(r'<w:numId w:val="(\d+)"/>', body)
    styles2 = styles.replace(body, '')
    print(f'样式「{key}」已删除')
    if cascade and numid:
        nid = numid.group(1)
        # 该 numId 是否仍被其它样式引用？
        if f'<w:numId w:val="{nid}"/>' not in styles2:
            mn = re.search(r'<w:num w:numId="' + nid + r'">.*?</w:num>', numbering, re.S)
            if mn:
                aid = re.search(r'<w:abstractNumId w:val="(\d+)"/>', mn.group(0)).group(1)
                numbering = numbering.replace(mn.group(0), '')
                # abstractNum 是否仍被其它 num 引用？
                if f'<w:abstractNumId w:val="{aid}"/>' not in numbering:
                    ma = re.search(r'<w:abstractNum [^>]*w:abstractNumId="' + aid + r'"[^>]*>.*?</w:abstractNum>', numbering, re.S)
                    if ma:
                        numbering = numbering.replace(ma.group(0), '')
                        print(f'  级联：编号链路 numId={nid} / abstractNumId={aid} 一并删除')
                else:
                    print(f'  级联：numId={nid} 已删除（abstractNumId={aid} 仍被其它列表引用，保留）')
    return styles2, numbering


def do_page(doc_xml, top=None, right=None, bottom=None, left=None):
    m = re.search(r'<w:sectPr.*?</w:sectPr>', doc_xml, re.S)
    if not m:
        print('!! 未找到 sectPr')
        return None
    sect = m.group(0)
    pm = re.search(r'<w:pgMar([^>]*)/>', sect)
    if pm:
        attrs = pm.group(1)
        for name, v in [('w:top', top), ('w:right', right), ('w:bottom', bottom), ('w:left', left)]:
            if v is not None:
                attrs = _set_attr(attrs, name, v)
        sect2 = sect.replace(pm.group(0), f'<w:pgMar{attrs}/>')
    else:
        parts = [f'{k}="{v}"' for k, v in [('w:top', top), ('w:right', right), ('w:bottom', bottom), ('w:left', left)] if v is not None]
        sect2 = sect.replace('>', f'><w:pgMar {" ".join(parts)}/>', 1)
    print('页面设置修改：' + '，'.join(f'{k}={v} 缇' for k, v in [('上', top), ('右', right), ('下', bottom), ('左', left)] if v is not None))
    return doc_xml.replace(sect, sect2)


# ---- 命令 ----
def cmd_list(styles, flt=None):
    rows = []
    for m in re.finditer(r'<w:style ([^>]*)>(.*?)</w:style>', styles, re.S):
        attrs, body = m.groups()
        sid = re.search(r'w:styleId="([^"]+)"', attrs)
        typ = re.search(r'w:type="([^"]+)"', attrs)
        name = re.search(r'<w:name w:val="([^"]+)"', body)
        sz = re.search(r'<w:sz w:val="(\d+)"/>', body)
        num = re.search(r'<w:numId w:val="(\d+)"/>', body)
        hid = 'hidden' if '<w:hidden/>' in body else ''
        nm = name.group(1) if name else '?'
        if flt and flt not in nm and flt not in (sid.group(1) if sid else ''):
            continue
        rows.append(f'  [{sid.group(1) if sid else "?"}] {nm} ({typ.group(1) if typ else "?"})'
                    + (f' sz={sz.group(1)}' if sz else '')
                    + (f' numId={num.group(1)}' if num else '')
                    + (f' {hid}' if hid else ''))
    print(f'共 {len(rows)} 个样式' + (f'（筛选：{flt}）' if flt else '') + '：')
    print('\n'.join(rows))


def main():
    ap = argparse.ArgumentParser(description='专家团标准模板 · 样式操作工具', add_help=True)
    ap.add_argument('command', choices=['list', 'show', 'set', 'hide', 'remove', 'page'])
    ap.add_argument('--doc', default=DEFAULT_DOC)
    ap.add_argument('--style', default=None)
    ap.add_argument('--filter', default=None)
    ap.add_argument('--sz', type=int, default=None)
    ap.add_argument('--line', type=int, default=None)
    ap.add_argument('--before', type=int, default=None)
    ap.add_argument('--after', type=int, default=None)
    ap.add_argument('--font-ea', dest='font_ea', default=None)
    ap.add_argument('--font-ascii', dest='font_ascii', default=None)
    ap.add_argument('--bold', choices=['on', 'off'], default=None)
    ap.add_argument('--align', choices=['center', 'left', 'right', 'both'], default=None)
    ap.add_argument('--first-line', dest='first_line', type=int, default=None)
    ap.add_argument('--left', type=int, default=None)
    ap.add_argument('--top', default=None)
    ap.add_argument('--right', default=None)
    ap.add_argument('--bottom', default=None)
    ap.add_argument('--no-cascade', action='store_true')
    args = ap.parse_args()

    doc = os.path.abspath(args.doc)
    if not os.path.exists(doc):
        print('!! 文件不存在：', doc)
        sys.exit(1)
    is_default = os.path.normcase(doc) == os.path.normcase(os.path.abspath(DEFAULT_DOC))
    print(f'目标：{doc}' + ('（专家团标准模板）' if is_default else ''))

    parts = _read_parts(doc)
    styles = parts.get('word/styles.xml', b'').decode('utf-8')
    numbering = parts.get('word/numbering.xml', b'').decode('utf-8')
    doc_xml = parts.get('word/document.xml', b'').decode('utf-8')

    if args.command == 'list':
        cmd_list(styles, args.filter)
        return
    if args.command == 'show':
        m = _find_style(styles, args.style) if args.style else None
        if not m:
            print('!! 未找到样式：', args.style)
            sys.exit(1)
        print(m.group(0))
        return

    # ---- 写操作：备份 → 修改 → 验证 → 写回 ----
    bak = _backup(doc)
    print(f'已备份：{bak}')

    if args.command == 'set':
        s2 = do_set(styles, args.style, args)
        if s2 is None:
            os.remove(bak)
            sys.exit(1)
        parts['word/styles.xml'] = s2.encode('utf-8')
        verify = ['word/styles.xml']
    elif args.command == 'hide':
        s2 = do_hide(styles, args.style)
        if s2 is None:
            os.remove(bak)
            sys.exit(1)
        parts['word/styles.xml'] = s2.encode('utf-8')
        verify = ['word/styles.xml']
    elif args.command == 'remove':
        s2, n2 = do_remove(styles, numbering, args.style, cascade=not args.no_cascade)
        if s2 is None:
            os.remove(bak)
            sys.exit(1)
        parts['word/styles.xml'] = s2.encode('utf-8')
        parts['word/numbering.xml'] = n2.encode('utf-8')
        verify = ['word/styles.xml', 'word/numbering.xml']
    else:  # page
        v = {k: (_parse_len(getattr(args, k)) if getattr(args, k) is not None else None)
             for k in ['top', 'right', 'bottom', 'left']}
        if all(x is None for x in v.values()):
            print('（未指定页面参数）')
            os.remove(bak)
            sys.exit(1)
        d2 = do_page(doc_xml, v['top'], v['right'], v['bottom'], v['left'])
        if d2 is None:
            os.remove(bak)
            sys.exit(1)
        parts['word/document.xml'] = d2.encode('utf-8')
        verify = ['word/document.xml']

    ok = _save_with_retry(doc, parts, verify)
    if ok:
        h = hashlib.sha256(open(doc, 'rb').read()).hexdigest()
        print(f'完成。新 SHA-256：{h[:16]}…  大小：{os.path.getsize(doc)} bytes')
        if is_default:
            print('提示：模板已更新——如本次为定版调整，请同步 ① 工作区规范修订记录 ② 规范/文档中的 SHA 引用。')
    else:
        print('可稍后重跑（文件被占用时工具会自动重试）。')
        sys.exit(2)


if __name__ == '__main__':
    main()
