#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concurrency_guard.py —— 共享空间防静默篡改（P0-④·对齐《AI Agent》Ch.10.5.1 MAST 第三类「共享状态意外修改」）

设计边界（诚实标注）：
  团长 §6.5 已用「派新即关旧 + 磁盘唯一事实底座」防 MAST ①并发冲突（逻辑覆盖）。
  本脚本补 MAST ③物理防护：对 `embossed_projects/<project_id>/` 做**内容哈希快照**，
  二次运行比对，捕获「文件被静默覆盖/篡改/删除」——哪怕逻辑上没并发，磁盘内容也已变。

  关键纪律（写入 governance.md §四'）：
    1. 团长在关键阶段（派发前/验收前）先 `snapshot` 固化基线；
    2. 成员回传落盘后 `check` 比对，差异须可解释（变更 v<N> / 派新即关旧）；
    3. 任何**非预期**修改（无对应变更 v<N>、或改了只读区如 references/）判阻断，转人工。

用法：
  python concurrency_guard.py --project-root <root> [--project <pid>] snapshot [--out snap.json]
  python concurrency_guard.py --project-root <root> [--project <pid>] check --baseline snap.json [--json]

退出码：0 一致 ｜ 1 存在非预期修改（阻断）｜ 2 用法/快照缺失
"""
import sys, os, json, argparse, hashlib

IMMUTABLE_PREFIXES = ("references/", "scripts/")  # 全团只读区，任何改动即非预期


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root, pid=None):
    base = os.path.join(root, pid) if pid else root
    files = {}
    for dp, _, fns in os.walk(base):
        for fn in fns:
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, base).replace("\\", "/")
            try:
                files[rel] = _sha(fp)
            except OSError:
                pass
    return {"base": base, "count": len(files), "files": files}


def check(root, pid, baseline_path):
    if not os.path.exists(baseline_path):
        print(f"[ERR] 基线快照缺失：{baseline_path}", file=sys.stderr)
        return 2
    with open(baseline_path, encoding="utf-8") as f:
        base = json.load(f)
    cur = snapshot(root, pid)
    added, modified, removed, unexpected = [], [], [], []
    bfiles = base["files"]
    cfiles = cur["files"]
    for rel, h in cfiles.items():
        if rel not in bfiles:
            added.append(rel)
        elif bfiles[rel] != h:
            modified.append(rel)
            if rel.startswith(IMMUTABLE_PREFIXES):
                unexpected.append(rel)
    for rel in bfiles:
        if rel not in cfiles:
            removed.append(rel)
            if rel.startswith(IMMUTABLE_PREFIXES):
                unexpected.append(rel)
    report = {
        "added": sorted(added), "modified": sorted(modified),
        "removed": sorted(removed), "unexpected_mutable_change": sorted(set(unexpected)),
        "healthy": not unexpected,
    }
    return report


def main():
    ap = argparse.ArgumentParser(description="共享空间内容哈希防护（防静默篡改）")
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--project")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("snapshot"); sp.add_argument("--out", required=True)
    ck = sub.add_parser("check"); ck.add_argument("--baseline", required=True); ck.add_argument("--json")
    args = ap.parse_args()
    if args.cmd == "snapshot":
        rep = snapshot(args.project_root, args.project)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print(f"[snapshot] {rep['count']} 文件 -> {args.out}")
        return 0
    else:
        rep = check(args.project_root, args.project, args.baseline)
        if isinstance(rep, int):  # 基线缺失/用法错误（check 已打印 ERR）
            return rep
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=2)
            print(f"[report] -> {args.json}")
        else:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
