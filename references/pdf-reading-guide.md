# PDF 读取指南（pdfkit-py 集成规范）

> **中央真相源**。本文件定义 `doc-in-agent` 读取 PDF 文件时必须调用的 `pdfkit-py` 技能的完整规范：CLI 路径、调用模式、大段 PDF 分块策略、OCR 降级链、与 `parse_docs.py` 的分工、溯源标签格式。全团引用，成员不自写副本。
>
> **核心原则**：凡涉及 `.pdf` 文件的读取、提取、搜索、分析，**必须优先调用 pdfkit-py**，不再仅依赖 `parse_docs.py` 的基础文本提取。`parse_docs.py` 仍用于 Word/PPT/Excel；PDF 的主力读取工具是 pdfkit-py。

---

## 一、CLI 定位与路径

pdfkit-py 技能安装路径：`<pdfkit 技能>`

| 组件 | 路径 |
|------|------|
| CLI 入口 | `<pdfkit 技能>/scripts/pdfkit.py` |
| Venv Python | `<pdfkit 环境>/Scripts/python.exe` |
| 字体目录 | `<pdfkit 技能>/fonts/` |

### 调用模板（Windows · Bash）

```bash
# 标准调用
PDFKIT_PY="<pdfkit 技能>/scripts/pdfkit.py"
PDFKIT_VENV="<pdfkit 环境>/Scripts/python.exe"

"$PDFKIT_VENV" "$PDFKIT_PY" <command> [flags]
```

> **注意**：Bash 环境下用双引号包裹路径即可，无需 PowerShell 的 `&` 调用运算符。

---

## 二、与 parse_docs.py 的分工

| 文件格式 | 主力工具 | 说明 |
|----------|----------|------|
| **PDF** | **pdfkit-py（强制）** | 所有 PDF 读取/提取/分析必须走 pdfkit-py，支持 OCR 降级、分块、表格提取、布局分析 |
| Word (.docx) | parse_docs.py | 维持不变 |
| PPT (.pptx) | parse_docs.py | 维持不变 |
| Excel (.xlsx) | parse_docs.py | 维持不变 |
| 图片 | OCR 技能 | 维持不变 |
| 网页 | 网页抓取/Read | 维持不变 |

**分工纪律**：
- `parse_docs.py` 的 PDF 分支不再作为主力解析器，仅当 pdfkit-py 不可用（venv 损坏、环境缺失）时作为降级备选，且须标注「降级·parse_docs.py·pdfkit 不可用」。
- pdfkit-py 负责格式识别、文本提取、OCR 降级、表格提取、布局分析等**确定性操作**。
- doc-in-agent（LLM）只消费 pdfkit-py 的 JSON 产出，做七维度语义归类与待澄清判断，**不重复做格式识别与页码标注**。

---

## 三、标准读取流程（每次读取 PDF 必须遵循）

### 3.1 第一步：探测 PDF 基本信息

```bash
# 获取页数
"$PDFKIT_VENV" "$PDFKIT_PY" page_count --input "<pdf_path>"
```

产出：`{"ok": true, "data": {"page_count": N}}`。据此判断后续策略。

### 3.2 第二步：检测页面类型（文本型 / 扫描型）

```bash
"$PDFKIT_VENV" "$PDFKIT_PY" detect_type --input "<pdf_path>" --pages '[0,1,2]'
```

- 若返回 `text` → 走 3.3 文本提取路径。
- 若返回 `scanned` / `image` → 走 3.4 OCR 降级路径。
- 若返回 `mixed` → 文本页走 3.3，扫描页走 3.4。

### 3.3 第三步·A：文本型 PDF 提取

```bash
# 小 PDF（≤ 20 页）：一次提取全部
"$PDFKIT_VENV" "$PDFKIT_PY" extract_text --input "<pdf_path>" --format text

# 大 PDF（> 20 页）：分页范围提取（见第四节大段策略）
"$PDFKIT_VENV" "$PDFKIT_PY" extract_text --input "<pdf_path>" --pages '[0,1,2,...,9]' --format text
```

### 3.4 第三步·B：扫描型 PDF 提取（OCR 降级）

```bash
# 自动 OCR 降级：纯扫描件页面自动 OCR
"$PDFKIT_VENV" "$PDFKIT_PY" extract_text --input "<pdf_path>" --pages '[0]' --ocr_fallback --lang "eng+chi_sim"
```

**OCR 降级链**（逐级尝试，失败才降级）：
1. `extract_text --ocr_fallback`（自动判断文字层，无文字层时 OCR）
2. 若仍空 → `to_images --dpi 300` 渲染成图片，再对图片做 `ocr_locate`
3. 若仍失败 → 标注「该页无法读取·待人工提供文本」

### 3.5 第四步：补充提取（按需）

| 需求 | 命令 |
|------|------|
| 提取表格 | `extract_table --input <pdf> --pages '[0]' --format markdown` |
| 分析布局 | `layout_analyze --input <pdf> --pages '[0]' --detail full` |
| 搜索关键词 | `search_text --input <pdf> --find "关键词"` |
| 提取内嵌图片 | `extract_images --input <pdf> --output_dir <dir>` |
| 页面转图片 | `to_images --input <pdf> --output_dir <dir> --dpi 300` |
| 结构化提取 | `schema_extract --input <pdf> --schema '<json>'` |

> **结构化字段抽取（`schema_extract`）用法**：当 PDF 含合同/报价单/资质表/指标卡等强结构内容，且需**直接拿到结构化字段**（编号/日期/金额/清单行）而非让 LLM 从全文二次解析时，按 JSON schema 抽取：
> ```bash
> "$PDFKIT_VENV" "$PDFKIT_PY" schema_extract --input "<pdf>" \
>   --schema '{"contract_no":"string","sign_date":"string","party_a":"string","amount":"number","items":[{"name":"string","qty":"number","price":"number"}]}'
> ```
> `schema_extract` 负责确定性字段抽取，与 LLM 的七维度语义归类**互补不互斥**（字段固定可枚举时用它，自由文本仍归 LLM）。抽取结果须按 §五 溯源标签标注来源页码。

---

## 四、大段 PDF 处理策略（核心优化）

当 PDF 页数 > 20 页或文本量 > 50,000 字符时，须采用分块策略，避免单次提取超出上下文窗口或信息过载。

### 4.1 分块读取流程

```
1. page_count 获取总页数 N
2. 按 chunk_size=10 页一组分块：[0-9], [10-19], [20-29], ...
3. 逐块 extract_text，每块产出独立 JSON
4. LLM 逐块做七维度语义归类
5. 跨块合并：同维度结论合并，标注「跨块合并·页码范围 [p.A-p.B]」
6. 跨块矛盾标注：不同块间出现矛盾时标「跨块矛盾·待澄清」
```

### 4.2 分块调用示例

```bash
# 假设 85 页 PDF
# 块1: 页 0-9
"$PDFKIT_VENV" "$PDFKIT_PY" extract_text --input "<pdf>" --pages '[0,1,2,3,4,5,6,7,8,9]' --format text --output /tmp/chunk_1.txt

# 块2: 页 10-19
"$PDFKIT_VENV" "$PDFKIT_PY" extract_text --input "<pdf>" --pages '[10,11,12,13,14,15,16,17,18,19]' --format text --output /tmp/chunk_2.txt

# ... 以此类推
```

### 4.3 智能分块（按结构切分）

当 PDF 有书签/目录时，优先按章节边界分块：

```bash
# 先获取书签结构
"$PDFKIT_VENV" "$PDFKIT_PY" bookmarks --action get --input "<pdf>"

# 按章节页码范围分块提取
"$PDFKIT_VENV" "$PDFKIT_PY" extract_text --input "<pdf>" --pages '[<章节起始页>,...,<章节结束页>]' --format text
```

### 4.4 语义分块（RAG / 语义完整性场景）

> **首选 `semantic` 策略**：按语义边界（句子/段落/表格）切分，避免把表格或长句从中间切断，七维度归类时上下文更完整。`paragraph` / `fixed` 仅作降级备选。

```bash
# 首选：语义分块（推荐）
"$PDFKIT_VENV" "$PDFKIT_PY" chunk_pdf --input "<pdf>" --strategy semantic --chunk_size 1000 --overlap 200

# 降级备选：按段落
"$PDFKIT_VENV" "$PDFKIT_PY" chunk_pdf --input "<pdf>" --strategy paragraph --chunk_size 1000 --overlap 200

# 降级备选：固定字符数
"$PDFKIT_VENV" "$PDFKIT_PY" chunk_pdf --input "<pdf>" --strategy fixed --chunk_size 500 --overlap 100
```

### 4.5 大段 PDF 读取纪律

- **逐块溯源**：每块提取的结论必须标注 `文件名 p.<起始页>-p.<结束页>`，不丢失页码精度。
- **跨块去重**：相同信息在多块出现时，保留首次出现处的溯源，后续标 `同 p.<首次页码>·重复`。
- **跨块矛盾优先标注**：不同块间出现数字/承诺/事实矛盾时，优先标「跨块矛盾·待澄清」，不擅自取舍。
- **加密/受限 PDF**：不破解，标 `加密·未解析`，请用户提供可解析版本。
- **混合型 PDF 逐页判断**：部分页文本型、部分页扫描型时，逐页走 detect_type，文本页直接提取、扫描页走 OCR 降级。

---

## 五、溯源标签格式

pdfkit-py 提取的文本须转换为 doc-in-agent 的溯源标签格式：

| pdfkit-py 产出 | doc-in 溯源标签 |
|----------------|-----------------|
| `extract_text --pages '[3]'` | `文件名 p.3` |
| `extract_text --pages '[3,4,5]'` | `文件名 p.3-p.5` |
| `extract_table --pages '[2]'` | `文件名 p.3·表` |
| `ocr_locate --page 7` | `文件名 p.8·OCR`（物理页序+1=显示页码，双记） |
| `to_images --pages '[0]'` | `文件名 p.1·图` |

**页码双记**：PDF 封面/目录常不计入正文页码，须同时记「物理页序 p.N（pdfkit 0-based+1）/ 显示页码 P.M」，避免下游溯源错位。pdfkit-py 页码从 0 开始，doc-in 溯源标签统一用 1-based 显示。

---

## 六、问答与总结场景

当团长或成员需要对 PDF 做问答/总结时，优先使用 `chat_pdf`：

```bash
# PDF 问答上下文提取
"$PDFKIT_VENV" "$PDFKIT_PY" chat_pdf --input "<pdf>" --question "主要结论是什么" --max_context_chars 8000
```

此命令会智能提取与问题最相关的上下文段落，避免全量提取的噪声。

---

## 七、错误处理与熔断

| 场景 | 处理 |
|------|------|
| pdfkit-py venv 不存在 | 运行 `bash <pdfkit 技能>/scripts/setup.sh` 初始化 |
| PDF 加密 | 标 `加密·未解析`，不破解；如用户提供密码则 `decrypt` 后重试 |
| OCR 依赖缺失（tesseract） | 自动安装后重试，不把安装指引丢给用户 |
| 单页提取失败 2 次 | 标「该页解析不可用·待人工提供文本」，不无限重试（熔断上限 2 次） |
| 文件不存在 | 标 `文件缺失·待用户提供` |

---

## 八、快速参考表

| 场景 | pdfkit-py 命令 | 关键参数 |
|------|----------------|----------|
| 获取页数 | `page_count` | `--input` |
| 检测页面类型 | `detect_type` | `--input`, `--pages` |
| 提取文本（文本型） | `extract_text` | `--input`, `--pages`, `--format` |
| 提取文本（扫描型） | `extract_text` | `--ocr_fallback`, `--lang` |
| 提取表格 | `extract_table` | `--format markdown`, `--pages` |
| 分析布局 | `layout_analyze` | `--detail full` |
| 搜索文字 | `search_text` | `--find`, `--engine` |
| 页面转图片 | `to_images` | `--dpi 300` |
| 提取内嵌图片 | `extract_images` | `--output_dir` |
| 分块（RAG） | `chunk_pdf` | `--strategy`, `--chunk_size`, `--overlap` |
| 问答上下文 | `chat_pdf` | `--question`, `--max_context_chars` |
| 结构化提取 | `schema_extract` | `--schema` |
| 获取书签 | `bookmarks` | `--action get` |
| 解密 | `decrypt` | `--password` |
| OCR 定位 | `ocr_locate` | `--page`, `--text`, `--lang` |
