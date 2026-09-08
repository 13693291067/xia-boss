# 边界限制与常量清单 — 虾料（ingest）

> 100% 还原的关键：以下常量、错误文案、判定阈值必须**逐字一致**。还原完成后用本文件做最终核对。

---

## 1. 限额常量（三处来源文件必须对齐）

| 常量 | 值 | 所在文件 | 语义 |
|---|---|---|---|
| `MAX_NOVEL_UPLOAD_BYTES` | 512 * 1024（512KB） | upload_safety.py | 上传流式写入上限 |
| `MAX_NOVEL_IMPORT_BYTES` | 1 * 1024 * 1024（1MB） | upload_safety.py | 导入任务文件大小上限 |
| `MAX_NOVEL_IMPORT_CHARS` | 100_000 | document_parsers.py | 单次导入计费字数上限 |
| `PASTE_TEXT_MAX_LENGTH` | 1000 | ingest.tsx | 粘贴文本上限 |
| 图谱快照默认节点 | 48（可调 20-80） | store.py | get_graph_snapshot |
| 图谱快照默认边 | max_nodes*3（≤160） | store.py | 同上 |
| 章节表展示 | 前 20 章 | ingest.tsx | slice(0,20) |
| 上传格式 | .txt / .md / .docx | document_parsers.py | 白名单 |
| 上传编码 | UTF-8 → GBK 回退 | document_parsers.py | decode_novel_bytes |
| 计费字数口径 | 去 `\s\u3000` 后长度 | document_parsers.py | 标点保留 |

---

## 2. 错误响应（error_type + 文案逐字）

### 2.1 upload 端点
| error_type | 文案 |
|---|---|
| （无） | `非法文件名` |
| `unsupported` | `不支持的文件类型: {suffix}，当前支持: txt、md、docx` |
| `file_too_large` | `文件超过 512KB 上限，请压缩文件或拆分正文后重新上传。`（data.limit_bytes=524288） |
| `text_too_large` | `正文共 {actual:,} 字，超过单次导入上限 100,000 字。请拆分后重新上传。`（data.limit_chars=100000 / actual_chars） |
| `parse` | `解析章节失败: {location}: {reason}`（data.format / detail） |
| （无） | `解析章节失败: 未检测到有效章节内容`（带 format_check） |
| （无） | `保存上传文件失败` |

### 2.2 start 端点
| 场景 | 文案 |
|---|---|
| 文件不存在 | `File '{filename}' not found in uploads/` |
| 无法保存历史原文 | `无法保存历史原文，请重新上传后再导入` |
| 无法读取上传文件 | `无法读取上传文件，请重新上传后再导入` |
| 解析失败 | `解析章节失败: {原因}` |
| 精品剧无场景头 | `精品剧必须包含场景头：系统没有识别到每个场景从哪里开始，请补充后重新导入。`（error_type=screenplay_format，带 format_check） |
| 非 rebuild 改类型 | `项目类型只能在重新导入时修改` |
| 无 project context | `导入需要 project context` |

### 2.3 摄入运行时错误
| 场景 | 文案 |
|---|---|
| 文件不存在 | `文件不存在: {path}` |
| 内容为空 | `小说内容为空，无法导入` |
| 精品剧无场景头 | `精品剧必须包含场景头，请补充后重新导入` |
| 缺 LLM key | `LLM API key 未设置。请在 .env 文件中添加:\n  OPENAI_API_KEY=your_key_here` |
| 图谱无节点 | `知识图谱构建失败：未生成任何图谱节点` |
| 图谱预览无节点 | `知识图谱预览生成失败：未读取到任何图谱节点` |
| graph 端点 503 | `知识图谱预览暂时不可用，请稍后重试`（Retry-After: 3） |

---

## 3. 格式检查（FormatCheck）

### 3.1 level 与 summary（build_import_format_check）
| 条件 | level | summary |
|---|---|---|
| drama 且场景头 missing | blocking | `精品剧必须包含场景头：系统没有识别到每个场景从哪里开始，请补充后重新导入。` |
| 无章节 | blocking | `未检测到有效章节或可识别正文，无法用于剧本结构化。` |
| 场景头 repairable | warning | `已识别场景边界；缺失的场景元数据将在场景规划时补齐。` |
| 有 issues | warning | `上传成功，但检测到 {n} 个格式风险，可能影响场景识别。` |
| 干净 | ok | `上传成功，剧本格式校验通过。` |

### 3.2 issue code 全集
```
missing_scene_headers（blocking 级）
not_screenplay_like / sparse_scene_headers / too_few_dialogue_lines
multi_speaker_lines / ambiguous_speakers / many_long_dialogues
scene_headers_missing_time / missing_interior_exterior / incomplete_scene_header
duplicate_chapter_number / non_increasing_chapter_number
nonstandard_scene_headers（repairable 时前置插入）
```

### 3.3 FIX_HINTS（12 条建议文案，原样还原）
- duplicate_chapter_number / scene_headers_missing_time / multi_speaker_lines / ambiguous_speakers / many_long_dialogues / missing_scene_headers / nonstandard_scene_headers / non_increasing_chapter_number / too_few_dialogue_lines / sparse_scene_headers（完整文案见 screenplay_quality.py，还原时逐字复制）

---

## 4. 判定阈值汇总

| 规则 | 阈值 |
|---|---|
| 像剧本判定 | 场景头≥2 或 对白行≥8 |
| 场景头过少 | total_scene_headers < max(1, dialogue//12)（dialogue<24 时跳过） |
| 对白过少 | dialogue_lines < 5 |
| 多说话人告警 | multi_speaker >= 3 |
| 模糊说话人告警 | ambiguous >= max(3, dialogue//5) |
| 超长对白告警 | long_dialogue >= max(3, dialogue//4)，单行 ≥40 字 |
| 超长台词定义 | dialogue_text 长度 ≥40 |
| 说话人行 | `^[^\n：:]{1,24}[：:].+$`（quality 里用 {1,20}） |
| 模糊说话人集合 | 他/她/他们/她们/对方/对面的人/男人/女人/那人/来人/某人/电话那头/电话里/声音/对面/那头 |
| 场景头标准判定 | 有 地点+显式时间（非 inferred）+内/外 |

---

## 5. 前端行为常量

| 常量 | 值 |
|---|---|
| `ACTIVE_INGEST_STATUSES` | {submitting, queued, pending, starting, running} |
| 本地缓存键 | `supertale-ingest-hidden-imported-preview:{project}` |
| toast warning 时长 | 10000ms |
| SSE 任务类型 | ingest_fast，episode=0 |
| 挂载对账 | useTasks({project, episode:0}) + isFetchedAfterMount |
| 日志格式 | `[{nn}] {log}`（nn 两位补零） |

---

## 6. 设置层选项全集

| 设置 | 值 |
|---|---|
| spine_template | drama（精品剧）/ narrated（解说剧）——**上传后锁定，切换需重新导入**（手册五章） |
| visual_style（内置） | chinese_period_drama / anime / guoman_fantasy / post_apocalyptic / realistic / republican_era_drama |
| narration_style | first_person / third_person（仅 narrated） |
| ethnicity（人种） | Chinese / Japanese / Korean / Western / Mixed —— **用于未明确设定角色时人物的默认外观方向**（手册五章） |
| legacy 默认识别 | visual_style=post_apocalyptic + narration_style=third_person + ethnicity=Japanese → 迁移为默认值 |

---

## 7. 场景头格式规范（NovelFormatDialog 写死内容）

### 7.1 标准格式（任选一种）
```
中文制片格式：
1-1 苏鸾寝殿 深夜 内
1.1 苏鸾寝殿 内 深夜

中文分字段格式：
场次：1
地点：苏鸾寝殿
时间：深夜
内外景：内

Fountain / Final Draft：
内景 苏鸾寝殿 - 深夜
INT. BEDROOM - NIGHT
```

### 7.2 可修复格式示例
```
第1集
1.1 苏鸾寝殿 内
人物：苏糖、锦绣
▲ 漆黑寝殿，烛火摇曳。
苏糖：锦绣，几更了？
```

### 7.3 6 条规则（ruleEpisode/ruleScene/ruleCharacters/ruleBody/ruleDialogue/ruleLocationChange）
每集写"第N集"；每场一个场景头（场号 地点 时间 内/外）；人物：列出出场角色；正文用 △/▲ 动作 + OS/对白；对白格式"角色（状态）：台词"；场景变化必须换场景头。

---

## 8. 硬性环境依赖
- 摄入必需：`LLM_API_KEY` 或 `OPENAI_API_KEY`（Cognee 图谱/向量阶段）
- Cognee 1.0.x 兼容（当前 1.0.5）；重复初始化 "already exists" / "UNIQUE constraint" 错误需容错
