# PR-015 发布打包管线建立（hooks 移出自动化）

> **类型**：工具与文档（包外维护工具 + README 修正） ｜ **版本**：1.2.3 → 1.2.4 ｜ **日期**：2026-10-16 ｜ **状态**：Merged

## 背景

1. 本包含 `hooks/`（运行时增强），而专家包规范将其列为禁项（官方校验器报错）。既定策略为「运行时保留、发布前移出」；此前移出动作**无自动化、无演练**，列为待决项。
2. README「打包分享」段引用的 `scripts/package_expert.py` 在包内并不存在（真实脚本由 expert-manager 技能提供、须在其技能目录下运行）——照抄该命令必然失败；「安装」段同源问题一并修正。

## 变更

| 位置 | 变更 |
|---|---|
| `package_release.py`（专家市场维护区 `_backups/`，包外） | 新增发布构建脚本：复制 → 移出 hooks/ 与 plugin.json 声明 → 清理平台标记/缓存 → 官方打包器（内置校验闸，0 错误才打包）→ zip 产物核验（无 hooks 残留、关键文件在位）→ 输出 `_dist/` 版本化 zip + 构建说明（含 SHA-256） |
| `README.md` | 「打包分享」重写：发布前须知（hooks 禁项）+ 一键流程 + 手工等价流程；「安装」命令补充运行目录说明 |
| `.codebuddy-plugin/plugin.json` | 版本 1.2.3 → 1.2.4 |

## 发布构建演练（2026-10-16 13:00）

- 命令：`package_release.py <expert-dir> --label 20261016`
- 构建区校验：官方校验器输出 **"✅ Expert package is valid!"**（0 错误 0 警告；源包的 hooks 错误已按预期移出）
- 产物核验：120 个文件、4.8 MB；无 hooks 残留；`settings.json` / `.codebuddy-plugin` / README 在位；plugin.json 无 hooks 字段
- 文件数账目：源 124 = 打包 120 + hooks/ 3（移出）+ `.gitkeep` 1（打包器跳过隐藏文件）
- SHA-256 与最终文件数：以 `_dist/` 构建说明为准（正式分享前重跑构建）

## 实施要点（两处关键发现）

1. **校验器定位要求**：官方校验器强制专家位于 `<WORKBUDDY_CONFIG_DIR>/plugins/marketplaces/my-experts/plugins/` 之下（"能否被发现"检查）。构建区因此按「仿真配置路径」组织，并向校验子进程传入对应 `WORKBUDDY_CONFIG_DIR`——构建区不触碰真实市场目录。
2. **打包器跳过规则**：隐藏文件（除 `.codebuddy-plugin`）与 `__pycache__` / `.gitkeep` 等不进入 zip。

## 回滚

- 删除 `_backups/package_release.py` 与 `_dist/` 产物；README 与版本号可由 `_backups/embossed-solution-team_20261016-1257` 快照还原。

## 备注

- 发布包仍含 `runs/` 历史样例与 `scripts/_sigtest/`（历史验证物）；如需精简分发，另行专项。
- 本记录随包发布时可能被包含在 zip 中：若 zip 的 SHA 与此处描述不一致，以 `_dist/` 构建说明为准。
