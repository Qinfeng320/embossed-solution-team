# 实例测试报告 · 模板自动编号 + 手写编号剥离（2026-08-12）

> ⚠️ **历史记录**：本文为 2026-08 运行档——当时模板口径为 `文字文稿1.dotx`；**现行 Word 输出统一以 §0.14 标准模板体系（`assets/样式模板.dotx`）为准**。

> 目的：验证 `embossed-solution-team` 输出文档严格套用 `assets/文字文稿1.dotx` 的
> Word 自动编号，且 JSON `section.title` 手写编号已被剥离，杜绝双重编号。
> 触发：用户指令"标题正文一定要套用模板的自动编号，而且要把文档的编号删除，要有实例测试"。

## 测试输入
- 文档树：`~/.workbuddy/embossed_projects/sample-2026-002/artifacts/doc_tree.json`
  （真实业务文档树，标题均为纯文本、无手写序号，`numbering="auto"`）
- 脚本：`scripts/build_docx.py`（已修复：移除 `normal.font.size=Pt(11)` 覆盖，
  新增 `_strip_manual_number` / `_remove_numpr` / `_add_heading_like`，改写 `_render_section`）
- 模板：`assets/文字文稿1.dotx`（已修复：Normal 14pt、heading1/2/3 = 16/16/15pt 加粗黑体、
  保留 numPr 自动编号、sectPr 改 GB/T 9704 页边距）

## 执行命令
```
python scripts/build_docx.py doc_tree.json -o _instance_test_20260812.docx \
  --template assets/文字文稿1.dotx
python scripts/inspect_docx.py _instance_test_20260812.docx --json
```

## 核验结果（逐项）

| 核验项 | 方法 | 结果 |
|--------|------|------|
| 标题无手写序号前缀 | 正则 `[(（]?[一二三四…\d]+[、．.)\）]` 扫描全部 heading | **0 命中**，10 个标题均为纯文本（如"建设背景与判断"） |
| 模板自动编号生效 | 检查 heading 样式 `numPr` | heading1/2/3 = numId=1, ilvl=0/1/2，绑定模板 `numbering.xml` 的 `chineseCounting`（abstractNumId=0） |
| 无双重编号 | `inspect_docx.py` 的 `double_numbering` 字段 | `[]`（空） |
| 正文 14pt | 读 `Normal` 样式 `w:sz` | sz=28 → 14.0pt ✅ |
| 标题字号/字体 | 读 heading 样式 | h1/h2=32(16pt) bold 黑体；h3=30(15pt) bold 黑体 ✅ |
| 页边距 GB/T 9704 | 读 `sectPr` 并换算 | top3.70 / right2.60 / bottom3.50 / left2.80 cm ✅（与标准完全一致） |
| 表格完整 | `inspect_docx.py` tables | 多表渲染正常，无异常空单元格 ✅ |
| 红线落位 | `inspect` + 读附录 | 红线数组非空，附录/脚注均含完整红线 ✅ |

## 结论
✅ **通过**。输出文档：标题序号由模板 Word 自动编号生成（一、/（一）/1.），
JSON 手写编号已被剥离，无双重编号；字号、字体、页边距严格继承模板，符合 GB/T 9704 公文体规范。

## 后续动作
- 专家已通过 `validate_expert.py` 校验并 `register_expert.py` 重新注册（session 8605d509…）。
- 规范已同步至 `agents/docx-agent.md`、`references/document-format-standards.md`、
  `references/doc-tree-spec.md`（标题禁手写编号、套用模板自动编号、build_docx.py 不覆盖模板样式）。
- `_template_aug.docx` 已废弃，统一改用 `文字文稿1.dotx` 作为唯一真相模板。
