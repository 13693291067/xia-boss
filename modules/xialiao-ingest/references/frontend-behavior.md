# 前端行为规格 — 虾料（ingest）页面

> 本文件定义虾料前端页面的**完整交互行为**，从零重写模式按此实现，克隆模式对照核查。
> 技术栈基线：React + TanStack Router + React Query + react-hook-form + zod + i18next + framer-motion（可等价替换，行为不变即可）。

---

## 1. 页面结构

```
虾料页（/_app/projects/$project/ingest）
├── 顶栏：鱼图标 + 标题「虾料」+ 副标题说明
├── 主体（max-w-[1080px] 居中）：
│   ├── 【未开始预览时】上传/粘贴表单区（motion.section）
│   │   ├── 上传模式：UploadZone（无文件时）/ SelectedFileCard（已选文件时）
│   │   ├── 粘贴模式：Textarea（≤1000字）+ 字数统计 + sourceHint
│   │   ├── 格式风险提示行（plain variant，仅上传模式）
│   │   └── 操作行：InputModeToggle + 项目类型Select + 视觉风格Select + 解说人称Select(仅narrated) + 族裔Select + 标准格式链接(仅drama) + 保存设置 + 开始导入
│   └── 【已开始/已导入时】预览区：
│       ├── UploadedFileCard（状态/进度/耗时/操作按钮）
│       ├── 知识图谱可视化（loading 骨架 / 图谱 / 错误重试）
│       ├── 5×StatCard（文件名/总字数/计费字数/章节数/预估集数）
│       ├── Script details（项目类型/风格/人称/族裔摘要）
│       ├── 章节表格（前20章，点击开抽屉）
│       └── 导入日志面板（编号日志 + 自动滚动）
└── 全局浮层：UploadingOverlay（上传中）/ FormatCheckDetailsDialog / NovelFormatDialog / 重导入确认 AlertDialog / 章节详情 Sheet
```

## 2. 状态定义

### 2.1 文件状态机 `IngestFileStatus`
```
uploaded → importing → completed
                   ↘ stopped
                   ↘ failed
```
- `ACTIVE_INGEST_STATUSES = {submitting, queued, pending, starting, running}`（服务端任务活跃判定）

### 2.2 输入模式 `InputMode = "upload" | "paste"`

### 2.3 上传来源 `UploadedFileSource = "upload" | "paste"`

## 3. 核心交互行为

### 3.1 上传文件（handleFile）
1. 调 `useUploadNovel`（POST upload，FormData: file + spine_template）
2. 成功 → `setUploadedFile(result.data)` + 来源 "upload" + toast「上传 ✓ — 文件名」+ 解除隐藏预览
3. **格式风险不走 toast**（SelectedFileCard 内常驻警告条），但失败走 toast.error
4. 上传期间全屏 `UploadingOverlay` 遮挡导航（防切页丢缓存）

### 3.2 粘贴文本（uploadPastedText）
1. `pastedText.trim()` 非空 → 包成 `new File([text], "pasted-novel.txt", {type:"text/plain;charset=utf-8"})`
2. 走同一上传接口；warning 格式风险用 **toast.warning（10s + 查看详情 action）**

### 3.3 开始导入（handleStartIngest / startIngestFromFilename）
1. 来源解析：upload 用 uploadedFile；paste 先 uploadPastedText
2. **blocking 拦截**：打开格式详情 + toast.error(summary)，不启动
3. 保存设置（如有变化）→ `POST ingest/start {filename, rebuild:true, spine_template}`
4. 状态 importing；`taskStream` 启用（SSE 订阅 ingest_fast, episode=0）

### 3.4 挂载对账（Mount reconcile）★关键
- 场景：用户导入中切走再回来，本地状态全重置、SSE 不重连，此时章节尚未持久化 → 页面会退回空上传页（"导入中的虾料不见了"）
- 修复：挂载时 `useTasks({project, episode:0})` 对账一次
  - 用 `isFetchedAfterMount`（只认本次挂载后新数据，防拿旧空列表误判）
  - 按 project 记账（`ingestReconciledProjectRef`），防跨项目复用残留
  - 有活跃 ingest_fast → 重开进度视图（ingestSubmitted/ingestStarted=true, status=importing）
  - 无活跃任务 → 幂等重置（防御）

### 3.5 取消导入（handleCancelIngest）
- 调 cancelTask（type=ingest_fast, project, episode=0）
- 成功 → stopped；**失败保留进度视图**（不误报停止）

### 3.6 失败重试
- 任务失败 → status=failed，允许直接用当前上传文件重试（上传是独立接口持久化的，不必重新上传）
- 失败后 refetch chapters + invalidate graph 缓存（防旧缓存把失败项目显示成"已导入"）

### 3.7 重新导入（已导入项目）
- 按钮文案「重新导入」→ 弹 AlertDialog 二次确认 → `startIngestFromFilename(source_filename, {lockSource:true})`
- `lockSource` 锁定源文件：重导入只允许原文件重试，不提供换文件/删除
- 删除只针对**未完成导入的临时上传**；已导入项目无删除按钮

### 3.8 删除文件（handleDeleteFile）
- **不复位 reimporting**（重导入流程中删文件只想换文件，复位会让类型选择器误锁）

### 3.9 设置保存（saveProjectSettings）
- 字段：spine_template / visual_style / narration_style / ethnicity
- 精品剧（非 narrated）**剥离 narration_style**（不落库，防脏值误导声线判断）
- 已导入且非重导入时剥离 spine_template（类型已锁）
- 有变化才调 updateProject（`hasIngestSettingsChanges`）

## 4. 校验与展示联动

### 4.1 resolveFormatCheckForSpineTemplate（按项目类型重算格式检查）
| 项目类型 | 场景头状态 | 结果 |
|---|---|---|
| narrated | 任意 | 过滤 missing_scene_headers/nonstandard_scene_headers 问题；剩余无问题且非 blocking → ok |
| drama | missing | **blocking**，summary「请按标准格式编写…」 |
| drama | repairable | warning「已识别场景边界；缺失元数据将在场景规划时补齐」 |
| drama | standard | 原样返回 |

### 4.2 展示联动规则
- `spineTemplateLocked = ingestStarted || (hasImportedContent && !reimporting)` → 类型 Select 禁用
- `showNarrationStyle = spine_template === "narrated"` → 解说人称仅解说剧显示
- `formatCheckBlocksImport = displayedFormatCheck.level === "blocking"`
- `canStartFromCurrentInput = (上传有文件 || 粘贴非空) && !blocking`

## 5. 缓存与持久化

| 键 | 作用 | 生命周期 |
|---|---|---|
| `supertale-ingest-hidden-imported-preview:{project}` | 记住"已隐藏已导入预览" | localStorage 持久 |
| React Query `chapterPreview(project, spine_template)` | 章节预览（上传 onSuccess 写入，preview_only:true） | 内存 + 服务端对账 |
| React Query `knowledgeGraph(project)` | 图谱快照 | staleTime 30s |
| SSE taskStream | ingest_fast 进度 | 连接期间 |

## 6. 日志面板
- 来源：SSE currentTask 去重追加（`prev[last] === currentTask` 则跳过）
- 完成时**显式补一条「完成」日志**（SSE 最终行可能被门控+覆盖竞态吞掉，不依赖它）
- 自动滚动到底（scrollTo scrollHeight）；编号格式 `[01]`、`[02]`…

## 7. 组件清单（行为即契约）
| 组件 | 关键行为 |
|---|---|
| UploadZone | 拖拽高亮、点击、键盘 Enter/空格；accept=".txt,.md,.docx" |
| UploadingOverlay | fixed inset-0 z-[1000]，aria-busy，上传中常驻 |
| FormatCheckWarning | boxed/plain 两 variant；blocking 红色底；"查看详情"按钮 |
| UploadedFileCard | 状态徽章（5色）、进度条+百分比+耗时、错误文案、格式警告、开始/停止/重传/删除 |
| SelectedFileCard | 已选文件：文件名+扩展名徽章+错误+删除 |
| InputModeToggle | upload/paste 两段切换 |
| IngestStartButton | 播放图标 + 文案 + 计费显示（CreditCostInline） |
| StatCard | label + 大数字（tnum） |
| ChapterPreviewSkeleton | 4 卡 + 表格骨架 |
| FormatCheckDetailsDialog | 问题列表：code/line 徽章/message/fix（灯泡）；blocking 红色 |
| NovelFormatDialog | 三态说明 + 格式规范 + 可修复示例 + 6 规则 + 完整示例（写死不翻译） |
| KnowledgeGraphVisualization | 力导向图 + 交互（详见 code-map.md A3） |
| IngestElapsedTime | startedAtMs 起计时 |
