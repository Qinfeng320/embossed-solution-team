# -*- coding: utf-8 -*-
"""ppt_probe.py —— 不解压、不开 PowerPoint，直接读 .pptx 每页文字，用于「改页单 vs 实物」对账

为什么要有这个脚本：清单上写"已改为 X"，但 deck 实际可能还是 Y（甚至根本没改）。
人眼翻 29 页 PPT 极易漏；本脚本把每页文字抽出来，按关键词定位到页号，**一眼看出改没改**。

用法：
    python scripts/ppt_probe.py <deck.pptx>                     # 每页首行 + 字数概览
    python scripts/ppt_probe.py <deck.pptx> --find 商电式 Index   # 这些词出现在第几页
    python scripts/ppt_probe.py <deck.pptx> --dump out.txt       # 导出全量文字（按页分隔）

实现：直接读 zip 内的 ppt/slides/slideN.xml（不依赖 python-pptx，258MB 文件也秒级）。
"""
import argparse, os, re, sys, zipfile


def _slide_texts(path):
    out = {}
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)]
        names.sort(key=lambda n: int(re.search(r'slide(\d+)\.xml', n).group(1)))
        for n in names:
            xml = z.read(n).decode("utf-8", "ignore")
            texts = re.findall(r'<a:t>(.*?)</a:t>', xml, re.S)
            txt = "".join(texts)
            txt = (txt.replace("&amp;", "&").replace("&lt;", "<")
                      .replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'"))
            out[int(re.search(r'slide(\d+)\.xml', n).group(1))] = txt
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--find", nargs="*", default=[], help="要在页内定位的关键词")
    ap.add_argument("--dump", default=None, help="导出全量文字到文件（按页分隔）")
    ap.add_argument("--max-chars", type=int, default=46)
    a = ap.parse_args()

    if not os.path.exists(a.pptx):
        print(f"[ppt_probe] 文件不存在：{a.pptx}")
        return 2
    pages = _slide_texts(a.pptx)
    print(f"[ppt_probe] {os.path.basename(a.pptx)}：{len(pages)} 页，总字 {sum(len(v) for v in pages.values())}")

    if not a.find:
        for i in sorted(pages):
            head = pages[i].strip().replace("\n", " ")[: a.max_chars]
            print(f"  P{i:<3} {len(pages[i]):>5} 字  {head}")
    else:
        for kw in a.find:
            hit = [i for i in sorted(pages) if kw in pages[i]]
            if hit:
                print(f"  「{kw}」命中 P{', P'.join(map(str, hit))}")
            else:
                print(f"  「{kw}」**未命中**（说明该处未改，或原文本身不含此词）")

    if a.dump:
        with open(a.dump, "w", encoding="utf-8") as f:
            for i in sorted(pages):
                f.write(f"\n===== P{i} =====\n{pages[i]}\n")
        print(f"  已导出：{a.dump}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
