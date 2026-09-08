# 后端 API 规格 — 虾料（ingest）3 端点

> 定义虾料后端的完整 REST 契约。从零重写按此实现；克隆模式对照核查。
> 技术栈基线：FastAPI + pydantic + Python 3.12（可等价替换，契约与行为不变）。

---

## 1. 端点总览

| 端点 | 方法 | 权限 | 职责 |
|---|---|---|---|
| `/api/v1/projects/{project}/ingest/upload` | POST | editor | 上传 → 解析 → 预览（不落库正式数据） |
| `/api/v1/projects/{project}/ingest/start` | POST | tasks:submit + editor | 正式摄入入队（ingest_fast） |
| `/api/v1/projects/{project}/ingest/graph` | GET | viewer | 返回知识图谱快照 |

> 注意：无 `/ingest/init`、`/ingest/setup` 等其它路径；`ingest_fast` 是任务类型不是 HTTP 端点。

---

## 2. POST /ingest/upload

### 2.1 请求
- multipart/form-data：`file`（必填）+ `spine_template`（可选，drama/narrated，缺省读项目配置或 "drama"）

### 2.2 处理流程（顺序固定）
1. 权限：editor
2. 上传目录 `project_dir/uploads/`（mkdir exist_ok）
3. `sanitize_upload_filename`（防路径穿越）→ `is_safe_upload_target` 兜底 → 非法文件名返回 `{ok:false, error:"非法文件名"}`
4. 格式白名单：不支持 → `{ok:false, error:"不支持的文件类型: {suffix}，当前支持: txt、md、docx", error_type:"unsupported"}`
5. staging 文件（`uploads/.staging/upload-{hex}{suffix}`）→ `stream_to_file_with_limit`（512KB 上限）→ 超限删残片返回 `file_too_large`
6. `load_novel_text` 解析（DocumentParseError → `{error_type:"parse", format, detail}`）
7. `count_billable_novel_chars` 计费字数 > 100,000 → `text_too_large`（含 limit_chars/actual_chars）
8. `build_chapter_preview(content, include_scene_blocks=(spine_template != "narrated"))`
9. `build_import_format_check(content, has_chapters, chapters)` → format_check
10. 无章节 → `{ok:false, error:"解析章节失败: 未检测到有效章节内容", format_check}`
11. 原子落盘：`os.replace(staged, uploads/{safe_name})`
12. 成功响应见 2.3

### 2.3 成功响应
```json
{
  "ok": true,
  "data": {
    "filename": "novel.txt",
    "size": 123456,
    "total_chars": 12345,
    "billable_chars": 11000,
    "count": 8,
    "chapters": [ { "number":1, "title":"...", "start_line":0, "end_line":120, "content":"...", "word_count":1500, "scene_blocks":[...], "unparsed_content_start_line":1, "unparsed_content_end_line":3 } ],
    "format_check": { "level":"ok|warning|blocking", "summary":"...", "issues":[...], "metrics":{...}, "scene_header_status":"standard|repairable|missing" }
  }
}
```

### 2.4 错误响应（全部 ok:false + error_type）
| error_type | 触发 | error 文案 |
|---|---|---|
| 缺省 | 非法文件名 | `非法文件名` |
| `unsupported` | 格式不支持 | `不支持的文件类型: {suffix}，当前支持: txt、md、docx` |
| `file_too_large` | >512KB | `文件超过 512KB 上限，请压缩文件或拆分正文后重新上传。`（data.limit_bytes） |
| `text_too_large` | >100,000 计费字数 | `正文共 {actual:,} 字，超过单次导入上限 100,000 字。请拆分后重新上传。`（data.limit_chars/actual_chars） |
| `parse` | 解析失败 | `解析章节失败: {原因}`（format/detail） |
| 缺省 | 无章节 | `解析章节失败: 未检测到有效章节内容`（带 format_check） |
| 缺省 | 保存失败 | `保存上传文件失败` |

---

## 3. POST /ingest/start

### 3.1 请求体（IngestStart）
```json
{ "filename": "novel.txt", "rebuild": false, "spine_template": "drama" }
```
- `spine_template` 可为 null → 读项目配置或默认 drama；narrated 之外一律归一 drama

### 3.2 处理流程
1. 权限：tasks:submit（require_scope）+ editor
2. 文件名安全/格式/存在性校验（同 upload）
3. **历史项目保护**：`uploads/` 无此文件但 `project_dir/novel.txt` 存在且文件名是 novel.txt → 先 copy2 到 uploads/（保证可重试）
4. 文件 ≤1MB（`MAX_NOVEL_IMPORT_BYTES`）→ 超限 `file_too_large`
5. 解析 + 计费字数 ≤100,000
6. **drama 模式** `build_import_format_check(require_scene_headers=True)` → blocking 返回：
```json
{ "ok":false, "error":"精品剧必须包含场景头：系统没有识别到每个场景从哪里开始，请补充后重新导入。", "error_type":"screenplay_format", "format_check":{...} }
```
7. 项目配置：保存 `ingest_source_filename`；`spine_template` 非 null 时（仅 rebuild 允许）同步更新 spine_template + aspect_ratio；**非 rebuild 改类型 → `{ok:false, error:"项目类型只能在重新导入时修改"}`**
8. 入队 `enqueue_project_task`（task_type="ingest_fast", episode=0, queue_kind="default", product_surface="mainline", payload 含 novel_path/config/billing）

### 3.3 成功响应
```json
{ "ok":true, "task_type":"ingest_fast", "task_id":"...", "task_key":"...", "backend":"celery", "queue":"default", "message":"导入任务已进入队列: {filename}" }
```

### 3.4 错误码
| 错误 | error 文案 |
|---|---|
| 文件不存在 | `File '{filename}' not found in uploads/` |
| 无法保存历史原文 | `无法保存历史原文，请重新上传后再导入` |
| 无法读取上传文件 | `无法读取上传文件，请重新上传后再导入` |
| 解析失败 | `解析章节失败: {原因}` |
| 类型修改受限 | `项目类型只能在重新导入时修改` |
| 无 project context | `导入需要 project context` |

---

## 4. GET /ingest/graph

### 4.1 行为
1. 权限：viewer
2. `{project_dir}/novel.txt` 不存在（未导入/已重建）→ 返回 `empty_graph_preview()`
3. 有 `graph-preview.json` sidecar → 直接读（正常路径，不打开 Ladybug）
4. 无 sidecar（legacy 项目）→ `ladybug_graph_access(read_only=True)` 锁内 materialize 一次（跨进程锁；请求取消也要等 cleanup 完成）；失败 → 503 `知识图谱预览暂时不可用，请稍后重试`（Retry-After: 3）

### 4.2 成功响应
```json
{ "ok":true, "data": {
  "nodes": [{"id":"...","label":"...","type":"Entity|EntityType|TextSummary|Document|DocumentChunk|...","degree":5,"properties":{...}}],
  "edges": [{"id":"src:tgt:0","source":"...","target":"...","relation":"...","properties":{...}}],
  "total_nodes": 120, "total_edges": 340, "truncated": true
}}
```

### 4.3 空图响应
```json
{ "ok":true, "data": {"nodes":[],"edges":[],"total_nodes":0,"total_edges":0,"truncated":false} }
```

---

## 5. 补充端点（页面依赖，非 ingest 专属但必须提供）
- `GET /api/v1/projects/{project}/chapters?spine_template=` — 章节列表（预览/导入完成判定依据：`chapters.length>0` 即"有内容"）
- `GET /api/v1/projects/{project}` — 项目配置（spine_template/visual_style/narration_style/ethnicity）
- `PATCH/PUT /api/v1/projects/{project}` — 保存设置
- `GET /api/v1/projects/{project}/tasks?episode=0` — 任务列表（挂载对账用）
- `POST /api/v1/tasks/{task}/cancel` 或等价 — 取消 ingest_fast
- 生成成本：`GET /api/v1/generation-credit-cost?feature=mainline.ingest_fast&quantity=N` — 计费显示（可降级为不显示）

## 6. 权限模型
- viewer：可读（graph/chapters）
- editor：可写（upload/start/项目配置）
- tasks:submit：可提交任务（start）
