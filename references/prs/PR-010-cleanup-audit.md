# PR-010：全面瘦身审计与低风险清理（cleanup-audit）

> 执行日期：2026-10-14 ｜ 状态：**已执行** ｜ 触发：用户"专家团经过多轮修改，看一下哪些内容可以优化精简，很多老旧的内容有没有可以删除的" ｜ 前置：PR-001~009

## 一、已执行清理（低风险 · 冗余副本 / 缓存 / 测试痕迹）

| 项 | 体量 | 理由 |
|---|---|---|
| `avatars/docx-agent.png.bak` | 1.2 MB | 旧头像备份（正式头像 `docx-agent.png` 在，备份冗余） |
| `assets/文字文稿1.dotx.bak_×2`（7/8 月） | ~27 KB | 旧模板备份（母文件在；且 `文字文稿1.dotx` 已降为"客户指定公文体"备用） |
| `scripts/__pycache__/` | ~60 KB | Python 字节码缓存（随时再生） |
| `runs/_cg_test/`、`runs/_rag_test/` | 微量 | 并发守护 / 稠密检索一次性自测痕迹 |

## 二、标注更新（防历史内容误导）

- `document-format-standards.md` §八 图题行：旧"宋体五号 10.5pt"口径 → 标注"由 §0.14 接管（图题=角标-图片/表题=角标-表格，自动编号）"；
- `runs/instance_test_20260812.md`：头部加历史声明（当时口径 ≠ 现行口径）。

## 三、建议保留（本次不动 · 附理由——供用户后续决策）

| 项 | 体量 | 保留理由 | 若要精简 |
|---|---|---|---|
| dfs §0.1 历史存档区（含 8-9 月历版口径 + 轮次答复） | ~10 KB | 规范演变追溯；已双处标注"存档"；删除会断修订链 | 可整体移入 `prs/` 附录（不建议直接删） |
| agents"各章深挖回灌"节（9 成员） | 各 ~2-4 KB | 经 PR-001 异源互审合入的正式内容（含实用规则，非纯理论） | 可折叠为独立附录文件（专项） |
| `pdf-chapter-summaries / deep-mining / reading-guide` | ~53 KB | **引用活跃**（9 个 agent + design-philosophy + governance）；PR-001 证据链 | 不建议删（断引用） |
| scripts 实验/理论类脚本（`concurrency_guard` / `dynamic_router` / `evolution_meta` / `ingest_run_log` / `retrieval_dense` / `sop_eval` / `trace_observability` / `verify_citation_lines` / `verify_text_count` / `apply_table_style` 等） | 共 ~100 KB | PR-001~004 治理登记在案；删除会破坏"登记-实现"对应；团队演进档案 | 不建议删 |
| `scripts/_sigtest/`（含 `pr2_full_scan.json` 259 KB 等） | ~330 KB | PR-002 全包扫描验证数据（可复现证据）；**无任何引用** | **插件总体积精简时此处最优先可删**（纯测试数据）；本次保守保留 |
| `assets/样式模板.dotx.bak_1791954391` | 16.8 KB | ⑬ 页边距终态化前的最近回退点 | 建议保留 |
| `runs/sample-2026-08-08/` + `instance_test_20260812.md` | ~8 KB | run-log 样例（ingest_run_log 演示）+ 实例测试档案 | 保留 |

## 四、回退保障

已删项均为**冗余副本 / 缓存 / 测试痕迹**（非事实源），无内容丢失：`.bak` 类可由母文件再生成；测试痕迹可由对应脚本重跑产生。

## 五、审核记录

- 触发：用户指令；执行方式：全插件扫描（大文件清单 / 废弃标记 grep / 引用密度检查 / 目录盘点）；
- 引用核验：`pdf-chapter-*`（活跃引用，保留）、`database-schema/*.sql`（4 文件齐全，team-lead 引用无断链）、`_sigtest`（零引用，列"可删候选"）；
- 限制：本档为"低风险清理 + 建议清单"模式——**中风险项（`_sigtest` 等）未动**，待用户点选后再行处置。
