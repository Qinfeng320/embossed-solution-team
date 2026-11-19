#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_docx_metadata.py — .docx 元数据清洁（对外交付件必经步骤，纯 stdlib）

依据 references/style-guide.md 与 docx-agent「文档自检清单」（PR-005 新增）：
  1) docProps/core.xml：作者（dc:creator）/ 最后修改者（cp:lastModifiedBy）清空
  2) docProps/app.xml：Company / Manager 清空（若存在）
  3) docProps/custom.xml：清空全部自定义属性（编辑器账号标识、校对残留等所在处）
  4) customXml/ 部件：整体移除（含 .rels 与 [Content_Types].xml 引用清理）

⚠️ Word/WPS 每次保存后会重新写入属性，**保存后须重跑本脚本**。
用法：
  python clean_docx_metadata.py <file.docx> [--dry-run] [--clear-title]
"""
import sys, os, re, zipfile, shutil, time, argparse

CORE_CLEAR_TAGS = ["dc:creator", "cp:lastModifiedBy", "cp:lastPrinted"]
APP_CLEAR_TAGS = ["Company", "Manager"]


def _clear_tag(xml, tag):
    """清空 <tag>…</tag> 的内容（保留标签）；返回 (新xml, 清理数)。"""
    n = 0
    pattern = re.compile(r"(<%s)([^>]*?)(>)(.*?)(</%s>)" % (re.escape(tag), re.escape(tag)), re.S)

    def repl(m):
        nonlocal n
        if m.group(4).strip():
            n += 1
        return m.group(1) + m.group(2) + m.group(3) + m.group(5)

    return pattern.sub(repl, xml), n


def _clear_custom_properties(xml):
    """清空 docProps/custom.xml 全部 <property> 元素；返回 (新xml, 属性名列表)。"""
    names = re.findall(r'<property[^>]*\bname="([^"]+)"', xml)
    xml = re.sub(r"<property\b[^>]*/>", "", xml)          # 自闭合
    xml = re.sub(r"<property\b[^>]*>.*?</property>", "", xml, flags=re.S)  # 成对
    return xml, names


def _filter_relationships(xml):
    """删除所有 Target 指向 customXml 的 Relationship（自闭合/成对两种写法）。"""
    def keep(m):
        return "" if "customXml" in m.group(0) else m.group(0)
    xml = re.sub(r"<Relationship\b[^>]*/>", keep, xml)
    xml = re.sub(r"<Relationship\b[^>]*>.*?</Relationship>", keep, xml, flags=re.S)
    return xml


def _filter_content_types(xml):
    """删除 PartName 指向 /customXml/ 的 Override。"""
    return re.sub(r"<Override\b[^>]*/customXml/[^>]*/>", "", xml)


def clean(path, dry_run=False, clear_title=False):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        parts = {n: z.read(n) for n in names}

    log = []

    # 1) core.xml
    if "docProps/core.xml" in parts:
        xml = parts["docProps/core.xml"].decode("utf-8", "ignore")
        total = 0
        tags = list(CORE_CLEAR_TAGS) + (["dc:title"] if clear_title else [])
        for tag in tags:
            xml, n = _clear_tag(xml, tag)
            total += n
        parts["docProps/core.xml"] = xml.encode("utf-8")
        log.append(f"core.xml：清空 {total} 项（{', '.join(tags)}）")

    # 2) app.xml
    if "docProps/app.xml" in parts:
        xml = parts["docProps/app.xml"].decode("utf-8", "ignore")
        total = 0
        for tag in APP_CLEAR_TAGS:
            xml, n = _clear_tag(xml, tag)
            total += n
        parts["docProps/app.xml"] = xml.encode("utf-8")
        log.append(f"app.xml：清空 {total} 项（{', '.join(APP_CLEAR_TAGS)}）")

    # 3) custom.xml
    if "docProps/custom.xml" in parts:
        xml = parts["docProps/custom.xml"].decode("utf-8", "ignore")
        xml, prop_names = _clear_custom_properties(xml)
        parts["docProps/custom.xml"] = xml.encode("utf-8")
        log.append(f"custom.xml：清空 {len(prop_names)} 个自定义属性" +
                   (f"（{'、'.join(prop_names[:8])}{'…' if len(prop_names) > 8 else ''}）" if prop_names else ""))

    # 4) customXml 部件移除
    cx = [n for n in list(parts) if n.startswith("customXml/")]
    if cx:
        for n in cx:
            del parts[n]
        # 清理所有 rels 与 Content_Types 中的引用
        for n in list(parts):
            if n.endswith(".rels"):
                parts[n] = _filter_relationships(parts[n].decode("utf-8", "ignore")).encode("utf-8")
            elif n == "[Content_Types].xml":
                parts[n] = _filter_content_types(parts[n].decode("utf-8", "ignore")).encode("utf-8")
        log.append(f"customXml/：移除 {len(cx)} 个部件（含引用清理）")
    else:
        log.append("customXml/：无")

    print(f"文件: {path}")
    for line in log:
        print("  " + line)

    if dry_run:
        print("  [dry-run] 未写出")
        return

    # 安全写入：重打包到临时文件 → 读回验证 → 覆盖
    tmp = path + ".cleantmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:  # 保持原部件顺序（customXml 已从 parts 删除）
            if n in parts:
                zout.writestr(n, parts[n])
    with zipfile.ZipFile(tmp) as zc:  # 读回验证：部件可列举、core.xml 可解析
        _ = zc.namelist()
        _ = zc.read("docProps/core.xml")
    last = None
    for _ in range(6):
        try:
            shutil.copyfile(tmp, path)
            os.remove(tmp)
            print("  已写回（安全写入，读回验证通过）。")
            return
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise RuntimeError(f"写回失败（原文件可能被 Word/WPS/同步盘占用）：{last}；中间件保留在 {tmp}")


def main():
    ap = argparse.ArgumentParser(description="docx 元数据清洁（对外交付件必经步骤）")
    ap.add_argument("file")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写出")
    ap.add_argument("--clear-title", action="store_true", help="同时清空 dc:title（默认保留标题）")
    args = ap.parse_args()
    clean(args.file, args.dry_run, args.clear_title)


if __name__ == "__main__":
    main()
