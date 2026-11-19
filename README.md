# 售前专家团（Presales Expert Team）

面向售前与各类内容工作场景的 Team 型专家团：团长 ORCH 编排 11 位领域专家（行业情报、政策研究、客户洞察、产品服务、案例管理、数据支持、方案架构、材料策略、输入文档规范、文档输出、核验风控），协同产出可追溯、可外发的报告、方案与各类材料（含 .docx 与保真 PDF）。

> 曾用名"具身智能方案专家团"；2026-10-12 更名为"售前专家团"（定位由具身智能专用调整为通用，详见 `references/prs/PR-006-external-integration-and-rename.md`）。

## 类型

Team 型（多角色协作团队），1 团长 + 11 专家。

## 功能

- **输入预处理**：多源材料（PPT/PDF/Word/图片/网页）结构化消化，七维度抽取 + 页码溯源 + 红线预检。
- **研究与情报**：研究分型与预算控制、行业趋势/风险、政策必要性、区域对标、来源质量批判。
- **方案构建**：分层产品能力、分层架构与分期路径、可证明案例与脱敏、预算测算与一致性。
- **材料与叙事**：面向受众的叙事策略、内容架构、页面级素材与客户版口吻；风格范本机制。
- **核验风控**：事实/政策/承诺/案例/数字多维核验、证据分级、双闸门外发判定。
- **文档落地**：**统一以标准模板体系（`assets/样式模板.dotx`，§0.14）产出 .docx** + 保真 PDF 外发版；编校检查与渲染成图核验。
- **文风合规与文档卫生**：行文红线终扫（三类禁用词 / 工作痕迹）、文本规范化（全角空格 / 邻接空格 / 自动间距）、元数据清洁（`references/style-guide.md` + 配套脚本）。
- **验收闭环**：团长按四维度逐项验收、上下文交接物跨阶段不丢失、不合格退回修订。
- **技能**：微信文章检索（中文信源补充，`skills/wechat-article-search`）。

## 工作说明

完整说明（角色全景、协作铁律、SOP、质量闸门、验收机制、上下文交接物、交互契约）见团长 MD 与各成员 MD。

### 中央真相源（references/）
- `references/redlines.md`：六红线与第三方科研/测试报告 caveat 的**唯一权威定义**，全团引用、不得各写各的。
- `references/knowledge-index.md`：政策库 / 行业信号源 / 案例库分层 / 产品能力目录的索引与统一引用格式，解决"依据与来源"空泛问题。
- `references/evidence-spec.md`：证据与来源规范（来源分级 / 证据四类分级 / 台账 / 数值价格 / 冲突处理 / 旧料更新 / 方法透明度），调研与引用类产出依据。
- `references/input-spec.md`：输入材料消化规范（七维度抽取 + 输入消化清单），doc-in-agent 产出自检标准，与 redlines/knowledge-index 同为中央真相源。
- `references/style-guide.md`：文风与文档卫生规范（行文红线三类禁用词 + 行业例外 / 工作痕迹 8 类 / 文体规范 / 受众适配 / 正式件与准备件纪律 / 图示规范 / 文本规范），mat / ver / docx 落地与交付终扫依据。
- `references/document-format-standards.md`：文档格式标准（字体 / 字号 / 版面 / 表格 / 命名 / 体裁路由）。
- `references/word-template-style-spec.md`：**标准 Word 输出模板配套规范**（`assets/样式模板.dotx` 定版体系：样式全量定义 / 编号机制 / 页面设置 / 内容映射与编号清洗 / 图·表宽度与比例 / WPS 面板清理 / 工具脚本用法）——Word 输出的唯一版式准绳（§0.14）。
- `references/doc-tree-spec.md`：文档树 JSON 契约（meta/redlines/sections/blocks，含 image 块），docx-agent 据此组织文档树、`scripts/build_docx.py` 据此确定性渲染 .docx/PDF（支持 `--template`）。
- `references/claim-evidence-discipline.md`：主张—证据纪律（主张四类绑定 / 动词强度三级 / 程度量化 / 可读性阈值 / 保留清单），ver M5 核验依据，mat / pro 产出阶段前置（PR-008 新增，部分整合自外部 Skill `academic-humanizer`）。
- `references/proposal-structure-guide.md`：申报与投标论证结构（四问题前置 / 目标设置 / 承诺—实施条件配对 / 投标响应性对照表 / 提交前自检清单），申报投标类材料依据（PR-008 新增）。
- `references/routing-config.json`：**局部复用路由唯一真相源**（意图 → 成员 → 验收标准；配套 `scripts/route_intent.py` 与用例 `references/routing-cases.json`）（PR-011 新增）。
- `references/lesson-index.md`：跨项目经验索引（场景 / 关键词 / 教训 / 固化位置），研究类任务起步先查；写回触发条件见 `governance.md` §六（PR-011 新增）。
- `references/model-dispatch.md`：**模型分派唯一真相源**（平台全量模型盘点 17 项 / 六档分派表 / 升降档规则 / 兜底映射 / 派活自检清单），团长派活指定模型的依据（PR-026/027 新增）。
- `references/team-overview.md`：**团队自述文档唯一维护版**（运作机制详解·Markdown·开源文档定位）；任何机制类变更合入后强制同步，纪律见 `governance.md` §二'（PR-029 新增）。

### 确定性脚本（scripts/）
- `scripts/parse_docs.py`：输入侧解析管线（与 build_docx.py 对称）——对 Word/PDF/PPT/Excel 做格式识别、文本/版面提取、自动溯源标签注入、红线正则预检，输出带标签的中间态 JSON 供 LLM 做七维度语义归类；依赖自举。
- `scripts/build_docx.py`：文档树 JSON → .docx（+PDF）确定性渲染；依赖自举。
- `scripts/content_to_docx.py`：**内容 JSON → 标准样式 .docx**（按类别套样式、标题/题注编号自动清洗生成；配套规范 §6.9）。
- `scripts/credit_report.py`：**会话积分消耗报告**——按模型归集团员积分（平台逐笔记账＋时间窗归属）与全链 token 用量，任务收口时输出（PR-031 新增）。
- `scripts/template_style_tool.py`：**标准模板样式操作工具**（`list / set / hide / remove / page`——改模板设置一条命令；配套规范 §6.9）。
- `scripts/inspect_docx.py`：只读读回渲染产物供 LLM 做 QA Gate 核验（不替 LLM 下结论）。
- 交付质检配套：`check_style_words.py`（文风终扫）/ `normalize_docx_text.py`（文本规范化）/ `clean_docx_metadata.py`（元数据清洁）/ `render_docx.py`（渲染成图）/ `lint_docx_text.py`（编校检查）。
- 文档工程：`merge_docx.py` / `split_docx.py`（多文档合并 / 按章节拆分）。
- 路由与包校验（PR-011 新增）：`scripts/route_intent.py`（意图 → 路由确定性建议；`--hint` / `--list` / `--test` 回归）/ `scripts/verify_package_coherence.py`（包一致性校验：引用完整性 / 章节编号唯一性 / 成员结构 / 注册字段 / 模板指纹）。

### 单点复用
团长支持"仅解析 / 仅核验 / 仅出文档 / 仅单角色研判 / 仅调研"的局部复用模式（跳过全 SOP），以及"需求变更 / 口径调整"的版本化异常处理回路，详见团长 MD 第六节。

## 使用示例

- 深度调研一个主题并产出结构化报告（先给大纲确认）
- 为某客户的方案做需求解析与必要性论证，并给出架构与预算建议
- 核对这份材料的事实来源、文风合规与数字一致性

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换：PNG（推荐）或 JPG，512×512 px，单张 ≤500KB。

## 安装

将专家包目录放到专家目录下：

```
C:\Users\Administrator\.workbuddy\plugins\marketplaces\my-experts/plugins/embossed-solution-team/
```

然后运行注册命令使其可见（注册脚本由内置 expert-manager 技能提供，需在其技能目录下运行）：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

> **状态**：本包已移除 hooks/（2026-11-16）。专家包规范将 hooks/ 列为禁项，移除后可直接通过官方校验与打包，无需再做发布前移出。原 hooks 已备份至维护区 `_backups/hooks_removed_20261116-1825/`（如需恢复运行时增强可移回）。

**发版流程**（官方工具在专家管理器技能目录下运行，命令中的 `<技能目录>` 与 `<包目录>` 请替换为实际路径）：

```bash
# ① 校验（须 0 错误）
python3 <技能目录>/validate_expert.py <包目录>
# ② 注册到本地专家市场（更新 marketplace.json）
python3 <技能目录>/register_expert.py <包目录>
# ③ 打包（产物为 <包名>.zip，落在当前工作目录或指定输出目录）
python3 <技能目录>/package_expert.py <包目录> <输出目录>
```

**打包后处理**（官方脚本产物不带版本号，需手工补两步）：

1. 重命名产物为版本化文件名：`<包名>_v<版本>_release_<日期>.zip`；
2. 在同目录写一份构建说明，记录校验结果、包内核验要点、文件大小与 SHA-256 指纹（可用 `sha256sum <产物>` 获取）。

产物与构建说明统一放在维护区 `_dist/`，便于按版本追溯。

> **关于早期的一键脚本**：旧版 README 曾提到 `_backups/package_release.py` 一键构建脚本（含 hooks 移出自动化）。该脚本自 2026-10-29 起已不在维护区，源码亦无留存；且 hooks 已于 2026-11-16 彻底移除、无需再自动移出，脚本的存在前提已消失。故本节改为上述官方工具流程，不再引用该脚本。

## 目录结构

```
embossed-solution-team/
├── agents/                 12 份角色定义（1 团长 + 11 专家）
├── references/             中央规范与治理文件（含 37 条编号经验、36 份变更记录）
│   ├── database-schema/    执行层数据底座（表结构、视图、种子数据）
│   └── prs/                逐次变更记录：问题、根因、修复、验证
├── scripts/                确定性出件与校验脚本（渲染、自检、归档、路由回归）
├── assets/                 标准 Word 模板（标题自动编号、封面、目录、图表题注）
├── avatars/                角色头像
├── skills/                 配套检索技能
├── manifest.yaml           包清单
└── README.md
```

## 核心文件从哪里读起

- 想了解**怎么协作**：`agents/embossed-solution-team-team-lead.md`（团长手册，含六道闸门与交接物规范）
- 想了解**机制为什么这么设计**：`references/design-philosophy.md`
- 想了解**文档怎么出**：`references/doc-tree-spec.md` + `references/word-template-style-spec.md`
- 想了解**质量怎么保证**：`references/communication-protocol.md` + `references/style-guide.md` + `scripts/doc_selfcheck.py`
- 想了解**踩过哪些坑**：`references/lesson-index.md`（37 条，每条含场景、教训、固化位置）
- 想了解**知识怎么演进**：`references/governance.md`（提案、异源审核、版本锁定、可回滚）

## 环境要求

- Python 3.9 及以上
- 出件依赖：`python-docx`；PDF 导出与核验另需 `pymupdf`
- 模板为 `.dotx`，可在 Microsoft Word 或 WPS 中使用

```bash
python -m pip install python-docx pymupdf
```

## 定制与复用

保留调度与纪律骨架，替换角色与知识库即可改造为其他领域的团队：

1. 角色可增删：按"该角色缺席时结论是否改变"决定启用与否；
2. 纪律可沿用：量化指标、四段式回传、验收四维度与具体业务无关；
3. 脚本可替换：出件与自检脚本可换成目标平台等价物，但建议保留自检门槛；
4. 诚实红线建议保留：这是交付可信的前提。

首次复用建议先跑一个中等复杂度任务，对照 `references/team-overview.md` 的量化指标核对执行情况，再决定裁剪幅度。

## 贡献

欢迎提交 Issue 与 Pull Request。涉及 `references/` 的改动请遵循 `references/governance.md`：附证据引用、走异源审核、锁版本、留痕可回滚。机制类改动合入后请同步更新 `references/team-overview.md`。

## 许可证

本项目采用 [MIT License](LICENSE)。

## 说明

- 文档中的项目名、客户名、金额均为脱敏后的示例，不代表任何真实客户或项目。
- 本项目引用的第三方书籍与资料，其著作权归原作者所有；本仓库仅作观点评述与引用，不含原文摘录。
