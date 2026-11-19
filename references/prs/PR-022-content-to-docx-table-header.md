# PR-022 · content_to_docx 表头跨页重复与表题修复

> 版本元数据：`PR: 022` ｜ 提出 2026-11-16 ｜ 状态：已合入 ｜ 关联经验：L-31
> 类型：工具修复（文档出件通道）｜ 触发：用方案 Markdown 出正式 .docx 时 doc_selfcheck 报 2 项 FAIL

## 一、起因

用 `content_to_docx.py`（标准模板内容→Word 通道）出《售前专家团技术方案》.docx，`doc_selfcheck.py` 报两项未通过：
- 表题数=表数：表题 0 / 表 16（内容 JSON 的 tbl 未带 caption）；
- 表头跨页重复：缺 `tblHeader`（16 个表格首行无 `<w:tblHeader/>`）。

## 二、根因

`content_to_docx.py` 的 `make_tbl()` 只生成普通 `<w:tr>`，未给首行加 `<w:trPr><w:tblHeader/></w:trPr>`。此为脚本固有缺口——L-20 记录的"表头跨页重复下沉到渲染层"是 `build_docx.py` 的 `_layout_table`，**不覆盖 content_to_docx 通道**，两条出件通道独立。

## 三、改动清单

| # | 文件 | 改动 |
|---|---|---|
| 1 | `scripts/content_to_docx.py` | `make_tbl()` 首行加 `<w:trPr><w:tblHeader/></w:trPr>`（修改前备份 `scripts/_content_to_docx.py.bak_pre_tblheader`） |
| 2 | 本次出件的内容 JSON | 每个 tbl 带 `caption`（表题取表头前两列拼接） |
| 3 | `references/lesson-index.md` | 追加 L-31 |

> 表题由调用方内容 JSON 提供，脚本侧 `make_tbl` 已支持 `caption`（原逻辑），本次仅补内容侧填写与表头重复。

## 四、验证

- 重新生成 .docx 后 `doc_selfcheck.py --expect ...`：**12/12 全通过**（表题 16/16、表头重复全部已设）。
- `python scripts/verify_package_coherence.py`：**ERROR 0 / WARN 0**（期间 settings.json 被平台清理，按 L-07 补齐）。
