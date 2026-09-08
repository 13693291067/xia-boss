# 原项目代码地图 — 虾料（ingest）功能

> 本文件是 DramaClaw 项目中「虾料」功能的**文件级代码地图**：原路径 → 职责 → 关键实现要点。
> 源码克隆模式下按此地图搬运；从零重写模式下按此对照"原项目是怎么组织的"。
> 项目根：`C:/Users/123/Desktop/AI学习资料/dramaclaw`（用户本机克隆；其它环境以实际路径为准）

---

## A. 前端（React + TanStack Router + React Query + i18n）

### A1. 主页面 — 虾料页（核心，2420 行）
**原路径**：`frontend/src/routes/_app/projects.$project/ingest.tsx`

| 行段 | 内容 | 关键实现要点 |
|---|---|---|
| 1-100 | imports + settingsSchema + SPINE_TEMPLATE_OPTIONS | zod 表单校验；项目类型仅 `drama`/`narrated` |
| 102-121 | VISUAL_STYLE_OPTIONS | 内置 6 种风格：chinese_period_drama/anime/guoman_fantasy/post_apocalyptic/realistic/republican_era_drama |
| 123-167 | chapterContentSlice / sceneBodyFromChapter / unparsedBodyFromChapter | 按行号切片取章节/场景正文（不复制内容，用 offsets） |
| 169-204 | ETHNICITY_OPTIONS + NARRATION_STYLE_OPTIONS | 族裔 5 种；解说人称 first_person/third_person |
| 185-258 | INGEST_SETTING_FIELDS / normalizeLegacyDefaults / resolveIngestSettings / hasIngestSettingsChanges | legacy 默认迁移（废土+第三人称+Japanese → 新默认）；精品剧剥离 narration_style |
| 260-287 | 类型定义 + 常量 | IngestFileStatus 5 态；ACTIVE_INGEST_STATUSES；PASTE_TEXT_MAX_LENGTH=1000；CSS class 常量 |
| 307-309 | countBillableNovelChars | 去空白计字数（前端预览用） |
| 311-371 | resolveFormatCheckForSpineTemplate | 按项目类型重算格式检查：narrated 过滤场景头问题；drama 场景头 missing→blocking、repairable→warning |
| 373-401 | hiddenImportedPreview localStorage | `supertale-ingest-hidden-imported-preview:{project}` 记住"已隐藏已导入预览" |
| 405-474 | UploadZone | 拖拽/点击/键盘；accept=".txt,.md,.docx" |
| 476-513 | UploadingOverlay | **全屏 fixed inset-0 z-[1000] 遮罩**，上传期间挡住导航（防切页丢缓存） |
| 515-585 | FormatCheckWarning | boxed（富卡片）/plain（轻量行）两 variant；blocking 红色 |
| 587-778 | UploadedFileCard | 文件卡：状态徽章/进度条/耗时/错误/格式警告/开始/停止/重传/删除按钮 |
| 780-820 | SelectedFileCard | 已选文件展示（上传模式预览） |
| 822-865 | InputModeToggle | upload/paste 切换 |
| 867-914 | IngestStartButton + IngestCreditCostSlot | 开始导入按钮 + 计费显示 |
| 916-930 | StatCard | 统计卡片（label + 大数字） |
| 932-981 | ChapterPreviewSkeleton | 加载骨架屏 |
| 985-988 | IngestPage | 路由组件壳 |
| 990-1032 | IngestPageContent 状态初始化 | 所有 useState + useForm + mutations |
| 1034-1052 | useChapters 读取 | `chaptersData.preview_only` 区分"仅上传预览"与"已正式导入" |
| 1049-1088 | 计费字数 + 生成成本 | useGenerationCreditCost("feature", "mainline.ingest_fast", {quantity}) |
| 1090-1152 | taskStream (SSE) | taskType=ingest_fast, episode=0；onComplete 显式补"完成"日志（防竞态吞行）；onError 清 chapters/graph 缓存 |
| 1154-1221 | **挂载对账 Mount reconcile** | 用 `isFetchedAfterMount` 避免拿旧缓存；按 project 记账防跨项目残留；活跃任务→重开进度视图，无任务→重置 |
| 1223-1238 | handleCancelIngest | 取消失败保留进度视图 |
| 1240-1259 | 日志收集 + 自动滚动 | SSE currentTask 去重追加；滚动到底 |
| 1262-1297 | 设置解析 + displayedFormatCheck | visualStyleOptions 优先用项目风格模板；spineTemplateLocked；showNarrationStyle |
| 1311-1323 | warnFormatCheck | warning 用 toast（10s + 查看详情按钮） |
| 1326-1348 | handleFile | 上传成功→写入 uploadedFile + toast |
| 1350-1369 | handleReplacementFile | 换文件：成功后 setReimporting(true)（保留重导入流程） |
| 1371-1389 | handleDeleteFile | 删除临时上传；**不复位 reimporting**（防止类型选择器被误锁） |
| 1391-1420 | uploadPastedText | 粘贴文本包成 pasted-novel.txt 走上传接口 |
| 1422-1455 | saveProjectSettings / handleSaveSettings | 精品剧删 narration_style；有变化才保存 |
| 1457-1499 | startIngestFromFilename | 保存设置→mutateAsync(startIngest{filename, rebuild:true, spine_template})→状态 importing |
| 1501-1524 | handleStartIngest | blocking 拦截；上传/粘贴二选一触发 |
| 1526-1539 | handleReimportExisting / handleRetryReimport | 原文件重导入（lockSource:true） |
| 1541-1604 | 派生状态 | chapters/selectedChapter/shouldShowPreview/previewFile/previewStatus/totalChars/billableChars/canStartFromCurrentInput |
| 1606-1917 | 主渲染（上传/粘贴表单区） | 动画切换、类型/风格/解说人称/族裔 4 个 Select、保存设置按钮、开始导入按钮 |
| 1918-1992 | 预览区 + 重导入确认 AlertDialog | UploadedFileCard 常驻；二次确认弹窗 |
| 1994-2047 | 图谱加载骨架/错误重试 | knowledgeGraph.isLoading/isError 分支 |
| 2049-2098 | StatCard 区 | 5 卡 |
| 2100-2149 | Script details 区 | 项目类型/视觉风格/解说人称/族裔 摘要 |
| 2151-2221 | 章节表格 | 前 20 章；drama 显示场景数；点击开抽屉 |
| 2223-2372 | 章节详情抽屉 Sheet | 精品剧：场景卡片列表（场景号/时间/内外/地点/角色/头原文/正文）+ 未解析区；小说：纯正文 |
| 2376-2400 | 日志面板 | ScrollArea h-48，编号 `[01]` 格式 |
| 2405-2413 | 两个 Dialog 挂载 | FormatCheckDetailsDialog + NovelFormatDialog |

### A2. API 封装 — `frontend/src/lib/queries/ingest.ts`（172 行）
- `useUploadNovel`：POST `api/v1/projects/{project}/ingest/upload`（FormData: file + spine_template）；成功把章节预览写入 chapters 缓存（`preview_only: true`）
- `useChapters`：GET `api/v1/projects/{project}/chapters?spine_template=`
- `useKnowledgeGraph`：GET `api/v1/projects/{project}/ingest/graph`（staleTime 30s；不随 unmount 取消，Ladybug 读不能中途断）
- `useStartIngest`：POST `api/v1/projects/{project}/ingest/start`（{filename, rebuild?, spine_template?}）

类型：`FormatCheckIssue{code,line,message,fix}`、`FormatCheck{level,summary,issues?,metrics?,scene_header_status?}`、`UploadResult{filename,size,total_chars?,billable_chars?,count?,chapters?,format_check?}`、`KnowledgeGraphNode/Edge/Snapshot{total_nodes,total_edges,truncated}`

### A3. 组件 — `frontend/src/components/ingest/`
| 文件 | 职责 | 要点 |
|---|---|---|
| `FormatCheckDetailsDialog.tsx` | 格式问题详情弹窗 | 问题列表：每条 code/line 徽章/message/fix（灯泡图标）；blocking 红色 |
| `NovelFormatDialog.tsx` | 精品剧标准格式教学 | 三种状态卡（ok/warning/blocking）+ 格式规范 pre + 可修复示例 + 6 条规则 + 完整示例（DRAMA_FORMAT_EXAMPLE 写死不翻译） |
| `KnowledgeGraphVisualization.tsx` | 知识图谱力导向可视化 | `buildKnowledgeGraphLayout`：确定性种子 + 120 步斥力/弹簧力模拟；类型着色（Entity 紫/EntityType 青/TextSummary 粉/Document 绿/DocumentChunk 琥珀）；节点大小按 degree；点击详情 + 12 条关系；缩放/拖拽/重置/全屏 |
| `IngestElapsedTime.tsx` | 导入耗时显示 | 从 startedAtMs 计时 |

---

## B. 后端（Python FastAPI）

### B1. REST 端点 — `src/novelvideo/api/routes/ingest.py`（418 行）
| 端点 | 方法 | 职责 | 关键行为 |
|---|---|---|---|
| `/projects/{project}/ingest/graph` | GET | 返回图谱快照 | novel.txt 不存在→空图；有 sidecar→直接读；legacy→加锁 materialize 一次 |
| `/projects/{project}/ingest/upload` | POST | 上传+解析+预览 | 见下方 B1.1 |
| `/projects/{project}/ingest/start` | POST | 正式摄入入队 | 见下方 B1.2 |

**B1.1 upload 端点流程**：
1. 权限 editor → staging 目录建唯一临时文件（`upload-{hex}{suffix}`）
2. `stream_to_file_with_limit`（超 512KB 删残片报 file_too_large）
3. `load_novel_text` 解析（DocumentParseError→parse 错误）
4. 计费字数超 10 万 → text_too_large
5. `build_chapter_preview(content, include_scene_blocks=spine_template!="narrated")`
6. `build_import_format_check` → format_check
7. 无章节 → "解析章节失败: 未检测到有效章节内容"（带 format_check）
8. 原子 `os.replace(staged, dest)` 落盘 `uploads/{safe_name}`

**B1.2 start 端点流程**：
1. 权限 tasks:submit + editor；文件名安全/格式/存在校验
2. legacy novel.txt 保护（历史项目只留 novel.txt 时先复制到 uploads/）
3. 大小 ≤1MB、计费字数 ≤10万
4. drama 模式 `require_scene_headers=True` 重查，blocking → `screenplay_format` 错误
5. 保存 `ingest_source_filename`；改类型仅 rebuild 时允许（同时更新 aspect_ratio）
6. `enqueue_project_task(task_type="ingest_fast", episode=0, queue_kind="default", payload={novel_path, config{rebuild,spine_template}, billing{billable_chars}})` → 返回 task_id/task_key

### B2. 章节预览 — `src/novelvideo/api/chapter_preview.py`（161 行）
- `build_chapter_preview`：ChapterDetector 切章 + 每章 number/title/start_line/end_line/content/word_count；`include_scene_blocks` 时解析场景块（header/scene_no/location/time_of_day/interior_exterior/characters/content 起止行）+ 未解析区（unparsed_content_*）
- `_build_scene_block_preview`：用行号 offsets（content_start_line/content_end_line）而非复制正文，前端按切片显示

### B3. Schema — `src/novelvideo/api/schemas.py`（121 行起）
```python
class IngestStart(BaseModel):
    filename: str
    rebuild: bool = False
    spine_template: Optional[Literal["drama", "narrated"]] = None
```

---

## C. 解析器（确定性，不依赖 AI）

### C1. 文档解析 — `src/novelvideo/utils/document_parsers.py`（139 行）
- `TEXT_NOVEL_EXTENSIONS={.txt,.md}`、`SUPPORTED_NOVEL_EXTENSIONS`+docx、`MAX_NOVEL_IMPORT_CHARS=100_000`
- `decode_novel_bytes`：UTF-8 → 失败 GBK
- `load_novel_text`：txt/md 归一 CRLF→\n；docx 走 python-docx（段落+表格，表格单元格 `\t` 连接）
- `DocumentParseError{source_format,location,reason,raw_exception}`

### C2. 上传安全 — `src/novelvideo/utils/upload_safety.py`（71 行）
- `MAX_NOVEL_UPLOAD_BYTES=512*1024`、`MAX_NOVEL_IMPORT_BYTES=1*1024*1024`
- `sanitize_upload_filename`：只留 basename、路径分隔符→`_`、拒绝 `.`/`..`
- `is_safe_upload_target`：resolve + is_relative_to 双重校验
- `stream_to_file_with_limit`：流式写，超限中断删残片抛 UploadTooLargeError

### C3. 场景头解析器 — `src/novelvideo/utils/screenplay_scene_parser.py`（636 行）
确定性正则 + 状态机，逐行解析：
- 支持格式（见 limits.md §C3）：中文制片/分字段/Fountain/插入场/国际格式/独立编号行
- `parse_scene_blocks(text) -> list[ParsedSceneBlock]`：header_line/location/time_of_day/interior_exterior/characters/lines/episode/scene_no/time_inferred
- `parse_location_line`：逗号/简单/时间+内外/尾缀提取；多地点 `/`、`、` 分隔；房间名继承建筑前缀（"李家"+"客厅"→"李家客厅"）
- `parse_character_line`：去标签、按 `、，,` 分割、括号提名字、**跳过含数字项**
- 时间词：中文 日/夜/晨/晚/午/黄昏/清晨/上午/正午/午后/下午/傍晚/夜晚/深夜/凌晨 + 十二时辰（子丑寅卯…+刻/半）+ 英文 DAY/NIGHT/MORNING/AFTERNOON/EVENING/DAWN/DUSK
- `INTERIOR_EXTERIOR={内,外}`；`ROOM_TYPES` 12 种房间用于前缀继承
- `_inherit_building_prefix`：`(.+?(?:家|公寓|楼))` 前缀 + ROOM_TYPES 组合

### C4. 章节检测器 — `src/novelvideo/cognee/chapter_detector.py`（260 行）
- `PATTERNS` 4 条：`第X章`/`第X集`（可带 `#` 标题 + `《书名》` 前缀）/`Chapter N`/`Episode N`
- 尾部形态校验 `_is_valid_title_tail`：防"第一集 已经结束。"误切
- 中文数字复合解析 `_parse_chinese_number`：十一/二十/一百零一/一千零一（CN_NUM_MAP 含大写 壹贰叁…）
- `has_chapters(min_chapters=2)`、`get_chapter_count`
- **无章节单章回退** `_prepare_fallback_content`：普通小说保原文；B档剧本用 `extract_screenplay_candidate_lines` 裁掉梗概/人物小传前言区

### C5. 格式检查 — `src/novelvideo/utils/screenplay_quality.py`（600 行）
- `assess_screenplay_scene_headers`：standard/repairable/missing 三态（须有结构证据 `_has_source_scene_header_evidence`，防散文"走到门外"误判）
- `check_screenplay_import_quality`：指标统计 + blocking/warning 判定（阈值见 limits.md §C5）
- `build_import_format_check`：汇总 issues（line-aware）+ 章节结构问题（重复/不递增序号）+ 三级 level/summary
- `extract_screenplay_candidate_lines`：从首个场景头开始；跳过 梗概/人物小传/END/编号行 前言区
- `FIX_HINTS`：12 条修复建议文案（原样还原）

---

## D. Cognee 摄入流水线

### D1. 任务 Runner — `src/novelvideo/task_backend/runners/ingest.py`（68 行）
- `register_project_task_runner("ingest_fast", run_ingest_fast)`
- 包装 `await_envelope_with_cancel_watch`（支持取消）
- `_run_ingest_fast`：CogneeStore.initialize → `ingest_novel_fast(novel_path, rebuild, spine_template, on_progress, on_log)` → close
- `update(progress, task)`：写任务进度/日志（progress=None 表示仅日志不重置进度）

### D2. 核心存储 — `src/novelvideo/cognee/store.py`（2500+ 行，ingest 相关段）
- `INGEST_PROGRESS_MILESTONES`：read 2% / prune 6% / parse 10% / parsed 25% / graph 30% / graph_validated 65% / index 70% / indexed 85% / preview 90% / preview_saved 95% / save 98% / complete 100%
- `ingest_novel_fast`（517 行起）：`ladybug_graph_access(state_dir, read_only=False)` 独占锁 → `_ingest_novel_fast_locked`：
  1. 读文件 + 非空校验 + drama 场景头校验 + **LLM key 校验**（LLM_API_KEY/OPENAI_API_KEY 缺则 ValueError 指明）
  2. rebuild：先 unlink novel.txt + delete_graph_preview + `_prune_cognee_only`（旧标志先失效）
  3. `init_cognee()` → Step1 `cognee.add(content)` → Step2 `cognee.cognify(datasets=[...])`（`_dataset_graph_has_nodes` 校验有节点否则 RuntimeError）→ Step3 `cognee.memify`（向量索引）
  4. `materialize_graph_preview`（写 sidecar，先于 novel.txt）
  5. **最后** `save_novel_content` 写 novel.txt（失败不留痕）
- `_run_cognee_pipeline_with_retry`：每阶段重试 1 次瞬时失败
- `get_graph_snapshot(max_nodes=48)`：按 degree+type_priority 排序截取，压缩属性（去 embedding/vector 字段，字符串≤500），nodes/edges/total/truncated
- `initialize`：ensure embedding binding → init_cognee → `cognee_project_context(state_dir)`（项目级上下文隔离）→ setup（"already exists" 容错）→ dataset 权限注册

### D3. 辅助模块（ingest 相关）
| 文件 | 职责 |
|---|---|
| `cognee/ladybug_access.py` | 项目图谱锁（读/写）、进程写锁、查询完成等待、上下文 patch |
| `graph_preview.py` | 图谱预览 sidecar 读写（load/write/delete/锁） |
| `cognee/screenplay_normalizer.py` | 场景头 AI 规范化（normalize_screenplay_scenes；clean_scene_name_and_time 确定性去时间粘连） |
| `cognee/script_parser.py` | 从剧本确定性解析场景列表（SceneCandidate：name/time/interior/episodes/characters/context_lines）+ 每集角色（get_episode_characters）+ 提取梗概（extract_synopsis） |
| `cognee/event_extractor.py` | 章节→事件提取（AI 规划模式用，10章→N集映射；单章 3-8 事件；失败回退整章一个事件） |
| `cognee/scene_name_migration.py` | 场景名迁移（改名/合并去重/资产路径重写/备份） |
| `cognee/pipeline.py` | 角色/剧集/场景 LLM 管线（extract_characters_from_graph / extract_episodes_with_characters / enrich_scene_environment_from_context） |

---

## E. 后端项目配置

### E1. 项目配置 — `src/novelvideo/project_config.py`
- `load_project_config_file_from_state_dir` / `save_project_config_in_state_dir`
- ingest 相关键：`spine_template`（drama/narrated）、`visual_style`、`narration_style`、`ethnicity`、`ingest_source_filename`、`aspect_ratio`
- `default_aspect_ratio_for_spine_template`：drama/narrated 各自默认宽高比

### E2. 项目上下文 — `src/novelvideo/project_context.py`
- `ProjectContext`：project_dir / output_dir / state_dir / owner_project_label / project_id
- `resolve_project_scope(project, user, required_role)`：权限解析（viewer/editor/tasks:submit）

---

## F. 数据契约（还原后必须一致）

### F1. 落盘文件
```
{project_dir}/
  uploads/{safe_name}          # 原始上传（novel.txt 例外：直接落 project_dir/novel.txt）
  novel.txt                    # 已导入标志（图谱成功后最后写）
{state_dir}/
  data.db                      # SQLite（章节/角色/剧集/道具 项目事实）
  graph-preview.json           # 图谱快照 sidecar
```

### F2. 项目配置键
`spine_template` / `visual_style` / `narration_style`（仅 narrated）/ `ethnicity` / `ingest_source_filename` / `aspect_ratio`

### F3. 章节 payload（GET /chapters 与 upload 预览共用结构）
```json
{
  "total_chars": 12345, "billable_chars": 11000, "count": 8,
  "chapters": [{
    "number": 1, "title": "第一章", "start_line": 0, "end_line": 120,
    "content": "...", "word_count": 1500,
    "scene_blocks": [{"header":"1-1 苏鸾寝殿 深夜 内","scene_no":"1","location":"苏鸾寝殿","time_of_day":"深夜","interior_exterior":"内","characters":["苏糖"],"content_start_line":3,"content_end_line":40}],
    "unparsed_content_start_line": 1, "unparsed_content_end_line": 3
  }]
}
```

### F4. 格式检查 payload
```json
{
  "level": "ok|warning|blocking",
  "summary": "上传成功，剧本格式校验通过。",
  "issues": [{"code":"missing_scene_headers","line":null,"message":"...","fix":"..."}],
  "metrics": {"non_empty_lines":100,"scene_headers":8,"dialogue_lines":30,"...":0},
  "scene_header_status": "standard|repairable|missing"
}
```

### F5. ingest/start 响应
```json
{"ok":true,"task_type":"ingest_fast","task_id":"...","task_key":"...","backend":"celery","queue":"default","message":"导入任务已进入队列: 文件名"}
```
