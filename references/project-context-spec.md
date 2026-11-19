# 项目上下文规范（Project Context Spec）

> 中央真相源。定义 `embossed-solution-team` 在"系统级去行业化"前提下，如何为每个具体项目注入行业针对性、并管理多项目（如医疗 A / 教育 B）相互独立。与 `redlines.md` / `input-spec.md` / `doc-tree-spec.md` 同级，全团引用，不得各写各的。

## 一、设计原则（最重要）

- **行业不是提示词常量，而是项目级运行时数据**。成员 agent 的系统提示词保持行业无关（已去锁）；行业只通过本规范定义的 **ProjectContext 信封**在每次交接物中由团长注入。
- **唯一状态归属**：跨调用的项目持久状态只存在于团长的项目工作区，成员 agent 无跨项目长期记忆。
- **单信封单项目**：每次下发的交接物只含一个 ProjectContext。

## 二、ProjectContext 信封（JSON schema）

```json
{
  "project_id": "med-2026-001",
  "display_name": "某三甲医院智慧物流方案",
  "client": "XX医院",
  "industry": "医疗",
  "industry_subdomain": "院内物流/消毒供应中心",
  "domain_terms": ["AGV", "院感管控", "医疗器械注册证", "HIS/LIS对接"],
  "compliance_redlines": ["患者隐私(个人信息保护法)", "医疗器械须注册证", "不承诺诊断结论"],
  "typical_scenarios": ["药品/标本跨楼转运", "手术室物资配送"],
  "policy_anchors": ["POL-AI-01", "POL-DEV-01"],
  "version": "v1.0",
  "updated_at": "2026-07-29T10:32:00+08:00",
  "open_questions": [],
  "change_log": [
    {"v": "v1.0", "ts": "2026-07-29T10:32:00+08:00", "by": "ORCH", "summary": "初始化项目上下文"}
  ]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| project_id | ✅ | 项目唯一 ID（建议 `<行业缩写>-<年>-<序号>` 或 UUID）；隔离与续写的主键 |
| display_name | ❌ | 项目显示名 |
| client | ❌ | 客户名称（企业/机构/院校等） |
| industry | ✅ | 所属行业（医疗/教育/制造…）；未明示时 cus 须列「待澄清」 |
| industry_subdomain | ❌ | 细分领域 |
| domain_terms | ✅ | 行业术语表，供 pro/mat/docx 使用正确词汇 |
| compliance_redlines | ✅ | 行业合规红线（如医疗：患者隐私/器械注册） |
| typical_scenarios | ✅ | 典型落地场景，供 arc/mat 组织针对性内容 |
| policy_anchors | ❌ | 本项目适用政策锚点 ID 列表（pol 产出，来自 knowledge-index） |
| version | ✅ | 版本号，与团长 6.2 版本纪律一致 |
| updated_at | ❌ | 更新时间 ISO8601 |
| open_questions | ❌ | 待澄清清单 |
| change_log | ❌ | 变更记录 v<N> |

## 三、项目工作区（隔离 + 持久化）

每个项目一个工作区目录，由 `project_id` 命名空间隔离：

```
<project_root>/<project_id>/
  context.json        # ProjectContext 信封（持久化）
  handoff_ledger.json # 跨阶段交接物可追溯链（仅本项目）
  artifacts/          # docx 产出、解析中间态（仅本项目）
  artifacts/budget_baseline.json  # 可选：预算版本基准（冻结快照）；存在时触发团长 §6.2「预算版本基线闸」
  decisions.log       # 变更 v<N>、待澄清
```

- **project_root 可配**：默认 `<专家包外的工作区>/projects/`；建议通过环境变量 `PROJECT_ROOT` 或团长配置指定，**不要放在专家包内部**（避免升级被覆盖）。
- 全局 `references/`（redlines/knowledge-index/input-spec/doc-tree-spec）保持静态通用，项目专属数据**绝不写回**此处。

## 四、团长（ORCH）职责：create / resume / switch

- **create**：收到新 `project_id` → 在 `<project_root>/<project_id>/` 建工作区，由 cus/pol 提炼结果初始化 `context.json`（信封）。
- **resume**：收到已有 `project_id` → 读取 `context.json` 恢复信封，续写版本（同项目多次调用 = 连续）。
- **switch**：收到不同 `project_id` → 加载新工作区、换信封；**必须为该项目新生成员 agent 实例**（全新上下文窗口），禁止复用上一项目的热实例（隔离铁律，见团长 6.3）。
- **inject**：把当前项目信封作为交接物「项目上下文 ProjectContext」块下发；下游成员只从该块取行业/术语/合规/场景。

## 五、各成员如何供给/消费信封

| 成员 | 角色 |
|------|------|
| cus-agent | **供给**「行业上下文」块（industry/subdomain/domain_terms/compliance_redlines/typical_scenarios），写入统一产出结构；未明示行业须列待澄清 |
| pol-agent | **供给**「行业政策锚点」：按 envelope.industry 从 knowledge-index 选取；目录无对应行业标「待检索」 |
| pro/arc/mat/ver/docx/doc-in | **消费**信封：用行业/术语/合规/场景做针对性匹配、架构、叙事、合规闸门、术语表达、维度标注 |
| 团长 ORCH | **治理**：组装信封、注入、持久化、隔离（唯一持有跨调用状态） |

## 六、隔离纪律（权威见团长 6.3）

- 每次交接物仅一个 ProjectContext；绝不拼接多项目信封。
- 切换项目 = 换信封 + 新生成员实例。
- 项目数据只进本项目工作区，不回写全局 references/。
- 项目 specifics 不进助手通用 memory。

## 七、与团长交接物的衔接

团长组装 Handoff Artifact 时，在结构内新增「项目上下文 ProjectContext」块（见团长 2.1）；成员统一产出结构新增 `project_id` 字段（见团长 3.1），使可追溯链可归属到具体项目。
