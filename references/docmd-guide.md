# docmd 规范（文档 ↔ Markdown 双向互转 · 团队共享引擎）

> 中央真相源：本文件定义 `scripts/docmd.py` 的安装、命令与边界。doc-in-agent / docx-agent 引用本文件，不得各写副本。
> 归属：入向（文档→MD）归 **doc-in-agent**；出向（MD→文档）归 **docx-agent**。两者共用同一引擎。

## 1. 引擎与依赖

| 引擎 | 默认路径 | 职责 |
|---|---|---|
| markitdown[all] | 隔离 managed venv：`C:\Users\Administrator\.workbuddy\binaries\python\envs\default` | docx / xlsx / pptx / pdf / html / csv / txt → Markdown |
| pandoc 3.x | `D:\BaiduSyncdisk\AI-agent\2026-08-17-18-08-51\tools\pandoc-*\pandoc.exe`（便携版） | Markdown → docx / pptx |
| openpyxl | 同上 venv | Markdown → xlsx（表格提取） |

### 安装（首次或换环境）

```bash
# markitdown 全量依赖（含 Office 后端，基础版不含）
VENV="<Python 环境>"
"$VENV/Scripts/python.exe" -m pip install "markitdown[all]" openpyxl

# pandoc 便携版：下载 windows-x86_64.zip 解压到 workspace/tools，目录名形如 pandoc-3.10.2
```

### 路径覆盖（环境变量）

引擎路径支持环境变量覆盖，便于跨环境复用，不改变默认行为：

- `DOCMD_VENV_PY`：markitdown 所在 venv 的 `python.exe`
- `DOCMD_PANDOC`：pandoc.exe 绝对路径（指定即优先于自动探测）
- `DOCMD_PANDOC_DIR`：pandoc-* 目录的父目录（默认 `workspace/tools`）

## 2. 命令

```bash
# 入向：文档 → Markdown（可一次多个）
python scripts/docmd.py 报告.docx 数据.xlsx 演示.pptx 论文.pdf

# 出向：Markdown → 文档
python scripts/docmd.py 笔记.md --to docx
python scripts/docmd.py 笔记.md --to pptx
python scripts/docmd.py 笔记.md --to xlsx

# 递归处理整个目录
python scripts/docmd.py --dir ./docs --to docx
```

输出规则：与源文件同目录、同名（仅扩展名不同）。

## 3. 双向能力矩阵（已验证）

| 方向 | 结果 |
|---|---|
| 文档 → MD（docx/xlsx/pptx/pdf/html/csv/txt） | ✅ |
| MD → DOCX / PPTX | ✅（pandoc） |
| MD → XLSX | ✅（openpyxl 表格提取） |

## 4. 边界（防误用 · 铁律）

1. **Markdown 中转 ≠ 客户交付主干道**。专家团正式交付走 `mat → ver → docx` 的 JSON 管线（build_docx.py / tencent-docx），保红线 / 编号 / 页码 / 脱敏。docmd 仅用于**内部速转 / 草稿 / 人读摘要**；未过 `ver` 闸的产物**禁止外发**。
2. **MD → XLSX 走 openpyxl，非 pandoc**。pandoc 便携版（Windows）**不支持 xlsx 输出格式**（`Unknown output format 'xlsx'`）。openpyxl 提取 MD 表格：每个表格写入一个工作表（`表格1`/`表格2`…）；若文档无表格，则整篇文本落入 `内容` 工作表。适合「MD 表格 → Excel」，非把整篇文档塞入单单元格。
3. **PDF → MD 质量边界**：文本型 PDF 效果好；扫描件 / 图片型 / 复杂多栏 / 公式 / 嵌套表格会丢结构。高保真需求（OCR / 分块 / 表格 / 布局）回落 doc-in 的 `pdfkit-py`，二者互补不互斥。
4. **涉密 / 客户敏感材料一律本地处理**，不调用任何云端解析服务。
5. **与团队现有管线分工**：doc-in 的 `pdfkit-py` / `parse_docs.py` 产出的是带溯源标签的**结构化 JSON 交接物**（供七维度抽取）；docmd 产出的是**人读 Markdown**（快速摘要 / 中转）。前者为正式输入主干道，后者为轻量补充。

## 5. 调用纪律

- doc-in-agent 调用前：确认目标为「快速人读 MD」，非需溯源的结构化抽取（后者走 pdfkit-py / parse_docs.py）。
- docx-agent 调用前：确认目标为「内部速转」，非客户版正式交付（后者走 ver 闸 + JSON 管线）。出向产出若拟外发，必须先经 `ver-agent` 核验。
