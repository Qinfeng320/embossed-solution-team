#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""售前专家团 · 包一致性校验（coherence check）。

检查项（E=错误，W=提示）：
  E1  plugin.json 合法性 + 与文件系统一致性（agents / skills / hooks / agentName / memberAgents）
  E2  Team 型必备件 settings.json（存在，且 agent 值与 agentName 一致）
  E3  章节编号唯一性（各 .md 同级标题的阿拉伯数字编号不得重复）
  E4  关键 JSON 合法性（routing-config / routing-cases / hooks.json）及 hooks 脚本存在性
  E5  数据库基准数据成员一致性（references/database-schema/seed.sql 的 dim_agent 与 plugin.json 成员一致）
  W1  引用完整性（包内反引号引用的 scripts/ references/ assets/ skills/ 路径存在性）
  W2  成员 MD 结构（含「统一产出结构」「SendMessage」；主理人含验收 / 交接物要素）
  W3  注册规范字段（tags=3、quickPrompts=3、displayDescription.zh 40–50 字）
  W4  标准模板指纹对照（期望前缀 87e6b832）

用法:
  python scripts/verify_package_coherence.py [--verbose]
退出码：存在 ERROR 时为 1，否则 0。
纪律：对专家包自身（agents / references / scripts / plugin.json / hooks / settings.json）
      的任何修改，合入前必须运行本脚本并修至 ERROR=0（见团长 MD §6.5）。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = []  # (level, code, message)


def add(level: str, code: str, msg: str) -> None:
    FINDINGS.append((level, code, msg))


def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def md_files_to_scan():
    files = []
    for base in ["agents", "references", "skills"]:
        files += sorted((ROOT / base).rglob("*.md"))
    files.append(ROOT / "README.md")
    return [f for f in files if f.exists()]


def check_plugin_json():
    pj, err = read_json(ROOT / ".codebuddy-plugin" / "plugin.json")
    if err:
        add("ERROR", "E1", f".codebuddy-plugin/plugin.json 不是合法 JSON：{err}")
        return None
    for rel in pj.get("agents", []):
        if not (ROOT / rel.lstrip("./")).exists():
            add("ERROR", "E1", f"agents 声明路径不存在：{rel}")
    for rel in pj.get("skills", []):
        if not (ROOT / rel.lstrip("./")).exists():
            add("ERROR", "E1", f"skills 声明路径不存在：{rel}")
    hooks = pj.get("hooks")
    if isinstance(hooks, str) and not (ROOT / hooks.lstrip("./")).exists():
        add("ERROR", "E1", f"hooks 声明路径不存在：{hooks}")
    agent_name = pj.get("agentName")
    if agent_name and not (ROOT / "agents" / f"{agent_name}.md").exists():
        add("ERROR", "E1", f"agentName 对应 MD 不存在：agents/{agent_name}.md")
    for m in (pj.get("teamInfo") or {}).get("memberAgents", []):
        if not (ROOT / "agents" / f"{m}.md").exists():
            add("ERROR", "E1", f"memberAgents 对应 MD 不存在：agents/{m}.md")
    # E2 Team 型必备件
    if pj.get("expertType") == "team":
        sp = ROOT / "settings.json"
        if not sp.exists():
            add("ERROR", "E2", "Team 型缺少 settings.json（规范要求 {\"agent\": \"<agentName>\"}）")
        else:
            sj, e2 = read_json(sp)
            if e2:
                add("ERROR", "E2", f"settings.json 不是合法 JSON：{e2}")
            elif sj.get("agent") != agent_name:
                add("ERROR", "E2", f"settings.json 的 agent 值与 agentName 不一致：{sj.get('agent')!r} ≠ {agent_name!r}")
    # W3 注册规范字段
    tags = pj.get("tags", [])
    if len(tags) != 3:
        add("WARN", "W3", f"tags 现 {len(tags)} 条（规范固定 3 条）")
    qp = pj.get("quickPrompts", [])
    if len(qp) != 3:
        add("WARN", "W3", f"quickPrompts 现 {len(qp)} 条（规范固定 3 条）")
    dd = (pj.get("displayDescription") or {}).get("zh", "")
    if dd and not (40 <= len(dd) <= 50):
        add("WARN", "W3", f"displayDescription.zh 现 {len(dd)} 字（建议 40–50 字）")
    return pj


def check_json_files():
    for rel in ["plugin.json", "references/routing-config.json", "references/routing-cases.json", "hooks/hooks.json"]:
        p = ROOT / rel if rel != "plugin.json" else ROOT / ".codebuddy-plugin" / rel
        if p.exists():
            _, e = read_json(p)
            if e:
                add("ERROR", "E4", f"{rel} 不是合法 JSON：{e}")
    hp = ROOT / "hooks" / "hooks.json"
    if hp.exists():
        hj, e = read_json(hp)
        if not e:
            for entries in (hj.get("hooks") or {}).values():
                for entry in entries:
                    for h in entry.get("hooks", []):
                        m = re.search(r"hooks/([A-Za-z0-9_\-\.]+\.mjs)", str(h.get("command", "")))
                        if m and not (ROOT / "hooks" / m.group(1)).exists():
                            add("ERROR", "E4", f"hooks.json 引用的脚本不存在：hooks/{m.group(1)}")
    # W4 模板指纹
    dotx = ROOT / "assets" / "样式模板.dotx"
    if not dotx.exists():
        add("ERROR", "E4", "标准模板 assets/样式模板.dotx 缺失")
    else:
        h = hashlib.sha256(dotx.read_bytes()).hexdigest()
        if not h.startswith("87e6b832"):
            add("WARN", "W4", f"标准模板指纹 {h[:8]} 与定版 87e6b832 不一致（如为有意更新请同步规范与自检记录）")


def check_numbering():
    pat = re.compile(r"^(#{2,6})\s+(\d+(?:\.\d+)*[A-Za-z]?)(?:[.、:：]|\s)")
    for f in md_files_to_scan():
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        seen = {}
        in_fence = False
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = pat.match(line)
            if not m:
                continue
            key = (len(m.group(1)), m.group(2))
            if key in seen:
                rel = f.relative_to(ROOT).as_posix()
                add("ERROR", "E3", f"{rel} 章节编号重复：『{'#' * key[0]} {key[1]}』（行 {seen[key]} 与行 {i}）")
            else:
                seen[key] = i


def check_refs():
    pats = [
        re.compile(r"`(scripts/[A-Za-z0-9_\-]+\.py)`"),
        re.compile(r"`(references/[A-Za-z0-9_\-/]+\.(?:md|sql|svg|json))`"),
        re.compile(r"`(assets/[^`\s]+\.(?:dotx|docx|png|svg))`"),
        re.compile(r"`(skills/[A-Za-z0-9_\-/\.]+)`"),
    ]
    allowlist = {"assets/_template_aug.docx"}
    skip_parts = {"prs", "runs"}
    scan = [f for f in md_files_to_scan() if not any(part in skip_parts for part in f.parts)]
    skill_dirs = [d for d in (ROOT / "skills").iterdir() if d.is_dir()] if (ROOT / "skills").exists() else []
    for f in scan:
        text = f.read_text(encoding="utf-8")
        for pat in pats:
            for m in pat.finditer(text):
                ref = m.group(1)
                if "<" in ref or ">" in ref or ref in allowlist:
                    continue
                if (ROOT / ref).exists():
                    continue
                if any((sd / ref).exists() for sd in skill_dirs):
                    continue
                add("WARN", "W1", f"{f.relative_to(ROOT).as_posix()} 引用的路径不存在：{ref}")


def check_member_structure(pj):
    agent_name = pj.get("agentName") if pj else None
    for f in sorted((ROOT / "agents").glob("*.md")):
        name = f.stem
        text = f.read_text(encoding="utf-8")
        if name == agent_name:
            for need in ["验收", "交接物", "SendMessage"]:
                if need not in text:
                    add("WARN", "W2", f"agents/{f.name} 缺少要素：{need}")
        else:
            for need in ["统一产出结构", "SendMessage"]:
                if need not in text:
                    add("WARN", "W2", f"agents/{f.name} 缺少必备节/要素：{need}")


def check_seed_members(pj):
    """E5: seed.sql 的 dim_agent 成员须与 plugin.json 成员一致（防成员清单漂移）。"""
    if not pj:
        return
    seed_path = ROOT / "references" / "database-schema" / "seed.sql"
    if not seed_path.exists():
        return
    text = seed_path.read_text(encoding="utf-8")
    m = re.search(r"INSERT INTO dim_agent[^;]+;", text, re.S)
    if not m:
        add("ERROR", "E5", "seed.sql 未找到 dim_agent INSERT 段")
        return
    codes_seed = set(re.findall(r"\('([A-Z][A-Z0-9-]+)',", m.group(0)))

    def to_code(aid: str) -> str:
        if aid.endswith("team-lead"):
            return "ORCH"
        return (aid[:-6] if aid.endswith("-agent") else aid).upper()

    lead = pj.get("agentName") or ""
    member_ids = (pj.get("teamInfo") or {}).get("memberAgents", [])
    codes_pj = {to_code(x) for x in ([lead] if lead else []) + list(member_ids)}
    missing = sorted(codes_pj - codes_seed)
    extra = sorted(codes_seed - codes_pj)
    if missing or extra:
        parts = []
        if missing:
            parts.append("缺 " + "/".join(missing))
        if extra:
            parts.append("多 " + "/".join(extra))
        add("ERROR", "E5", "seed.sql dim_agent 与 plugin.json 成员不一致（" + "；".join(parts) + "）")


def main() -> None:
    ap = argparse.ArgumentParser(description="售前专家团 · 包一致性校验")
    ap.add_argument("--verbose", action="store_true", help="输出扫描统计")
    args = ap.parse_args()

    pj = check_plugin_json()
    check_json_files()
    check_numbering()
    check_refs()
    if pj:
        check_member_structure(pj)
        check_seed_members(pj)

    if args.verbose:
        print(f"扫描：agents/references/skills/*.md + README.md；plugin.json={'OK' if pj else 'FAIL'}")

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    FINDINGS.sort(key=lambda x: (order.get(x[0], 9), x[1], x[2]))
    print("售前专家团 · 包一致性校验")
    print("=" * 36)
    if not FINDINGS:
        print("全部通过：无 ERROR / WARN。")
    else:
        for lv, code, msg in FINDINGS:
            print(f"[{lv:<5}] {code}  {msg}")
    ne = sum(1 for f in FINDINGS if f[0] == "ERROR")
    nw = sum(1 for f in FINDINGS if f[0] == "WARN")
    print("-" * 36)
    print(f"结果：ERROR {ne} · WARN {nw}")
    sys.exit(1 if ne else 0)


if __name__ == "__main__":
    main()
