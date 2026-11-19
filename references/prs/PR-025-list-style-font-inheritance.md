# PR-025：修复注入列表样式的字体体系脱钩（列表字号偏小、符号变形）

- 日期：2026-11-17
- 类型：缺陷修复（脚本，`scripts/build_docx.py`）
- 状态：已合入
- 前置：PR-024（同一注入函数的第一层缺陷：编号错位）

## 现象

PR-024 修复编号后，用户在 Word 中打开正式件仍见列表格式与正文不一致：列表字号明显偏小、项目符号"·"被渲染成短横线观感、行距偏紧。LibreOffice 渲染成图核验（render_docx.py）无异常——**渲染引擎用回退字体掩盖了问题，仅 Word 实机可见**。

## 根因

`_ensure_list_styles()` 从 python-docx 默认模板注入 `List Bullet` / `List Number` 样式时，注入的样式元素携带三处"默认模板遗产"：

1. **无有效 basedOn / 既有 basedOn 指向默认模板的 Normal**（在目标模板中是悬空引用）——不继承正文样式的字体、字号、行距；
2. **rPr 引用主题字体**（minorHAnsi / minorEastAsia）——Word 按当前模板主题字体渲染，脱离正文的仿宋体系；
3. pPr 携带 autoSpaceDE/DN=0、contextualSpacing 等本地覆盖，与正文规范（autoSpace 校正）冲突。

三层叠加导致列表在 Word 中自成一套字体体系。

## 修复（`scripts/build_docx.py` `_ensure_list_styles`）

deepcopy 注入元素后，删除其携带的 `w:pPr`、`w:rPr`、既有 `w:basedOn`，重新挂 `basedOn` 指向当前模板 Normal 的 styleId。注入样式自此只剩"名字 + 基于正文样式"，字体字号行距完全继承正文口径；列表符号仍由渲染层确定性前缀（PR-024）承担，缩进仍由 `make_docx.fix_lists()` 设置。

注意：默认模板的这两个 built-in 样式**自带 basedOn（指向默认模板 Normal）**，直接追加新 basedOn 会产生两条并存（非法，Word 容错行为不可依赖）——必须先删后加。

## 验证

- Word 实机（COM 自动化）读回生效格式：列表条目＝仿宋 14pt，与正文段落完全一致；
- 样式表核验：两样式各仅一条 basedOn，指向模板 Normal（styleId="1"）；
- 全部出件闸门复跑通过（自检 12 项 / 文风终扫 0 命中 / 文本规范化 / 元数据清洁 / 渲染成图）。

## 教训（已录 L-34）

- 样式注入的缺陷不止编号错位一类：**basedOn 悬空 + 主题字体引用**会让列表脱离正文字体体系；
- LibreOffice 渲染成图不能代表 Word 实机效果（回退字体掩盖差异），涉及字体字号的核验须用 Word 实机（COM 读回生效格式）或人工在 Word 中确认。
