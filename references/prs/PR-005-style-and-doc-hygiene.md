# PR-005：文风与文档卫生规范（style-and-doc-hygiene）

> 合入日期：2026-10-12 ｜ 状态：Merged ｜ 来源：《汽车防夹手报告编写总结与专家团优化计划》（防夹手项目复盘，经用户确认执行）｜ 前置：PR-001 / 002 / 003 / 004

## 一、动机

用户指令（2026-10-12）：梳理报告编写过程的方法论、工作流程与输出行为规范，据此改进专家团协作方式与输出质量——"更新专家团策略，使专家团输出的文档更聪明、更符合要求"。

对照核查结论（范围：12 名成员定义、全部 references、全部 scripts、3 个历史项目运行记录）：

- **核验与治理层已完备**（红线、caveat、勘误记录、决议书、复验轮次等已具备或部分具备）；
- **缺口集中在输出侧**——① 行文红线缺失，且现行格式规范"不禁用任何词"条款（2026-08-10）与用户 2026-10-12 要求**直接冲突**；② 文本卫生（全角空格 / 拉丁邻接空格 / 自动间距）无处理；③ 元数据清洁缺失；④ 渲染成图验证缺失；⑤ 投屏件纪律缺失；⑥ 核验台账模板与案例场景核验缺失；⑦ HTML 辅助形态、研究报告体裁、术语同步流程缺失。

用户确认"都修改"——P0 + P1 + P2 十项措施全部执行。

## 二、变更清单（十项措施 → 落地映射）

| # | 措施 | 落地文件 | 要点 |
|---|------|----------|------|
| P0-1 | 文风红线体系 | `references/style-guide.md`（新增）；`document-format-standards.md`（修订）；`scripts/check_style_words.py`（新增）；`mat/ver/docx/team-lead` 四份 agent（衔接） | 三类禁用词＋行业例外；工作痕迹 8 类；交付前终扫（筛子定位、判读在 ver） |
| P0-2 | 文本规范化 | `scripts/normalize_docx_text.py`（新增）；规范条款 | U+3000→半角空格×2；数字/英文邻接空格清理；autoSpaceDE/DN=0；幂等、安全写入 |
| P0-3 | 元数据清洁 | `scripts/clean_docx_metadata.py`（新增）；docx 自检清单 | 作者/最后修改者清空；customXml / custom.xml 残留移除；保存后须重跑 |
| P1-1 | 渲染成图验证 | `scripts/render_docx.py`（新增）；docx QA Gate | Word COM→PDF→逐页 PNG；结构化读回之外的视觉核对层 |
| P1-2 | 投屏件纪律 | `mat-agent.md`；`style-guide.md` §五 | 正式件与准备件分离；元层面内容扫描 |
| P1-3 | 修改后验证五步 | `team-lead.md` §6.5；`docx-agent.md` | 修改→全域扫描→渲染验证→备份差异→版本收敛 |
| P1-4 | 核验台账与场景核验 | `ver-agent.md` | 台账模板（可外部核验/二手附限定/内部数据标性质）；案例/判例场景适配核验 |
| P2-1 | 辅助 HTML 附版 | `mat-agent.md`；`docx-agent.md` | 浅色单文件 HTML；双写同步纪律 |
| P2-2 | 研究报告体裁 | `document-format-standards.md` §0.12；`style-guide.md` §3.1 | 论文标准基线（与公文体分场景并行）；文研究体裁规范 |
| P2-3 | 术语/口径同步清单 | `team-lead.md` §6.5 | 修正登记＋全域扫描＋旧表述清零 |

配套：`governance.md` bump 至 v1.5（头部元数据＋change_log 行）；`README.md` 同步（功能、真相源、脚本清单）。

## 三、验证

1. **四脚本自测（2026-10-12，样例 docx + md）**：
   - `check_style_words.py`：正确命中 4 处（含表格单元格内文），白名单例外（左对齐 / 整改闭环）正确排除，退出码符合预期 ✓
   - `normalize_docx_text.py`：U+3000 ×1 → 0；邻接空格删 3 个（"100 N"→"100N"、"Anti-Pinch System"→"Anti-PinchSystem"）；autoSpace 注入 37 处（docDefaults + 段落样式）；**幂等复跑全 0 变化** ✓
   - `clean_docx_metadata.py`：creator 清空验证通过；customXml 3 个部件移除；清理后文件经 Word 正常打开（渲染链路实测）✓
   - `render_docx.py`：Word COM → PDF → PNG 链路通过（1 页样例渲染成功）✓
2. **一致性核对**：style-guide 与四份 agent 定义、格式规范、README 引用互链齐全；governance v1.5 记录在案。

## 四、诚实边界（未夸大）

- `check_style_words.py` 为**词表筛**——语义判定仍由 ver 执行（呼应 governance §五-②「语义解析而非关键字黑名单」精神：脚本负责把可疑项挑出，不代替判读）；
- 词表为**核心表**（用户明确列举词），后续可经本 PR 协议扩充；
- `render_docx.py` 依赖本机 Word 组件，不可用时**降级提示**（不静默跳过）；
- 元数据清洁：Word/WPS 保存后会重新写入属性，须**保存后重跑**（已在自检清单注明，非一次性动作）。

## 五、合入

- `references/`：新增 `style-guide.md`（v1.0）；修订 `document-format-standards.md`、`governance.md`（v1.5）；本 PR 文档。
- `agents/`：`mat-agent.md`、`ver-agent.md`、`docx-agent.md`、`embossed-solution-team-team-lead.md` 四份（属 agent 指令层，按 governance §六 实测反馈回流协议合入）。
- `scripts/`：新增 4 个（含自测）。
- **回退保障**：执行前全量备份于项目工作区 `output/team_optimization_20261012/plugin_backup_20261012/embossed-solution-team/`；如需回退，以备份覆盖对应文件后按 §五 逐项核验。

## 六、维护注记

- **2026-10-12（同日追加）**：`check_style_words.py` 复验中新增**语境排除规则**（正则 `占位[符文图页]`——遮蔽"占位符/占位文本/占位图"等技术用法，避免对"占位"进取腔的误报），白名单与语境排除机制已文档化于脚本头部。属词表筛的边界修正，随本 PR 记录；回归测试通过（既有命中项不变、技术语境正确排除）。
