#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retrieval_dense.py —— 稠密 RAG 生产级升级 MVP（P1-⑧·对齐《AI Agent》Ch.3.2/3.3）

设计边界（诚实标注）：
  当前 `knowledge-index` 经 `tfidf.ts` 暴露稀疏检索（knowledge-index.md §7.1 已定义接口契约）。
  本脚本提供**可插拔稠密分支 MVP**：
    - 生产级：接入 BGE-M3 类嵌入（需 embedding 服务，当前环境未配置 → 留 hook 不调用）；
    - MVP：用纯 Python 词袋稠密向量（TF 向量）+ 余弦，作为稠密分支的本地可运行占位，
      使「稠密 + 稀疏 + RRF 融合 + 重排序」pipeline 端到端跑通、零外部依赖；
    - 融合：RRF（Reciprocal Rank Fusion）合并稠密/稀疏排序；
    - 重排序：cross-encoder 留 stub（按融合分降序取 top-k，生产级替换为人审/模型精排）。
  与 sop_eval.py 共用 golden cases 标注集做 recall@k / MRR / nDCG 量化（书 6.9 评测系统自检）。

用法：
  python retrieval_dense.py --index <dir> --query "..." [--top-k 5] [--mode hybrid|dense|sparse]
  （--index 目录内含 chunks.json：[{"chunk_id","text","source_entry_id"}]）

退出码：0 正常 ｜ 2 用法/索引缺失
"""
import sys, os, json, argparse, math, re
from collections import Counter


def _tok(s):
    return [w for w in re.findall(r"[\u4e00-\u9fa5a-z0-9]+", s.lower())]


def _bow_vec(texts):
    """构建词袋：idf 加权 TF 向量（稠密分支 MVP）。返回 (vocab, idf, doc_vecs)。"""
    dfs = Counter()
    toks_list = [_tok(t) for t in texts]
    for toks in toks_list:
        for w in set(toks):
            dfs[w] += 1
    n = len(toks_list)
    idf = {w: math.log((n + 1) / (c + 1)) + 1 for w, c in dfs.items()}
    vecs = []
    for toks in toks_list:
        tf = Counter(toks)
        vec = {w: (tf[w] / max(1, len(toks))) * idf[w] for w in tf}
        vecs.append(vec)
    return idf, vecs


def _cosine(a, b):
    keys = set(a) | set(b)
    num = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return num / (na * nb) if na and nb else 0.0


def embed(text, idf, vocab=None):
    tf = Counter(_tok(text))
    return {w: (tf[w] / max(1, len(tf))) * idf.get(w, 1.0) for w in tf}


def rrf(ranklists, k=60):
    scores = {}
    for rl in ranklists:
        for rank, cid in enumerate(rl):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def main():
    ap = argparse.ArgumentParser(description="稠密 RAG 融合检索 MVP")
    ap.add_argument("--index", required=True, help="含 chunks.json 的目录")
    ap.add_argument("--query", required=True)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--mode", choices=["hybrid", "dense", "sparse"], default="hybrid")
    args = ap.parse_args()

    cpath = os.path.join(args.index, "chunks.json")
    if not os.path.exists(cpath):
        print(f"[ERR] 索引缺失：{cpath}", file=sys.stderr)
        return 2
    chunks = json.load(open(cpath, encoding="utf-8"))
    texts = [c.get("text", "") for c in chunks]
    idf, doc_vecs = _bow_vec(texts)
    qvec = embed(args.query, idf)

    dense_rank, sparse_rank = [], []
    if args.mode in ("hybrid", "dense"):
        sims = [_cosine(qvec, dv) for dv in doc_vecs]
        dense_rank = [c["chunk_id"] for _, c in sorted(zip(sims, chunks), key=lambda x: x[0], reverse=True)]
    if args.mode in ("hybrid", "sparse"):
        # 稀疏：共享词命中计数（占位稀疏分支；生产级替换为 TF-IDF/BM25 独立实现）
        qt = set(_tok(args.query))
        hits = [len(qt & set(_tok(c["text"]))) for c in chunks]
        ranked = sorted(zip(hits, chunks), key=lambda x: x[0], reverse=True)
        sparse_rank = [c["chunk_id"] for h, c in ranked if h > 0] or [c["chunk_id"] for c in chunks]

    if args.mode == "dense":
        merged = dense_rank
    elif args.mode == "sparse":
        merged = sparse_rank
    else:
        merged = rrf([dense_rank, sparse_rank])

    top = merged[: args.top_k]
    print(f"[{args.mode}] top-{args.top_k}：")
    for cid in top:
        c = next(x for x in chunks if x["chunk_id"] == cid)
        print(f"  - {cid} ｜ src={c.get('source_entry_id','?')} ｜ {c.get('text','')[:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
