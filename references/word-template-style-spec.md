# Word 样式规范 — 样式模板.dotx

## 一、头部信息

| 项 | 值 |
|---|---|
| 来源文件 | `E:\User\桌面\样式模板.dotx` |
| 文件性质 | Word 模板（OOXML/ZIP 包），核心资产为样式定义与编号定义，非内容文档 |
| 文件大小 | 16,810 bytes（2026-10-14 修订版；初版 19,840 bytes，大小差异为 zip 重压缩所致） |
| SHA-256 | `87e6b832ae3890664891e0ecf9d1580c7b2195e224316d4cf7423d850988426c`（2026-10-14 修订版；初版解析值 `2373282b…e374`；历次修订 SHA 见修订记录 ⑤–⑬） |
| 解析时间 | 2026-10-14 |
| 解析方法 | Python `zipfile` 解包 + `xml.etree.ElementTree` / 正则逐部件全字段解析（未使用 parse_docs.py 内容抽取管线，本任务面向样式/编号 XML） |
| 生成应用 | WPS Office_12.1.0.28802（`docProps/app.xml` 记录 `Application`）；`docProps/core.xml` creator/lastModifiedBy=作者 |
| 用途说明 | 从该模板提取 15 个指定样式的完整定义与标题 1–6 的多级自动编号机制，作为后续新文档**原生继承并自动续编**的强制规范。 |
| 修订记录 | ① 2026-10-14：增补 §6.1 页面设置（输出默认值）——A4；页边距上/下 2.54 cm、左/右 3.18 cm（用户确认）。<br>② 2026-10-14：增补 §6.7 内容 → 样式映射与编号清洗（识别 → 清洗 → 套样式；手写编号清除；端到端验证）（用户确认）。<br>③ 2026-10-14：§6.7 修正——表格内各段落套「居中-表格」（39）、图片段套「居中-图片」（36，真实图片对象验证）；映射表对应行修订并去除待确认项。<br>④ 2026-10-14：增补 §6.8 图片与表格宽度（顶满版心：8306 缇；图片高度按比例不限）（用户确认）。<br>⑤ 2026-10-14：**目录 1/2/3（toc 1/2/3）样式修订**——字号→小四 12pt（`sz`/`szCs`=24；toc 1 遗留 `szCs=44` 一并修正）、行距→1.5 倍（`line`=360）；**样式模板.dotx 已同步更新**（修订版 SHA-256：`5b76c537…e56359`；修订前备份于 `_verify_编号继承测试/样式模板-备份-20261014-修订前.dotx`）。<br>⑥ 2026-10-14：**新增「封面」样式（styleId 41）**——黑体 · 二号 22pt（`sz`/`szCs`=44）· 居中 · 无首行缩进 · 段前/段后各 12pt · 不参与编号（用户委托设计，见 §4.16）；**样式模板.dotx 已同步更新**（修订版 SHA-256：`14157c2d…4ba76`；修订前备份：`样式模板-备份-20261014-封面修订前.dotx`）；v5 演示实测通过（22pt / 黑体 / 居中 / 无编号）。<br>⑦ 2026-10-14：**删除并隐藏「标题 7/8/9」**（用户确认不使用）——移除段落样式 styleId 8/9/10 与字符样式 33/34/35，及专属编号链路 `numId=2`/`abstractNumId=3`；`latentStyles` 中 heading 7/8/9 设为隐藏（`semiHidden=1`、`unhideWhenUsed=0`、移除 `qFormat`）；**样式模板.dotx 已同步更新**（修订版 SHA-256：`6010f535…74a061`；修订前备份：`样式模板-备份-20261014-删标题7-9前.dotx`）；v6 回归实测标题 1–6 编号无恙；属性核验 QuickStyle=False（不在快速样式库）/ InUse=False。<br>⑧ 2026-10-14：**移除「Title（标题）」样式定义**（用户确认不使用）——删除 `Title`(17) 定义、`latentStyles` 同步隐藏；heading 7/8/9 保持"定义已移除 + latent 隐藏"双层保障（中间曾试验"显式隐藏壳"方案，经 WPS 对照样本分析后回退为最简的"移除 + latent 隐藏"方案）；**样式模板.dotx 已同步更新**（修订版 SHA-256：`0d1f4c30…3eef1b`；修订前备份：`样式模板-备份-20261014-纯删除前.dotx`）；v7 回归通过。<br>⑨ 2026-10-14：**编号定义裁剪 + 删除「列表编号」**（配合标题 7–9 面板残留清除与用户新需求）——① 标题编号 `abstractNumId=1` 由 9 级裁至 **6 级**（移除无绑定的 lvl6–8 级联级）；② 图题/表题编号（abstractNumId=2/0）裁至单级；③ 删除「列表编号」（`List Number`，11）及专属编号链路 `numId=3`/`abstractNumId=4`，`latentStyles` 同步隐藏；**样式模板.dotx 已同步更新**（修订版 SHA-256：`a970da2a…6f96b4`；修订前备份：`样式模板-备份-20261014-裁剪前.dotx`）；v8 回归通过（标题 1–6 编号、图 1、表 1 全部正常）。<br>⑩ 2026-10-14：**为「标题 7/8/9」建立隐藏定义**（用户发现 WPS「下一级标题引导」机制后，指定采用"隐藏"方案）——`heading 7/8/9` 以隐藏壳定义恢复 styleId 8/9/10：`<w:hidden/>` + `<w:semiHidden/>` + `uiPriority=99`，无 `qFormat`/编号/链接；**样式模板.dotx 已同步更新**（修订版 SHA-256：`06e70104…99a8c`；修订前备份：`样式模板-备份-20261014-隐藏定义前.dotx`）；引擎实测：样式集合遍历不可见、直接访问 `Hidden=True`；v9 回归通过；**用户验证：WPS 面板已不显示「标题 7」（2026-10-14）**。<br>⑪ 2026-10-14：**处理「默认段落字体」**（`Default Paragraph Font`，styleId 20；用户确认不使用）——先试"隐藏"（`hidden`+`semiHidden` 改造，写入版 `ee30b10a`），经引擎实测其 hidden 声明被**规范化无视**（默认样式特例，`Hidden=False`）；删除实验证明打开无损（引擎自动隐式提供，与原生 Word 行为一致）后，**最终移除定义**（用户首选"先删除"方案）；**样式模板.dotx 已同步更新**（修订版 SHA-256：`99b1b968…76c33e`；修订前备份：`样式模板-备份-20261014-删默认段落字体前.dotx`）；**用户验证：WPS 面板已不显示「默认段落字体」（2026-10-14）**。<br>⑫ 2026-10-14：**模板定版并固定至专家团**——`样式模板.dotx`（`99b1b968…76c33e`）作为专家团 Word 输出标准模板，固定于插件 `assets/样式模板.dotx`；本规范同步固定于插件 `references/word-template-style-spec.md`；中央规范 `document-format-standards.md` 新增 §0.14 登记。<br>⑬ 2026-10-14：**模板页边距终态化 + 配套工具脚本**——① 模板本体 `pgMar` 由原值（3.7/2.6/3.5/2.8 cm）改为**输出终值（上/下 1440、左/右 1800 缇）**（"以模板为基底=页面即正确"，消除逐次覆盖步骤）；② 新增 `scripts/template_style_tool.py`（模板设置操作：list/set/hide/remove/page）与 `scripts/content_to_docx.py`（内容→样式落盘，见 §6.9）；③ 修复**自锁写回缺陷**（修订脚本未关闭 zip 读句柄，导致 `os.replace` 被自身进程拒绝——系此前"写回被占用"报告的主导原因；现读写均即开即关）。模板新 SHA-256：`87e6b832…88426c`（16,810B，插件版与桌面版一致）。<br>⑭ 2026-10-14：**审计补正（沉淀）**——§6.4"以模板为基底"句的页边距表述同步为终值口径（消除 ⑬ 遗留的"须覆盖"旧说法）；与专家团沉淀档 PR-009 同步。<br>⑮ 2026-10-15：**增补 §6.7.5 既有文档的标题识别与目录层级规范**（用户确认）——标题识别上限六级（超限按正文）、识别=上下文级联定级（模式族栈+兄弟闭合）、目录只输出到三级（`\o "1-3"`）；本次仅规范文本增补，**未改动样式模板.dotx 本体**。 |

**保真声明**：本文所有 XML 原值逐字取自原始部件，未四舍五入、未脑补补全；换算值均给出公式，XML 原值与换算值双记。若某字段在完整继承链中仍无定义，标注「未定义」并说明实际回退来源。

---

## 二、样式总览表

> 说明：`styleId` 为该模板 XML 内的内部 ID（本模板使用纯数字 ID）；「样式名」取自 `w:name` 的 `w:val`。样式类型 `w:type`：paragraph=段落 / character=字符。

| # | 样式名 (w:name) | styleId | 类型 | basedOn | next | link(字符) | 大纲级别 | 自动编号 (numPr) |
|---|---|---|---|---|---|---|---|---|
| 1 | `heading 1`（标题 1） | 2 | paragraph | 1 (Normal) | 1 (Normal) | 29 | 0 | **有** numId=1 / ilvl=0 |
| 2 | `heading 2`（标题 2） | 3 | paragraph | 1 | 1 | 27 | 1 | **有** numId=1 / ilvl=1 |
| 3 | `heading 3`（标题 3） | 4 | paragraph | 1 | 1 | 28 | 2 | **有** numId=1 / ilvl=2 |
| 4 | `heading 4`（标题 4） | 5 | paragraph | 1 | 1 | 30 | 3 | **有** numId=1 / ilvl=3 |
| 5 | `heading 5`（标题 5） | 6 | paragraph | 1 | 1 | 31 | 4 | **有** numId=1 / ilvl=4 |
| 6 | `heading 6`（标题 6） | 7 | paragraph | 1 | 1 | 32 | 5 | **有** numId=1 / ilvl=5 |
| 7 | `居中-表格` | 39 | paragraph | 1 | — | — | — | 无 |
| 8 | `居中-图片` | 36 | paragraph | 1 | — | — | — | 无 |
| 9 | `角标-表格` | 38 | paragraph | 36 | — | — | — | **有** numId=5 / ilvl=0 |
| 10 | `角标-图片` | 37 | paragraph | 36 | — | — | — | **有** numId=4 / ilvl=0 |
| 11 | `toc 1`（目录 1） | 15 | paragraph | 1 | 1 | — | — | 无 |
| 12 | `toc 2`（目录 2） | 16 | paragraph | 1 | 1 | — | — | 无 |
| 13 | `toc 3`（目录 3） | 13 | paragraph | 1 | 1 | — | — | 无 |
| 14 | `Normal`（正文） | 1 | paragraph（default=1） | — | — | — | — | 无 |
| 15 | `page number`（页码） | 21 | **character** | — | — | — | — | 无 |
| 16 | `封面`（2026-10-14 新增） | 41 | paragraph | 1 | — | — | — | 无 |

**与用户指定清单的核对**：用户清单逐条命中。仅两点须以 XML 实况说明：
- 第 15 项 `page number` 在 styles.xml 中实际为 **字符样式（w:type="character"）**，非段落样式；
- 第 14 项显示名为 `Normal`（英文），Word 中文界面将其本地化显示为「正文」。

**范围外样式（不提取）**：`caption`(12)、`footer`(14)、`Table Grid`(19)、`方案表格`(26)、及在用段落样式对应的 `*字符` 链接样式等。**`List Number`(11)、`heading 7/8/9`（8/9/10 + 字符 33/34/35）与 `Title`（17）已于 2026-10-14 移除并隐藏**（用户确认不使用，见修订记录 ⑦–⑨）。

---

## 三、继承基线（所有样式属性回溯的公共上游）

### 3.1 `w:docDefaults`（styles.xml 首个部件元素，逐字）

```xml
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi" w:eastAsiaTheme="minorEastAsia" w:cstheme="minorBidi"/></w:rPr></w:rPrDefault><w:pPrDefault/></w:docDefaults>
```

- `rPrDefault/rPr` 仅声明字体主题引用：ASCII/hAnsi→`minorHAnsi`、eastAsia→`minorEastAsia`、cs→`minorBidi`；**无字号（sz/szCs）、字形、颜色等定义**。
- `pPrDefault` 为空 → 段落无全局默认属性。

### 3.2 主题字体（`word/theme/theme1.xml` 的 `<a:fontScheme>`）

| 主题槽位 | majorFont | minorFont |
|---|---|---|
| latin | `Calibri` | `Cambria` |
| ea（东亚） | 空 | 空 |
| script="Hans"（简体中文） | `宋体` | `宋体` |

**主题解析结论**：
- `minorHAnsi`（docDefaults 的 ascii/hAnsi 主题） → minorFont latin = **Cambria**；
- `minorEastAsia`（docDefaults 的 eastAsia 主题） → minorFont 的 Hans = **宋体**（因 `a:ea` 为空，中文回落到 Hans 槽）；
- `minorBidi`（docDefaults 的 cs 主题） → minorFont latin/cs 无对应（`a:cs` 为空）→ 实际 cs 无有效字体，走系统默认。

> 注意：上述主题字体仅在样式链**未显式指定**时生效。本模板 `Normal` 样式已显式指定 `ascii=宋体 hAnsi=宋体 eastAsia=仿宋`，因此以 Normal 为准；docDefaults/主题主要作为「Normal 未覆盖且样式链更上游」的最后回退依据。

### 3.3 `Normal`（styleId=1）—— 其余全部目标样式的 basedOn 根

| 属性 | XML 原值 | 换算 / 说明 | 来源 |
|---|---|---|---|
| type | `paragraph` | — | 样式显式 |
| default | `1` | 文档默认样式 | 样式显式 |
| 名称 | `Normal` | 中文界面「正文」 | 样式显式 |
| rFonts ascii | `宋体` | — | 样式显式 |
| rFonts hAnsi | `宋体` | — | 样式显式 |
| rFonts eastAsia | `仿宋` | — | 样式显式 |
| rFonts cs | `cstheme="minorBidi"` | 主题回退，无有效字体 | 主题 |
| sz | `28` | 28÷2 = **14 pt** | 样式显式 |
| szCs | `28` | 28÷2 = **14 pt** | 样式显式 |
| color | `000000`（themeColor=text1） | 黑 | 样式显式 |
| kern | `2` | 2÷2 = 1 pt（字距调整阈） | 样式显式 |
| lang | en-US / zh-CN / bidi=ar-SA | — | 样式显式 |
| spacing line | `360`（lineRule=`auto`） | 360÷240 = **1.5 倍行距** | 样式显式 |
| ind firstLine | `560` | 560÷567 = **0.988 cm** | 样式显式 |
| ind firstLineChars | `200` | 200÷100 = **2 字符** | 样式显式 |
| widowControl | `0` | 关闭孤行控制 | 样式显式 |
| w14:textFill | schemeClr tx1 | 文字填充=正文色 | 样式显式 |

**换算公式（全文通用）**：
- 字号：`pt = w:sz(或 szCs) ÷ 2`（单位为半磅）；
- 行距：`lineRule="auto"` 时 `倍数 = line ÷ 240`；
- 段前/段后：`pt = 缇值 ÷ 20`（1 pt = 20 twips）；
- 缩进：`cm = 缇值 ÷ 567`（1 cm ≈ 567 twips）；`*Chars` 值 ÷100 = 字符数。

**关键基线**：Normal 行距 1.5 倍、首行缩进 2 字符、正文字体 宋体(西文)+仿宋(中文)、字号 14 pt。**下列所有基于 Normal 的样式，凡未显式覆盖上述项者，均继承此基线。**

---

## 四、逐样式完整定义

> 每节字段表标注**每项来源**：`样式显式` / `继承 basedOn(id)` / `docDefaults` / `主题` / `未定义`。末附该样式的完整 XML 摘录（逐字）。

### 4.1 `heading 1`（标题 1）— styleId = 2

**元数据**：type=paragraph；basedOn=`1`(Normal)；next=`1`(Normal)；link=`29`(标题 1 字符)；qFormat=✓；uiPriority=9；customStyle=否。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii | 未定义 | `宋体` | 继承 basedOn=1 |
| rFonts hAnsi | 未定义 | `宋体` | 继承 basedOn=1 |
| rFonts eastAsia | 未定义 | `仿宋` | 继承 basedOn=1 |
| rFonts cs | `宋体` | `宋体` | **样式显式** |
| sz | 未定义 | 28÷2 = **14 pt** | 继承 basedOn=1 |
| szCs | `44` | 44÷2 = **22 pt** | **样式显式** |
| kern | `44` | 44÷2 = 22 pt（字距阈） | **样式显式** |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| jc | 未定义 | 左对齐 | 未定义（Word 默认） |
| ind firstLine | 未定义 | 560 | 继承 basedOn=1 |
| ind firstLineChars | `0` | **0 字符**（firstLineChars 优先，首行**不缩进**） | **样式显式** |
| spacing line | 未定义 | 360 → 1.5 倍 | 继承 basedOn=1 |
| spacing before | `100` | 100÷20 = **5 pt** | **样式显式** |
| spacing after | `100` | 100÷20 = **5 pt** | **样式显式** |
| outlineLvl | `0` | 大纲 1 级 | **样式显式** |
| adjustRightInd | `0` | 关闭右缩进自动调整 | **样式显式** |
| widowControl | 未定义 | `0`（关闭） | 继承 basedOn=1 |
| **numPr** | ilvl=`0` numId=`1` | **自动编号（一级）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:styleId="2"><w:name w:val="heading 1"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:link w:val="29"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr><w:adjustRightInd w:val="0"/><w:spacing w:before="100" w:after="100"/><w:ind w:firstLineChars="0"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:rFonts w:cs="宋体"/><w:kern w:val="44"/><w:szCs w:val="44"/></w:rPr></w:style>
```

### 4.2 `heading 2`（标题 2）— styleId = 3

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=`27`(标题 2 字符)；uiPriority=9。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii/hAnsi/eastAsia | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| rFonts cs | `宋体` | `宋体` | **样式显式** |
| sz | 未定义 | **14 pt** | 继承 basedOn=1 |
| szCs | `40` | **20 pt** | **样式显式** |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| ind firstLine | 未定义 | 560 | 继承 basedOn=1 |
| ind firstLineChars | `0` | **0 字符**（首行不缩进） | **样式显式** |
| spacing line | 未定义 | 1.5 倍 | 继承 basedOn=1 |
| spacing before/after | `100` / `100` | **5 pt** / **5 pt** | **样式显式** |
| tabs | `left@709`、`clear@420` | 709÷567=1.25 cm | **样式显式** |
| outlineLvl | `1` | 大纲 2 级 | **样式显式** |
| **numPr** | ilvl=`1` numId=`1` | **自动编号（二级）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:styleId="3"><w:name w:val="heading 2"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:link w:val="27"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr><w:tabs><w:tab w:val="left" w:pos="709"/><w:tab w:val="clear" w:pos="420"/></w:tabs><w:spacing w:before="100" w:after="100"/><w:ind w:firstLineChars="0"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:rFonts w:cs="宋体"/><w:szCs w:val="40"/></w:rPr></w:style>
```

### 4.3 `heading 3`（标题 3）— styleId = 4

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=`28`(标题 3 字符)；uiPriority=9。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii/hAnsi/eastAsia | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| rFonts cs | `宋体` | `宋体` | **样式显式** |
| sz | 未定义 | **14 pt** | 继承 basedOn=1 |
| szCs | `40` | **20 pt** | **样式显式** |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| ind firstLine | 未定义 | 560 | 继承 basedOn=1 |
| ind firstLineChars | `0` | **0 字符**（首行不缩进） | **样式显式** |
| spacing line | 未定义 | 1.5 倍 | 继承 basedOn=1 |
| spacing before/after | `100` / `100` | **5 pt** / **5 pt** | **样式显式** |
| tabs | `left@1440`、`clear@0` | 1440÷567=2.54 cm | **样式显式** |
| outlineLvl | `2` | 大纲 3 级 | **样式显式** |
| **numPr** | ilvl=`2` numId=`1` | **自动编号（三级）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:styleId="4"><w:name w:val="heading 3"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:link w:val="28"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:numPr><w:ilvl w:val="2"/><w:numId w:val="1"/></w:numPr><w:tabs><w:tab w:val="left" w:pos="1440"/><w:tab w:val="clear" w:pos="0"/></w:tabs><w:spacing w:before="100" w:after="100"/><w:ind w:firstLineChars="0"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:rFonts w:cs="宋体"/><w:szCs w:val="40"/></w:rPr></w:style>
```

### 4.4 `heading 4`（标题 4）— styleId = 5

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=`30`(标题 4 字符)；uiPriority=9。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii/hAnsi/eastAsia | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| rFonts cs | 未定义 | `minorBidi`（主题，无有效字体） | 继承 basedOn=1→主题 |
| sz | 未定义 | **14 pt** | 继承 basedOn=1 |
| szCs | 未定义 | **14 pt** | 继承 basedOn=1 |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| ind firstLine / firstLineChars | 未定义 | 560 / 200 → **首行缩进 2 字符** | 继承 basedOn=1 |
| spacing line | 未定义 | 1.5 倍 | 继承 basedOn=1 |
| spacing before/after | `100` / `100` | **5 pt** / **5 pt** | **样式显式** |
| outlineLvl | `3` | 大纲 4 级 | **样式显式** |
| **numPr** | ilvl=`3` numId=`1` | **自动编号（四级）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:styleId="5"><w:name w:val="heading 4"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:link w:val="30"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:numPr><w:ilvl w:val="3"/><w:numId w:val="1"/></w:numPr><w:spacing w:before="100" w:after="100"/><w:outlineLvl w:val="3"/></w:pPr></w:style>
```

### 4.5 `heading 5`（标题 5）— styleId = 6

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=`31`(标题 5 字符)；uiPriority=9。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii/hAnsi/eastAsia | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| rFonts cs | `Times New Roman` | `Times New Roman` | **样式显式** |
| sz | 未定义 | **14 pt** | 继承 basedOn=1 |
| szCs | 未定义 | **14 pt** | 继承 basedOn=1 |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| ind firstLine / firstLineChars | 未定义 | 560 / 200 → **首行缩进 2 字符** | 继承 basedOn=1 |
| spacing line | 未定义 | 1.5 倍 | 继承 basedOn=1 |
| spacing before/after | `100` / `100` | **5 pt** / **5 pt** | **样式显式** |
| tabs | `left@1440`、`clear@0` | 2.54 cm | **样式显式** |
| outlineLvl | `4` | 大纲 5 级 | **样式显式** |
| **numPr** | ilvl=`4` numId=`1` | **自动编号（五级）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:styleId="6"><w:name w:val="heading 5"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:link w:val="31"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:numPr><w:ilvl w:val="4"/><w:numId w:val="1"/></w:numPr><w:tabs><w:tab w:val="left" w:pos="1440"/><w:tab w:val="clear" w:pos="0"/></w:tabs><w:spacing w:before="100" w:after="100"/><w:outlineLvl w:val="4"/></w:pPr><w:rPr><w:rFonts w:cs="Times New Roman"/></w:rPr></w:style>
```

### 4.6 `heading 6`（标题 6）— styleId = 7

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=`32`(标题 6 字符)；uiPriority=9。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii | 未定义 | `宋体` | 继承 basedOn=1 |
| rFonts hAnsi | `Arial` | `Arial` | **样式显式** |
| rFonts eastAsia | 未定义 | `仿宋` | 继承 basedOn=1 |
| rFonts cs | `Times New Roman` | `Times New Roman` | **样式显式** |
| bCs | `（空元素）` | 复杂文种**加粗** | **样式显式** |
| sz | 未定义 | **14 pt** | 继承 basedOn=1 |
| szCs | 未定义 | **14 pt** | 继承 basedOn=1 |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| ind firstLine | 未定义 | 560 | 继承 basedOn=1 |
| ind firstLineChars | `0` | **0 字符**（首行不缩进） | **样式显式** |
| spacing line | 未定义 | 1.5 倍 | 继承 basedOn=1 |
| spacing before/after | `100` / `100` | **5 pt** / **5 pt** | **样式显式** |
| tabs | `left@1440` | 2.54 cm | **样式显式** |
| outlineLvl | `5` | 大纲 6 级 | **样式显式** |
| **numPr** | ilvl=`5` numId=`1` | **自动编号（六级）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:styleId="7"><w:name w:val="heading 6"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:link w:val="32"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:numPr><w:ilvl w:val="5"/><w:numId w:val="1"/></w:numPr><w:tabs><w:tab w:val="left" w:pos="1440"/></w:tabs><w:spacing w:before="100" w:after="100"/><w:ind w:firstLineChars="0"/><w:outlineLvl w:val="5"/></w:pPr><w:rPr><w:rFonts w:hAnsi="Arial" w:cs="Times New Roman"/><w:bCs/></w:rPr></w:style>
```

### 4.7 `居中-表格` — styleId = 39

**元数据**：type=paragraph；customStyle=**是**；basedOn=`1`；next=—；link=—；uiPriority=0。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii/hAnsi/eastAsia | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| rFonts cs | 未定义 | 主题 minorBidi | 继承 basedOn=1 |
| sz | `24` | 24÷2 = **12 pt** | **样式显式** |
| szCs | 未定义 | **14 pt** | 继承 basedOn=1 |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| jc | `center` | **居中** | **样式显式** |
| ind firstLine | `0` | 0（无首行缩进） | **样式显式** |
| ind firstLineChars | `0` | 0 字符 | **样式显式** |
| spacing line | 未定义 | 1.5 倍 | 继承 basedOn=1 |
| outlineLvl | 未定义 | — | 未定义 |
| numPr | 无 | 不参与编号 | — |

```xml
<w:style w:type="paragraph" w:customStyle="1" w:styleId="39"><w:name w:val="居中-表格"/><w:basedOn w:val="1"/><w:qFormat/><w:uiPriority w:val="0"/><w:pPr><w:ind w:firstLine="0" w:firstLineChars="0"/><w:jc w:val="center"/></w:pPr><w:rPr><w:sz w:val="24"/></w:rPr></w:style>
```

### 4.8 `居中-图片` — styleId = 36

**元数据**：type=paragraph；customStyle=**是**；basedOn=`1`；next=—；link=—；uiPriority=0。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii/hAnsi/eastAsia | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| rFonts cs | `Times New Roman` | `Times New Roman` | **样式显式** |
| sz | `24` | **12 pt** | **样式显式** |
| szCs | 未定义 | **14 pt** | 继承 basedOn=1 |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| jc | `center` | **居中** | **样式显式** |
| ind firstLine | `0` | 0 | **样式显式** |
| ind firstLineChars | `0` | 0 字符 | **样式显式** |
| spacing line | 未定义 | 1.5 倍 | 继承 basedOn=1 |
| numPr | 无 | 不参与编号 | — |

```xml
<w:style w:type="paragraph" w:customStyle="1" w:styleId="36"><w:name w:val="居中-图片"/><w:basedOn w:val="1"/><w:qFormat/><w:uiPriority w:val="0"/><w:pPr><w:ind w:firstLine="0" w:firstLineChars="0"/><w:jc w:val="center"/></w:pPr><w:rPr><w:rFonts w:cs="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:style>
```

### 4.9 `角标-表格` — styleId = 38

**元数据**：type=paragraph；customStyle=**是**；basedOn=`36`(居中-图片)；next=—；link=—；uiPriority=0。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii/hAnsi/eastAsia | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=36→1 |
| rFonts cs | 未定义 | `Times New Roman` | 继承 basedOn=36 |
| sz | 未定义 | **12 pt** | 继承 basedOn=36 |
| jc | 未定义 | **居中（继承自 36）** | 继承 basedOn=36 |
| ind left | `0` | 0（左缩进 0） | **样式显式** |
| ind firstLine | `0` | 0 | **样式显式** |
| **numPr** | ilvl=`0` numId=`5` | **自动编号（表格题注：表 N）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:customStyle="1" w:styleId="38"><w:name w:val="角标-表格"/><w:basedOn w:val="36"/><w:qFormat/><w:uiPriority w:val="0"/><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="5"/></w:numPr><w:ind w:left="0" w:firstLine="0"/></w:pPr></w:style>
```

### 4.10 `角标-图片` — styleId = 37

**元数据**：type=paragraph；customStyle=**是**；basedOn=`36`(居中-图片)；next=—；link=—；uiPriority=0。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts | 未定义 | 同 `居中-图片` | 继承 basedOn=36 |
| sz | 未定义 | **12 pt** | 继承 basedOn=36 |
| jc | 未定义 | **居中（继承自 36）** | 继承 basedOn=36 |
| ind left / firstLine | `0` / `0` | 0 / 0 | **样式显式** |
| **numPr** | ilvl=`0` numId=`4` | **自动编号（图片题注：图 N）** | **样式显式** |

```xml
<w:style w:type="paragraph" w:customStyle="1" w:styleId="37"><w:name w:val="角标-图片"/><w:basedOn w:val="36"/><w:qFormat/><w:uiPriority w:val="0"/><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="4"/></w:numPr><w:ind w:left="0" w:firstLine="0"/></w:pPr></w:style>
```

### 4.11 `toc 1`（目录 1）— styleId = 15

> 2026-10-14 修订：字号 → 小四 12pt（`sz`/`szCs`=24）；行距 → 1.5 倍（`line`=360）。

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=—；uiPriority=39。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii | `仿宋` | `仿宋` | **样式显式** |
| rFonts hAnsi | `仿宋` | `仿宋` | **样式显式** |
| rFonts eastAsia | 未定义 | `仿宋` | 继承 basedOn=1 |
| rFonts cs | `仿宋` | `仿宋` | **样式显式** |
| sz | `24` | 24÷2 = **12 pt（小四）** | **样式显式** |
| szCs | `24` | 24÷2 = **12 pt（小四）** | **样式显式** |
| color | `auto` | 自动（默认色） | **样式显式** |
| ind firstLine | `0` | 0 | **样式显式** |
| ind firstLineChars | `0` | 0 字符 | **样式显式** |
| spacing line | `360`（auto） | 360÷240 = **1.5 倍** | **样式显式** |
| tabs | `right@8306 leader=dot` | 8306÷567=**14.65 cm**，点线前导 | **样式显式** |
| numPr | 无 | 不参与编号 | — |

```xml
<w:style w:type="paragraph" w:styleId="15"><w:name w:val="toc 1"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:qFormat/><w:uiPriority w:val="39"/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8306"/></w:tabs><w:spacing w:line="360" w:lineRule="auto"/><w:ind w:firstLine="0" w:firstLineChars="0"/></w:pPr><w:rPr><w:rFonts w:ascii="仿宋" w:hAnsi="仿宋" w:cs="仿宋"/><w:color w:val="auto"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
```

### 4.12 `toc 2`（目录 2）— styleId = 16

> 2026-10-14 修订：字号 → 小四 12pt（`sz`/`szCs`=24）；行距 → 1.5 倍（`line`=360）。

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=—；uiPriority=39；`unhideWhenUsed`=✓。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| sz | `24` | 24÷2 = **12 pt（小四）** | **样式显式** |
| szCs | `24` | 24÷2 = **12 pt（小四）** | **样式显式** |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| ind left | `840` | 840÷567 = **1.481 cm** | **样式显式** |
| ind leftChars | `300` | 300÷100 = **3 字符** | **样式显式** |
| ind firstLine / firstLineChars | `0` / `0` | 0 / 0 字符 | **样式显式** |
| spacing line | `360`（auto） | 360÷240 = **1.5 倍** | **样式显式** |
| tabs | `right@8296 leader=dot` | 8296÷567=**14.63 cm** | **样式显式** |
| numPr | 无 | 不参与编号 | — |

```xml
<w:style w:type="paragraph" w:styleId="16"><w:name w:val="toc 2"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:unhideWhenUsed/><w:qFormat/><w:uiPriority w:val="39"/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8296"/></w:tabs><w:spacing w:line="360" w:lineRule="auto"/><w:ind w:left="840" w:leftChars="300" w:firstLine="0" w:firstLineChars="0"/></w:pPr><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
```

### 4.13 `toc 3`（目录 3）— styleId = 13

> 2026-10-14 修订：字号 → 小四 12pt（`sz`/`szCs`=24）；行距 → 1.5 倍（`line`=360）。

**元数据**：type=paragraph；basedOn=`1`；next=`1`；link=—；uiPriority=39。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts | 未定义 | `宋体`/`宋体`/`仿宋` | 继承 basedOn=1 |
| sz | `24` | 24÷2 = **12 pt（小四）** | **样式显式** |
| szCs | `24` | 24÷2 = **12 pt（小四）** | **样式显式** |
| color | 未定义 | `000000` | 继承 basedOn=1 |
| ind left | `960` | 960÷567 = **1.693 cm** | **样式显式** |
| ind leftChars | `400` | **4 字符** | **样式显式** |
| ind firstLine / firstLineChars | `0` / `0` | 0 / 0 字符 | **样式显式** |
| spacing line | `360`（auto） | 360÷240 = **1.5 倍** | **样式显式** |
| tabs | `right@8296 leader=dot` | 14.63 cm | **样式显式** |
| numPr | 无 | 不参与编号 | — |

```xml
<w:style w:type="paragraph" w:styleId="13"><w:name w:val="toc 3"/><w:basedOn w:val="1"/><w:next w:val="1"/><w:qFormat/><w:uiPriority w:val="39"/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8296"/></w:tabs><w:spacing w:line="360" w:lineRule="auto"/><w:ind w:left="960" w:leftChars="400" w:firstLine="0" w:firstLineChars="0"/></w:pPr><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
```

### 4.14 `Normal`（正文）— styleId = 1

见 §3.3 完整字段表。XML 摘录：

```xml
<w:style w:type="paragraph" w:default="1" w:styleId="1"><w:name w:val="Normal"/><w:qFormat/><w:uiPriority w:val="0"/><w:pPr><w:widowControl w:val="0"/><w:spacing w:line="360" w:lineRule="auto"/><w:ind w:firstLine="560" w:firstLineChars="200"/></w:pPr><w:rPr><w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="仿宋" w:cstheme="minorBidi"/><w:color w:val="000000" w:themeColor="text1"/><w:kern w:val="2"/><w:sz w:val="28"/><w:szCs w:val="28"/><w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/><w14:textFill><w14:solidFill><w14:schemeClr w14:val="tx1"/></w14:solidFill></w14:textFill></w:rPr></w:style>
```

### 4.15 `page number`（页码）— styleId = 21

**元数据**：type=**character**（字符样式）；basedOn=—；next=—；link=—；uiPriority=0。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii | `Times New Roman` | — | **样式显式** |
| rFonts hAnsi | `Times New Roman` | — | **样式显式** |
| rFonts eastAsia | `仿宋` | — | **样式显式** |
| rFonts cs | 未定义 | 主题 minorBidi（无有效字体） | docDefaults→主题 |
| sz | `15` | 15÷2 = **7.5 pt** | **样式显式** |
| szCs | 未定义 | 未定义（字符样式无 basedOn，docDefaults 亦无 sz）→ 走 Word 内置默认 | 未定义 |

```xml
<w:style w:type="character" w:styleId="21"><w:name w:val="page number"/><w:qFormat/><w:uiPriority w:val="0"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="仿宋"/><w:sz w:val="15"/></w:rPr></w:style>
```

> **注**：模板页脚 `footer1.xml` 中实际页码文字**未使用**该 `page number` 字符样式（详见 §5.1 与 §6.5），页脚字符格式为行内 `rPr` 直接指定。

### 4.16 `封面` — styleId = 41

**元数据**：type=paragraph；customStyle=**是**；basedOn=`1`(Normal)；next=—；link=—；uiPriority=0。**2026-10-14 新增（用户委托设计）**。

| 属性 | XML 原值 | 换算 / 有效值 | 来源 |
|---|---|---|---|
| rFonts ascii / hAnsi | `黑体` | `黑体` | **样式显式** |
| rFonts eastAsia | `黑体` | `黑体` | **样式显式** |
| sz | `44` | 44÷2 = **22 pt（二号）** | **样式显式** |
| szCs | `44` | 44÷2 = **22 pt** | **样式显式** |
| jc | `center` | **居中** | **样式显式** |
| ind firstLine / firstLineChars | `0` / `0` | 0 / 0 字符（无首行缩进） | **样式显式** |
| spacing before / after | `240` / `240` | 240÷20 = **12 pt** / **12 pt** | **样式显式** |
| numPr | 无 | **不参与编号** | — |
| color | 未定义 | `000000`（继承 Normal） | 继承 basedOn=1 |
| b（加粗） | 未定义 | 不加粗（黑体承担视觉重量，延续全体系惯例） | 继承 |

**设计说明**：封面主标题专用样式。封面其余文字（副标题、编制信息行）暂用正文等非标题样式，如需专属样式另行增补。

```xml
<w:style w:type="paragraph" w:customStyle="1" w:styleId="41"><w:name w:val="封面"/><w:basedOn w:val="1"/><w:qFormat/><w:uiPriority w:val="0"/><w:pPr><w:spacing w:before="240" w:after="240"/><w:ind w:firstLine="0" w:firstLineChars="0"/><w:jc w:val="center"/></w:pPr><w:rPr><w:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/><w:sz w:val="44"/><w:szCs w:val="44"/></w:rPr></w:style>
```

---

## 五、编号机制专章（重点）

### 5.1 标题 1–6 的绑定链

**链路结构**：`heading 1~6 样式` → 各自 `pPr/w:numPr` 直接引用 `numId=1` + 对应 `ilvl=0~5`；`numbering.xml` 中 `numId=1` → `<w:num><w:abstractNumId w:val="1"/>` → `abstractNumId=1` 的各 `<w:lvl>` 内再用 `<w:pStyle w:val="2..7">` **反向绑定**回样式。

**numId=1 的 `<w:num>` 定义（numbering.xml 逐字）**：

```xml
<w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>
```

**对应 `<w:abstractNum w:abstractNumId="1">` 头部**：

```xml
<w:abstractNum w:abstractNumId="1"><w:nsid w:val="5D9BC0F4"/><w:multiLevelType w:val="multilevel"/><w:tmpl w:val="5D9BC0F4"/>
```

### 5.2 `abstractNumId=1` 全量 lvl 明细（逐级）

> 2026-10-14 修订：裁剪至 **6 级**（移除原 lvl6–8 无绑定的级联前缀，配合标题 7–9 清理，见修订记录 ⑨）。

| ilvl | 样式 (styleId) | w:start | w:numFmt | w:lvlText | 实际呈现格式 | w:lvlJc | w:suff | w:isLgl | w:ind (left / firstLine) | 该 lvl 的 rPr |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | heading 1 (2) | 1 | `chineseCounting` | `%1 ` | 「一 」「二 」…（中文数字 + 空格，无顿号） | left | 未定义=**tab** | — | 0 / 0（tabs: left@420） | rFonts hint=eastAsia |
| 1 | heading 2 (3) | 1 | `decimal` | `%1.%2` | 「1.1」「1.2」… | left | **space** | ✓ | 0 / 0（tabs: left@420） | rFonts hint=eastAsia |
| 2 | heading 3 (4) | 1 | `decimal` | `%1.%2.%3` | 「1.1.1」… | left | **space** | ✓ | 0 / 0（tabs: left@0） | rFonts hint=eastAsia |
| 3 | heading 4 (5) | 1 | `decimal` | `%4.` | 「1.」「2.」…（仅第 4 级自身序号） | left | **space** | — | 0 / 283（283÷567=0.499 cm） | rFonts hint=eastAsia + 宋体(ascii/hAnsi/eastAsia/cs) |
| 4 | heading 5 (6) | 1 | `decimal` | `%5）` | 「1）」「2）」…（自身序号 + 全角右括号） | left | **space** | — | 0 / 567（1.00 cm） | rFonts hint=eastAsia + 宋体(ascii/eastAsia)；b=0 i=0 strike=0 dstrike=0 spacing=0 w=100 sz=28 vertAlign=baseline |
| 5 | heading 6 (7) | 1 | `decimalEnclosedCircleChinese` | `%6` | 「①」「②」…（带圈序号） | left | **space** | — | 0 / 0 | rFonts hint=eastAsia + eastAsia=宋体；b=0 i=0 |

**各级起始值 `w:start`：全部为 `1`**（1–6 级均从 1 开始）。

**完整 XML 摘录（abstractNumId=1，逐字）**：

```xml
<w:abstractNum w:abstractNumId="1">
  <w:nsid w:val="5D9BC0F4"/><w:multiLevelType w:val="multilevel"/><w:tmpl w:val="5D9BC0F4"/>
  <w:lvl w:ilvl="0" w:tentative="0"><w:start w:val="1"/><w:numFmt w:val="chineseCounting"/><w:pStyle w:val="2"/><w:lvlText w:val="%1 "/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="left" w:pos="420"/></w:tabs><w:ind w:left="0" w:firstLine="0"/></w:pPr><w:rPr><w:rFonts w:hint="eastAsia"/></w:rPr></w:lvl>
  <w:lvl w:ilvl="1" w:tentative="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="3"/><w:isLgl/><w:suff w:val="space"/><w:lvlText w:val="%1.%2"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="left" w:pos="420"/></w:tabs><w:ind w:left="0" w:firstLine="0"/></w:pPr><w:rPr><w:rFonts w:hint="eastAsia"/></w:rPr></w:lvl>
  <w:lvl w:ilvl="2" w:tentative="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="4"/><w:isLgl/><w:suff w:val="space"/><w:lvlText w:val="%1.%2.%3"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="left" w:pos="0"/></w:tabs><w:ind w:left="0" w:firstLine="0"/></w:pPr><w:rPr><w:rFonts w:hint="eastAsia"/></w:rPr></w:lvl>
  <w:lvl w:ilvl="3" w:tentative="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="5"/><w:suff w:val="space"/><w:lvlText w:val="%4."/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="left" w:pos="0"/></w:tabs><w:ind w:left="0" w:firstLine="283"/></w:pPr><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体"/></w:rPr></w:lvl>
  <w:lvl w:ilvl="4" w:tentative="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="6"/><w:suff w:val="space"/><w:lvlText w:val="%5）"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="left" w:pos="0"/></w:tabs><w:ind w:left="0" w:firstLine="567"/></w:pPr><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="宋体" w:eastAsia="宋体"/><w:b w:val="0"/><w:i w:val="0"/><w:strike w:val="0"/><w:dstrike w:val="0"/><w:spacing w:val="0"/><w:w w:val="100"/><w:sz w:val="28"/><w:vertAlign w:val="baseline"/></w:rPr></w:lvl>
  <w:lvl w:ilvl="5" w:tentative="0"><w:start w:val="1"/><w:numFmt w:val="decimalEnclosedCircleChinese"/><w:pStyle w:val="7"/><w:suff w:val="space"/><w:lvlText w:val="%6"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="0" w:firstLine="0"/></w:pPr><w:rPr><w:rFonts w:hint="eastAsia" w:eastAsia="宋体"/><w:b w:val="0"/><w:i w:val="0"/></w:rPr></w:lvl>
</w:abstractNum>
```

### 5.3 绑定关系类型复核结论

对照三种可能关联（`w:styleLink` 元素 / `w:numStyleLink` 元素 / abstractNum 内 `w:pStyle`）：

| 关联类型 | 全包出现次数 | 结论 |
|---|---|---|
| `w:styleLink`（numbering 内的编号样式链接元素） | **0** | 不存在 |
| `w:numStyleLink`（编号样式间接引用） | **0** | 不存在 |
| abstractNum 内 `w:pStyle`（编号级 → 样式反向绑定） | **存在**（abstractNumId=1 的 lvl0–5 绑定 styleId 2–7） | **生效** |

**绑定机制明确结论（复核团长初检）**：
> 本模板标题编号的绑定机制为「**样式 pPr 内直接 `numPr`（numId+ilvl）引用 + abstractNum 各级 `w:pStyle` 反向绑定**」的**样式关联式多级列表**，**不存在** `styleLink` / `numStyleLink` 两类编号样式互链。

**对新文档继承复用的含义**：
- 该编号是「**列表库中与标题样式挂钩的列表**」：只要新文档同时保留 (a) 标题样式的 `numPr(numId=1)` 与 (b) numbering.xml 中 `numId=1 → abstractNumId=1` 及其各级 `pStyle` 绑定，Word 即自动把编号渲染到标题上，且**跨段落自动续编**；
- 由于使用 `pStyle` 绑定，编号级与样式一一对应（ilvl 0↔2、1↔3 …），**不可随意交换 ilvl 与样式的配对**，否则编号格式（中文数字/级联/带圈）会与标题级别错位；
- 因无 `numStyleLink`，**不能**仅凭一个「编号样式」定义复用到别的样式名；必须连同样式块与 numbering 部件一并继承。

> 附：`w:link` 属性（如 heading 1→29「标题 1 字符」）是段落↔字符**链接样式对**（Linked Style），与编号无关，不参与编号绑定。

### 5.4 完整编号体系概要（其余 num 用途）

numbering.xml 共 **3 个 `<w:abstractNum>`（id 0/1/2）+ 3 个 `<w:num>`（numId 1/4/5）**，映射如下，用以说明「模板中哪些内容参与编号」：

| numId | abstractNumId | multiLevelType / nsid | 参与编号的样式（abstractNum 内 pStyle） | 用途 |
|---|---|---|---|---|
| **1** | 1 | multilevel / 5D9BC0F4 | styleId 2,3,4,5,6,7 | **标题 1–6**（本文核心；6 级） |
| ~~2~~ | ~~3~~ | — | — | **2026-10-14 删除**：标题 7–9 未使用；样式与编号定义一并移除（见修订记录 ⑦） |
| ~~3~~ | ~~4~~ | — | — | **2026-10-14 删除**：列表编号未使用；样式与编号定义一并移除（见修订记录 ⑨） |
| 4 | 2 | singleLevel / 5FB01EDA | styleId 37（角标-图片） | **图片题注** `图%1`（lvl0 绑定 37；2026-10-14 裁至单级） |
| 5 | 0 | singleLevel / D8966A3C | styleId 38（角标-表格） | **表格题注** `表%1`（lvl0 绑定 38；2026-10-14 裁至单级） |

**要点**：
- 标题 1–6 使用独立多级列表（`numId=1`，现为 6 级）。原标题 7–9 的 `numId=2/abstractNumId=3` 与列表编号 `numId=3/abstractNumId=4` 已于 2026-10-14 删除（当前编号体系：numId 1＝标题 1–6、4＝图片题注、5＝表格题注）。
- 图片/表格题注（numId=4 / 5）与标题编号**互不干扰**，各自独立计数。
- `角标-图片`/`角标-表格` 的 `w:numPr`（numId=4/5）**只在样式内引用**，其 `pStyle` 反向绑定在 abstractNum 2/0 的 lvl0；**注意**：`角标-表格`(38) 在 numbering 中绑定到 abstractNumId=0（numId=5），其 lvlText=`表%1`；`角标-图片`(37) 绑定 abstractNumId=2（numId=4），lvlText=`图%1`。

### 5.5 部件关联关系（供生产文档时复刻）

**`word/_rels/document.xml.rels` 中 numbering 关系条目（逐字）**：

```xml
<Relationship Id="rId7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
```

（同文件其余关系：rId1→styles.xml、rId2→settings.xml、rId3→footnotes.xml、rId4→endnotes.xml、rId5→footer1.xml、rId6→theme/theme1.xml、rId8→fontTable.xml）

**`[Content_Types].xml` 中 numbering 声明（逐字）**：

```xml
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
```

（同文件 styles 声明：`<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>`；本文档 main part 类型为 `...wordprocessingml.template.main+xml`，即 `.dotx` 模板类型）

**`word/settings.xml` 与编号/样式相关设置（逐字摘要）**：

```xml
<w:attachedTemplate r:id="rId1"/>
<w:documentProtection w:enforcement="0"/>
<w:defaultTabStop w:val="720"/>
<w:characterSpacingControl w:val="doNotCompress"/>
... <w:compat><w:useFELayout/><w:compatSetting w:name="compatibilityMode" ... w:val="14"/> ...</w:compat>
```

- 模板中**无**与编号直接相关的专用设置项（如 `w:numbering` 相关开关、`w:useWord2002TableStyleRules` 等一概未出现）；
- `w:attachedTemplate r:id="rId1"`：`settings.xml.rels` 中 rId1 指向**外部**模板 `file:///<桌面>/示例方案.docx`（`TargetMode="External"`），即本模板由该外部模板「挂接」生成——**生产文档时应断开或替换该 attachedTemplate，避免指向上游模板**；
- `compatibilityMode=14`（Word 2010 兼容模式）。

---

## 六、生成文档时的应用说明

### 6.1 页面设置（输出默认值 · 用户确认 2026-10-14）

> 凡按本规范输出的文档，页面设置默认如下；如用户/客户另有指定，从其指定。

| 项 | 默认值 | XML 取值（twips） | 说明 |
|---|---|---|---|
| 纸张 | **A4**（21.0 × 29.7 cm） | `<w:pgSz w:w="11906" w:h="16838"/>` | 模板已符合，保持不变 |
| 页边距 · 上/下 | **2.54 cm** | `w:top="1440"` / `w:bottom="1440"` | **模板已内置终值**（2026-10-14 ⑬ 修订） |
| 页边距 · 左/右 | **3.18 cm** | `w:left="1800"` / `w:right="1800"` | **模板已内置终值**（2026-10-14 ⑬ 修订）；1800 缇 = 3.175 cm（界面显示 3.18 cm） |

**实现要点**：**模板已内置输出终值**（2026-10-14 ⑬ 修订：`w:pgMar = top/bottom 1440、left/right 1800`）——以模板为基底生成文档时**直接继承即可**（"以模板为基底=页面即正确"，无需逐次覆盖）；向其它文档注入样式时须按此值设置 `sectPr`。参考 XML：

```xml
<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800" w:header="720" w:footer="720" w:gutter="0"/>
```

（`header` / `footer` / `gutter` 保持模板原值；换算沿用 §3.3 公式：cm = 缇值 ÷ 567。）

### 6.2 如何应用这些样式

1. **按样式 ID（styleId）应用**：段落级样式通过 `w:pPr/w:pStyle w:val="<styleId>"` 引用，字符级样式通过 `w:rPr/w:rStyle w:val="<styleId>"` 引用。本模板 styleId 为纯数字（见 §二总览表）。示例：标题段落写 `<w:pPr><w:pStyle w:val="2"/></w:pPr>` 即应用「标题 1」。
   - 注意区分**样式名 vs styleId**：Word 界面按 `w:name`（如 `heading 1`）显示与匹配；OOXML 实际引用按 `w:styleId`（如 `2`）。程序化生成时**务必使用 styleId**，切勿把显示名写进 `w:val`（否则匹配失败回退为默认样式）。
2. **段落样式 vs 字符样式**：`page number`(21) 为字符样式，只能用 `rStyle` 引用，不可作段落 `pStyle`。
3. **链接样式对**：标题 1–6、footer 等为 Linked Style（段落+字符成对，如 2↔29）。应用段落样式即可，Word 会自动带出对应字符样式，无需单独引用。
4. **不参与编号的样式**：`封面`、`居中-表格`、`居中-图片`、`toc 1/2/3`、`Normal`、`page number` 均无 `numPr`，直接应用即无编号。
5. **内容块识别与清洗（生成前处理）**：大模型内容在套用样式前，须执行"识别 → 清洗 → 套样式"三步，详见 §6.7。

### 6.3 让标题自动编号「原生继承并自动续编」

**核心原则：编号文本一律由 `numbering.xml` 定义、由标题样式的 `numPr` 引用驱动；生成文档时严禁手写「一、」「1.1」等编号文字。**

- 正确做法：段落仅指定 `pStyle`（如 `w:val="2"`），并让该样式携带 `numPr(numId=1, ilvl=0..5)`。Word 依据 numbering.xml 计算并渲染编号，新增/删除/移动标题时**自动重排续编**。
- 错误做法：把「1.1」「一、」等作为正文文字写进 `<w:t>`；一旦如此，编号与样式脱钩，插入新标题不会续编。
- **保证续编的关键三件套**（缺一不可）：
  1. 标题样式的 `<w:numPr><w:ilvl w:val="N"/><w:numId w:val="1"/></w:numPr>` 完整保留；
  2. `numbering.xml` 中 `numId=1 → abstractNumId=1` 的映射及 `abstractNumId=1` 的**全部 lvl（含各级 `pStyle` 反向绑定）**完整保留；
  3. 段落确实应用了对应的标题样式（`pStyle`）。
- **同一列表跨段落续编**：同一 `numId` 下的所有相关样式段落共享计数器，天然跨段落、跨页续编；若需多套独立编号，才需新增 `num`（新 `numId`），但本规范不要求。
- **级联语义提示**：本模板 lvl0=中文数字（一、），lvl1=`%1.%2`，lvl2=`%1.%2.%3`，而 lvl3 起 `%4.`/`%5）`/`%6` **只显示自身级序号**（不含父级前缀）。这是模板既定格式，沿用即可，勿改写。

### 6.4 须保留 / 复制的部件清单

**以模板为基底建新文档（最稳妥，强烈推荐）**：直接以 `样式模板.dotx` 为模板（或在 Word/WPS 中「基于此模板新建」）另存为 `.docx`，随后仅在 `document.xml` 内写入正文段落。此时 styles.xml、numbering.xml、theme、fontTable、footer 等**整部件天然继承**，编号与样式零改动即生效（**页面设置终值已内置**——2026-10-14 ⑬ 修订：模板 `pgMar = 1440/1800`，直接继承即正确，无需再逐次覆盖）。

**若「向已有文档注入」这些样式/编号，须分步处理**：

| 步骤 | 部件 | 操作要点 |
|---|---|---|
| 1 | `word/styles.xml` | 复制 16 个目标 `w:style` 块（styleId 1,2,3,4,5,6,7,39,36,38,37,15,16,13,21,41）。**依赖链勿漏**：heading 1–6 依赖 Normal(1)；角标依赖 `居中-图片`(36)；`居中-图片/表格`、`封面` 依赖 Normal；字符样式 `标题 N 字符`(27–35) 为 link 目标，若保留 `w:link` 属性则须一并复制，否则删除 link 属性。 |
| 2 | `word/numbering.xml` | 至少复制 `numId=1` 及其 `abstractNumId=1` 全量 lvl（现为 6 级）；若用题注加 numId=4,5（标题 7–9 的 numId=2、列表编号 numId=3 均已删除）。**abstractNumId 与 numId 是局部 ID，须整体搬移并确保唯一、无冲突**（与目标文档已有 numbering 合并时重新编号并同步修改样式内 numId 引用）。 |
| 3 | `word/_rels/document.xml.rels` | 确保存在 numbering 关系（`Type=.../numbering`，`Target=numbering.xml`），获得其 `rId`；无则新增。 |
| 4 | `[Content_Types].xml` | 声明 `<Override PartName="/word/numbering.xml" ...numbering+xml/>` 及 styles 的 Override（若尚未声明）。 |
| 5 | `word/settings.xml` | 如需 `defaultTabStop=720`、`compatibilityMode=14` 等与排版一致，比对复制；**清除或替换 attachedTemplate 外部链接**。 |
| 6 | 交叉校验 | 注入后打开：标题应自动出现编号且续编；若显示无编号，优先排查 (a) numId 未同步 (b) numbering 部件缺失或未声明 (c) pStyle 与 ilvl 配对错误。 |

**整部件继承方式**（推荐用于「以模板为基底」）：连同 `styles.xml` / `numbering.xml` / `theme/theme1.xml` / `fontTable.xml` / 页脚部件及其 rels、Content_Types 声明整体复制，最大限度避免 ID 冲突与属性丢失。

### 6.5 封面与页码不参与编号

- **编号仅作用于 `heading 1`–`heading 6`**（numId=1，ilvl 0–5）。其余目标样式（`居中-表格`、`居中-图片`、`toc 1/2/3`、`Normal`、`page number`）**均无 `numPr`**，不参与任何编号。
- **封面**：封面主标题套「**封面**」（41，无 `numPr`，不参与编号）；其余封面文字（副标题、编制信息行）用正文等非标题样式。**禁止套标题 1–6**（防止进入编号序列）。
- **页码不参与编号**：页脚 `footer1.xml` 的页码由 **PAGE 域**实现，与本文档编号体系完全无关：
  - 页脚段落 `pStyle="14"`（footer 样式），字符格式为**行内 `rPr`**（`宋体` + `w:sz=18`（9 pt） + `color=000000`），**未引用** `page number`(21) 字符样式；
  - 域结构为：制表符 → 文本 `— `（前有破折号+空格） → `fldChar begin` → `instrText PAGE` → `fldChar separate` → `fldChar end` → 文本 ` —`（空格+破折号） → 制表符，呈现为 **`— 页码 —`** 形式；
  - `sectPr` 含 `<w:pgNumType w:start="1"/>`，页码从 1 起。
- **含义**：页码是「字段自动生成」而非「列表编号」，二者机制不同；生成新文档时**不要**把标题编号与页码混为一谈——标题编号走 numbering.xml，页码走页脚 PAGE 域。

### 6.6 技术注意事项

1. **styleId 与样式名引用差异**：程序化生成用 `w:styleId`；界面/样式库按 `w:name`。混用会导致样式不生效。
2. **Word/WPS 保存可能重排 styleId**：本模板 styleId 为纯数字（由 WPS 生成）。在 Microsoft Word 中编辑另存后，styleId 可能被重命名为 `Heading1`、`a1` 等**字符串**。因此**不要硬编码 styleId 到生成逻辑**，应以 `w:name` 反查，或用「以模板为基底」方式让 Word 自行维护 ID 一致性。
3. **numbering 部件缺失时的回退**：若目标文档缺 `numbering.xml`（或未被 rels/Content_Types 正确引用），标题的 `numPr` 无法解析 → **编号静默回退为「无编号」**（不报错）。排查编号丢失时优先查此部件。
4. **abstractNumId / numId 是文档局部 ID**：合并到已有 numbering 时必须全局重编号并同步所有引用（样式 `numPr`、`w:pStyle` 不需改，因其引用的是 styleId）。
5. **标题字号提示（数据保真说明）**：`heading 1`–`heading 6` 样式块内**均未定义 `w:sz`**，故拉丁/中文字号**继承 Normal = 14 pt**；仅 `w:szCs`（复杂文种字号）在 h1=22 pt、h2/h3=20 pt 显式指定，h4–h6 亦继承 14 pt。此为模板原始定义，沿用勿改。
6. **首行缩进优先规则**：`heading 1/2/3/6` 显式 `firstLineChars=0` 覆盖了继承自 Normal 的 `firstLine=560`（Word 中 `*Chars` 优先），故这些标题**无首行缩进**；`heading 4/5` 未覆盖，继承 2 字符首行缩进。
7. **`w:cs` 字体**：多数样式未定义 cs，回退主题 `minorBidi`（主题 `a:cs` 为空 → 无有效字体）。若文档含复杂文种（阿拉伯、希伯来等），需补 cs 字体，否则走系统默认。
8. **链接字符样式**：若只搬运段落样式而删除其 `w:link` 指向的字符样式（如 29「标题 1 字符」），须同步删除 `w:link` 属性，避免悬空引用。
9. **WPS 样式面板的「下一级标题引导」与 heading 7/8/9 隐藏定义**（2026-10-14）：WPS 面板会自动提供"当前已用**最大标题级别 + 1**"的入口（如用到标题 6 → 面板出现「标题 7」；点击（应用）后继续出现「标题 8」，以此类推）——该行为由 WPS 界面机制驱动，**删除样式定义、裁剪编号级数均无法移除该入口**。已为 `heading 7/8/9` 建立**隐藏定义**（`<w:hidden/>` + `<w:semiHidden/>`、`uiPriority=99`、无 `qFormat`/编号/链接，styleId 8/9/10）以抑制该入口；MS Word 引擎实测 `Hidden=True`、样式集合遍历不可见。同日另对「默认段落字体」（`Default Paragraph Font`）经实验评估后**移除定义**——该样式系引擎"隐式提供"的内置默认项，删除后打开无损（另注：其 hidden 声明会被引擎规范化无视，属默认样式特例，见修订记录 ⑪）。**验证（2026-10-14 · 用户确认）：WPS 面板中「标题 7」与「默认段落字体」均已不再显示——两方案（隐藏 / 删除）确认生效。**

### 6.7 内容 → 样式映射与编号清洗（生成前处理 · 用户确认 2026-10-14）

> 大模型产出的内容为**无样式纯内容**（可含手写编号文本）；生成交付 Word 时，按"**识别 → 清洗 → 套样式**"三步执行：先判定每个内容块的类型；对被映射到**带自动编号样式**（标题 1–6、角标-图片、角标-表格）的块，**删除文本中的手写编号前缀**（编号一律由样式自动生成）；再套用样式。**严禁双重编号。**

#### 6.7.1 内容块 ↔ 样式映射表

| 内容块 | 目标样式（styleId） | 自动编号 | 清洗要求（删除行首手写前缀） |
|---|---|---|---|
| 一级标题 | 标题 1（2） | 一 | `一、` `第一部分` `1.` 等 |
| 二级标题 | 标题 2（3） | 1.1 | `1.1` `（一）` 等 |
| 三级标题 | 标题 3（4） | 1.1.1 | `1.1.1` `1、` 等 |
| 四级标题 | 标题 4（5） | 1. | `1.` `（1）` 等 |
| 五级标题 | 标题 5（6） | 1） | `1）` 等 |
| 六级标题 | 标题 6（7） | ① | `①` 等 |
| 正文段落 | 正文 Normal（1） | 无 | **不清洗**（正文内容原样保留） |
| 图片段（图片本体） | 居中-图片（36） | 无 | — |
| 图片角标（图题） | 角标-图片（37） | 图 N | `图N` `图 N` |
| 表格角标（表题） | 角标-表格（38） | 表 N | `表N` `表 N` |
| 表格 | 表格内**各段落**套「居中-表格」（39） | 无 | 表格内文字不参与编号清洗 |
| 封面主标题 | **封面（41）** | 无 | 不参与编号；**禁止套标题 1–6**（防止进入编号序列） |
| 封面其他文字（副标题/编制信息行） | 正文（1）等非标题样式 | — | 不参与编号 |
| 目录 | 目录域自动生成（toc 1/2/3） | — | 目录条目不手写；「目录」占位标题不套标题 1–6 |

> 说明：上表"表格"与"图片"的落地方式均经端到端实测（2026-10-14，见 §6.7.4）——表格内各段落套「居中-表格」，图片段（含真实图片对象）套「居中-图片」。
>
> **PR-034 补充（2026-11-19，套样式 ≠ 样式生效）**：①「居中-表格」的字体字号（12pt）只有在文字级无 `rFonts/sz/szCs` 直接格式时才真正生效；旧 `make_docx.py` 的"宽表降字号 fs=8/9"会把字号写死成 8/9pt，造成"套了样式但字号没变过去"，该逻辑已删除，列宽靠内容分配（L-20）、字号一律交样式决定。② 图片段"视觉居中"不等于套了样式，必须给含 `w:drawing` 的段落真正设 `居中-图片`（styleId=36）。新增 `scripts/fix_docx_styles.py` 可对已生成文档批量归位，新增 `doc_selfcheck.py` 两项可数判据防漏检。生成脚本已全线根治：① editor_sdk 批量插图后须补跑修复脚本；② `build_docx.py` 的 add_picture 后套样式；③ `content_to_docx.py` 的 make_img_p 已带 pStyle=36。

#### 6.7.2 手写编号清洗清单（行首模式，按序剥离）

| 模式 | 示例 | 适用块 |
|---|---|---|
| 汉字序号 + 标点 | 一、 / 二． / 三， | 标题 1 |
| 章节词 | 第一部分 / 第二篇 / 第3章 | 标题 1 |
| 多级数字 | 1.1 / 2.4.1 / 1.1.1（可带后缀标点） | 标题 2–6 |
| 单级数字 + 标点 | 1. / 2、 / 3． | 标题 4 等 |
| 括号汉字 | （一） / （二） | 标题 2 |
| 圆括号数字 | 1） / （1） | 标题 5 |
| 带圈数字 | ① / ② | 标题 6 |
| 图题前缀 | 图1 / 图 1 / 图1： | 图片角标 |
| 表题前缀 | 表1 / 表 1 / 表1： | 表格角标 |

> 清洗实现须保证**不误伤正文**：仅对"已识别为标题/角标"的块执行；匹配限定行首；正文段落一律不清洗。参考实现见 `_verify_编号继承测试/demo_clean_and_map.py`（演示管线）。

#### 6.7.3 校验要求

生成后必须核验：① 界面/渲染中不存在双重编号（如"1.1 1.1"、"图1 图1"、"一 第一部分"）；② 标题编号连续且层级正确（同级续编、下级挂靠，见 §6.3）；③ 角标编号为"图 N / 表 N"独立序列；④ 封面与目录不参与编号（§6.5）；⑤ 表格内各段落为「居中-表格」、图片段为「居中-图片」，不得残留默认"正文"；⑥（PR-034）套了「居中-表格」的段落里直接字体字号数=0、含图片对象的段落未套「居中-图片」数=0——两项以 `doc_selfcheck.py` 的可数判据为准，肉眼或"对齐看起来居中"不作数；⑦（PR-036）「角标-表格」「角标-图片」段落的直接字体字号数=0——题注字体字号只由样式决定（继承仿宋 12pt），旧渲染写死的黑体 10.5pt 会把它盖掉；表题数须**严格等于**多列表格数，多套（把"…如下表"引导句误判为题注）会凭空给正文加"表 N"编号，同判不合格。

#### 6.7.4 端到端验证（2026-10-14 实测）

输入含 `一、项目背景 / 1.1 建设需求分析 / 1.1.1 教学场景需求 / 图1 系统总体架构 / 表1 设备配置清单` 的模拟内容 → 清洗 → 套样式 → 渲染实测（v2，含**真实图片对象**与表格）：输出为「一 项目背景 / 1.1 建设需求分析 / 1.1.1 教学场景需求 / 图1 系统总体架构 / 表1 设备配置清单」；图片段套「居中-图片」、表格内各段落套「居中-表格」；**全部编号由样式自动生成、无双重编号**。验证明细：`_verify_编号继承测试/`（demo_clean_and_map.py + 演示-内容清洗与样式映射-v2.docx + render-v2 目录）。

#### 6.7.5 既有文档的标题识别与目录层级（保真重排扩展 · 用户确认 2026-10-15）

对既有文档做保真重排时，标题识别与目录层级遵循以下规范（首例实测：风电场示范工程技术方案，78 项升级）：

1. **标题识别上限 = 六级**。样式化标题（一~四级，按 pStyle 识别）之外的行首编号式细分，按上下文级联定级：四级标题下第 1 层细分候选 = 五级，再下 = 六级；**六级以后再细分的，一律按正文处理**（保留原文编号文字，不清洗、不升级）。
2. **候选模式族（行首）**：`（汉字）` / `（数字）` / `(数字)` / `数字、` / `数字）` / `四级数字`（x.x.x.x 及以上连续级联，如 2.1.2.5.1）/ `数字紧贴`（数字后直接接汉字，如「1基本规范」）。
3. **定级算法（模式族栈 + 兄弟闭合）**：每个样式化标题分支内维护「模式族 → 级别」栈。候选归族后：族已在栈中 → **同级（兄弟）**，并**闭合修剪栈中更深族**（其子层级随上一兄弟结束）；族未在栈中 → 当前栈内最深级别 + 1（上限 6，超限 → 正文）。
4. **标题性守卫**（不满足 → 正文，原文编号保留）：去前缀后含 `，。；`（含句末）；去前缀后长度 > 30 字；空文本。**边界口径（用户确认）**：结尾冒号 → 仍为标题（冒号保留，如「1）数据采集调试方法：」）；带分号/句号结尾的短列举项（如「(1)数据采集与处理功能检查；」）→ 正文。
5. **numPr 列表项**：自动编号的短列表项（渲染前缀为「N、」或「（N）」、文本 ≤ 16 字且无标点）按其渲染前缀归族参与定级；升级时**删除该段 numPr**（列表编号由标题样式自动编号替代），文本不动。
6. **目录层级 = 三级**：目录域指令用 `TOC \o "1-3"`；原目录含更深层级条目的，重出后按三级上限收敛（2026-10-15 首例执行口径：原四级目录重出为三级，16 条四级条目移除、新增三级条目进入）。
7. **升级项编号**：前缀清洗后编号由样式自动生成——三级 =「N.N.N」式、五级 =「N）」式、六级 =「①」式（见 §5.2），严禁手写编号。

### 6.8 图片与表格宽度（顶满版心 · 用户确认 2026-10-14）

> **所有图片与表格的宽度一律顶满左右页边距**（图片高度不限，按原始比例自适应）。

**版心宽度派生**（依据 §6.1 页面设置）：A4 宽 11906 缇 − 左 1800 − 右 1800 = **8306 缇（≈ 14.65 cm）**。

| 对象 | 宽度实现 | 说明 |
|---|---|---|
| 图片 | 显示宽 = **5,274,310 EMU**（= 8306 缇 × 635 EMU/缇） | 高按原始宽高比缩放（`cy = cx × 原高 ÷ 原宽`），不裁切、不变形 |
| 表格 | `tblW = 8306` 缇（type=`dxa`）；`tblGrid` 各列宽合计 = 8306；不设 `tblInd` | 列宽按内容分配，但**总和恒为 8306** |

**实现示例**：

```xml
<!-- 图片：段落套「居中-图片」，extent 宽固定为版心宽当量 -->
<wp:extent cx="5274310" cy="按比例计算"/>

<!-- 表格：宽度恒为 8306 缇（两列均分示例：4153 + 4153） -->
<w:tblPr><w:tblW w:w="8306" w:type="dxa"/></w:tblPr>
<w:tblGrid><w:gridCol w:w="4153"/><w:gridCol w:w="4153"/></w:tblGrid>
```

**备注**：
- 图片素材分辨率建议 ≥ 约 900 px 宽（对应 150 DPI 打印），避免拉伸到 14.65 cm 后模糊；
- 图片段套「居中-图片」后，宽度顶满时"居中"即两端顶齐页边距；
- **校验**：渲染后图片与表格的左右边缘应与页边距线重合（无缩进、无右侧留空）。

### 6.9 配套工具脚本（设置修改与内容落盘 · 2026-10-14）

**① 模板设置操作 — `scripts/template_style_tool.py`**（"改设置一条命令"；默认目标＝专家团标准模板 `assets/样式模板.dotx`）：

```bash
python template_style_tool.py list   [--filter 关键字]        # 列样式概览
python template_style_tool.py set    --style "toc 1" --sz 26 [--line 360] [--font-ea 黑体] [--align center] …
python template_style_tool.py hide   --style "heading 7"      # 隐藏（hidden+semiHidden）
python template_style_tool.py remove --style "List Number"    # 删除（自动级联清理专属编号）
python template_style_tool.py page   --top 1440 --right 1800 --bottom 1440 --left 1800   # 页面（缇；支持 2.54cm 记法）
```

每次写操作自动执行：备份（`.bak_时间戳`）→ 修改 → 读回验证 → 写回（被占用时自动重试）；读写全程"即开即关"（防自锁）。

**② 内容 → 样式落盘 — `scripts/content_to_docx.py`**（"类别已判断、脚本套样式"）：

```bash
python content_to_docx.py --input content.json --out 交付物.docx [--base 模板路径]
```

输入 JSON：`cover` / `toc` / `blocks`（类型：`h1–h6`、`p`、`img`、`cap_img`、`cap_tbl`、`tbl`、`toc1–toc3`）；标题与题注的**手写编号自动清洗**（编号一律由样式生成）；图/表宽度顶满版心；以标准模板为基底（页面终值已内置）。

**使用纪律**：改动标准模板后须同步 ① 本规范修订记录与 SHA 引用 ② `document-format-standards.md` §0.14。

---

## 附：溯源索引

| 内容 | 来源部件 | 元素定位 |
|---|---|---|
| 15 样式定义 | `word/styles.xml` | 各 `<w:style w:styleId=...>` |
| docDefaults | `word/styles.xml` | 首个子元素 `<w:docDefaults>` |
| 标题 1–6 编号 | `word/numbering.xml` | `<w:num w:numId="1">`、`<w:abstractNum w:abstractNumId="1">` |
| 其余编号 | `word/numbering.xml` | abstractNumId 0/2/3/4 及 numId 2/3/4/5 |
| 页码域 | `word/footer1.xml` | `<w:p>` 内 `fldChar`+`instrText PAGE` |
| numbering 关系 | `word/_rels/document.xml.rels` | `<Relationship Id="rId7" ... Target="numbering.xml"/>` |
| numbering 声明 | `[Content_Types].xml` | `<Override PartName="/word/numbering.xml" .../>` |
| 主题字体 | `word/theme/theme1.xml` | `<a:majorFont>` / `<a:minorFont>` |
| 设置项 | `word/settings.xml` | `attachedTemplate`/`defaultTabStop`/`compat` |
| 页边距/页码起始 | `word/document.xml` | `<w:sectPr>`（`w:pgMar` 按 §6.1 输出默认值覆盖；`w:pgNumType w:start="1"`） |
