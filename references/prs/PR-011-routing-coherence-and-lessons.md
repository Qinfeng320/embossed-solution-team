# PR-011：路由单源 + 包一致性校验 + 经验索引（routing-coherence-and-lessons）

> 执行日期：2026-10-16 ｜ 状态：**已执行** ｜ 触发：用户放行（对 reverse-skill 迁移评估 P0 三件套的落地批准）｜ 前置：PR-001~010 ｜ 回退基线：`_backups/embossed-solution-team_20261016-1030`

## 一、背景

调研 `zhaoxuya520/reverse-skill`（面向 AI 客户端的安全技能路由包）后评估出可迁移 P0 三件套：① 路由单源 + 路由回归；② 包一致性校验脚本；③ 「先查经验」消费纪律 + 经验索引。本 PR 为其实施批次——全部为既有契约的补强，**不新增角色、不新增阶段**。

## 二、变更清单

### 新增（7 件）

| 文件 | 说明 |
|---|---|
| `references/routing-config.json` | 局部复用路由唯一真相源（12 条基础路由 + 组合规则） |
| `references/routing-cases.json` | 路由回归用例（20 条：hint → 期望路由） |
| `scripts/route_intent.py` | 确定性路由建议（`--hint` / `--list` / `--test` / `--json`） |
| `scripts/verify_package_coherence.py` | 包一致性校验（E1~E4 错误级 + W1~W4 提示级，共八类检查） |
| `references/lesson-index.md` | 经验索引（消费入口 + 写回登记；首批 L-01~L-06 条目） |
| `settings.json` | Team 型必备件（`{"agent": "embossed-solution-team-team-lead"}`） |
| `references/prs/PR-011-routing-coherence-and-lessons.md` | 本记录 |

### 修改（6 处）

| 文件 | 变更 |
|---|---|
| `agents/embossed-solution-team-team-lead.md` | ① §2.3 增「路由配置」「经验索引」两条中央真相源；② §6.1.1 路由表 → 路由配置指针 + 用法三步（-403 字符，顺带瘦身）；③ §6.4 研究规范第 3 条改为「先查经验、再列计划」；④ §6.5 修改后验证五步第②步并入一致性校验；⑤ §6.5 定期整理例程增 lesson-index 维护；⑥ §6.5 增「包一致性校验」纪律条目 |
| `references/governance.md` | v1.10 → v1.11：§六 补「经验写回触发条件」五类；change_log 加行 |
| `references/design-philosophy.md` | 第二个「## 19」→「## 20」（编号重复修复） |
| `scripts/content_to_docx.py` | CLEAN_RULES「章节词」`[部分篇章节]` → `[部分篇章节]+`（修复「第一部分」残留「分」） |
| `README.md` | 真相源与脚本清单同步新增件 |
| `.codebuddy-plugin/plugin.json` | version 1.1.0 → 1.2.0 |

## 三、测试记录（2026-10-16）

| 测试 | 结果 |
|---|---|
| 路由回归 `route_intent.py --test` | **20/20 通过** |
| 路由示例（"帮我核对这份投标材料的数字一致性，顺便看看能不能外发"） | 命中 [R-ver] → ver / Phase 4 清单 |
| 一致性校验首跑 | 捕获 ERROR 2：design-philosophy 双「19」（真实问题）+ document-format-standards（脚本误报——`0.2b/0.2c` 带字母后缀被正则截断，已同步修正脚本） |
| 一致性校验复跑 | **ERROR 0**（余 WARN：quickPrompts / displayDescription，见待决项） |
| SOP 评估回归 `sop_eval.py` | PASS 8 / WARN 2 / FAIL 0（与基线一致；2 WARN 为既有待补项） |
| 编号清洗单测 | `第一部分 采购需求` → `采购需求`；`第三方评估` 不受影响 |
| `validate_expert.py` | 错误 3 → **2**（settings.json 已补；余 quickPrompts 4 条 + hooks 禁项） |
| `register_expert.py` | 重新注册通过 |

## 四、已知待决项（本批未动）

1. `quickPrompts` 现 4 条（规范固定 3 条）——需用户定夺删减或合并哪条；
2. `displayDescription.zh` 现 69 字（建议 40–50 字）——文案取舍待定；
3. `hooks/` 为专家包校验器禁项（平台运行时可加载插件钩子，见 hooks 批次记录）；
4. 数据库设计文档仍按「ORCH + 9 域」建模（与现行 11 成员口径不一致，待专项批次）；
5. 原 `content_to_docx` 修复涉及的演示脚本 `demo_clean_and_map.py` 未定位（如需同步请提供路径）。

## 五、回退保障

- 时点基线：`_backups/embossed-solution-team_20261016-1030`（目录副本 + zip + 注册快照 + INFO 说明）；
- 单项回退：删除新增 7 件 + 还原 6 处修改即可；路由与校验脚本均为独立文件，不影响主流程。
