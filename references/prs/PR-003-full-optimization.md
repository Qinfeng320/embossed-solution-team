# PR-003 · 专家团全量优化（对齐《AI Agent》方法论补齐 8 短板）

> **元信息**：PR 号 `PR-003-full-optimization` ｜ 日期 2026-08-08 ｜ 状态 **Merged** ｜ 作者 ORCH（团长）｜ 审核方式 异源人工复核（八点逐条核）｜ 合入 `governance.md` v1.3 / `design-philosophy.md` §19
> **背景**：用户"全量更新以及优化"——将此前（对话）梳理的 8 个"专家团对照《AI Agent》方法论的可优化点"全部落地为 PR-003，补齐已知短板。

---

## 一、动机

此前审计确认：专家团整体**高度遵循**《AI Agent》方法论（`design-philosophy.md` 已逐章对齐全书 10 章），但存在 8 处"方法论有、实际偏弱"的缝隙。本 PR 将它们全部补齐为可执行 SOP，使专家团从"原则已标注"升级为"机制可核查"。

## 二、优化点与落地清单

| # | 优化点 | 书中依据 | 落地文件 / 机制 | 状态 |
|---|--------|----------|----------------|------|
| ① | SOP 级评估数据集与 pass^k 回归 | Ch.6.3/6.4/6.9 | 新增 `scripts/sop_eval.py` + `references/sop_eval_cases.md`（6 golden cases，k=5 确定性 True） | 已落地（骨架；端到端 LLM 编排质量评估待接运行日志） |
| ② | RAG 稠密向量 + 重排序架构 | Ch.3.2 | `knowledge-index.md` §7.1 补检索层接口契约（BGE-M3 稠密 + RRF 混合 + bge-reranker + recall@k 量化；MVP 仍 TF-IDF） | 已落地（架构与接口；embedding 推理待算力） |
| ③ | 客户不可信输入审计闸 | Ch.4 / Ch.5.1 | `ver-agent.md` §7 补「闸门②·不可信输入两层统一核验」**真实定义**（原 SOP 指针悬空）+ `input-spec.md` 补不可信输入信任边界条目 | 已落地 |
| ④ | 双 ver 冗余 / 异源交叉 | Ch.10.4 / MAST | `ver-agent.md` §7 冗余条款 + `team-lead.md` Phase 4 双 ver | 已落地（机制定义；依赖运行时多实例调度） |
| ⑤ | 主动遗忘 / 定期修剪 | Ch.8.2/8.4 | `team-lead.md` 定期整理例程补"主动遗忘/修剪"步骤 | 已落地 |
| ⑥ | 状态栏看门狗 | Ch.10.4.2 | `team-lead.md` §6.5 看门狗条款（停滞 2 轮自动 shutdown+派新） | 已落地（机制定义） |
| ⑦ | 评估驱动动态选型 | Ch.6.6 | `team-lead.md` §6.5 动态选型条款（前置①） | 已落地（接口占位） |
| ⑧ | 异步事件驱动标注 | Ch.4.7 | `team-lead.md` §6.5 标注为"有意简化" | 已落地（标注） |

## 三、实测与验证

- **sop_eval 回归**：`python scripts/sop_eval.py --k 5` → **6/6 PASS，通过率 100%，确定性 True**（k=5 同输入结果一致，杜绝"看运气"）。
- **闸门②定义补全**：消除团长 SOP §6.5 长期悬空的"闸门② 定义见 ver-agent §6"指针，现为 `ver-agent.md` §7 的真实可执行定义，并下沉到 `input-spec.md` 入口隔离规则。
- **治理自洽**：`governance.md` v1.2→v1.3，change_log 补 v1.3 行；`design-philosophy.md` 新增 §19 八点落地映射。
- **未破坏既有机制**：sop_eval 回归与既有 `verify_citation_lines.py` 自测（11/11）互不冲突，PR-002 收敛态保持。

## 四、诚实边界（已知待补，不夸大）

1. **① 端到端 LLM 编排质量评估**：当前 sop_eval 校验"结构合规 + 红线可达性 + 确定性闸可达性"，端到端（团长运行真实 SOP 产出方案）的质量评估需接入团长运行日志后补全（脚本预留 `ingest_run_log()` 接口）。
2. **② 稠密 embedding**：BGE-M3 类嵌入需本地/内网推理服务，当前环境未配置，故 `knowledge-index` 仍运行 TF-IDF MVP；接口契约已就位，算力到位即可插拔升级。
3. **④⑥ 运行时依赖**：双 ver 冗余、状态栏看门狗依赖团长调度层实际派发多实例并监控状态栏——机制已定义，运行期编排需显式实现。

## 五、合入判定

**Merged**。八点全部落地并校验：
- 机制级可核查项（①③④⑤）已写入 agent/reference 定义；
- 接口/架构级（②）已定契约；
- 机制定义级（⑥⑦）与标注级（⑧）已显式声明。
所有改动经异源人工复核，未引入回归（`verify_citation_lines.py` 仍 0 阻断，sop_eval 6/6 PASS）。

> 后续增量：① 的端到端日志接入、② 的 embedding 落地，可作为 PR-004 候选。
