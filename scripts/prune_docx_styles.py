#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prune_docx_styles.py — 裁剪 .docx 中未被使用的样式定义。

（document-format-standards.md §0.4 ② 「样式清理」的确定性实现）

为什么需要本脚本
----------------
html-to-docx 基于 python-docx 默认模板生成文档，`word/styles.xml` 会打包 **160 余个**
样式定义，而实际文档通常只引用 4~5 个。这些冗余样式会让 Word 的"样式"面板出现
Book Title / Intense Emphasis / Quote / TOC Heading 等大量用不到的条目，污染交付件。

处理逻辑
--------
  1. 扫描 `word/document.xml` / `word/header*.xml` / `word/footer*.xml`，收集实际引用
     的样式 ID（`w:pStyle` / `w:rStyle` / `w:tblStyle`）。
  2. 保留集合 = 被引用样式 ∪ {Normal, DefaultParagraphFont, TableNormal, NoList}
     ∪ 其 `basedOn` / `next` / `link` 指向样式的传递闭包（含被段落样式 link 的字符样式）。
  3. 从 `word/styles.xml` 与 `word/stylesWithEffects.xml` 中删除其余 `<w:style>`；
     `docDefaults` 等非 `<w:style>` 内容原样保留。
  4. **清理 `latentStyles`**：清空 `<w:lsdException>` 并把默认置为 `defSemiHidden=1` /
     `defUnhideWhenUsed=0`。仅删 `<w:style>` 不够——latent 声明会让 Word 把
     "标题 3 / 标题 4 / Title / Quote" 等**未使用**的内置样式照样显示在样式面板里。

用法:
    python prune_docx_styles.py <file.docx> [file2.docx ...]

依赖: lxml（可用 html-to-docx 托管 venv 的解释器运行）
注意: 目标 .docx 可能被 Word / 预览面板占用——先写临时文件、再 shutil.copyfile 覆盖。
"""
import os
import re
import shutil
import sys
import zipfile

try:
    from lxml import etree
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "[prune_docx_styles] 需要 lxml：请用 html-to-docx 托管 venv 的 python 运行，"
        "或 pip install lxml\n"
    )
    sys.exit(2)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
Q = lambda t: f"{{{W}}}{t}"
MANDATORY = {"Normal", "DefaultParagraphFont", "TableNormal", "NoList"}
STYLE_PARTS = ("word/styles.xml", "word/stylesWithEffects.xml")
REF_PARTS_RE = re.compile(r"word/(document|header\d*|footer\d*)\.xml")


def used_ids(z: zipfile.ZipFile) -> set:
    """收集正文/页眉/页脚中实际引用的样式 ID。"""
    used = set()
    for n in z.namelist():
        if REF_PARTS_RE.fullmatch(n):
            x = z.read(n).decode("utf-8")
            for attr in ("pStyle", "rStyle", "tblStyle"):
                used |= set(re.findall(rf'<w:{attr} w:val="([^"]+)"', x))
    return used


def clean_latent_styles(root) -> int:
    """将 latentStyles 中未使用的内置样式统一置为隐藏。

    仅删除 `<w:style>` 定义还不够：`<w:latentStyles>` 里的 `<w:lsdException>`
    会让 Word 把"标题 3 / 标题 4 / Title / Quote"等**未被引用的内置样式**照样显示在
    样式面板里。本函数清空全部 lsdException，并把默认行为改为 semiHidden=1 /
    unhideWhenUsed=0；显式定义在 styles.xml 中的样式（如 Heading 1/2）不受影响，
    仍会正常显示。返回被清除的条目数。
    """
    n = 0
    for ls in root.findall(Q("latentStyles")):
        for exc in ls.findall(Q("lsdException")):
            ls.remove(exc)
            n += 1
        ls.set(Q("defSemiHidden"), "1")
        ls.set(Q("defUnhideWhenUsed"), "0")
        if ls.get(Q("count")) is not None:
            ls.set(Q("count"), "0")
    return n


def prune_styles_xml(data: bytes, used: set):
    """删除未被引用的 <w:style>，并清理 latentStyles，返回 (新字节, 删除统计)。"""
    root = etree.fromstring(data)
    styles = root.findall(Q("style"))
    by_id = {s.get(Q("styleId")): s for s in styles}
    keep = set(used) | MANDATORY

    # 正向闭包：basedOn / next / link 指向的样式一并保留
    changed = True
    while changed:
        changed = False
        for sid in list(keep):
            s = by_id.get(sid)
            if s is None:
                continue
            for tag in ("basedOn", "next", "link"):
                e = s.find(Q(tag))
                if e is not None:
                    v = e.get(Q("val"))
                    if v and v not in keep and v in by_id:
                        keep.add(v)
                        changed = True
    # 反向：被保留段落样式 link 的字符样式
    for sid, s in by_id.items():
        l = s.find(Q("link"))
        if l is not None and l.get(Q("val")) in keep:
            keep.add(sid)

    removed = []
    for s in styles:
        sid = s.get(Q("styleId"))
        if sid not in keep:
            root.remove(s)
            removed.append(sid)

    latent_removed = clean_latent_styles(root)
    return (
        etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True),
        removed,
        latent_removed,
    )


def process(path: str):
    zin = zipfile.ZipFile(path, "r")
    used = used_ids(zin)
    payload, removed_total, latent_total = {}, 0, 0
    for n in zin.namelist():
        data = zin.read(n)
        if n in STYLE_PARTS:
            try:
                data, removed, latent = prune_styles_xml(data, used)
                removed_total += len(removed)
                latent_total += latent
            except Exception as e:  # 保持原样，绝不破坏文件
                sys.stderr.write(f"[prune_docx_styles] {n} 处理失败，已跳过: {e}\n")
        payload[n] = data
    zin.close()

    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n, d in payload.items():
            zout.writestr(n, d)
    try:
        shutil.copyfile(tmp, path)
    except PermissionError:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return used, removed_total, latent_total


def main() -> None:
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(2)
    for p in sys.argv[1:]:
        if not os.path.isfile(p):
            sys.stderr.write(f"[prune_docx_styles] 跳过（不存在）: {p}\n")
            continue
        used, removed, latent = process(p)
        print(
            f"[prune_docx_styles] {os.path.basename(p)} | "
            f"实际引用 {len(used)} 个样式 {sorted(used)} | "
            f"删除 {removed} 个未用样式 | 清除 {latent} 条 latentStyles 条目"
        )


if __name__ == "__main__":
    main()
