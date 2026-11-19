#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""售前专家团 · 局部复用路由（确定性建议）。

用法:
  python scripts/route_intent.py --hint "帮我核对这份材料"     # 路由建议
  python scripts/route_intent.py --list                        # 浏览全部路由（人读视图）
  python scripts/route_intent.py --test                        # 路由回归（用例见 references/routing-cases.json）
  python scripts/route_intent.py --hint "..." --json           # 机器可读输出

说明：路由唯一真相源为 references/routing-config.json（团长 MD §6.1.1 只引用其用法）。
      脚本仅做关键词确定性匹配，供团长调度参考；模糊意图的最终调度权在团长（语义判断兜底）。
      路由配置或脚本变更后，必须运行 --test 回归。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "references" / "routing-config.json"
DEFAULT_CASES = ROOT / "references" / "routing-cases.json"


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def match_routes(hint: str, config: dict):
    h = hint.lower()
    hits = []
    for r in config["routes"]:
        for kw in r["keywords"]:
            if kw.lower() in h:
                hits.append(r)
                break
    return hits


def cmd_hint(hint: str, config: dict, as_json: bool = False) -> int:
    hits = match_routes(hint, config)
    if as_json:
        print(json.dumps({
            "hint": hint,
            "matched": [
                {"id": r["id"], "members": r["members"], "acceptance": r["acceptance"], "notes": r.get("notes", "")}
                for r in hits
            ],
        }, ensure_ascii=False, indent=2))
        return 0
    print(f"路由建议（hint：{hint}）")
    print("-" * 36)
    if not hits:
        print("未命中确定性路由——交由团长语义判断；无法归属时先向用户澄清，不擅自调度。")
        return 0
    multi = len(hits) > 1
    if multi:
        print(f"命中 {len(hits)} 条（多意图，按依赖顺序拆分执行）：")
    for i, r in enumerate(hits, 1):
        prefix = f"  {i}. " if multi else "  "
        print(f"{prefix}[{r['id']}] {r['intent']}")
        print(f"     成员：{'、'.join(r['members'])}")
        print(f"     验收：{r['acceptance']}")
        if r.get("notes"):
            print(f"     备注：{r['notes']}")
    if multi:
        print("> 提示：复合请求按依赖顺序分步；语义明显不符时由团长重判。")
    return 0


def cmd_list(config: dict) -> int:
    print(f"局部复用路由（{len(config['routes'])} 条 · 唯一真相源：references/routing-config.json）")
    print("=" * 56)
    for r in config["routes"]:
        print(f"[{r['id']}] {r['intent']}")
        print(f"    成员：{'、'.join(r['members'])}｜验收：{r['acceptance']}")
        print(f"    触发词：{' / '.join(r['keywords'])}")
    print("-" * 56)
    for c in config.get("composition_rules", []):
        ex = f"（示例：{c['example']}）" if c.get("example") else ""
        print(f"· {c['rule']}{ex}")
    return 0


def cmd_test(config: dict, cases_path: Path) -> int:
    cases = load_json(cases_path)["cases"]
    print(f"路由回归（用例 {len(cases)} 条 · 配置 v{config.get('version', '?')}）")
    print("-" * 56)
    passed = 0
    for c in cases:
        got = [r["id"] for r in match_routes(c["hint"], config)]
        ok = sorted(got) == sorted(c["expect"])
        if ok:
            passed += 1
            shown = "、".join(got) if got else "（未命中）"
            print(f"  PASS  {c['id']}  {c['hint']} → {shown}")
        else:
            print(f"  FAIL  {c['id']}  {c['hint']}")
            exp = "、".join(c["expect"]) if c["expect"] else "（未命中）"
            act = "、".join(got) if got else "（未命中）"
            print(f"        期望：{exp}")
            print(f"        实际：{act}")
    print("-" * 56)
    print(f"结果：{passed}/{len(cases)} 通过")
    return 0 if passed == len(cases) else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="售前专家团 · 局部复用路由（确定性建议）")
    ap.add_argument("--hint", help="用户话术摘要")
    ap.add_argument("--list", action="store_true", help="浏览全部路由")
    ap.add_argument("--test", action="store_true", help="运行路由回归用例")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="配置文件路径")
    ap.add_argument("--cases", default=str(DEFAULT_CASES), help="回归用例路径")
    ap.add_argument("--json", action="store_true", help="--hint 以 JSON 输出")
    args = ap.parse_args()

    config = load_json(Path(args.config))
    if args.test:
        sys.exit(cmd_test(config, Path(args.cases)))
    if args.list:
        sys.exit(cmd_list(config))
    if args.hint:
        sys.exit(cmd_hint(args.hint, config, args.json))
    ap.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
