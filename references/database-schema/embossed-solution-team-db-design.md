# embossed-solution-team 数据库表格方案设计说明书

> 适用对象：专家团 `embossed-solution-team`（团长 ORCH + 11 位成员：9 域专家 IND/POL/CUS/PRO/CAS/DAT/ARC/MAT/VER + 文档输入 DOC-IN / 文档输出 DOCX）
> 配套文件：
> - `embossed-solution-team-schema.sql` — 建库 DDL（PostgreSQL 14+）
> - `embossed-solution-team-er.svg` — ER 关系图
> - `seed.sql` — 基准数据（ORCH + 11 位成员、9 分类、示例项目）
> - `views.sql` — 售前工作台查询视图
> - `archive_procedure.sql` — 自动归档存储过程 + 定时调度

---

## 1. 概述

本数据库用于存储与处理**经过规范化**的专家团作业数据，覆盖从原始采集到最终交付文件的全生命周期。设计目标：

1. **规范化优先**：所有原始输入先经解析与结构化抽取（`/api/ingest` + doc-in 七维度抽取；竞品场景用 8 维拆解引擎）落为 `normalized_data.normalized_payload`（JSONB 规范结构），后续流转只消费规范结构。
2. **分类即路由**：分类结果直接驱动多智能体调度（`dim_category.route_agent_code`）。
3. **过程可归档**：热表只保留"进行中/未完成"数据；运行结束后整批迁移至归档表，并以 `archive_batch` 溯源，保证在线查询性能。
4. **生成可版本化**：最终交付物按不可变版本快照保存（`asset_version`）。
5. **文件强命名**：文件命名规范化，元数据全量留痕（`file_metadata` + SHA-256）。

### 1.1 类型约定
| 约定 | 取值 |
|---|---|
| 主键 | UUID，默认 `gen_random_uuid()`（pgcrypto） |
| 时间戳 | `TIMESTAMPTZ`（带时区） |
| 结构化负载 | `JSONB` |
| 哈希 | `CHAR(64)`（SHA-256 十六进制） |
| 字符串 | `VARCHAR(n)`，超长用 `TEXT` |
| 状态枚举 | `VARCHAR(20)`，取值见各表 `status` 列 |

---

## 2. 总体架构与数据流

```
raw_ingest ──▶ normalized_data ──▶ data_classification ──┐ (classification_rule 驱动)
        │                          (dim_category 路由)      │
        └──────────────────────────────────────────────────┘
                                                          ▼
process_run ──▶ process_step ──▶ agent_output              (多智能体处理 + handoff_contract 交接)
                                                          │ 运行结束
                                                          ▼
archive_batch ──▶ process_step_archive / agent_output_archive   (热表→归档表硬迁移)
                                                          ▼
generated_asset ──▶ asset_version ──▶ file_metadata              (生成保存 + 文件命名落盘)
```

四大子系统：**维度层 → 分类层 → 过程/归档层 → 生成/文件层**。

---

## 3. 维度表（Dimension）

### 3.1 `dim_project` — 项目维度
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| project_id | UUID | PK | 项目代理键 |
| project_code | VARCHAR(32) | U, NOT NULL | 项目编码，如 `EISA-2026-001` |
| project_name | VARCHAR(200) | NOT NULL | 项目名称 |
| client_name | VARCHAR(200) | | 客户/学校名称 |
| scenario_type | VARCHAR(50) | | 场景：职教实训基地/产教融合/设备更新/官方模板填报 |
| owner_agent | VARCHAR(20) | FK→dim_agent(agent_code) | 项目主理人（ORCH） |
| status | VARCHAR(20) | DEFAULT 'active' | active/archived |
| created_at / updated_at | TIMESTAMPTZ | | 时间戳 |

### 3.2 `dim_agent` — 智能体维度（ORCH + 11 位成员）
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| agent_code | VARCHAR(20) | PK | ORCH/IND/POL/CUS/PRO/CAS/DAT/ARC/MAT/DOC-IN/DOCX/VER |
| agent_name | VARCHAR(100) | NOT NULL | 显示名 |
| agent_role | VARCHAR(20) | | lead/domain/specialist（文档专员） |
| domain_label | VARCHAR(100) | | 领域标签，如"产业行业" |
| description | TEXT | | 职责说明 |
| model_binding | VARCHAR(100) | | 绑定模型/JudgmentPort |
| is_active | BOOLEAN | DEFAULT true | 是否启用 |

### 3.3 `dim_category` — 分类维度（与 9 域对齐）
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| category_id | VARCHAR(20) | PK | IND/POL/CUS/PRO/CAS/DAT/ARC/MAT/VER/CROSS/UNC |
| category_name | VARCHAR(100) | NOT NULL | 分类名 |
| parent_category_id | VARCHAR(20) | FK→dim_category | 自引用，支持层级 |
| route_agent_code | VARCHAR(20) | FK→dim_agent | 该分类由哪个专家处理 |
| description | TEXT | | 说明 |

> 注：分类层按 9 个**内容域**设计（+CROSS / UNC）；DOC-IN / DOCX 为阶段角色（输入解析 / 输出渲染），不参与分类路由，故不出现在 dim_category 中。

---

## 4. 分类子系统

### 4.1 `raw_ingest` — 原始采集
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| ingest_id | UUID | PK | 采集记录 ID |
| project_id | UUID | FK→dim_project | 归属项目 |
| source_type | VARCHAR(20) | | pdf/docx/pptx/text/api/form |
| source_name / source_path | VARCHAR(255)/TEXT | | 来源名/路径 |
| raw_size_bytes | BIGINT | | 原始大小 |
| checksum | CHAR(64) | | 原始文件 SHA-256 |
| ingested_at | TIMESTAMPTZ | DEFAULT now() | 采集时间 |
| normalized_data_id | UUID | FK→normalized_data | 规范化后回填 |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/normalized/failed |

### 4.2 `normalized_data` — 规范化数据主表
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| data_id | UUID | PK | 规范化数据 ID |
| ingest_id | UUID | FK→raw_ingest | 来源采集（非文件可为空） |
| project_id | UUID | FK→dim_project | 归属项目 |
| data_type | VARCHAR(50) | | requirement/spec/contract/policy_doc/case_doc… |
| normalized_payload | JSONB | NOT NULL | 规范结构（七维度抽取结果；竞品场景为 8 维拆解） |
| schema_version | VARCHAR(20) | | 规范化 schema 版本 |
| data_hash | CHAR(64) | | 规范化载荷 SHA-256 |
| status | VARCHAR(20) | DEFAULT 'classified' | classified/processing/done |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| created_by | VARCHAR(20) | | 触发者 |

### 4.3 `classification_rule` — 分类规则
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| rule_id | UUID | PK | 规则 ID |
| category_id | VARCHAR(20) | FK→dim_category | 命中后归入的分类 |
| rule_code | VARCHAR(50) | U | 规则编码，如 `RULE_IND_KEYWORD` |
| rule_name | VARCHAR(200) | | 规则名 |
| match_dimension | VARCHAR(50) | | 检查 `normalized_payload` 的字段（JSON 路径） |
| match_operator | VARCHAR(20) | | equals/in/like/regex/range |
| match_value | TEXT | | 匹配值/正则/范围 |
| priority | INT | | 越大越先评估 |
| weight | NUMERIC(5,2) | | 多规则打分权重 |
| enabled | BOOLEAN | DEFAULT true | 是否启用 |
| created_at / updated_at | TIMESTAMPTZ | | |

### 4.4 `data_classification` — 分类结果（分类存储结构）
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| classification_id | UUID | PK | |
| data_id | UUID | FK→normalized_data, NOT NULL | 被分类数据 |
| category_id | VARCHAR(20) | FK→dim_category, NOT NULL | 命中分类 |
| rule_id | UUID | FK→classification_rule | 触发规则（手动为空） |
| confidence | NUMERIC(5,4) | | 置信度 0–1 |
| is_primary | BOOLEAN | | 是否主分类 |
| classifier | VARCHAR(20) | | auto/manual |
| classified_at | TIMESTAMPTZ | DEFAULT now() | |
| — | — | U(data_id, category_id) | 同数据同分类不重复 |

---

## 5. 过程数据与归档子系统

### 5.1 `process_run` — 处理批次
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| run_id | UUID | PK | 运行实例 ID |
| project_id | UUID | FK→dim_project | |
| run_code | VARCHAR(50) | U | 运行编码 `RUN-YYYYMMDD-NNN` |
| orchestrator | VARCHAR(20) | FK→dim_agent | 团长 ORCH |
| trigger_type | VARCHAR(20) | | manual/api/scheduled |
| stage | VARCHAR(20) | | stage1…stage5（5 阶段工作流） |
| status | VARCHAR(20) | DEFAULT 'running' | running/success/failed/**archived** |
| started_at / finished_at | TIMESTAMPTZ | | |
| total_steps / success_steps | INT | | 步骤统计 |

### 5.2 `process_step` — 处理步骤（每成员一步）
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| step_id | UUID | PK | |
| run_id | UUID | FK→process_run | |
| step_seq | INT | | 运行内顺序 |
| agent_code | VARCHAR(20) | FK→dim_agent | 执行专家 |
| category_id | VARCHAR(20) | FK→dim_category | 聚焦分类 |
| input_ref | UUID | | 输入引用（data_classification/normalized_data） |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/running/success/failed/skipped |
| started_at / finished_at | TIMESTAMPTZ | | |
| duration_ms | BIGINT | | 耗时 |
| retry_count | INT | DEFAULT 0 | 重试次数 |
| — | — | U(run_id, step_seq) | |

### 5.3 `agent_output` — 智能体输出（过程数据）
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| output_id | UUID | PK | |
| step_id | UUID | FK→process_step, NOT NULL | |
| agent_code | VARCHAR(20) | FK→dim_agent | |
| output_type | VARCHAR(30) | | narrative/judgment/citation/teardown/metric |
| content | JSONB | NOT NULL | 结构化输出（叙事/评分/引用契约） |
| token_usage | INT | | token 消耗 |
| model_used | VARCHAR(100) | | 模型 |
| quality_score | NUMERIC(5,2) | | JudgmentPort 评分 |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### 5.4 `handoff_contract` — 交接/交互/验证契约
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| contract_id | UUID | PK | |
| run_id | UUID | FK→process_run | |
| from_step_id / to_step_id | UUID | FK→process_step | 来源/去向步骤 |
| contract_type | VARCHAR(20) | | handoff/interaction/verification |
| payload | JSONB | NOT NULL | 契约内容（上下文/验收标准） |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/accepted/rejected |
| created_at / resolved_at | TIMESTAMPTZ | | |

### 5.5 `archive_batch` — 归档批次（归档机制核心）
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| batch_id | UUID | PK | 批次 ID |
| batch_code | VARCHAR(50) | U | `ARCH-YYYYMMDD-HHMMSS-xxxxxxxx` |
| trigger | VARCHAR(20) | | on_complete/scheduled/manual |
| archived_by | VARCHAR(20) | | 触发者 |
| started_at / finished_at | TIMESTAMPTZ | | |
| record_count | INT | | 归档记录数 |
| status | VARCHAR(20) | | running/done/failed |
| note | TEXT | | |

### 5.6 `process_step_archive` — 步骤归档表
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| archive_id | UUID | PK | |
| batch_id | UUID | FK→archive_batch | 归属批次 |
| original_step_id | UUID | | 原 `process_step.step_id`（溯源） |
| run_id / step_seq / agent_code / category_id | 同原表 | | 原字段快照 |
| input_ref / status / started_at / finished_at / duration_ms / retry_count | 同原表 | | |
| archived_at | TIMESTAMPTZ | DEFAULT now() | |
| payload_snapshot | JSONB | | 完整快照（step+outputs+handoffs） |

### 5.7 `agent_output_archive` — 输出归档表
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| archive_id | UUID | PK | |
| batch_id | UUID | FK→archive_batch | |
| original_output_id / original_step_id | UUID | | 溯源 |
| agent_code / output_type / content / token_usage / model_used / quality_score | 同原表 | | |
| archived_at | TIMESTAMPTZ | DEFAULT now() | |

**归档机制（硬迁移而非软删）**：运行 `success` 后，由 `archive_run()` 创建批次 → 将 `process_step` 及其 `agent_output`/`handoff_contract` 写入归档表（含 `payload_snapshot`）→ 从热表 `DELETE` → `process_run.status` 置 `archived`。热表因此只保留活跃数据，查询轻量；归档表按批次可整体回放。

---

## 6. 生成数据子系统

### 6.1 `generated_asset` — 生成资产主表
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| asset_id | UUID | PK | |
| project_id | UUID | FK→dim_project | |
| run_id | UUID | FK→process_run | 来源运行 |
| asset_type | VARCHAR(30) | | solution_doc/eval_report/teardown_bundle/knowledge_index |
| title | VARCHAR(300) | NOT NULL | 标题 |
| version | VARCHAR(20) | | 当前版本标签，如 `v1.2` |
| content_format | VARCHAR(20) | | md/json/pdf/docx |
| content_ref | TEXT | | 存储路径或（小体积）内容 |
| content_hash | CHAR(64) | | 内容 SHA-256 |
| status | VARCHAR(20) | DEFAULT 'draft' | draft/published/archived |
| created_at / created_by / published_at | TIMESTAMPTZ/VARCHAR(20)/TIMESTAMPTZ | | |

### 6.2 `asset_version` — 资产版本（不可变快照）
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| version_id | UUID | PK | |
| asset_id | UUID | FK→generated_asset | |
| version_no | VARCHAR(20) | NOT NULL | `v1.0`/`v1.1`… |
| snapshot_ref | TEXT | | 不可变快照路径 |
| change_note | TEXT | | 变更说明 |
| created_at / created_by | TIMESTAMPTZ/VARCHAR(20) | | |
| — | — | U(asset_id, version_no) | 同资产版本不重复 |

**保存方式**：每次 `publish` 写一条 `generated_asset`（更新 `version/status`），并写一条 `asset_version`（不可变快照）。溯源链：`asset_version → generated_asset → process_run → archive_batch`。

---

## 7. 文件元数据与命名规范

### 7.1 `file_metadata` — 文件元数据表
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| file_id | UUID | PK | |
| asset_id | UUID | FK→generated_asset, NOT NULL | 来源资产 |
| project_id | UUID | FK→dim_project | |
| file_name | VARCHAR(255) | NOT NULL | 按规范生成 |
| naming_pattern | VARCHAR(100) | | 所用命名模式 ID |
| project_code / domain_code / version_label / seq / file_ext | VARCHAR(32)/VARCHAR(20)/VARCHAR(20)/CHAR(2)/VARCHAR(10) | | 命名分解字段 |
| storage_path | TEXT | NOT NULL | 落盘路径 |
| file_hash | CHAR(64) | | 文件 SHA-256 |
| file_size_bytes | BIGINT | | 大小 |
| mime_type | VARCHAR(100) | | MIME |
| generated_at / uploaded_by | TIMESTAMPTZ/VARCHAR(20) | | |
| — | — | U(project_code, domain_code, version_label, seq, file_ext) | 防重名 |

### 7.2 文件命名规范
**模式**：`{PROJECT_CODE}_{DOMAIN_CODE}_v{VERSION}_{YYYYMMDD}_{SEQ}.{EXT}`
示例：`EISA-2026-001_IND_v1.2_20260828_01.md`

| 段 | 来源 | 说明 |
|---|---|---|
| PROJECT_CODE | `dim_project.project_code` | 项目编码 |
| DOMAIN_CODE | `dim_category.category_id` 或 `ALL` | 跨域交付物用 `ALL` |
| VERSION | `generated_asset.version`（去 `v` 前缀） | 版本号 |
| YYYYMMDD | `file_metadata.generated_at` 日期 | 生成日期 |
| SEQ | 零填充序号 `01`–`99` | 同日同域同版本序号 |
| EXT | `content_format` 映射（md/json/pdf/docx） | 扩展名 |

同一资产多格式导出 → 多行 `file_metadata`（不同 `EXT`/`SEQ`）。

---

## 8. 主键 / 外键关系汇总

| 表 | 主键 | 外键 |
|---|---|---|
| dim_project | project_id | owner_agent→dim_agent |
| dim_agent | agent_code | — |
| dim_category | category_id | parent→self；route_agent_code→dim_agent |
| raw_ingest | ingest_id | project_id→dim_project；normalized_data_id→normalized_data |
| normalized_data | data_id | ingest_id→raw_ingest；project_id→dim_project |
| classification_rule | rule_id | category_id→dim_category |
| data_classification | classification_id | data_id→normalized_data；category_id→dim_category；rule_id→classification_rule |
| process_run | run_id | project_id→dim_project；orchestrator→dim_agent |
| process_step | step_id | run_id→process_run；agent_code→dim_agent；category_id→dim_category |
| agent_output | output_id | step_id→process_step；agent_code→dim_agent |
| handoff_contract | contract_id | run_id→process_run；from_step_id/to_step_id→process_step |
| archive_batch | batch_id | — |
| process_step_archive | archive_id | batch_id→archive_batch |
| agent_output_archive | archive_id | batch_id→archive_batch |
| generated_asset | asset_id | project_id→dim_project；run_id→process_run |
| asset_version | version_id | asset_id→generated_asset |
| file_metadata | file_id | asset_id→generated_asset；project_id→dim_project |

---

## 9. 完整流转逻辑（分类→处理→归档→生成→文件）

1. **采集录入**：原始文件/接口进入 `raw_ingest`，计算 `checksum`，`status='pending'`。
2. **规范化**：解析与结构化抽取（PDF/DOCX/PPTX 经 `/api/ingest` + doc-in 七维度抽取；竞品场景 8 维拆解）→ 写 `normalized_data`（`normalized_payload` JSONB，`data_hash`），回填 `raw_ingest.normalized_data_id`，`status='normalized'`。
3. **分类**：对 `normalized_data` 应用 `enabled` 的 `classification_rule`（按 `priority` 排序，依 `match_dimension/operator/value` 匹配 `normalized_payload`）→ 写 `data_classification`（`category_id`、`rule_id`、`confidence`、`is_primary`）。可多标签，主类 = 最高 `confidence`；`dim_category.route_agent_code` 决定后续处理专家；`normalized_data.status='classified'`。
4. **处理**：ORCH 创建 `process_run`（`run_code`、`stage`），按分类/5 阶段排布 `process_step`（每域专家一步）；逐步执行，智能体产出写 `agent_output`（`narrative/judgment/citation`），步骤间通过 `handoff_contract`（`handoff/interaction/verification`）交接上下文；更新 `process_run` 统计与 `status`。
5. **归档**：运行 `success` 后触发 `archive_run()` → 建 `archive_batch` → `process_step` + 关联 `agent_output`/`handoff_contract` 快照写入 `*_archive`（含 `payload_snapshot`）→ 热表 `DELETE` → `process_run.status='archived'`。按保留策略可 `scheduled` 周期性执行。
6. **生成保存**：ORCH 汇总各 `step` 输出组装最终交付物 → 写 `generated_asset`（`asset_type`、`title`、`version`、`content_ref`）；每次发布写 `asset_version` 不可变快照；`status: draft→published`。
7. **文件命名落盘**：将 `generated_asset` 导出为文件，按 §7.2 规范生成 `file_name`，落盘 `storage_path`，写 `file_metadata`（`file_hash`、`size`、`mime`、命名分解字段）。同一资产多格式导出生成多行。

---

## 10. 索引与性能建议
- 已在 FK 列、`data_hash`、`(project_id, asset_type)`、`(project_code, domain_code)` 建索引（见 DDL）。
- 热表 `process_step`/`agent_output` 随归档持续收缩，保持在线查询轻量。
- `normalized_payload`/`content`/`payload_snapshot` 用 `JSONB`（支持 GIN 索引按需加速）。
- 归档表按 `batch_id` 分区可选（数据量大时）。
- `file_metadata` 唯一约束防重名，配合对象存储路径唯一。

## 11. 附录：增强脚本
- `seed.sql`：灌入 ORCH + 11 位成员、9 分类（+CROSS/UNC）、示例项目，可直接 `psql -f seed.sql`。
- `views.sql`：`v_classified_data`、`v_run_summary`、`v_agent_output_latest`、`v_asset_files`、`v_runs_to_archive` 等售前工作台视图。
- `archive_procedure.sql`：`archive_run()` / `archive_all_completed()` 存储过程 + `pg_cron` 定时调度示例。
