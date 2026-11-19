#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_text_count.py — 交付文件中文字符串"全 XML 去标签 + html.unescape"确定性计数

落实 ver-agent M1/M2/M3 铁律：
  M1 全 XML 部件去标签计数（docx/xlsx 遍历所有 .xml/.rels，禁止单部件 grep）
  M2 xlsx 数字实体须 html.unescape 解码（否则中文关键词全部假阴性为 0）
  M3 同目录残留材料一并扫描（docx/xlsx/pdf/md/bak 等全扫）

用法：
  python verify_text_count.py 某供应商 示例客户名 --paths "<样例目录>/01_某高校" [--no-decode]
  输出：每行 <文件>\t<词>=<次数> ...
"""
import sys, os, re, html, zipfile, argparse


def text_of_ooxml(fp):
    """docx/xlsx 全 XML 部件去标签拼接（M1）。"""
    z = zipfile.ZipFile(fp)
    s = ''
    for n in [x for x in z.namelist() if x.endswith('.xml') or x.endswith('.rels')]:
        s += re.sub(r'<[^>]+>', '', z.read(n).decode('utf8', 'ignore'))
    return s


def text_of_plain(fp):
    with open(fp, encoding='utf-8', errors='ignore') as f:
        return f.read()


def iter_files(paths):
    exts = ('.docx', '.xlsx', '.pdf', '.md', '.txt', '.bak')
    for p in paths:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                for f in fs:
                    if f.lower().endswith(exts):
                        yield os.path.join(root, f)
        else:
            yield p


def main():
    ap = argparse.ArgumentParser(description="交付文件中文关键词确定性计数（M1/M2/M3）")
    ap.add_argument('patterns', nargs='+', help='要计数的关键词')
    ap.add_argument('--paths', nargs='+', required=True, help='文件或目录（目录递归扫描常见格式）')
    ap.add_argument('--no-decode', action='store_true', help='跳过 html.unescape（仅当确认非 xlsx 实体时）')
    args = ap.parse_args()

    for fp in iter_files(args.paths):
        try:
            if fp.lower().endswith(('.docx', '.xlsx')):
                t = text_of_ooxml(fp)
            else:
                t = text_of_plain(fp)
            if not args.no_decode:
                t = html.unescape(t)   # M2：必须先解码再计数
            counts = {w: t.count(w) for w in args.patterns}
            print(fp + "\t" + "\t".join(f"{w}={c}" for w, c in counts.items()))
        except Exception as e:
            print(fp + "\tERR " + str(e))


if __name__ == '__main__':
    main()
