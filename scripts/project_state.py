#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
project_state.py — 项目上下文(ProjectContext)工作区确定性管理脚本

契约见 references/project-context-spec.md。团长(ORCH)在 create / resume / switch
时调用本脚本，负责多项目信封的持久化、版本化与相互隔离。脚本只做状态管理：
  - 不推断行业（行业由 cus/pol 产出后回填）
  - 不写回全局 references/（项目数据只进本项目工作区）
  - 每次只操作一个 project_id（单信封单项目，杜绝拼接）

纯标准库实现，无第三方依赖、无需 venv 自举。

工作区布局（project_root 可配，默认放专家包外）：
  <project_root>/<project_id>/
    context.json        # ProjectContext 信封（持久化）
    handoff_ledger.json # 跨阶段交接物可追溯链（仅本项目）
    artifacts/          # docx 产出、解析中间态（仅本项目）
    decisions.log       # 变更 v<N>、待澄清（纯文本追加）

用法示例：
  python project_state.py create --project-id med-2026-001 --industry 医疗 \
      --domain-terms "AGV,院感管控" --compliance "患者隐私,器械注册证" \
      --scenarios "药品跨楼转运"
  python project_state.py resume --project-id med-2026-001
  python project_state.py update --project-id med-2026-001 --patch patch.json --summary "cus 回填行业上下文"
  python project_state.py switch --project-id edu-2026-001
  python project_state.py list
  python project_state.py verify-isolation --project-a med-2026-001 --project-b edu-2026-001
"""
import sys, os, json, argparse, uuid
from datetime import datetime, timezone, timedelta

# 默认项目根：放在专家包外（避免升级被覆盖）。可用 --project-root 或环境变量覆盖。
DEFAULT_PROJECT_ROOT = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "embossed-solution-team-projects"
)

TZ = timezone(timedelta(hours=8))  # 中国时区，用于 updated_at / ts 默认

SKELETON_KEYS = [
    "project_id", "display_name", "client", "industry", "industry_subdomain",
    "domain_terms", "compliance_redlines", "typical_scenarios", "policy_anchors",
    "version", "updated_at", "open_questions", "change_log",
]


# ----------------------------- 基础工具 -----------------------------
def now_iso():
    return datetime.now(TZ).isoformat()


def eprint(*a):
    sys.stderr.write(" ".join(str(x) for x in a) + "\n")


def die(msg, code=1):
    eprint(f"[project_state] {msg}")
    sys.exit(code)


def resolve_project_root(args):
    return args.project_root or os.environ.get("PROJECT_ROOT") \
        or os.environ.get("EMBOSSED_PROJECT_ROOT") or DEFAULT_PROJECT_ROOT


def project_dir(root, pid):
    return os.path.join(root, pid)


def context_path(root, pid):
    return os.path.join(project_dir(root, pid), "context.json")


def ledger_path(root, pid):
    return os.path.join(project_dir(root, pid), "handoff_ledger.json")


def decisions_path(root, pid):
    return os.path.join(project_dir(root, pid), "decisions.log")


def artifacts_dir(root, pid):
    return os.path.join(project_dir(root, pid), "artifacts")


def load_context(root, pid):
    p = context_path(root, pid)
    if not os.path.exists(p):
        die(f"项目工作区不存在: {p}（先用 create 创建，或确认 project_id 正确）")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_context(root, pid, ctx):
    d = project_dir(root, pid)
    os.makedirs(d, exist_ok=True)
    with open(context_path(root, pid), "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)
        f.write("\n")


def append_ledger(root, pid, phase, note, version):
    p = ledger_path(root, pid)
    ledger = []
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except Exception:
            ledger = []
    ledger.append({
        "ts": now_iso(),
        "project_id": pid,
        "phase": phase,
        "version": version,
        "note": note,
    })
    os.makedirs(project_dir(root, pid), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
        f.write("\n")


def append_decisions(root, pid, line):
    os.makedirs(project_dir(root, pid), exist_ok=True)
    with open(decisions_path(root, pid), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def bump_version(v, kind="major"):
    s = str(v).lstrip("vV")
    parts = s.split(".")
    try:
        major = int(parts[0]) if parts[0] else 1
        minor = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    except ValueError:
        major, minor = 1, 0
    if kind == "minor":
        minor += 1
    else:
        major += 1
        minor = 0
    return f"v{major}.{minor}"


def deep_merge(base, patch):
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = deep_merge(dict(base.get(k)), v)
        else:
            base[k] = v
    return base


def split_csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else []


# ----------------------------- 信封构造 -----------------------------
def new_envelope(pid, industry):
    ts = now_iso()
    return {
        "project_id": pid,
        "display_name": "",
        "client": "",
        "industry": industry,
        "industry_subdomain": "",
        "domain_terms": [],
        "compliance_redlines": [],
        "typical_scenarios": [],
        "policy_anchors": [],
        "version": "v1.0",
        "updated_at": ts,
        "open_questions": [],
        "change_log": [{"v": "v1.0", "ts": ts, "by": "ORCH", "summary": "初始化项目上下文"}],
    }


# ----------------------------- 命令实现 -----------------------------
def cmd_create(args):
    root = resolve_project_root(args)
    pid = args.project_id or f"proj-{uuid.uuid4().hex[:8]}"
    if not args.industry and not args.init_json:
        die("create 须提供 --industry（或经由 --init-json 提供完整信封）。")
    industry = args.industry or "待澄清"
    ctx = new_envelope(pid, industry)

    if args.init_json:
        if args.init_json == "-":
            init = json.load(sys.stdin)
        else:
            with open(args.init_json, "r", encoding="utf-8") as f:
                init = json.load(f)
        deep_merge(ctx, init)

    # CLI 旗标覆盖（显式优先）
    over = {}
    if args.display_name:
        over["display_name"] = args.display_name
    if args.client:
        over["client"] = args.client
    if args.industry:
        over["industry"] = args.industry
    if args.subdomain:
        over["industry_subdomain"] = args.subdomain
    if args.domain_terms:
        over["domain_terms"] = split_csv(args.domain_terms)
    if args.compliance:
        over["compliance_redlines"] = split_csv(args.compliance)
    if args.scenarios:
        over["typical_scenarios"] = split_csv(args.scenarios)
    if args.policy:
        over["policy_anchors"] = split_csv(args.policy)
    if over:
        deep_merge(ctx, over)

    pid = ctx["project_id"]
    if not pid:
        die("project_id 不能为空。")

    d = project_dir(root, pid)
    os.makedirs(artifacts_dir(root, pid), exist_ok=True)
    save_context(root, pid, ctx)
    append_ledger(root, pid, "create", "初始化项目工作区", ctx["version"])
    append_decisions(root, pid, f"[{now_iso()}] {ctx['version']} create 初始化项目工作区")
    print(json.dumps({"project_id": pid, "path": d, "context": ctx},
                     ensure_ascii=False, indent=2))


def cmd_resume(args):
    root = resolve_project_root(args)
    ctx = load_context(root, args.project_id)
    print(json.dumps(ctx, ensure_ascii=False, indent=2))


def cmd_switch(args):
    root = resolve_project_root(args)
    ctx = load_context(root, args.project_id)
    append_ledger(root, args.project_id, "switch", "切换至该项目（须新生成员实例）", ctx["version"])
    # 切换的本质是 ORCH 换信封 + 新生成员 agent 实例；脚本只负责加载并提示纪律。
    eprint(f"[project_state] switch -> {args.project_id}：ORCH 必须为该项目新生成员 agent 实例"
           f"（全新上下文窗口），禁止复用上一项目的热实例（隔离铁律，见团长 6.3）。")
    print(json.dumps(ctx, ensure_ascii=False, indent=2))


def cmd_update(args):
    root = resolve_project_root(args)
    ctx = load_context(root, args.project_id)

    if args.patch:
        if args.patch == "-":
            patch = json.load(sys.stdin)
        else:
            with open(args.patch, "r", encoding="utf-8") as f:
                patch = json.load(f)
        deep_merge(ctx, patch)

    if args.set:
        for kv in args.set:
            if "=" not in kv:
                die(f"--set 格式应为 key=value，收到: {kv}")
            k, v = kv.split("=", 1)
            ctx[k.strip()] = v.strip()

    old_v = ctx.get("version", "v1.0")
    new_v = bump_version(old_v, args.bump)
    ctx["version"] = new_v
    ctx["updated_at"] = now_iso()
    by = args.by or "ORCH"
    summary = args.summary or "更新项目上下文"
    ctx.setdefault("change_log", []).append(
        {"v": new_v, "ts": ctx["updated_at"], "by": by, "summary": summary}
    )

    save_context(root, args.project_id, ctx)
    append_ledger(root, args.project_id, "update", summary, new_v)
    append_decisions(root, args.project_id, f"[{ctx['updated_at']}] {new_v} update {summary} (by {by})")
    print(json.dumps({"project_id": args.project_id, "version": new_v,
                      "prev_version": old_v, "context": ctx},
                     ensure_ascii=False, indent=2))


def cmd_ledger(args):
    root = resolve_project_root(args)
    load_context(root, args.project_id)  # 确保工作区存在
    append_ledger(root, args.project_id, args.phase or "handoff", args.note or "", args.version or "")
    append_decisions(root, args.project_id,
                     f"[{now_iso()}] ledger phase={args.phase or 'handoff'} {args.note or ''}")
    print(json.dumps({"project_id": args.project_id, "ledger": ledger_path(root, args.project_id)},
                     ensure_ascii=False, indent=2))


def cmd_list(args):
    root = resolve_project_root(args)
    if not os.path.isdir(root):
        print(json.dumps([], ensure_ascii=False))
        return
    out = []
    for name in sorted(os.listdir(root)):
        p = context_path(root, name)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    c = json.load(f)
                out.append({
                    "project_id": c.get("project_id"),
                    "industry": c.get("industry"),
                    "version": c.get("version"),
                    "display_name": c.get("display_name"),
                    "updated_at": c.get("updated_at"),
                })
            except Exception:
                out.append({"project_id": name, "error": "context.json 解析失败"})
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_verify_isolation(args):
    """校验项目 B 的信封里不含项目 A 的 project_id 与行业专属词（防串味）。"""
    root = resolve_project_root(args)
    a = load_context(root, args.project_a)
    b = load_context(root, args.project_b)

    foreign_pid = a.get("project_id", "")
    if args.terms:
        foreign_terms = split_csv(args.terms)
    else:
        foreign_terms = list(a.get("domain_terms", []))
        for k in ("industry", "industry_subdomain"):
            if a.get(k):
                foreign_terms.append(a[k])

    blob = json.dumps(b, ensure_ascii=False).lower()
    offending = []
    if foreign_pid and foreign_pid.lower() in blob:
        offending.append(f"project_id:{foreign_pid}")
    for t in foreign_terms:
        if t and str(t).lower() in blob:
            offending.append(str(t))

    passed = len(offending) == 0
    report = {
        "passed": passed,
        "project_a": args.project_a,
        "project_b": args.project_b,
        "checked_terms": foreign_terms,
        "offending": offending,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if passed else 1)


# ----------------------------- CLI -----------------------------
def build_parser():
    # 全局选项下放到 parent parser，使 --project-root 在子命令前后均可使用
    pp = argparse.ArgumentParser(add_help=False)
    pp.add_argument("--project-root",
                   help="项目根目录（覆盖环境变量 PROJECT_ROOT / EMBOSSED_PROJECT_ROOT；默认 ~/.workbuddy/embossed-solution-team-projects）")
    p = argparse.ArgumentParser(
        prog="project_state.py", parents=[pp],
        description="ProjectContext 项目工作区确定性管理（create/resume/switch/update/list/verify-isolation）")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="新建项目工作区并初始化信封")
    c.add_argument("--project-id", help="项目唯一 ID（缺省自动生成 proj-<uuid8>）")
    c.add_argument("--init-json", help="完整信封 JSON 文件（- 表示读 stdin），其字段覆盖默认值")
    c.add_argument("--display-name")
    c.add_argument("--client")
    c.add_argument("--industry", help="所属行业（必填，除非由 --init-json 提供）")
    c.add_argument("--subdomain", help="细分领域")
    c.add_argument("--domain-terms", help="行业术语表，逗号分隔")
    c.add_argument("--compliance", help="行业合规红线，逗号分隔")
    c.add_argument("--scenarios", help="典型落地场景，逗号分隔")
    c.add_argument("--policy", help="适用政策锚点 ID，逗号分隔")
    c.set_defaults(func=cmd_create)

    r = sub.add_parser("resume", help="读取并恢复已有项目信封（只读）")
    r.add_argument("--project-id", required=True)
    r.set_defaults(func=cmd_resume)

    s = sub.add_parser("switch", help="切换至项目（加载信封 + 提示新生成员实例纪律）")
    s.add_argument("--project-id", required=True)
    s.set_defaults(func=cmd_switch)

    u = sub.add_parser("update", help="合并补丁、版本化、记录变更")
    u.add_argument("--project-id", required=True)
    u.add_argument("--patch", help="补丁 JSON 文件（- 表示读 stdin），深度合并进信封")
    u.add_argument("--set", action="append", help="顶层标量覆盖 key=value（可多次）")
    u.add_argument("--summary", help="变更摘要（写入 change_log / decisions.log）")
    u.add_argument("--by", help="操作人，默认 ORCH")
    u.add_argument("--bump", choices=["major", "minor"], default="major", help="版本递增方式")
    u.set_defaults(func=cmd_update)

    l = sub.add_parser("ledger", help="向本项目 handoff_ledger 追加一条交接记录")
    l.add_argument("--project-id", required=True)
    l.add_argument("--phase", help="阶段标识（如 Phase1 / handoff）")
    l.add_argument("--note", help="备注")
    l.add_argument("--version", help="关联信封版本")
    l.set_defaults(func=cmd_ledger)

    ls = sub.add_parser("list", help="列出所有项目（id/行业/版本）")
    ls.set_defaults(func=cmd_list)

    v = sub.add_parser("verify-isolation", help="校验 B 信封不含 A 的 project_id 与行业专属词")
    v.add_argument("--project-a", required=True, help="参照项目（被隔离来源）")
    v.add_argument("--project-b", required=True, help="受检项目（应纯净）")
    v.add_argument("--terms", help="自定义外源词（逗号分隔），缺省用 A.domain_terms+industry")
    v.set_defaults(func=cmd_verify_isolation)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
