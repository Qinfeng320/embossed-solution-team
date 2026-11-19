# PR-004：九项架构优化（architecture-optimization）

> 合入日期：2026-08-08 ｜ 状态：Merged ｜ 来源：《深入理解 AI Agent》（`AI-Agents-in-Depth-zh-CN.pdf`）整体架构启发 ｜ 前置：PR-001/002/003

## 一、动机

用户在评审 PR-001~003 后提出：**整体的智能体架构逻辑，通过 PDF 能获得哪些优化与启发**。
评审结论（详见 `design-philosophy.md` §19）指出：前序 PR 已吸收书的"骨架"（不共享上下文＋管理者模式＋显式 handoff＋L0/L1/L2＋双 ver MAST），
但书的"血肉"——第 6 章评估/可观测性、第 8 章持续进化、第 3 章稠密 RAG——尚有明确待补优化头口。
本 PR 将九项优化全部落地为**机制可核查**（脚本＋治理纪律＋agent 指令），而非停留在声明。

## 二、变更清单（九项）

| # | 优化项 | 呼应章节 | 落地文件 |
|---|--------|----------|----------|
| ① | 端到端评估接 run log（失败归因从首个错误） | Ch.6.5.2 / Ch.6.9 | `ver-agent.md` §8 ＋ `scripts/ingest_run_log.py` |
| ② | 可观测性 span 树（成本/质量/延迟审计） | Ch.6.8 | `team-lead.md` §6.7 ＋ `scripts/trace_observability.py` |
| ③ | 并发写哈希校验（MAST ③ 共享状态意外修改） | Ch.10.5.1 | `governance.md` §四' ＋ `scripts/concurrency_guard.py` |
| ④ | 动态选型降级（工作流↔自主路由） | Ch.1.2 / Ch.10.2 / Ch.6.6 | `team-lead.md` §6.5 ＋ `scripts/dynamic_router.py` |
| ⑤ | 双层思考建模（慢规划/快执行＋AdaptThink） | Ch.9.8 / Ch.9.9 | `team-lead.md` §6.8 |
| ⑥ | 稠密 RAG 落地（稠密+稀疏+RRF+重排 MVP） | Ch.3.2 / Ch.3.3 | `knowledge-index.md` §7.1 ＋ `scripts/retrieval_dense.py` |
| ⑦ | 工作笔记 artifact（成员侧中间态复用） | Ch.2.7 | `team-lead.md` §2.4 |
| ⑧ | 进化闭环 meta 化（经验→知识提案） | Ch.8.2 | `governance.md` §六' ＋ `scripts/evolution_meta.py` |
| ⑨ | 全章理论背书总映射 | 全书 | `design-philosophy.md` §19 |

配套：`governance.md` bump 至 v1.4（含头部版本元数据与 change_log 行）。

## 三、验证

1. **六脚本实测（纯 stdlib，Windows + 3.13.12）**：
   - `ingest_run_log.py`：样例 run-log（10 事件）正确定位第 10 步 error 为根因 ✓
   - `trace_observability.py`：span 树聚合 + verdict 统计（含修复：verdict 复用 root span 时独立收集）✓
   - `concurrency_guard.py`：snapshot/check 哈希比对正确检出 modified/added；基线缺失分支返回 exit 2 不崩溃（修复 TypeError）✓
   - `dynamic_router.py`：低后果单点→autonomous、高后果+历史错误率→workflow+双 ver ✓
   - `retrieval_dense.py`：hybrid 融合检索命中正确 chunk（修复 tuple 解包 bug）✓
   - `evolution_meta.py`：样例轨迹无可沉淀信号时如实输出"无提案"（不夸大）✓
2. **行号机检闸复跑**：`verify_citation_lines.py` → **阻断 0 ｜ 存疑 14 ｜ 通过 227**。
   存疑 14 条全部 ⊆ PR-002 §5.5 已人工回原文判读的 19 条集合（cus:80 / tl:355 / mat:95 / pol:78 / pol:81 已转 PASS），
   无新增误报；抽样 grep 确认 A 轮标注（〔引申〕/〔已核验·忠实〕/〔弱锚〕）全部在位。
3. **九点异源人工复核**：Proposer（本包）与 Reviewer 逐项核对「章节呼应真实性＋脚本可运行性＋与既有纪律不冲突」——通过。

## 四、诚实边界（未夸大）

- 端到端评估（①）与可观测性（②）的**真实数据**依赖运行时 run-log 接入：schema 已定、脚本已就位，
  但 `runs/` 尚无真实团长运行轨迹——待实际调度接入后跑首轮回归（样例 `runs/sample-2026-08-08/run_demo.jsonl` 仅供 schema 演示）。
- 稠密 RAG（⑥）：`retrieval_dense.py` 的稠密分支为纯 Python 词袋 TF 向量**占位**，生产级 BGE-M3 嵌入受算力约束仍未实装（接口 hook 已留）。
- 动态选型（④）：`dynamic_router.py` 为确定性启发式路由；基于评估反馈的模型级动态选型仍待 SOP 数据集积累。
- 未改动任何既存忠实引证；未为压低 WARN 指标篡改引用。

## 五、合入

- `references/` 改动：`governance.md`（v1.4）、`knowledge-index.md` §7.1、`design-philosophy.md` §19 —— 已按 PR 协议合入。
- `agents/` 改动：`team-lead.md`（§2.4/§6.5/§6.7/§6.8/§6.6 备注）、`ver-agent.md`（§8）—— 属 agent 指令层，按 §六 实测反馈回流协议合入。
- `scripts/` 新增 6 个脚本 —— 纯 stdlib、无外部依赖，校验通过后随包注册。
