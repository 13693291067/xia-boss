# 项目台工程细节（生图任务队列 · 已知修复 · 设置项 · 双语提示词）

> ★ 2026-09-03 P2-1 从 SKILL.md §1.4.0/§1.4.1 迁入（root 瘦身）。本文件是**工程细节懒加载源**：排查项目台问题、改队列/设置项、查修复记录时必读；SKILL.md 正文只留索引与触发词。

### 1.4.0 生图任务队列（★ 2026-08-19 固化，templates/ 内置）

**目的**：限制同时执行的生图任务数（默认上限 **5**），避免并发过多触发中转 API 报错。**后端队列 + 前端面板**双端实现，已内置在 templates/server.py 与 templates/index.html，新项目复制模板即开箱即用。

**后端（templates/server.py）**：
- `GenTaskQueue` 类：★ 2026-08-19 改**调度器模式**——`MAX_CONCURRENT=5`（同时执行）+ `MAX_QUEUED=60`（批量等待上限）、线程安全、状态机 `queued → running → success/failed`；**不持久化**（内存态，重启清空）；「任务完成」区保留最近 20 条（`DONE_KEEP`）；任务记录**保存原始垫图列表**（调度执行时重建，防丢参考图）。
- `POST /gen-image`：**入队检查**——普通请求（无 `batch`）：队列满（执行中+排队 ≥ 5）→ HTTP 429 + `{ok:false, queue_full:true}`；`batch:true`（批量生成）：上限 60 全部接收。入队后**立即返回**（`{ok:true, task_id, queued:true}`），由**调度线程 `_dispatch_loop`**（启动于 `__main__`，`object.__new__(Handler)` 实例）按并发 5 调度执行——`take_next()` 锁内预占 running 位并取最早 queued，每完成一个自动取下一个；HTTP 请求不阻塞。
- 新增端点：
  - `GET /tasks` → `{ok, running:[], done:[], stats:{running, queued, max, done_total}}`（running=排队中+执行中；done=完成区按时间序）
  - `GET /tasks/count` → `{ok, running, queued, max, done_total}`（角标用）
- 任务记录字段：`task_id / category / name / model / size / ratio(→SIZE_TO_RATIO映射) / prompt / images数(垫图数) / channel_id / ep / status / created_at / started_at / finished_at / duration / result(落盘路径) / error / hist_path`。★ **prompt 存储完整（#40 修复）**——曾存 `prompt[:80]` 且执行复用截断版，导致中转平台收到截断提示词；现 add_task 存**完整** prompt、`snapshot()`（/tasks 返回）才截 80 用于列表显示（存储/显示/执行三层分离）。任务记录含 `ep`（所属集，分集链路）。
- 完成回调：成功 → `_save_generated_image` 写盘 + mark_ready；失败 → 记录 error，不写盘。

**前端（templates/index.html）**：
- 底部 taskbar 改为**任务队列面板**：展开后**左右等分**——左侧「⏳ 任务中」（蓝点脉冲=生成中 / 灰点=排队中）、右侧「✅ 任务完成」（绿✅=成功 / 红❌=失败，含耗时与错误，保留最近 20 条），各栏独立滚动。
- **任务时间显示**（2026-08-19 增强）：每条任务显示时钟时间——排队中=提交时间（created_at）、生成中=开始时间（started_at）、任务完成=完成时间（finished_at）+ **用时**（duration，如 `45s`）；一行模式同样带时间。格式 `HH:MM:SS`（前端 `fmtClock()`）。
- **任务中元信息**（2026-08-19 增强）：任务中（queued/running）名称后追加 `size=960x1280（→3:4） 垫图数=N`（灰色小字 `.meta`）——size 与 ratio 来自后端任务记录，垫图数=images 数。
- 轮询 `GET /tasks`（1s）；一行模式显示最新状态；角标显示任务中数量，**满 5 变橙色**。
- `genSend()`：入队即返回（不再等生图完成）；收到 `queue_full` → 红色 toast「⚠️ 任务队列已满，请等待…」；入队成功后 `genWatchTask(task_id, category, name)` 每 2s 轮询，任务完成自动 `markReadyInMemory` + **无条件 `rerenderCurrent()`**（★ 2026-08-19 修复：xiatang 资产位与 **xiajing 草图/首帧位都实时刷新**，曾漏判 `curSection==="xiajing"` 导致草图/渲染图完成后不刷新）；`markReadyInMemory` 的 sketch/frame 分支 **首次生成空字段也写入新路径**（曾 `if(b[imgKey])` 拦截，首次草图只能刷新页面才出现）。
- **★ 批量生图（2026-08-19 用户确认四类通用；2026-08-20 去掉全局锁；2026-08-21 草图类目→故事板）**：`batchGenImages(cat)` 泛化批量——**故事板**（故事板 Tab「🎨 批量生成故事板图」，当前集勾选分镜 6/9 格 → 整张故事板图，prompt 由 `buildStoryPrompt` 生成，按集存 `ep.storyboard_image`）、**场景**（虾塘场景页「✨ 批量生图」，image 为空的场景）、**道具**（道具页「✨ 批量生图」，image 为空的道具）、**角色主图**（角色页「✨ 批量生主图」，image_ready 为空的角色主图；身份图批量见下一条「批量生定妆/批量生四视」）。逻辑：收集未生成项 → confirm → 循环逐个 POST `/gen-image`（`batch:true`；429 满队列等待 3s 重试最多 20 次；渠道取第一个 configured，模型取 `.name`；尺寸按类别默认：storyboard/scene=1536x768、prop=1280x960、character=960x1280，设置 default_sizes 优先）→ **★ 2026-08-20 用户拍板：去掉全局 `batchLock`——批量进行中不再拦截任何提交（单张 `genSend` / 再次批量 / 场景视角 / 上帝视角均可并行）**；`batchEnqueue` 入队成功即 `genWatchTask(task_id, cat, name, ep)` **每任务独立 watch**（完成自动 `markReadyInMemory` + `rerenderCurrent()`，互不阻塞，可并发多批量）；后端排队上限统一 60（普通/批量一致，见 #44），并发执行仍 5。任务面板任务中区显示**全部任务**（排队中=灰点 / 生成中=蓝点），一行模式文案统一「排队中」。★ 2026-08-20 分集：`batchEnqueue(..., ep)` 入队带集号，watch 完成按集应用——**批量故事板/首帧只写当前集**。
- **★ 角色页批量生定妆/批量生四视（2026-08-28 新增；★ 2026-09-02 补同步模板，见 #87）**：角色页顶部两按钮——🎭 `batchGenIdentities()`（批量生成所有角色的身份定妆照：前提=该角色主图已生成（`image_ready`，自动垫主图锁脸 `findCurrentMainImage`），逐身份检查 `image_ready`/`prompt`，不满足自动跳过并列明；prompt=各身份自身 `id.prompt`；类目 `identity`）＋ 🀄 `batchGenIdentitySheets()`（批量生成四视图卡：前提=该身份定妆照已生成（`image_ready`），检查 `sheet_ready` 已生成跳过；prompt=`IDENTITY_SHEET_PROMPT` 固定模板，垫图=该身份定妆照；类目 `character`）。两者均 confirm 列清单 → 渠道取第一个 configured，尺寸 `default_sizes.identity || 1088x1920` → 循环 `batchEnqueue` 每任务独立 watch 汇总完成数。
- 静态模式（file://）无队列，任务栏显示"无任务"。

**★ 资产图防缓存（文件名时间戳，2026-08-19 固化）**：`_save_generated_image` 生成时若已有同名主图 → **旧图归档 history/，新文件用 `{name}-{毫秒时间戳}.png`**（URL 变化，浏览器必取新图，杜绝刷新命中缓存显示旧图）；`mark_ready` 匹配逻辑**剥离一个或多个时间戳后缀**（`角色A-1787xxx.png` / `角色F-1787xxx-1787xxx.png` → 基础名 `角色A`/`角色F`，正则 `(?:-\d{13})+$`），并把 SQLite 对应 image 指向最新文件名；前端 `findHistObj`/`markReadyInMemory` 同样剥离时间戳后缀匹配（`baseNoTs`），队列完成回调传 `newPath`（后端最新路径）更新 image，避免旧路径 404。



**★ 分集（ep 贯穿全链路，2026-08-20 修复，防跨集串数据）**：分镜/首帧/视频等「跨集同名对象（shotN）」的资源必须按集隔离——曾因①后端目录硬编码 `ep001`、②mark_ready 按 beat_number **遍历所有集**匹配（ep1.beat1 与 ep2.beat1 同名都命中），导致 ep2 显示 ep1 的图。
- **规则（#39）**：凡是「跨集同名对象（shotN）」，匹配逻辑必须携带集维度——**目录按集**（`assets/ep{NNN}/…`）+ **匹配按集**（sketch/frame/blocking/firstframe/tailframe 分支 `if ep is not None and 集number != ep: continue`），只做一个会静默串数据。
- **后端**：`add_task / _execute_task / _save_generated_image / mark_ready / handle_upload` 全部带 `ep` 参数（目录 `ep{ep:03d}`）；`POST /gen-image` body 与 `/upload` query 均收 `ep`。
- **前端**：`genBtn` 出 `data-ep` → `openGenModal(cat, name, prompt, ep)` → `genState.ep` → `genSend` body 带 `ep` → `genWatchTask(taskId, cat, name, ep)` → `markReadyInMemory(category, name, hist, newPath, ep)`（按 ep 过滤匹配集）；`doUpload(input, cat, name, ep)` 上传带集号；批量用 `batchEp`（见上）。

**★ 生图弹窗·参考图（2026-08-20 改造；2026-08-21 去掉画面标注 tab）**：生图弹窗「📂 选择参考图」3 个 tab——**🎭 角色 / 📦 道具 / 🏯 场景**。
- **场景 tab**：每个场景除主图外，**已生成的多角度视角图（`s.views`）也各出一张卡片**（紫色边框 + 「多视角」标注）——可垫视角图做参考。

**★ 保存提示词（2026-08-20 用户拍板）**：生图弹窗提示词框下新增「💾 保存提示词」按钮（「↺ 恢复默认」旁）——**当前输入保存到该资产/Beat，下次打开弹窗/生成自动用修改后的版本**。
- **前端**：`savePrompt()` POST `/save-prompt` + 内存立即同步（不刷新也生效）；「恢复默认」指向保存后的新值。
- **后端 `POST /save-prompt`**：body `{category, name, prompt, ep?}` 按 category+name 匹配写 SQLite——character→`c.prompt`、identity→`id.prompt`（name 形如「角色名-身份名」）、scene→`s.prompt`、prop→`p.prompt`、firstframe/tailframe/video→shots 对应镜头提示词字段（按 ep+镜号）。
- **⚠️ 测试纪律**：对「写库端点」做端到端测试**必须用测试专用资产名（如 `_test` 后缀）**，不能拿真实资产当靶子（曾污染「<某场景名>」prompt，原值无文件留存，只能按格式重建）。

**★ 提示词中文参考（双语展示，★ 2026-09-06b 用户拍板；★ 2026-09-07 补记前端契约）**：所有资产类提示词**同轮双产**——`prompt` = 英文生图执行版（唯一进生图链路），`prompt_cn` = 中文理解稿（给用户审稿，**只读、不进生图**）。前端展示层已内置双语渲染，改任一端必须四端联动（index.html / gen.js / xiatang.js / tingfeng.js）。

- **字段契约（数据层）**：角色/场景/道具 = `prompt` + `prompt_cn`；身份图 = `prompt`/`prompt_cn`（①定妆照）+ `sheet_prompt`/`sheet_prompt_cn`（②四视图卡）；听风 = 集级 `storyboard_prompt_cn`（故事板）+ 空间拓扑图 `space_map[i].prompt_cn`。**`prompt_cn` 是元数据理解层**（与资产名/标签同级），不受"英文纯净"约束，不参与生图、不参与 check-assets 指纹。
- **弹窗（templates/index.html）**：提示词框上方 `<details id="gen-prompt-cn-wrap">`，标题固定「📝 中文参考稿（理解用 · 生图执行以下方英文为准 · 只读）」，内容区 `#gen-prompt-cn-body`（`white-space:pre-wrap`）。**无中文时整块 `display:none`**（不占空间、不显示空壳）。
- **弹窗逻辑（templates/js/gen.js）**：
  - `openGenModal(cat, name, prompt, ep, promptCn)` —— **第 5 参**为中文稿 → 存 `genState.defaultPromptCn` → 有值才 `display:""` 并写入 `#gen-prompt-cn-body`（`esc()` 转义）；无值隐藏。
  - `promptBlockDual(cn, en)` —— 卡片区双语渲染函数：**中文默认展开**（复制按钮为「复制中文」，只复制中文），**英文折叠**在「🖥 生图执行版（EN）」里；两者任一缺失自动降级为 `promptBlock()` 单语，**不报错、不留空块**。
  - `genBtn(category, name, prompt, ep, promptCn)` —— 出 `data-prompt-cn`；`document` 捕获阶段事件委托取 `btn.dataset.promptCn` 传入 `openGenModal`。**漏传第 5 参 = 弹窗没有中文参考稿（静默失效）**。
- **虾塘展示（templates/js/xiatang.js，5 类全量走双语）**：12 字段提示词 / 定妆提示词 / 身份图（①定妆照 + ②四视图卡）/ 场景提示词 / 道具参考图提示词 —— 一律 `promptBlockDual(x.prompt_cn, x.prompt)`；对应 `genBtn(..., "", x.prompt_cn)` 传第 5 参。
- **听风展示（templates/js/tingfeng.js）**：空间拓扑图卡新增「📝 拓扑图提示词（双语）」折叠块（`promptBlockDual(m.prompt_cn, m.prompt)`，无提示词时不出现）；`openGenModal("tf_space_map", …, own || TF_SPACE_MAP_GENERIC, "", (m && m.prompt_cn) || "")`；听风故事板 `openGenModal("tingfeng", …, p, "", ep.storyboard_prompt_cn || "")`。
- **★ 只读纪律**：弹窗里手改的是**英文**提示词（保存走 `/save-prompt` 写 `prompt`），**中文稿不随英文回写**（改英文不会同步改中文，卡片可标注手改状态）。要改中文稿必须改数据层 `prompt_cn` 字段本身。
- **★ 同步纪律（改一处 = 改四处）**：调 `promptBlockDual`/`gen-prompt-cn-wrap`/`openGenModal` 任一签名或 DOM id，必须同时核对 index.html + gen.js + xiatang.js + tingfeng.js，**还要回写 templates/ 并同步 `xiaji-conductor/templates/`**（2026-09-07 已对齐）；漏一边表现为"有中文不显示"或"弹窗无中文参考"。



**★ 场景切换视角（★ 2026-09-01 晚重构：任意图作参考 + 全部可重生成）**：
- **入口 = 每张图自己的 👀 按钮（蓝色圆形，右下角 .sv-sv-btn）**——主图、7 张视角图、视距/航拍产物图均有；**点谁的 👀 就以那张图为参考图**生成其他视角（任意图可作参考，不再限于主图/正面）；平面布局/线稿不放 👀（俯视布局作照片级视角参考无意义）。顶部「↔ 切换视角」按钮保留 = 无参调用，默认以主图为参考。
- **弹窗**：显示「参考图：<标签>（以当前这张图为基准生成其他视角）」（旧 主图/正面 radio 已移除，`svState.refImg/refLabel` 取代 `ref`）；7 视角多选——**已生成的视角不再禁用，全部可勾选再次生成**（2026-09-01 用户拍板；"已生成"仅灰字提示「已生成·重生成将替换」，重生成**替换旧图**、走时间戳命名防缓存）；「🚀 发送生成」→ 每视角一个生图任务（`batch:true`，name=`场景名-视角`，尺寸 1536x768 或设置 scene 默认，参考图=所选图）→ 后端 `mark_ready` scene 分支写 `s.views[视角]`/`s.views_ready[视角]`，前端 `markReadyInMemory` 同步，场景详情 `.scene-views` 展示（点击放大）。
- **「设为正面」按钮与 `setSceneAsFront` 已移除（2026-09-01 用户拍板）**：任何视角图都能用 👀 作参考，不再需要"晋升正面"机制；后端 `/scene-set-front` 端点保留未动（无前端入口）。
- **主图与正面区分（2026-08-20，继续有效）**：主图=场景基准图，正面=额外生成的正面视角，各自独立显示缩略图。
- **按钮布局（★ CSS 纪律，2026-09-01，#86）**：每张图三个绝对定位小按钮**各自独立 class/角位**——×=右上角（.sv-del-btn 红）、👁️ 视距=左下角（.sv-dist-btn 深色）、👀 切换视角=右下角（.sv-sv-btn 蓝）；**复用同一 class = 同位互盖且无报错**（曾致 👀 完全被 👁️ 盖住）。
- **build 重建保留运行时字段（#47，2026-09-01 扩展为 8 字段）**：build-data-js.py 的 scenes 组装从 SQLite 旧 xiatang 快照 merge `views/views_ready/plan/plan_ready/plan_sketch/plan_sketch_ready/dists/dists_ready`，多视角/上帝视角/视距·航拍变体在 build 重建后不丢。
- **7 条视角提示词为固定模板（用户指定，不可修改，仅机位词不同）**：
```
正面：基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成正面机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。
左侧：基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成左侧机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。
右侧：基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成右侧机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。
背面：基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，生成同一场景对向反向平视回望；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全。
斜侧：基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成斜侧机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。
俯视：基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成俯视机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。
45°俯视全景：基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，生成同一场景的45°俯视斜角全景；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全。
```
前端常量 `SCENE_VIEW_PROMPTS`（js/xiatang.js）与本文档**必须保持一致**，改动需用户确认。

**★ 视距推拉/航拍（👁️ 按钮，左下角；2026-08-22 推拉上线，★ 2026-09-01 增加航拍系 4 选项）**：场景详情每张图（主图/视角图/平面布局/线稿/视距·航拍产物图）的「👁️」→ 弹【视距】窗口 → 可多选批量生成。**选项（`VD_DISTS`，js/xiatang.js）= 前移/后移 1/2/3/5/10 米 + 航拍系 4：航拍 / 45°航拍 / 高航拍 / 45°高航拍**（航拍系浅蓝底色区分）。发送 = `batchEnqueue("scene", 场景名-源标签-选项, 固定提示词, ref=当前图)`——提示词**固定写死逐字使用**（`SCENE_VIEW_DIST_PROMPTS`，js/xiatang.js，弹窗注明不可修改）：前移/后移 10 条含 `[ORIGINAL LENS]` 镜头占位符（原样保留不替换）；航拍系中 **45°航拍 / 高航拍 / 45°高航拍为用户钦定英文逐字**（keep-all-elements 只变机位/高度），「航拍」为同句式起草版（待用户最终确认，替换时项目+模板一起改）。**落库配对（★ 成对规则，#85）**：后端 mark_ready scene 分支 dists 正则 `^(.*?)-([^-]+)-((?:前移|后移)\d+米|(?:45°)?高?航拍)$` → `s.dists[源标签|选项]`（不写 history）——**前端 gen.js `markReadyInMemory` 必须保持同一正则**（只改一边 = 完成后不落库/页面不显示）；新增带特殊字符的命名类选项时，同步检查后端 name 白名单正则（° 已允许）。产物展示在场景详情 dists 区（标签「源标签·选项」），可继续叠加视距（👁️ 链式）、可用 👀 作参考图、自动进参考图选择器与下载窗口。

**★ 上帝视角（2026-08-20 用户拍板）**：场景页「👁 上帝视角」按钮（替换原「生成 360」占位）→ 自动引用**正面/背面/45°俯视全景**三张图（图1/图2/图3）发送一个生图请求生成**平面布局**。**★ 正面兜底规则（2026-08-20 用户拍板）**：额外生成过「正面」视角用 views.正面，**否则用场景主图**（主图即正面）；必检视角仅「背面」「45°俯视全景」；**平面布局与线稿比例固定 9:16（1088x1920）**（2026-08-20 用户拍板，不随设置 default_sizes）（90°垂直正俯），该请求完成后**自动**发送第二个请求生成**线稿**（自动引用平面布局图）。两段流程串行（waitTaskDone 轮询，非并发）。生成结果：`s.plan`/`s.plan_ready`（平面布局）、`s.plan_sketch`/`s.plan_sketch_ready`（线稿），场景详情 `.scene-views` 展示（点击放大）。**2 条提示词固定模板（用户指定，不可修改）**：
```
平面布局：以图1、图2、图3为场景母版，生成同一场景的90°垂直正俯上帝视角。镜头从正上方垂直向下拍摄，呈现完整平面布局。
线稿：转成线稿
```
**★ 视角/派生图不产生历史（2026-08-20 用户拍板；2026-09-01 扩展）**：场景多视角图（正面/左侧/.../45°俯视全景）、上帝视角产物（平面布局/线稿）、视距/航拍变体图（`s.dists`）均可重复生成，但**不写入场景 history**（后端 mark_ready scene 分支与前端 markReadyInMemory 均已去掉 views/plan/plan_sketch/dists 的 history 写入）。

**调参**：改生图并发上限 → 修改 `GenTaskQueue.MAX_CONCURRENT`（后端，默认 5）即可，前端角标逻辑自动跟随（`stats.max`）；视频独立并发上限 → `GenTaskQueue.VIDEO_MAX_CONCURRENT`（默认 3，2026-08-23 新增：视频与生图共用排队上限 60，但不挤占生图并发位）；批量等待上限 → `GenTaskQueue.MAX_QUEUED`（默认 60）。

**⚙ 设置·图片默认比例（2026-08-19 固化）**：设置弹窗（渠道下方）有 5 类别默认尺寸下拉——角色主图 `960x1280`(3:4) / 身份图 `1920x1088`(16:9 四视图横版) / 场景 `1536x768`(2:1) / 道具 `1280x960`(4:3) / 草图·首帧 `1536x768`(2:1)；存 `img_config.json` 的 `default_sizes` 字段（`/gen-config` 返回，前端 `openGenModal` 按类别自动选中，可手动切换）。★ 后端保存防御：**未传 channels 时保留现有渠道**（曾因 `merge_channels(None)` 清空渠道），default_sizes 按 key 合并保存。★ **2026-09-03 用户拍板：听风故事板（tingfeng）生图默认尺寸 = 「草图·首帧」（sketch_frame）的设置值**——单张生图弹窗（`openGenModal("tingfeng",…)`，gen.js catKey 映射 tingfeng→sketch_frame）与批量生图（`tfBatchGenStory` 读 `default_sizes.sketch_frame`，兜底 1536x768）都跟随该设置；设置面板该档位标签改为「草图·首帧/听风故事板」。

**⚙ 设置·h3_dual_product（★ 2026-09-03 P2-2 新增）**：`img_config.json` 顶层字段 `h3_dual_product`（布尔，**缺省 true**=维持 2026-09-02 同步双产拍板行为）——`false` 时听风线仅产 Seedance（standalone md 单块、tingfeng.json 不写 `video_prompts.h3`），check-fidelity.py 的 ④H3 检查自动跳过；消费方：storyboard-cinematic §1.9（产出纪律）+ scripts/check-fidelity.py（`h3_enabled()`）。当前改 `project/img_config.json` 即生效，设置面板 UI 兜底后续模板接入。

**触发词**：任务队列、队列满了、生图队列、并发限制、任务面板、任务中、任务完成、队列已满、图片缓存、显示旧图、缓存问题、图片默认比例、默认尺寸、默认比例、黑白草图、草图前缀、尺寸列表、尺寸裁剪、尺寸太多、尺寸精简、中文参考稿、提示词中文、中文稿不显示、双语提示词、prompt_cn、promptBlockDual。

### 1.4.1 项目台已知修复与调试（★ 排查项目台问题时必读）

- **templates/ 已内置全部已知修复**：Agent 模块（/agent-chat 等端点 + 前端对话页）、原子写入（防渠道保存 Permission denied）、Node 脚本轮询鉴权头（http.get 漏 Authorization）、SSE 逐行透传（readline 替代 read(4096)）、前端 delta 兜底 reasoning_content、道具页历史按钮、bat 启动前清端口、server.log 日志、**任务队列（容量5+面板）**、**资产图防缓存（文件名时间戳）**、**提示词完整存储（#40）**、**分集 ep 贯穿（#39）**、**保存提示词（/save-prompt）**、**参考图 tabs（角色/道具/场景/多视角）**、**听风电影模块（★ 2026-09-01 集成：js/tingfeng.js + 侧栏「🎬 听风电影」入口 + server 类目 tingfeng/tf_space_map/space_map + mark_ready 分支与 tingfeng 落库配对 + /gen-video・/story-video-delete module 路由 + build-data-js.py tingfeng 组装 + ⚙ 分镜主力线设置）**；**★ 听风 H3 双模型提示词（2026-09-02 方案A，见 #89；★ 同日用户两轮拍板定稿为「同步双产」：分镜 Stage 2 生成每段视频提示词时同步产出 H3 六段式——一次双份、禁止事后补转化；必须严格按 `modules/storyboard-cinematic/references/quality-spec.md` 执行（storyboard-cinematic SKILL.md §1.9 两关全过才写入）；字段契约 = 每段 `video_prompt` + `video_prompts.h3` 双字段；项目台函数 `buildTfVideoPromptH3` 仅作旧数据兜底初稿非交付路径）**：`tfEnsureVP(ep, seg)` 懒装填改造——h3 槽位为空时**实时构建 `buildTfVideoPromptH3(ep, seg)` MiniMax-H3 全参考六段式**（subject_definitions / summary / retention_analysis / detailed_description / overall_soundscape / non_diegetic_music），不再复制 Seedance 文本；引用行「名字=图N」解析 → `<Subject N>`（角色=character reference sheet / 场景=scene / 空间拓扑图=spatial layout reference 空间锚点硬约束，Subject 编号=图号与 tfAutoRefs 垫图顺序对齐）；video_prompt 的【STYLE】英文风格段直接搬入 detailed_description 头部、【NEGATIVE】并入尾部 Style guardrails；逐镜用 shots 的 ts 起始做 `[Shot N] At MM:SS.mmm` 时间轴，visual/dialogue 清理混入的「- 音效/- 对白」尾巴（音效对白有独立字段不丢内容）；无 shots 兜底取 video_prompt 正文；弹窗手改后写回 h3 槽位（openTfVideoModal/tfGvStart/tfBatchGenVideo 三调用点均传 ep，批量生视频同样按当前模型取词）。
- **排查流程**：先看 `project/server.log`（启动/生图/Agent 全记录）→ 对照 `references/platform-fixes.md` 症状清单 → 直连 API 对照验证。
- **完整修复记录见 `references/platform-fixes.md`**（9 项：症状→根因→修复 + 调试方法论 + 模板同步规则）。
- **改完项目台必须回写模板**：修复验证通过后同步覆盖 `templates/server.py`、`templates/index.html`、`templates/启动项目台.bat`，并在 platform-fixes.md 追加记录；★ **2026-08-20 项目化拆分后**：前端样式在 `templates/css/main.css`、JS 在 `templates/js/`（11 文件：core/gen/agent/xiage/xialiao/xiatang/xiajing/xiaju/tingfeng/ann/init——tingfeng.js 听风工作台 2026-09-01 集成、xiaju.js 剧本工作台；**init.js 主启动必须最后加载**），改前端需 `cp -r index.html css js` 到模板（**注意：模板会被同步覆盖，大重构前先留独立完整备份，别依赖「模板同步」链路做恢复源**）；`templates/img_config.json` **默认自带 888 渠道（up_lk888，含用户 key + gpt-image-2/gpt-image-1 模型与脚本）**——新项目复制模板后**开箱即用 888 生图**，无需再配渠道；**sizes 12 个精选全尺寸**（auto/1024x1024/1024x1536/1536x1024/960x1280/1280x960/1088x1920/1920x1088/1024x1280/1280x1024/960x1920/1920x960，首位 960x1280 3:4 主图默认，2026-08-19 由 44 个裁剪）+ `default_sizes` 各类别默认比例。新增平台渠道 = 设置页添加（协议 openai/gemini/ark/up_lk888）。
- **★ 拆分事故教训（2026-08-20，见 #38）**：①单文件拆分必须内置「覆盖校验」（无缺失行/无重叠区间），第一版区间重叠导致 `batchLock` 重复声明；②css/js/index.html 拆分后，**body 骨架提取要校验关键 UI 元素齐全（sidebar/taskbar/弹窗）**——曾漏掉 body 末尾的 taskbar HTML，底部队列面板消失（`initTaskbar()` 找不到元素静默 return）；③模板被同步覆盖后不能当恢复源（曾从已覆盖的新结构模板重新切分，project/js 全毁，幸 既有项目 保留完整版才恢复）。
