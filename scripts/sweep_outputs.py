# -*- coding: utf-8 -*-
"""sweep_outputs.py —— 交付目录旧版归档（PR-037）

配合 make_docx.py 的「占用即改名」：出件不再覆盖被打开的文件，而是另起
带时间戳的新名字，因此同目录会积累多个版本。本脚本按「基名」归组，
每组保留最近 N 份（默认 2），其余移入 `<dir>/_archive/`。

设计原则：
  - 只移动，不删除——归档目录里的文件随时可取回；
  - 被 WPS / Word 占用的文件自动跳过，不报错、不阻断；
  - 默认演练（dry-run），加 --apply 才真正移动。

用法：
    python scripts/sweep_outputs.py <目录> [--keep 2] [--apply]
"""
import argparse
import os
import re
import shutil
import sys

# 依次剥离文件名尾部的版本/时间戳标记，还原出「基名」
_SUFFIX_PATTERNS = [
    re.compile(r"_\d{8}-\d{6}(_\d+)?$"),   # _20261119-163245 或 _20261119-163245_1
    re.compile(r"_\d{8}$"),                # _20261119
    re.compile(r"_v\d+$"),                 # _v2
    re.compile(r"_(fixed|fixtest)$"),      # 历史手工后缀
]


def base_name(stem):
    """反复剥离尾部版本标记，直到稳定。"""
    prev = None
    while prev != stem:
        prev = stem
        for pat in _SUFFIX_PATTERNS:
            new = pat.sub("", stem)
            if new and new != stem:
                stem = new
                break
    return stem


def is_writable(path):
    try:
        with open(path, "r+b"):
            return True
    except OSError:
        return False


def scan(directory, keep):
    groups = {}
    for name in os.listdir(directory):
        full = os.path.join(directory, name)
        if not os.path.isfile(full):
            continue
        stem, ext = os.path.splitext(name)
        if ext.lower() not in (".docx", ".pdf"):
            continue
        if name.startswith("~$"):
            continue
        groups.setdefault(base_name(stem) + ext.lower(), []).append(full)

    plan, skipped = [], []
    for key, files in groups.items():
        if len(files) <= keep:
            continue
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for old in files[keep:]:
            if not is_writable(old):
                skipped.append(old)
                continue
            plan.append(old)
    return plan, skipped, len(groups)


def main():
    ap = argparse.ArgumentParser(description="交付目录旧版归档（只移动不删除）")
    ap.add_argument("directory", help="要整理的目录")
    ap.add_argument("--keep", type=int, default=2, help="每组保留最新几份（默认 2）")
    ap.add_argument("--apply", action="store_true", help="真正执行移动；缺省仅演练")
    a = ap.parse_args()

    if not os.path.isdir(a.directory):
        sys.stderr.write(f"目录不存在：{a.directory}\n")
        return 2

    plan, skipped, ngroups = scan(a.directory, a.keep)
    print(f"[sweep_outputs] 扫描 {a.directory}")
    print(f"[sweep_outputs] 归组 {ngroups} 组，待归档 {len(plan)} 个，被占用跳过 {len(skipped)} 个")

    for p in plan:
        print(("  归档 " if a.apply else "  待归档 ") + os.path.basename(p))
    for p in skipped:
        print("  跳过（被占用，关闭后重跑）：" + os.path.basename(p))

    if not a.apply:
        print("[sweep_outputs] 演练模式，未移动。加 --apply 执行。")
        return 0

    if plan:
        arch = os.path.join(a.directory, "_archive")
        os.makedirs(arch, exist_ok=True)
        moved = 0
        for p in plan:
            try:
                shutil.move(p, os.path.join(arch, os.path.basename(p)))
                moved += 1
            except OSError as e:
                print(f"  移动失败（跳过）：{os.path.basename(p)} | {e}")
        print(f"[sweep_outputs] 已归档 {moved} 个到 {arch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
