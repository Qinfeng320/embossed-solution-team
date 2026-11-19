# PR-012：quickPrompts 收敛 & settings.json 生命周期定性（quickprompts-and-settings-lifecycle）

> 执行日期：2026-10-16 ｜ 状态：**已执行** ｜ 触发：用户决策（待决项①：quickPrompts 4→3，选定「方案一：合并第 2、4 条」）｜ 前置：PR-011 ｜ 回退基线：`_backups/embossed-solution-team_20261016-1030`（本批改动为 3 个文本文件 + 1 个人工补齐件，逐项可逆）

## 一、背景

- **待决项①**：`plugin.json` 的 `quickPrompts` 现 4 条，专家包规范固定 3 条（`plugin-json-spec.md`；校验器为 error 级）。
- 决策过程：完整展示 4 条原文与展示逻辑（详情页「专家帮你做」全量列出 / 会话侧随机抽样 / 卡片优先第一条）→ 给出四个处理方案（删第 4 条 / 删第 2 条 / 删第 3 条 / 合并第 2、4 条）→ **用户选定方案一：合并第 2、4 条**（四个能力域零丢失）。

## 二、变更清单

| 文件 | 变更 |
|---|---|
| `.codebuddy-plugin/plugin.json` | ① version 1.2.0 → 1.2.1；② `quickPrompts` 4 → 3 条：第 2、4 条合并为新文案「为某客户的方案做需求解析与必要性论证，并给出架构与预算建议」（EN: "Build a demand-analysis and necessity argument for a client's solution, with architecture and budget estimation."）；原第 4 条「给出分层架构、分期路径与预算测算建议」删除 |
| `README.md` | 「使用示例」同步为 3 条 |
| `scripts/verify_package_coherence.py` | W3 提示语移除「待定夺删减」字样（事项已决） |
| `settings.json` | **重新补齐**（11:19 被平台清理，内容不变；见 §三） |

## 三、settings.json 事件复盘（2026-10-16 11:19）

- **现象**：10:36 校验时还在的 `settings.json`（10:30 依包规范新增），于 **11:19:14.697** 从源目录消失（源目录 mtime 精确锁定该时刻）；同期应用完成插件版本物化（cache 1.1.0 → 1.2.0）。文件总数 121 → 120。
- **机制**（自 `app.asar` 内 `ExpertPluginService` 源码取证，非推测）：
  1. **识别签名**：恰含单一 `agent`（字符串）键的 `settings.json`，即被识别为「应用生成的代理覆盖文件」（`readGeneratedAgentOverride`）；
  2. **清理路径 A**：专家停用/会话切换时，`deactivateExpert()` → `removeGeneratedAgentOverrideFile()` 将其作为过期覆盖删除（console 文案「Removed stale expert settings.json」，该行未落入文件日志）；
  3. **清理路径 B**：应用启动时 `removePersistedGeneratedAgentOverrides()` 对官方专家市场（`marketplaces/experts`）做同类清扫；
  4. **生成路径**：专家激活时由应用自行维护该覆盖文件（运行态）；插件加载端读取 `{agent, subagentStatusLine}` 并合并进插件设置。
- **时间线佐证**：专家会话「传感器类别学习」（74d7041e）日志显示——10:14:16 与 11:19:24 代理覆盖两次被置为 `embossed-solution-team-team-lead`；删除发生于 11:19:13–18 的会话/专家切换窗口内，与 deactivate 清理路径吻合。
- **结论与策略**：`settings.json` 属**平台运行态文件**（激活时生成、停用时清理），源目录中手工保留的副本会被平台在停用/切换时清掉；而**包规范（校验器）要求其在位**。采取「保留副本 + 被清理后补齐」策略，`verify_package_coherence.py` E2 检查负责缺失报警。本 PR 已重新补齐（121 文件恢复）。
- **顺带确认（平台插件安装体系）**：市场插件按版本物化到 `plugins/cache/<marketplace>/<plugin>/<version>/`（含 `.in_use` / `.orphaned_at` 标记与 `installed_plugins.json` 安装记录）；**会话实际加载缓存安装件**；源目录版本号变更后，应用在下次专家使用/更新触发时自动重装新版本——本次已自动完成 1.1.0 → 1.2.0，**1.2.1（含本 PR 新 quickPrompts）将在下次专家会话触发时自动物化**。
- **hooks 实证状态更新**：此前会话加载的 1.1.0 安装件不含 `hooks/`（hooks 为 10-15 18:11 新增，1.1.0 快照早于它）；1.2.0 安装件首次包含 `hooks/`。故 `subagent-events.jsonl` 至今无记录属预期。真实会话验证顺延至下次专家会话（届时观察该日志是否新增行）。

## 四、测试记录（2026-10-16）

| 测试 | 结果 |
|---|---|
| `validate_expert.py` | 错误 2 → **1**（quickPrompts 已合规；余 `hooks/` 禁项〔既定偏差〕）；警告 1（displayDescription 69 字＝待决项②） |
| `verify_package_coherence.py` | **ERROR 0 · WARN 1**（仅 displayDescription，待决项②） |
| quickPrompts 结构核验 | 3 条；第 1 条 = `defaultInitPrompt`（首条一致性规则满足） |
| `register_expert.py` | 重新注册通过（注册信息未变更） |
| settings.json | 已补齐并复查在位（121 文件；平台后续再清理时按 §三 策略处理） |

## 五、待决与后续

1. displayDescription 69 字收敛（待决项②，校验警告）；
2. `hooks/` 禁项（既定偏差，打包分享前须移出）；
3. 数据库设计文档「9 域」口径与 11 成员不一致（待专项）；
4. 原演示脚本 `demo_clean_and_map.py` 未定位（如需要请提供路径）；
5. 观察 settings.json 是否再次被平台清理（预期：专家停用时会发生），缺失即按 §三 补齐。
