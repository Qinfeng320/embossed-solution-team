# 文档树规范（doc-tree-spec）

> 中央真相源。`docx-agent` 把上游验收后的结论**组织成结构化文档树（JSON）**，`scripts/build_docx.py` 据此**确定性渲染**为 .docx（并可选导出 PDF）。本文件是两者的唯一契约：渲染脚本只认本规范，docx-agent 只产出符合本规范的 JSON，不得各写各的。
>
> 设计意图：渲染是确定性工程活，下沉脚本；LLM 只做"语义组织成树"，不碰排版细节，避免乱码/丢红线/编号错位。

## 一、顶层结构

```json
{
  "meta": { "title": "", "subtitle": "", "version": "", "client": "", "date": "", "author": "", "classification": "" },
  "redlines": [ "红线文本1", "红线文本2" ],
  "redline_placement": "appendix | footnote | both",
  "sections": [ { "level": 1, "numbering": "auto", "title": "", "blocks": [ ... ] } ],
  "appendix": { "redlines": true, "sources": [ "来源1", "来源2" ] }
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `meta.title` | ✅ | 方案主标题（封面 + 正文首行） |
| `meta.subtitle` | ❌ | 副标题（封面） |
| `meta.version` | ✅ | 版本号，如 `v1.0`；须与变更记录一致（见团长 MD 6.2） |
| `meta.client` | ✅ | 客户名称（企业/机构/院校等） |
| `meta.date` | ✅ | ISO 日期 `YYYY-MM-DD`（渲染为封面日期） |
| `meta.author` | ❌ | 默认"售前专家团" |
| `meta.classification` | ❌ | 密级，如"内部参考"，渲染到封面与页眉 |
| `redlines` | ✅ | 抽象为泛型后的诚实红线文本数组（来源 `references/redlines.md`），**逐条保留不丢** |
| `redline_placement` | ✅ | 红线落位：`appendix`=仅附录；`footnote`=仅脚注；`both`=两者 |
| `sections` | ✅ | 正文章节数组，顺序即文档顺序 |
| `appendix.redlines` | ❌ | 默认 `true`；为 `false` 时红线不进附录（仅按 placement 走脚注） |
| `appendix.sources` | ❌ | 来源/引用清单，渲染到附录"资料来源" |

## 二、section 对象

| 字段 | 必填 | 说明 |
|------|------|------|
| `level` | ✅ | 1~3，映射 Heading 1~3 |
| `numbering` | ❌ | `auto`（默认）套用模板 `heading` 样式的 Word 自动编号（numPr），脚本**不手动拼接**中文序号；`none` 套用模板 heading 样式但移除 numPr（用于附录等非编号标题） |
| `title` | ✅ | 章节标题。**严禁包含手写编号前缀**（一、/（一）/1./(1)/①/第X 等）；编号由模板 heading 样式自动生成（numbering=auto 时） |
| `blocks` | ✅ | 块数组，顺序即渲染顺序 |

## 三、block 类型（type 枚举）

| type | 必填字段 | 渲染为 |
|------|---------|--------|
| `paragraph` | `text` | 普通段落 |
| `bullet` | `items[]` | 项目符号列表（`style: disc|circle|square`，默认 disc） |
| `numbered` | `items[]` | 编号列表（自动 1. 2. 3.） |
| `table` | `headers[]`, `rows[][]` | 表格（style `Table Grid`），可选 `caption` |
| `callout` | `text` | 强调框：`tone` = `redline`(红框红字，用于红线/caveat) / `info`(蓝) / `warning`(黄)；可选 `title` |
| `image` | `src`/`caption`/`width` | 图片块：渲染 `src` 路径图片（**默认宽＝版心宽·顶满版心（14.65 cm / 5,274,310 EMU，§6.8）**；`width` 可选覆盖，单位英寸；**高度一律按原图比例同步缩放，不变形**）；`caption` 可选表题；`src` 缺失/不存在时渲染占位提示「[图片素材未提供]」而非崩溃 |
| `pagebreak` | — | 分页符 |

block 示例：
```json
{ "type": "paragraph", "text": "本方案面向…" }
{ "type": "bullet", "items": ["要点A", "要点B"] }
{ "type": "numbered", "items": ["步骤一", "步骤二"] }
{ "type": "table", "caption": "表1 预算测算", "headers": ["项目", "金额(万元)"], "rows": [["硬件", "120"], ["软件", "80"]] }
{ "type": "callout", "tone": "redline", "title": "诚实边界", "text": "本数据仅为示意，非已验证结论。" }
{ "type": "image", "src": "evidence/截图1.png", "caption": "图1 客户现场设备照" }
{ "type": "pagebreak" }
```

## 四、红线保真铁律（脚本强制）
- `redlines` 数组**逐条**渲染，不得省略、弱化、改写。
- `redline_placement=both` 时，脚注处放精简版、附录放完整版；脚本保证两者都来自同一 `redlines` 数组。
- 任何 `callout.tone=redline` 的块以红框红字渲染，不参与普通段落流，确保显眼不丢。
- 若 `redlines` 为空数组，脚本报错退出（红线是外发闸门，不可缺）。

## 五、与团长交接物的关系
- docx-agent 消费的是团长下发的「已通过 ver 核验的定稿」交接物，而非原始上游；`meta.version` 取自团长 6.2 版本纪律。
- `redlines` 内容由 docx-agent 从 `references/redlines.md` 按当前场景抽象为泛型后填入，脚本原样渲染。
- 脚本只渲染、不篡改；文档自检清单（docx-agent.md）的对账项由 docx-agent **在脚本产出后读回真实文件**逐项核验——`scripts/inspect_docx.py` 负责只读抽取，docx-agent（大模型）负责判断 `通过/修订后通过/不通过`，不盲信脚本退出码。

## 六、调用方式
```bash
python scripts/build_docx.py <input.json> -o <output.docx> [--pdf] [--template assets/样式模板.dotx]
```
- `--pdf`：渲染后尝试用 MS Word COM 导出同名词 PDF；不可用时降级并提示手动导出。
- `--template <path>`：基于 .dotx/.docx 模板创建（保留其样式底座），与内置商务样式二选一；**Word 输出统一使用标准模板 `assets/样式模板.dotx`（§0.14）；客户另行指定模板（如 GB/T 9704 公文体 `文字文稿1.dotx`）时从其指定**。
- 脚本自带依赖自举：缺 `python-docx`/`pywin32` 时自动建 managed venv 安装后重执行。
- `image` 块：证据图片经 `--template` 或内置样式渲染；`src` 缺失时渲染占位提示而非崩溃，docx-agent 在 QA Gate 读回时据 inspect 结果确认图片是否到位。
