# 确定性解析器规格 — 章节检测 / 场景头 / 格式检查

> 虾料最有价值的工程资产是三个**不依赖 AI 的确定性解析器**。100% 还原必须保证正则与判定逻辑等价。
> 源文件：`cognee/chapter_detector.py`、`utils/screenplay_scene_parser.py`、`utils/screenplay_quality.py`、`utils/document_parsers.py`、`utils/upload_safety.py`。

---

## 1. 章节检测器（ChapterDetector）

### 1.1 支持的章节标记（行首匹配，优先级从高到低）
```python
PATTERNS = [
    # 第X章，可带 markdown 标题(#) 与《书名》前缀
    r"^(?:#{1,6}\s*)?(?:《[^》\n]{1,40}》\s*)?第\s*([一二三四五六七八九十百千\d]+)\s*章(?=$|[\s:：《（(【\[\-—–、.。．])",
    # 第X集
    r"^(?:#{1,6}\s*)?(?:《[^》\n]{1,40}》\s*)?第\s*([一二三四五六七八九十百千\d]+)\s*集(?=$|[\s:：《（(【\[\-—–、.。．])",
    # Chapter N
    r"^(?:#{1,6}\s*)?Chapter\s*(\d+)(?=$|[\s:：(\[\-—–.。．])",
    # Episode N
    r"^(?:#{1,6}\s*)?Episode\s*(\d+)(?=$|[\s:：(\[\-—–.。．])",
]
```

### 1.2 防误切校验 `_is_valid_title_tail`
- 标记后无内容 → 是章节
- 后随 `.。．` → 再看剩余是否像句子结尾（`[。\.…]\s*$` 判定）
- 后随 `:：《（(【[-—–、` → 是章节（标题分隔符）
- 其余 → 不以句号结尾才是章节

### 1.3 中文数字解析 `_parse_chinese_number`
- 支持：单个（一/二/十…）、复合（十一/二十/二十三/一百/一百零一/一百二十三/一千零一）
- 大写数字（壹贰叁肆伍陆柒捌玖拾佰仟）也映射
- 零为占位跳过；结果 ≤0 时回退 1
- `CN_NUM_MAP`：零0 一1 二2(两) 三3 四4 五5 六6 七7 八8 九9 十10 百100 千1000 + 大写

### 1.4 无章节回退 `_prepare_fallback_content`
- 空文本 → 返回空
- `extract_screenplay_candidate_lines` 提取候选行；候选非空且与原文不同 → 用候选（B档剧本裁掉前言）
- 否则保原文，作为单章（第1章, is_fallback=True）

---

## 2. 场景头解析器（screenplay_scene_parser）

### 2.1 时间词（TIME_TOKEN_RE）
- 现代中文：日/夜/晨/晚/午/黄昏/清晨/上午/正午/午后/下午/傍晚/夜晚/深夜/凌晨（按长度倒序合并）
- 古典：`(子|丑|寅|卯|辰|巳|午|未|申|酉|戌|亥)时(?:[一二三四]刻|半)?`
- 英文：DAY/NIGHT/MORNING/AFTERNOON/EVENING/DAWN/DUSK → 映射中文

### 2.2 支持的场景头格式（全部要识别）
| 格式 | 示例 | 识别正则 |
|---|---|---|
| 编号+地点同行 | `1-2商场一层入口处 日 内` | NUMBERED_SCENE_RE `^(?P<episode>\d+)\s*[-－.．]\s*(?P<scene>\d+)(?:[、，,\s])?(?P<rest>.*)$` + 尾部解析 |
| 独立编号行 | `1-1` 换行 地点行 | SCENE_MARKER_RE `^(?:场次|场|第)?[（(]?\d+[）)]?(?:\s*场)?(?:\s*[:：])?\s*$` |
| 分字段 | `场次：1` / `地点：…` / `时间：…` / `内外景：…` / `人物：…` | COLON_SCENE_MARKER_RE / LABELED_*_RE |
| 插入场 | `+场(1) 地点…` | INSERT_SCENE_RE `^[+＋]\s*场(?:次)?…` |
| Fountain 中文 | `内景 苏鸾寝殿 - 深夜` / `外景…` | CHINESE_FOUNTAIN_SCENE_RE |
| Fountain 国际 | `INT. BEDROOM - NIGHT` / EXT/EST/INT./EXT | INTERNATIONAL_SCENE_RE `^(INT|EXT|EST|INT\./EXT|INT/EXT|I/E)\.?\s+…` |
| 简单地点 | `商场一层入口处 日 内`（时间+内外在尾部，两顺序都支持） | SIMPLE_LOCATION_RE |
| 括号标签 | `1 场景：【深夜 商场 内】` | BRACKETED_LABELED_SCENE_RE |
| 集头 | `第1集` | EPISODE_HEADER_RE（切集号，不建场景块） |

### 2.3 解析状态机要点
- `parse_scene_blocks`：逐行扫描，`collecting_header` 阶段吸收 地点/时间/内外/人物 元数据行，直到首个正文行
- 正文行判定 `_looks_like_content_line`：`△▲【[` 开头 或 说话人行 `^[^\n：:]{1,24}[：:].+$`
- `ParsedSceneBlock` 字段：header_line/location/time_of_day/interior_exterior/characters/lines/episode/scene_no/**time_inferred**（缺时间时默认"日"但标记 inferred）
- 多地点 `parse_location_line`：`/`、`、` 分隔；`_inherit_building_prefix` 用 `(.+?(?:家|公寓|楼))` 前缀 + ROOM_TYPES（客厅/厨房/卧室/书房/阳台/衣帽间/走廊/门口/餐厅/浴室/卫生间/洗手间）组合 → "李家"+"客厅"→"李家客厅"
- 角色行 `parse_character_line`：去前缀（人物：/出场人物：/角色：）、按 `、，,` 分割、括号内名字优先、**跳过含数字项**

### 2.4 ★ xia-boss 剧本先行：场景头权威源约定（本包适配层，不降 blocking 判定）

> 上游 `xiaju-script` 成稿每个场景只写**一行权威场景头**：`场景：<纯地点名> <时间> <内/外>`（`场景：` 开头，`_has_source_scene_header_evidence` 天然命中；location 只到"纯地点名"粒度）。

- **绑头不绑启发式**：还原/摄入时，**场景边界只认以 `场景：` 开头的显式行**（以及传统 slugline：Fountain/编号/分字段）。`_looks_like_content_line` 已把 `△ ▲ 【 [` 开头判为正文——因此**禁止再对 `【` 开头的六字段正文 bullet 跑 `SIMPLE_LOCATION_RE` / `parse_location_line` 的多地点（`、` 分隔）+ 尾部"内/外"启发式**。
- **为什么**：DramaClaw 原松解析器会把 `- **【出场角色】** 苏墨、王员外` 误读成"多地点 + 外景"→ 生成假 `scene_blocks`（本包实测：一份两场景成稿虚增到 11 个场景头）。假块会污染 `scene_blocks → scene-chain → 补建清单 → scene_name 未映射=0`，让虾塘/虾镜对不上拓扑图。`assess` 更严不受影响，但 `scene_blocks` 会脏。
- **不改解析器时的等价替代**：由上游虾剧保证"出场角色行尾以句号收口、不停在内/外结尾人名"（见 `xiaju-script` 出场角色行铁律）。**二者取其一即可根治**；本包优先按上面"绑头"收敛。
- **验收补充**：`len(scene_blocks) == 成稿中 '场景：' 头的数量`；无任何 `【` 开头的行被计为 `scene_block.header_line`。此条不改变 `missing_scene_headers` blocking 判定（仍要求至少命中真实场景头）。

---

## 3. 格式检查（screenplay_quality）

### 3.1 场景头三态 `assess_screenplay_scene_headers`
```
missing   ← 无任何带结构证据的场景头
standard  ← 全部检测场景头都含 地点+显式时间+内/外
repairable← 检测到了边界但元数据不全
```
**结构证据 `_has_source_scene_header_evidence`**（防"孙悟空快步走到门外"这类散文误判）：
- 括号标签/Fountain/插入场/分字段/编号场景头（rest 非空或纯编号）
- 以 场次/地点：/环境：/场景： 开头，或 `^第\d+场`
- 或结尾 `(时间词)[\s，,、]*(内|外)`

### 3.2 指标统计（metrics）
`non_empty_lines` / `scene_headers`（普通）/ `scene_block_headers`（场次开头）/ `total_scene_headers` / `dialogue_lines` / `multi_speaker_lines` / `ambiguous_speakers` / `parenthetical_dialogues` / `long_dialogue_lines`(≥40字) / `scene_headers_missing_time` / `standard_scene_headers`

### 3.3 判定阈值
| 条件 | 结果 |
|---|---|
| `looks_like_screenplay = total_scene_headers>=2 || dialogue_lines>=8` 为假 | warning `not_screenplay_like`（不阻断） |
| total_scene_headers == 0（且像剧本） | **blocking** `missing_scene_headers` |
| total_scene_headers < max(1, dialogue_lines//12) | warning `sparse_scene_headers`（dialogue<24 时跳过） |
| dialogue_lines < 5 | warning `too_few_dialogue_lines` |
| multi_speaker_lines >= 3 | warning `multi_speaker_lines` |
| ambiguous_speaker_count >= max(3, dialogue//5) | warning `ambiguous_speakers` |
| long_dialogue_count >= max(3, dialogue//4) | warning `many_long_dialogues` |
| 场景头缺时间 | warning `scene_headers_missing_time`（与行级问题去重） |

### 3.4 行级问题（`_build_line_aware_format_issues`）
逐场景块诊断：缺 地点/时间/内/外 → 组装 issue（带行号 line_number）
- 缺失 >1 项 → `incomplete_scene_header`；只缺时间 → `scene_headers_missing_time`；只缺内/外 → `missing_interior_exterior`
- 修复建议：场次开头且已有地点 → `"{header}；地点：{loc}，[日/夜]，[内/外]"`；否则 → `"{header} [地点] [日/夜] [内/外]"`

### 3.5 章节结构问题（`_build_chapter_structure_issues`）
- 重复章节序号 → `duplicate_chapter_number`
- 序号回跳/重复（number <= previous）→ `non_increasing_chapter_number`
- 建议文案取 `FIX_HINTS`（12 条，原样还原）

### 3.6 综合判定 `build_import_format_check`
```
require_scene_headers 且场景头 missing → blocking「精品剧必须包含场景头…」
否则 无章节 → blocking「未检测到有效章节或可识别正文，无法用于剧本结构化。」
否则 场景头 repairable → warning「已识别场景边界；缺失的场景元数据将在场景规划时补齐。」
否则 有 issues → warning「上传成功，但检测到 {n} 个格式风险，可能影响场景识别。」
否则 → ok「上传成功，剧本格式校验通过。」
```

### 3.7 候选行提取 `extract_screenplay_candidate_lines`
- 找到首个 `is_scene_start_line` → 从此行开始全部返回（裁掉前置前言）
- 无场景头：跳过 `梗概|人物小传|人物介绍|角色介绍|角色小传` 区块、`END` 行、编号人物行 `(1)人名：`，其余保留

---

## 4. 文档解析与上传安全（document_parsers / upload_safety）

### 4.1 编码与格式
- `.txt`/`.md`：UTF-8 解码失败 → GBK；CRLF/CR → `\n`
- `.docx`：python-docx；段落 + 表格（单元格 strip、行内 `\t` 连接、空单元格跳过）；空段落跳过
- 其它 → `DocumentParseError{source_format, location, reason}`（location 区分 文件编码/文件类型/依赖/文档/段落N/表格N）

### 4.2 限额常量（必须一致）
| 常量 | 值 |
|---|---|
| `MAX_NOVEL_UPLOAD_BYTES` | 512 * 1024（上传原始大小） |
| `MAX_NOVEL_IMPORT_BYTES` | 1 * 1024 * 1024（导入原始大小） |
| `MAX_NOVEL_IMPORT_CHARS` | 100_000（去空白计费字数） |

### 4.3 计费字数
`count_billable_novel_chars = len(re.sub(r"[\s\u3000]+", "", text))`（标点保留、布局空白不计）

### 4.4 文件名清洗
- `PurePosixPath(name).name` 只留 basename → 剩余 `/` `\` 替换 `_` → 空/`.`/`..` 回退 `upload.txt`
- `is_safe_upload_target`：`(upload_dir / safe_name).resolve().is_relative_to(upload_dir.resolve())`

### 4.5 流式写入限流
`stream_to_file_with_limit`：chunk 1MB 流式写，超 max_bytes 中断 + 删除残片 + 抛 `UploadTooLargeError`
