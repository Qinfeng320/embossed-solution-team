#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_table_style.py — 为 .docx 注入统一表格样式，并让全部表格引用它。

（document-format-standards.md §0.10「表格统一样式」的确定性实现）

做四件事：
  ① 注入【表格样式】「方案表格」(SolutionTable)：全边框（外 1.0pt / 内 0.5pt · #BFBFBF）、
     单元格边距、表宽 100% 版心、单元格垂直居中、表行距 1.5 倍、
     表头行黑体 小四 12pt + 跨页重复（tblStylePr firstRow）。
  ② 注入【段落样式】「表格文字」(TableText)：宋体 · 小四 12pt · 1.5 倍行距 · 左对齐 ·
     首行不缩进 —— 该样式会出现在 Word/WPS 的「样式」窗格中，用于统一单元格内文字。
  ③ 给每张表的 <w:tblPr> 首子元素插入 <w:tblStyle>；给**数据行**各单元格段落套用
     「表格文字」（表头行不套，保留表格样式给的黑体）。
  ④ 剥离表级/单元格级/文字级直接格式（tblBorders / tcBorders / tblCellMar / tblW / tblInd /
     表内 rFonts·sz·szCs / 单元格段落的 spacing·ind / tcPr 的 shd），使样式真正生效。
     保留：tblGrid 列宽、tblLayout、行属性 tblHeader、单元格 tcW。

用法: python apply_table_style.py <file.docx> [...]
"""
import os
import re
import shutil
import sys
import zipfile

TBL_ID = 'SolutionTable'
PAR_ID = 'TableText'
SONG, HEI = '宋体', '黑体'
SZ = '24'            # 半磅 → 12pt（小四）
LINE = '360'         # 1.5 倍行距（240 = 单倍）
COLOR = 'BFBFBF'

TBL_STYLE = (
    f'<w:style w:type="table" w:styleId="{TBL_ID}">'
    f'<w:name w:val="方案表格"/><w:aliases w:val="方案表;方案表格;SolutionTable"/>'
    f'<w:basedOn w:val="TableNormal"/><w:uiPriority w:val="1"/><w:qFormat/>'
    f'<w:pPr><w:spacing w:line="{LINE}" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr>'
    f'<w:rPr><w:rFonts w:ascii="{SONG}" w:eastAsia="{SONG}" w:hAnsi="{SONG}" w:cs="{SONG}" w:hint="eastAsia"/>'
    f'<w:sz w:val="{SZ}"/><w:szCs w:val="{SZ}"/></w:rPr>'
    f'<w:tblPr><w:tblW w:w="5000" w:type="pct"/>'
    f'<w:tblBorders>'
    f'<w:top w:val="single" w:sz="8" w:space="0" w:color="{COLOR}"/>'
    f'<w:left w:val="single" w:sz="8" w:space="0" w:color="{COLOR}"/>'
    f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="{COLOR}"/>'
    f'<w:right w:val="single" w:sz="8" w:space="0" w:color="{COLOR}"/>'
    f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{COLOR}"/>'
    f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="{COLOR}"/>'
    f'</w:tblBorders><w:tblLayout w:type="autofit"/>'
    f'<w:tblCellMar><w:top w:w="28" w:type="dxa"/><w:left w:w="85" w:type="dxa"/>'
    f'<w:bottom w:w="120" w:type="dxa"/><w:right w:w="85" w:type="dxa"/></w:tblCellMar></w:tblPr>'
    f'<w:tcPr><w:vAlign w:val="center"/></w:tcPr>'
    f'<w:tblStylePr w:type="firstRow">'
    f'<w:pPr><w:spacing w:line="{LINE}" w:lineRule="auto"/></w:pPr>'
    f'<w:rPr><w:rFonts w:ascii="{HEI}" w:eastAsia="{HEI}" w:hAnsi="{HEI}" w:cs="{HEI}" w:hint="eastAsia"/>'
    f'<w:sz w:val="{SZ}"/><w:szCs w:val="{SZ}"/></w:rPr>'
    f'<w:trPr><w:tblHeader/></w:trPr>'
    f'<w:tcPr><w:vAlign w:val="center"/></w:tcPr>'
    f'</w:tblStylePr></w:style>'
)

PAR_STYLE = (
    f'<w:style w:type="paragraph" w:styleId="{PAR_ID}">'
    f'<w:name w:val="表格文字"/><w:aliases w:val="表格文字;TableText"/>'
    f'<w:basedOn w:val="Normal"/><w:uiPriority w:val="2"/><w:qFormat/>'
    f'<w:pPr><w:spacing w:line="{LINE}" w:lineRule="auto"/>'
    f'<w:ind w:firstLine="0" w:firstLineChars="0"/><w:jc w:val="left"/></w:pPr>'
    f'<w:rPr><w:rFonts w:ascii="{SONG}" w:eastAsia="{SONG}" w:hAnsi="{SONG}" w:cs="{SONG}" w:hint="eastAsia"/>'
    f'<w:sz w:val="{SZ}"/><w:szCs w:val="{SZ}"/></w:rPr></w:style>'
)


def _fix_par(m):
    """给单元格段落套用「表格文字」并清掉直接行距/缩进/旧 pStyle。"""
    p = m.group(0)
    p = re.sub(r'<w:spacing [^/]*/>', '', p)
    p = re.sub(r'<w:ind [^/]*/>', '', p)
    # 清除已有的「表格文字」pStyle，避免重复跑时堆叠
    p = re.sub(rf'<w:pStyle w:val="{PAR_ID}"\s*/>', '', p)
    if '<w:pPr>' in p:
        p = p.replace('<w:pPr>', f'<w:pPr><w:pStyle w:val="{PAR_ID}"/>', 1)
    elif '<w:pPr/>' in p:
        p = p.replace('<w:pPr/>', f'<w:pPr><w:pStyle w:val="{PAR_ID}"/></w:pPr>', 1)
    else:
        p = re.sub(r'^(<w:p(?: [^>]*)?>)', rf'\1<w:pPr><w:pStyle w:val="{PAR_ID}"/></w:pPr>', p, count=1)
    return p


def process_table(tbl: str) -> str:
    tbl = re.sub(r'<w:tblBorders>.*?</w:tblBorders>', '', tbl, flags=re.S)
    tbl = re.sub(r'<w:tblCellMar>.*?</w:tblCellMar>', '', tbl, flags=re.S)
    tbl = re.sub(r'<w:tblW [^/]*/>', '', tbl)
    tbl = re.sub(r'<w:tblInd [^/]*/>', '', tbl)
    tbl = re.sub(r'<w:tcBorders>.*?</w:tcBorders>', '', tbl, flags=re.S)
    tbl = re.sub(r'<w:shd [^/]*/>', '', tbl)
    tbl = re.sub(r'<w:rPr>.*?</w:rPr>',
                 lambda m: re.sub(r'<w:rFonts [^/]*/>|<w:sz [^/]*/>|<w:szCs [^/]*/>', '', m.group(0)),
                 tbl, flags=re.S)
    # 先清除已有的同类引用，避免重复插入（tblPr 内 tblStyle 只允许 1 个）
    tbl = re.sub(r'<w:tblStyle [^/]*/>', '', tbl)
    if '<w:tblPr>' in tbl:
        tbl = tbl.replace('<w:tblPr>', f'<w:tblPr><w:tblStyle w:val="{TBL_ID}"/>', 1)
    # 数据行（第 2 行起）套用「表格文字」；表头行不套，保留黑体
    segs = re.split(r'(?=<w:tr[ >])', tbl)
    out = []
    for k, seg in enumerate(segs):
        if k == 0 or not seg.startswith('<w:tr'):
            out.append(seg)
            continue
        out.append(re.sub(r'<w:p[ >].*?</w:p>', _fix_par, seg, flags=re.S))
    return ''.join(out)


def process(path: str):
    zin = zipfile.ZipFile(path, 'r')
    payload = {n: zin.read(n) for n in zin.namelist()}
    zin.close()

    doc = payload['word/document.xml'].decode('utf-8')
    n_tbl = len(re.findall(r'<w:tbl>', doc))
    doc = re.sub(r'<w:tbl>.*?</w:tbl>', lambda m: process_table(m.group(0)), doc, flags=re.S)
    payload['word/document.xml'] = doc.encode('utf-8')

    sty = payload['word/styles.xml'].decode('utf-8')
    for sid, xml in ((TBL_ID, TBL_STYLE), (PAR_ID, PAR_STYLE)):
        sty = re.sub(rf'<w:style [^>]*w:styleId="{sid}".*?</w:style>', '', sty, flags=re.S)
        sty = sty.replace('</w:styles>', xml + '</w:styles>', 1)
    payload['word/styles.xml'] = sty.encode('utf-8')

    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for k, v in payload.items():
            zout.writestr(k, v)
    try:
        shutil.copyfile(tmp, path)
    except PermissionError:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return n_tbl


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(2)
    for p in sys.argv[1:]:
        if not os.path.isfile(p):
            print(f'[apply_table_style] 跳过（不存在）: {p}')
            continue
        n = process(p)
        print(f'[apply_table_style] {os.path.basename(p)} | 已注入「方案表格」+「表格文字」，处理表格 {n} 张')
