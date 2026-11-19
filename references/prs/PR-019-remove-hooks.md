# PR-019 · 移除 hooks（调整运行时增强策略）

> 版本元数据：`PR: 019` ｜ 提出 2026-11-16 ｜ 状态：已合入 ｜ 关联经验：L-28
> 类型：包维护（移除官方校验器禁项）｜ 触发：用户明确指令「删除 hooks」

## 一、起因与目标

专家包原有两枚只读 hook：`SessionStart` 环境自检、`SubagentStop` 成员轨迹采集（落 `subagent-events.jsonl`）。专家包规范将 `hooks/` 列为禁项，官方 `validate_expert.py` 因此长期报 1 错误（既定偏差，原策略为「运行时保留、发布前移出」）。

用户决定移除 hooks，目标：源包直接通过官方校验与打包，消除该禁项偏差。

## 二、改动清单（最小 diff · 可回滚）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `hooks/`（3 文件） | **移出**至维护区 `_backups/hooks_removed_20261116-1825/hooks/`（未硬删，可移回恢复） |
| 2 | `.codebuddy-plugin/plugin.json` | 删除 `"hooks": "./hooks/hooks.json"` 字段（否则 coherence E1 报悬空路径） |
| 3 | `README.md` | 「发布前须知」改写为本包已移除 hooks、可直接打包；补备份位置说明 |
| 4 | `references/lesson-index.md` | 追加 L-28 经验条目 |

> 历史留档未改：L-01/L-03/L-10 及 PR-011~015 中关于 hooks 的记录系当时事实，按治理规范保留不覆写。

## 三、验证

- `python scripts/verify_package_coherence.py` —— 须 ERROR=0 / WARN=0。
- `python scripts/validate_expert.py <expert-dir>` —— 预期 hooks 禁项错误消除（0 错误）。
- `python scripts/register_expert.py <expert-dir>` —— 修改后重新注册。

## 四、回滚方式

将 `_backups/hooks_removed_20261116-1825/hooks/` 移回包根，并在 `.codebuddy-plugin/plugin.json` 恢复 `"hooks": "./hooks/hooks.json"` 字段，重新注册即可。
