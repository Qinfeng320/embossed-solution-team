# PR-014：数据库设计文档 11 位成员口径对齐（db-schema-member-alignment）

> 执行日期：2026-10-16 ｜ 状态：**已执行** ｜ 触发：用户放行（待决项③：「一并做」＝方案甲 + 附项）｜ 前置：PR-011 / 012 / 013 ｜ 回退基线：`_backups/embossed-solution-team_20261016-1030`（本批改动为文本修订 + seed 数据行，逐项可逆）

## 一、背景

- 待决项③：`references/database-schema/` 仍按「ORCH + 9 域专家」建模，与执行层 11 位成员（9 域专家 + DOC-IN + DOCX）口径不一致。
- 决策过程：逐件核查 6 个文件 → 给出方案甲（全量对齐）/ 乙（口径注记）/ 丙（维持）→ 用户选定**甲 + 附项（一致性脚本防复发检查）**。
- 设计判断（已写入文档）：**分类层 dim_category 保持 9 个内容域**（DOC-IN / DOCX 为阶段角色，不参与"分类即路由"），文档 §3.3 加注说明防再误读。

## 二、变更清单

| 文件 | 变更 |
|---|---|
| `references/database-schema/seed.sql` | ① dim_agent 补 `DOC-IN`（文档输入专员）/ `DOCX`（文档输出专员）两行，role=**specialist**（12 行 = ORCH + 11 成员）；② 头注释与分节标题同步口径 |
| `references/database-schema/embossed-solution-team-db-design.md` | 11 处修订：适用对象 / seed 描述（2 处）/ §3.2 标题与 agent_code、agent_role 枚举 / §3.3 加「分类层为何保持 9」注记 /「8 维拆解」措辞统一为「七维度抽取（竞品场景 8 维变体）」（3 处）/ §5.2「每专家一步」→「每成员一步」 |
| `references/database-schema/embossed-solution-team-schema.sql` | 头注释口径同步（11 位成员枚举） |
| `agents/embossed-solution-team-team-lead.md` | §7.1：表数量修正（16 → **17** 张，实测 17）；seed 口径同步；§7.5 验证行更新为复验结果 |
| `scripts/verify_package_coherence.py` | **新增 E5 检查**：`seed.sql` dim_agent 成员 ↔ plugin.json 成员一致性（防成员清单漂移；含负向测试） |
| `.codebuddy-plugin/plugin.json` | version 1.2.2 → 1.2.3 |
| （环境侧，不入包）`~/.workbuddy/embossed-solution-team-data/tools/db-verify.cjs` | pg-mem 等价验证脚本（重建；原版未随包，本次留档于团队数据目录供复跑） |

无改动（核查确认）：`embossed-solution-team-er.svg`（纯实体图、无成员枚举）、`views.sql`、`archive_procedure.sql`。

## 三、测试记录（2026-10-16）

| 测试 | 结果 |
|---|---|
| `verify_package_coherence.py` | **ERROR 0 · WARN 0**（含新增 E5 静默通过） |
| E5 负向测试 | 人为破坏（DOC-IN → DOCXIN）→ 准确拦截 `[ERROR] E5 …（缺 DOC-IN；多 DOCXIN）`；恢复后逐字节一致、全通过 |
| pg-mem 复验（`db-verify.cjs`） | **20/20 断言通过**：17 表建表 / seed 灌入 / dim_agent=12（role=specialist 校验）/ 分类路由完整性 / 5 视图创建查询 / 采集→分类→路由链路 / 含 DOC-IN 步的过程记录（FK 通过）/ 交接契约 / 归档等价重放（批次→快照→热表清空→置 archived）/ 资产链 + 文件命名正则 / 唯一约束防重名 |
| `validate_expert.py` | 错误 1（仅余平台禁项）；警告 0 |
| `register_expert.py` | 重新注册通过 |

## 四、待决与后续

1. 平台禁项（既定偏差）；
2. 原演示脚本 `demo_clean_and_map.py` 未定位；
3. settings.json 平台清理行为（PR-012 §三）继续观察，缺失即补齐；
4. 平台侧：源版本 1.2.3（含 PR-011～014 全部改动）将在下次专家会话时自动物化到缓存安装件。
