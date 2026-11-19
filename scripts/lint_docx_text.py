#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lint_docx_text.py — .docx 编校检查（可脚本项筛查）

依据 docx-agent「文档自检清单 · 编校检查」（PR-006）：
筛查可脚本化的编校级缺陷，供 LLM 读回判定前先行过滤——
  1) 疑似复词（"以及以及"式连续重复；合法叠词经白名单过滤）
  2) 连续标点（"，。"、"，，"式）
  3) 半角标点混用（汉字后紧跟半角 , ; : ? !）
  4) 引号配对（中文引号成对计数；中文文本中混入英文直引号的提示）
脚本是筛子不是法官：命中项须逐条按上下文人工/LLM 判读后处理。

用法：
  python lint_docx_text.py <file.docx> [--json]
  退出码：0=无命中、1=有命中、2=执行错误
"""
import sys, os, re, json, zipfile, argparse

# 合法叠词白名单（避免"看看/渐渐"类误报）
DUPLICATE_WHITELIST = {
    "看看", "想想", "试试", "谈谈", "说说", "走走", "听听", "写写", "问问",
    "渐渐", "纷纷", "常常", "慢慢", "快快", "深深", "静静", "悄悄", "微微",
    "淡淡", "层层", "步步", "个个", "天天", "年年", "人人", "种种", "件件",
    "处处", "时时", "点点", "滴滴", "星星", "团团", "整整", "好好", "轻轻",
}


def para_texts(docx_path):
    """提取段落级文本（w:p -> 拼接 w:t），含表格内段落。"""
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    paras = []
    for pm in re.finditer(r"<w:p[ >].*?</w:p>|<w:p/>", xml, re.S):
        seg = pm.group(0)
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", seg, re.S)
        # 还原 XML 实体
        text = "".join(texts)
        for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
            text = text.replace(a, b)
        if text.strip():
            paras.append(text)
    return paras


def check_paras(paras):
    findings = {"duplicate": [], "punct_seq": [], "halfwidth": []}
    for i, t in enumerate(paras, 1):
        for m in re.finditer(r"([\u4e00-\u9fff]{1,6})\1", t):
            frag = m.group(0)
            if len(frag) >= 2 and frag not in DUPLICATE_WHITELIST:
                ctx = t[max(0, m.start() - 12): m.end() + 12]
                findings["duplicate"].append((i, frag, ctx))
        for m in re.finditer(r"[，。；、]{2,}", t):
            ctx = t[max(0, m.start() - 12): m.end() + 12]
            findings["punct_seq"].append((i, m.group(0), ctx))
        for m in re.finditer(r"[\u4e00-\u9fff][,;:?!]", t):
            ctx = t[max(0, m.start() - 12): m.end() + 12]
            findings["halfwidth"].append((i, m.group(0), ctx))
    return findings


def check_quotes(paras):
    text = "\n".join(paras)
    checks = {}
    for name, o, c in (('"“”"', "“", "”"), ("「」", "「", "」"), ("『』", "『", "』")):
        n_o, n_c = text.count(o), text.count(c)
        if n_o != n_c:
            checks[name] = f"不配对：{o}×{n_o} vs {c}×{n_c}"
    straight = len(re.findall(r'[\u4e00-\u9fff]"|"[\u4e00-\u9fff]', text))
    if straight:
        checks["英文直引号混用"] = f"疑似中文语境直引号 ×{straight}"
    return checks


def main():
    ap = argparse.ArgumentParser(description="docx 编校检查（可脚本项筛查；判读权在 LLM）")
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        paras = para_texts(args.file)
    except Exception as e:
        print(f"读取失败：{e}")
        sys.exit(2)

    f = check_paras(paras)
    quotes = check_quotes(paras)
    total = sum(len(v) for v in f.values()) + len(quotes)

    if args.json:
        print(json.dumps({"file": args.file, "paragraphs": len(paras),
                          "findings": {k: v for k, v in f.items()},
                          "quotes": quotes, "total": total}, ensure_ascii=False, indent=2))
    else:
        print("=" * 62)
        print(f"编校检查（可脚本项）—— {args.file}")
        print(f"段落数：{len(paras)}")
        print("=" * 62)
        labels = {"duplicate": "疑似复词", "punct_seq": "连续标点", "halfwidth": "半角标点混用"}
        for k, label in labels.items():
            for i, frag, ctx in f[k]:
                print(f"[{label}] 段 {i}: 「{frag}」 …{ctx}…")
        for k, v in quotes.items():
            print(f"[引号] {k}: {v}")
        if total == 0:
            print("未筛查到可脚本项缺陷（语义项请继续按自检清单读回判定）。")
        else:
            print(f"\n合计 {total} 处疑似——请逐条按上下文判读（脚本是筛子不是法官）。")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
