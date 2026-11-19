# PR-006：外部专家整合（external-integration）

> 合入日期：2026-10-12 ｜ 状态：Merged ｜ 来源：外部专家包整合（deep-research / competitive-market-research / deep-research-team）＋ 第二批优化候选清单 ｜ 前置：PR-001~005

## 一、动机

用户指令：提取两个外部专家（"深度研究专家""竞品调查与市场研究"）的优点，整合进自建专家团。

用户确认（2026-10-12）：整合范围**全部**（含可选资产迁移）；与第二批候选清单**并行执行**；微信文章检索技能**迁入**。

## 二、变更清单

| 类别 | 内容 | 落地 |
|------|------|------|
| 整合包一·研究方法 | 研究三型判定（深挖/广扫/直答）、预算与终止条件、计划落盘、子任务分派要素、澄清问题规范（≤3）、阶段确认门、降级标注 | `team-lead.md` §6.4、`ind-agent.md`、`cus-agent.md` |
| 整合包二·证据体系 | 来源分级（一手/二手/低质）＋低质识别特征、证据四类分级（事实/自述/推断/未知，"未知≠否定"）、来源登记与事实台账、冲突处理、方法论透明度、调研边界 | 新建 `references/evidence-spec.md`、`ver-agent.md` |
| 整合包三·数值价格 | 原值保留、不自行换算、不可比标注、旧料更新（不覆盖/口径匹配才写变化） | `evidence-spec.md` §四/§六、`dat-agent.md` |
| 整合包四·文体与产物 | 研究报告结构模块（含局限节）与篇幅分档、prose 文体、操作手册体裁、汇报件结构原则、图示规范 | `style-guide.md` v1.1、`docx-agent.md` |
| 整合包五·资产与评测 | 微信文章检索技能迁入（3 文件、纯标准库）；评估用例扩充 4 例（多源冲突 / 旧料更新 / 未知≠否定 / 降级声明） | `skills/wechat-article-search/`、`sop_eval_cases.md` |
| 第二批并行项 | C3 技术踩坑 2 条；B2 风格范本；B1 编校检查（清单＋脚本）；C1 图示 / C2 合并拆分 | `document-format-standards.md` §0.5、`mat-agent.md`、`docx-agent.md`、`style-guide.md` |
| 工程脚本 | `lint_docx_text.py`（编校检查）、`merge_docx.py`（多文档合并）、`split_docx.py`（按章节拆分） | `scripts/` |
| 治理 | governance bump v1.6 | `governance.md` |

## 三、验证

1. **脚本自测（全部通过）**：
   - `lint_docx_text.py`——正确检出复词（"以及以及"）/ 连续标点 / 半角标点混用（3 处，rc=1）✓
   - `merge_docx.py`——3 份文档合并后：段落/表格/标题完整，2 张图片迁移成功；**Word 渲染打开验证通过**（3 页 PDF）✓
   - `split_docx.py`——按一级标题拆出 3 份，标题归属与图片引用筛选正确（无引用媒体未随册输出）✓
   - 既有脚本回归：`check_style_words.py` 语境排除回归通过 ✓
2. **全包扫描**：`plugin.json` / 注册配置 JSON 校验通过 ✓
3. **技能迁移**：`skills/wechat-article-search`（SKILL.md + references + scripts）迁移完成并完成登记 ✓

## 四、诚实边界（未夸大）

- `merge_docx.py` / `split_docx.py` 为 v1 版：适配**标准结构文档**（同管线产出 / 一级标题分节）；合并时编号定义以骨架为准；超链接关系、复杂编号合并等边界已标注于脚本 docstring；两者均内置"合并/拆分后须重跑规范化与编校检查并渲染核对"提示——不替代核验环节。

## 五、回退保障

执行前全量备份于项目工作区 `output/team_optimization_20261012/plugin_backup_pr006_20261012/embossed-solution-team/`；任一文件异常，以备份覆盖还原。
