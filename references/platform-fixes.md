# 虾集项目台 · 已知问题与修复记录（2026-08-18 固化）

> 适用对象：`templates/server.py` + `templates/index.html` + `templates/启动项目台.bat` 生成的虾集项目台。
> 这些修复已全部合入模板；遇到下述症状时先对照排查，避免重复踩坑。
> 排查顺序建议：先查 `project/server.log`（模板已内置日志），再看本清单。

---

## 修复清单（症状 → 根因 → 修复）

### 1. 生图「平台已完成，页面一直生成/等待」—— Node 脚本轮询漏鉴权头

- **症状**：模型配置了自定义脚本（img_config.json 的 model.script）时，lk888 平台任务早已 success，项目台轮询 600s 超时，前端一直"生成中"。
- **根因**：`WRAPPER_JS_TEMPLATE` 里 `http.get()` 的 `fetch(url, Object.assign({method:'GET'}, opts))` **漏传 `headers`（Authorization）**；`http.post()` 有传。无鉴权时 `/media/status` 响应里 `state/is_final` 全为 undefined → `d?.is_final === true` 永不成立 → 空转至 timeoutMs。
- **修复**：`http.get` 改为 `fetch(url, Object.assign({method:'GET', headers}, opts))`。
- **验证要点**：日志出现 `🖼 生图走模型脚本` 后，`✅ 生图脚本完成` 应在几十秒~3 分钟内出现；若卡满 600s 即此 bug。

### 2. 生图慢（gpt-image-2 high 约 3 分钟）与等待提示

- **事实**：quality 参数影响耗时——`low/auto`≈40s，`high`≈179s。脚本默认 `auto`，Python 轮询分支写死 `high`。
- **处理**：非 bug，但前端等待提示应注明"高画质约需 2-3 分钟"；不要误判为卡死。

### 3. Agent 流式（stream=true）页面收不到任何内容

- **症状**：`/agent-chat` 请求 200、SSE 已透传（日志 `🤖 Agent 流式完成`），但前端 0 内容。
- **根因**：后端透传用 `upstream.read(4096)`——urllib 的 `read(n)` 等**凑满 n 字节或 EOF**才返回；lk888 生成完不立即关连接 → 永久阻塞。
- **修复**：SSE 是行格式，改 `readline()` 逐行透传（读到 `\n` 即返回），`self.wfile.write(line); flush()`。
- **验证**：curl `-N` 流式应能实时收到 `data:` 行并以 `data: [DONE]` 结束。

### 4. Agent 流式页面只有打字点、无内容—— delta 取法漏 reasoning_content

- **症状**：deepseek-v4-flash 深度思考时 `delta.content` 常为空（内容在 `delta.reasoning_content`），前端只取 `content` → `asstMsg.content` 一直空 → 永远显示三个点。
- **修复**：前端 delta 取法兜底三个字段：`delta.content || delta.reasoning_content || choice.message?.content`。
- **后续优化**（可选）：把 reasoning_content 用灰色小字单独展示在正文上方，与正式回复区分。

### 5. Agent 发消息后页面消息被冲掉 / 提示未配置渠道

- **症状**：发消息后立即 rerender，刚 push 的消息消失（页面空白/回到旧对话）。
- **根因**：`agentSend` push 消息后调用 `rerenderCurrent()`，而 `renderAgent()` 第一行 `_agentLoad()` 会**从 localStorage 重读对话覆盖内存**——push 后未先 `_agentSave()`，新消息丢失。
- **修复**：push 后**立即 `_agentSave()`** 再重绘。
- **附带**：发送前 `if(!agentState.cfg) await _agentLoadCfg()`，修复首屏秒发消息时的配置竞态（误报"未配置渠道"）。

### 6. 渠道设置保存报 Permission denied（Windows 瞬时文件锁）

- **症状**：⚙ 设置保存渠道时 `Permission denied`，但文件 ACL 正常、手动可写。
- **根因**：Windows 下文件被其他程序短暂独占（用户开着的编辑器/OneDrive/Defender 扫描）；裸 `open(path,'w')` 一锁即败。
- **修复**：统一走 `atomic_write_json()`——先写 `<path>.tmp` 再 `os.replace`，3 次重试（0.4s 递增），免疫瞬时锁；用于 img_config/agent_config 的全部保存点。
- **防覆盖保险**：`handle_gen_config_save` 若 `img_config.json` 存在但读取失败（channels 为空），**返回 409 拒绝保存**，避免拿默认配置静默清空用户 key。

### 7. 项目台重启无效 / 旧版代码在跑 / 日志时灵时不灵

- **症状**：改了 server.py 重启后行为不变；多个 python 进程残留；请求被分到旧进程。
- **根因**：旧 server 进程占着端口，新进程绑定失败静默退出；Windows 上同端口可能多个 LISTENING。
- **修复**：`启动项目台.bat` 启动前先 `netstat` 找 8317 的 LISTENING PID 并 `taskkill /F`，再启动。
- **清理**：`Get-CimInstance Win32_Process -Filter "Name='python.exe'"` 按 CommandLine 含 `server.py` 批量 Stop-Process。

### 8. 道具页不显示历史图片按钮

- **症状**：角色/场景/虾镜都有"🕘 历史"按钮，道具没有。
- **根因**：`renderPropGrid` 的 `prop-actions` 漏调 `histWidget("prop", ...)`（其他页面都调了）。
- **修复**：补上 `histWidget` 调用。注意：`histWidget` 只在 `obj.history` 非空时显示按钮（设计如此）。

### 9. 日志能力（模板内置）

- `server.log`（项目目录下）+ CMD 窗口 stderr 双写，`log(msg)` 函数；关键事件：启动、每个 POST 路由、生图建任务/脚本进出/成功失败/超时、Agent 调用/流式完成。排查一切项目台问题先看它。

---

## 调试方法论（快速定位）

1. **先看 `project/server.log`**：能区分是「请求没到」「建任务失败」「轮询空转」「下载/写盘失败」。
2. **分清生图走哪条路**：模型配了 `script` → 走 Node 沙箱（`_run_model_script`）；没配 → 走 Python 轮询分支。两条路问题不同。
3. **直连 API 对照**：用 Python urllib 直连 lk888（建任务→轮询→下载）验证平台侧正常，再对比项目台路径，差异即 bug 所在。
4. **端口与进程**：改代码后重启必须确认旧进程已死（bat 已自动清）；测试完用 PowerShell 批量清 `server.py` 进程。
5. **Git Bash 的坑**：`/tmp` 与 Windows Python 的 `/tmp` 不同（node/python 找不到文件）；后台 `&` 启动会让 bash `cd` 不生效——**一律用绝对路径**。
6. **测试不烧用户额度**：生图测试每次消耗 lk888 余额（约 0.05/次），测试前确认余额充足；测试完清理 assets 下测试文件。

---

## 模板同步规则（★ 改完项目台必须回写模板）

改 `project/server.py` / `project/index.html` / `启动项目台.bat` 时，修复验证通过后**同步覆盖** `skills/xia-boss/templates/` 对应文件（templates 是生成新项目台的唯一来源），并在此文档追加记录。模板 `img_config.json` 保持**无 API key**（空占位），禁止覆盖成带 key 的版本。

---

## 10. build-data-js.py 跨项目兼容性修复（2026-08-18 追加）

在 A 项目重建 data.js 时发现脚本存在多处硬编码/不兼容,已修复(跨项目通用):

| 问题 | 修复 |
|---|---|
| `meta.name`/`project_id` 硬编码为某旧项目("旧项目名…") | 改从 `pipeline-state.json` 读 `title`/`project`,兜底用目录名 |
| 风格文件硬编码 `chinese_period_drama.json` | 改为自动扫描 `outputs/styles/*.json` 取第一个 |
| 风格字段硬编码 `id`/`label` | 兼容 `style_id`/`style_label` 两种命名 |
| 场景 header 用 `s['episode']-s['scene']` | 改为 `s.get("header")` 优先(assets-registry 直接带 header) |
| `registry["props_merged_into_characters"]` 硬索引 | 改 `.get(..., [])` 兜底 |
| 角色提示词匹配只认 `1.1 名称`(双数字) | 兼容 `1. 名称`(单数字):`re.match(r"^\d+\.\d*\s*", ...)` |
| Beat 草图/首帧只从 5zone md 解析 | 改为 `b.get("sketch_prompt") or md解析`,beats.json 直带字段优先 |

**教训**:build-data-js.py 是跨项目复用的,任何"从老项目复制"留下的硬编码(项目名/风格名/字段名)都会在新项目爆炸。改脚本时必须用 `.get()` + 自动检测,禁止硬编码具体项目/风格/字段。

---

## 11. 生图"平台没收到请求"——名称校验正则拒绝括号（2026-08-18 追加）

- **症状**：点击生成后弹窗显示"已提交"，但 lk888 平台从未收到请求；server.log 只有"收到生图请求"，无"生图走模型脚本/建任务"。
- **根因**：`handle_gen_image` 名称校验正则 `^[\u4e00-\u9fff\w·\-]+$` 不允许括号，带括号角色名(如"角色A(别名)")被 400 拦截(error: 非法名称)。无括号项目不会暴露此问题。
- **修复**：正则改为 `^[\u4e00-\u9fff\w·\-（）()]+$`（允许全角/半角括号；仍禁止 / \ 等路径非法字符）。
- **调试要点**：请求是否到达 lk888 看 server.log——有"🖼 生图走模型脚本"才算进入转发；只有"收到生图请求"说明在参数校验被拦。

---

## 12. 项目数据污染清理（2026-08-18 架构级，★ 最高纪律）

**背景**：某旧项目世界观页面混入另一项目内容，排查发现是**模板/脚本残留项目数据**导致，非数据源问题。

**清理清单**（skill 内全部清零，复扫无残留）：
1. `build-data-js.py`：删掉硬编码的 10 个角色 meta（角色A/角色B/角色D等），改从项目 `assets-registry.json` 动态读取 role/desc/identity。
2. `templates/index.html`：世界观渲染函数 `renderWorldView` 从"项目专属硬编码版"重写为**数据驱动通用版**（世界格局/环境/时间线/力量体系/势力/物产/矛盾/机制/规则全部动态渲染，无任何世界观专属词）；Agent 示例消息去项目角色名。
3. `SKILL.md`：示例路径用 `<用户名>/<项目名>` 占位。
4. `templates/server.py` / `templates/index.html` 注释示例名用"角色A"占位。
5. `references/platform-fixes.md`：修复记录中的项目名改为"某旧项目/角色A"。

**固化纪律（SKILL.md 最高纪律章节，优先级最高）**：
- skill/模板/脚本/references 禁止出现任何项目数据；数据只进项目目录；
- 生成脚本零硬编码、渲染层数据驱动；复制即清理；每模块 grep 验收自查；
- 偷懒造成的污染 = 最高级别事故。

**教训**：从老项目复制模板到 skill 时必须全文清理项目残留，否则每个新项目都会带前一个项目的世界观/角色。

---

## 13. 多 server 并存导致"CMD 不显示 log"(2026-08-19 追加)

- **症状**：CMD 不显示新 log、页面行为错乱(请求打到别的实例)。
- **根因**：8317 端口同时有 2+ 个 server 进程(测试实例残留 + 用户 bat 启动),Windows 随机分发请求。
- **排查**：`netstat -ano | findstr :8317` 出现多个 LISTENING = 多实例。
- **纪律**：排查时测试实例**用完立即杀掉**,绝不占用 8317;用户遇到"CMD 没 log"第一动作查端口多实例。

## 14. build-data-js.py / 前端插入"条件静默跳过"教训(2026-08-19)

- **症状**：Agent 按钮点击 `ReferenceError: toggleAgentDrawer is not defined`;CSS 缺失导致布局错乱。
- **根因**：批量插入脚本用 `if 锚点 in txt and 新内容 not in txt` 条件,条件不满足时**静默跳过**,但日志仍打印"成功"(print 在 if 外),造成"以为插入了实际没有"。
- **纪律**：①插入类修改用**无条件插入 + 事后 grep 验证**(验证函数/CSS 确实存在);②print 成功必须与插入动作绑定在 if 内。

## 15. build-data-js.py 场景提示词误匹配角色段(2026-08-19)

- **症状**：黑市场景提示词错配成"老李(黑市商人)"的定妆照提示词。
- **根因**：场景匹配用 `场景名 in 标题`,"黑市"出现在角色标题"老李(黑市商人·经济线搭档)"且排在场景段前。
- **修复**：优先匹配场景段格式标题(`标题=场景名开头 且 含·`,如"黑市(黑市·夜·内景)"),找不到再 fallback。

## 16. 数据架构:data.js → SQLite 唯一数据源(2026-08-19)

- 移除 data.js,前端经 `GET /api/data` 从 SQLite(xiaji.db)加载;build-data-js.py 直写 SQLite(snapshots 表,JSON 原样)。
- 数据流:outputs/ → build-data-js.py → xiaji.db → /api/data → 前端。
- handoff 只接受 .json(旧格式 handoff-xiage.md 会导致 JSONDecodeError,已修)。
- 静态模式(file://)无法读库 → 前端提示"需服务模式"。

---

## 17. SQLite 数据源同步缺口排查(2026-08-19)

- **症状**：页面生图/上传/虾格保存后,刷新数据不对(生图后列表无图;虾格保存新风格前端看不到)。
- **根因**：切 SQLite 后部分写操作仍走旧链路——`mark_ready` 读已删除的 data.js(直接 return,SQLite 从不更新);虾格保存/确认只写文件不更新 SQLite 的 xiage 模块;`/styles/confirm` 的 pipeline-state 路径误用 ROOT(应为 PROJECT_ROOT)。
- **修复**：①mark_ready 改 db_read_all→标记→db_upsert(xiatang/xiajing);②新增 db_sync_xiage()(从 outputs/styles/ 重组 xiage 写回),styles/save 与 confirm 成功后调用;③confirm 路径改 PROJECT_ROOT。
- **教训**：数据源切换后必须全局排查所有写操作链路(生图/上传/回滚/虾格),不能只改读取端。

## 18. xiaji.db 位置规范(2026-08-19)

- **位置**：`project/xiaji.db`(与 server.py/index.html 同级),不放项目根。
- **改两处**：server.py `DB_PATH=os.path.join(ROOT,"xiaji.db")`;build-data-js.py 直写 `os.path.join(BASE,"project","xiaji.db")`。

---

## 19. API 插槽架构:api_slot.py(2026-08-19)

- **需求**：把 server.py 里 API 设置与 API 调用抽成独立 py,用插槽方式(可插拔)。
- **api_slot.py**(与 server.py 同级,不依赖 server.py,自带 log/ROOT):常量、配置读写(load/save img&agent config、merge_channels、渠道工具)、生图调用 generate_image(4 协议+Node 自定义脚本,返回 (img_bytes, err, meta))、Agent 调用 agent_chat_completion(返回 (ok, resp) 含 body 或 stream 上游连接)、测试(test_img_channel/fetch_models/test_agent_channel,错误带 status)。
- **server.py**：import api_slot as slot;全部 API 细节删除,handler 改调 slot.xxx(33 处);生图保存/SSE 转发仍在 server。
- **踩坑**：①大段 old→new 替换易因细微字符差异失败→改用区间截断(锚点定位);②new 字符串里的 \n 会被三引号解释为换行→注释里写 \n 要转义;③测试时假 channel_id 会 fallback 到真实渠道触发真实调用→用单元级验证(无 key 渠道)代替,不消耗 API 额度。
- 同步：模板 templates/server.py + api_slot.py + 既有项目 + 既有项目。

---

## 20. 身份图锁脸铁律(2026-08-19)

- **痛点**:角色资产里"主图和身份图不是同一个人"——AI 生图每次随机出新角色,身份图不用主图作 ref 就自然不一致。
- **三层纪律**:
  - **xiatang-characters** 新增「身份图锁脸铁律」:身份图 prompt 必须含 `same face as the reference image, identical facial features, only change outfit/accessories/environment/pose, NOT face` 等锁脸指令;生成时主图作为 ref 必传。
  - **xia-boss** 纪律第 12 条:身份图与主图必须同一张脸;主图必须作为 images[0] 传入。
  - **build-data-js.py** `_ensure_lock_face(prompt)`:自动给身份图 prompt 追加锁脸指令(已含则跳过);29 处身份图全量回填 11/11 + 18/18。
  - **前端 genSend**:身份图自动读取 `assets/characters/<角色名>.png` 作 ref(images[0]);`fetchMainRefAsDataUrl()` 读图 → 转 base64;自动垫图,用户零操作。
- **生成结果**:身份图与主图同一张脸(模特基底/骨骼/五官继承),只变换造型与场景,整套角色资产"长得像同一个人"。
- 同步:两个 skill 文档 + templates + 既有项目 + 既有项目 全套。

---

## 21. 主图 3:4 + 身份图左特写右三视图(2026-08-19)

- **用户规范变更**:
  - 主图比例从 1:1 → **3:4 竖版面部特写**(3:4 vertical portrait, facial close-up, head-and-shoulders, 85mm f/1.8)。
  - 身份图结构:从"四视图"→ **左=面部特写肖像 + 右=全身三视图(正面/侧面/背面)摄影图**(character reference sheet: left side close-up facial portrait, right side full body three-view turnaround: front view / side profile / back view)。
- **回填**:既有项目 主图 10/10、身份图 11/11;既有项目 主图 13/13、身份图 18/18(three-view 恢复)。
- **默认尺寸**:DEFAULT_SIZES + GEN_DEFAULT_SIZES + img_config.json 的 sizes 均把 960x1280(3:4)放首位(gen-size 弹窗默认选中第一项)→ 主图/身份图生成默认 3:4。
- 同步:templates(api_slot.py/index.html/img_config.json)+ 两项目。

---

## 22. 主图 = 证件照式标准像(2026-08-19)

- **用户拍板**:主图不是"面部特写肖像"而是要**证件照(ID/passport style)**——正面居中/中性表情/纯色背景/均匀棚拍光/无姿态动作(禁叉腰/举手/侧身/手持道具/戏感表情),3:4 竖版,85mm f/1.8。
- **skill**:xiatang-characters 主图规范改为证件照式;xia-boss 纪律第 11 条同步。
- **回填**:既有项目 主图 10/10、既有项目 13/13 全部证件照化(去姿态/戏感表情、背景纯色、灯光均匀);共 100+ 处替换;身份图段相同文本也被同步修正(合理)。
- 教训:主图曾写"叉腰/市侩笑意/戏剧侧光"——证件照语义完全不同,写提示词前先确认画幅类型。

---

## 23. 主图证件照:肩以上构图 + 禁腰下细节 + 负面词(2026-08-19)

- **用户追加要求**:证件照主图 ①画面只到**肩膀上沿**(正面肩以上头像构图,不露肩/锁骨/手臂/胸部,衣领自然覆盖肩颈);②**禁写腰以下细节**(腰带/腰佩/腰间挂件/护腕/手持道具等——证件照看不到,写了会带偏构图成半身/胸像);③负面词加 `露肩，露锁骨，短袖，手臂入镜，胸部入镜，半身构图，胸像构图`。
- **skill**:xiatang-characters 证件照规范细化(构图硬性要求 + 禁腰下细节 + 负面词必含)。
- **回填**:既有项目 主图 10/10(删窄袖/腰束织带/古玉腰佩/腰间算盘/护腕/腰悬长剑/魔气/手部等;角色F角色G原缺中文收尾镜头句,已补构图+镜头+负面词);既有项目 13/13(删鞋尖磨破/scuffed shoes/腰间别刀/医疗包/frayed cuffs;英文段加 head-and-shoulders composition + frame ends above shoulders + 负面词)。
- **注意**:身份图段(三视图全身)的服装细节必须保留(护腕/战痕/腰剑/储物袋等是全身造型有效信息)——回填时限定主图段范围,身份图段误删的已恢复。
- 教训:主图与身份图共用角色描述文本时,替换必须按段落限定范围。

---

## 24. set-current 必须换文件名(历史图应用为当前,2026-08-19)

- **症状**:历史图设为当前,提示成功,刷新又变回旧图。
- **根因**:set-current 把历史图"覆盖复制"到 `{name}.png`(文件名不变)→ 浏览器缓存同一 URL 旧图 → 刷新显示旧图。
- **修复**:
  - server.py:历史图应用为**新文件名 `{base}-<毫秒时间戳>.png`**;mark_ready 加 `rename_to` 更新 SQLite image;路径统一正斜杠。
  - build-data-js.py 加 `latest_versioned(rel_dir, base_name)`:扫描 `assets/` 下 `{name}-<数字>.png` 最新版本作为当前图 → **重建 SQLite 不丢 set-current 的新文件名**。
  - 前端 setCurrent:image 直接用后端返回的 `j.path`(新文件名)。
- **教训**:凡"图片内容替换但 URL 不变"的操作必然踩浏览器缓存;换文件名(带时间戳)是标准解法。

## 25. Node 沙箱脚本不走系统代理(2026-08-19)

- **症状**:走模型脚本生图报 `TypeError: fetch failed` / `Client network socket disconnected before secure TLS connection was established`;Python urllib 也 SSL UNEXPECTED_EOF。
- **根因**:①Node(undici)fetch **不读系统代理环境变量**,直连被墙/受限平台 → TLS 断;②Python urllib 只认**小写** http_proxy/https_proxy 环境变量,大写的 HTTP_PROXY/HTTPS_PROXY 不一定生效(Windows 更多读注册表代理)。
- **排查顺序**:DNS(nslookup)→ 直连(curl --noproxy *)→ 显式代理(curl -x http://127.0.0.1:7892)→ 对比已知可用平台(lk888 401 = 代理正常)。平台直连和代理都 000/TLS 断 = **平台侧不可达**,不是代码问题。
- **对策**:需要代理的平台优先走**内置协议分支**(Python urllib),别配模型脚本;或给 Node 沙箱显式注入代理 dispatcher。
- **平台排查案例**:n.conai.com(OpenAI 兼容)在直连+代理下均 TLS 断 → 平台当前不可用,先用 888。

---

## 26. 模型脚本分支垫图必须传 data URI,不能传纯 base64(2026-08-19)

- **症状**:888 渠道图生图报 `未返回 task_id: {"code":400,"msg":"image 参数格式错误:第1个元素 'iVBORw0KGgo...'"}`。
- **根因**:api_slot.generate_image 的脚本分支调 `_run_model_script(channel, model, prompt, image_b64s, size)` 传了**纯 base64**;而 lk888 平台的 params.images 要求 **data URI(`data:image/...;base64,...`)或 URL**;内置 lk888 分支一直用 image_datauris(正确),脚本分支用错参数。
- **修复**:脚本分支改传 `image_datauris`;脚本如需纯 base64 自行 `split(";base64,",1)[1]`。
- **教训**:server.handle_gen_image 里裸 base64 → data URI 的前缀补充只在 image_datauris;凡"透传给平台"的参数一律用 data URI/URL,纯 base64 只给 gemini inline_data / openai edits 解码用。

## 27. 草图/首帧生图完成后不实时刷新资产位(2026-08-19)

- **症状**:草图、渲染图(首帧)生图任务完成后,卡片图片不出现,刷新页面才显示。
- **根因**(两处叠加):①`genWatchTask` 完成回调 `if(curSection==="xiatang") rerenderCurrent()`——草图/首帧在 **xiajing** 页面生成,从不触发重渲染;②`markReadyInMemory` sketch/frame 分支 `if(imgKey && b[imgKey])`——**首次生成**时 sketch_image 为空(假值),新路径不写入内存。
- **修复**:完成回调改**无条件 `rerenderCurrent()`**(函数内按 curSection 分发);sketch/frame 分支改 `if(imgKey)` 无条件写入(`setImg` 用后端 newPath)。
- **教训**:前端"完成回调→内存标记→重渲染"链路,任何一环带条件判断都可能漏掉某个页面;完成回调尽量无条件触发,匹配逻辑才做条件。

## 28. ⚙ 设置·图片默认比例(default_sizes)(2026-08-19)

- **功能**:设置弹窗新增 5 类别默认尺寸下拉(角色主图3:4/身份图16:9/场景2:1/道具4:3/草图·首帧2:1),存 `img_config.json.default_sizes`;`/gen-config` 返回,前端 `openGenModal` 按类别自动选中(可手动切换)。
- **实现**:后端 `handle_gen_config` 返回 default_sizes、`handle_gen_config_save` 按 key **合并保存**;前端 `CAT_DEFAULT_SIZE` 读取 `genState.defaultSizes`(sketch/frame 查 `sketch_frame` 键)。
- **★ 顺带修复 merge_channels 清空渠道 bug**:保存时 `patch.get("channels") is None` → **保留现有渠道**(曾因只传 default_sizes 不传 channels,`merge_channels(None)` 返回空列表把渠道覆盖清空,既有项目 渠道一度丢失,从模板 img_config.json 恢复)。

## 29. 尺寸列表裁剪 44 → 12(2026-08-19)

- **功能**:img_config.json 的 sizes 从 44 个裁剪为 12 个精选(见 SKILL.md §1.4.1),既有项目/模板同步;img_config.json 改动服务即时重读,无需重启。
- **注意**:`ratio_of` 动态 gcd 计算兼容任意尺寸,裁剪不影响后端映射。

## 30. 草图前缀统一「黑白草图」(2026-08-19)

- **功能**:草图提示词前缀「黑白分镜草图」→「黑白草图」(用户拍板),全量替换:beats.json 67 条 + SQLite + 交付 md + 构建脚本 + skill 文档。
- **注意**:grep 二进制 xiaji.db 仍能搜到旧词 = SQLite 旧数据页物理残留,逻辑数据已替换,不影响功能。

## 31. 新资产无图点生成报「category/name/prompt 缺失」(2026-08-19)

- **症状**:新增资产(如「多角色群像」群像)未生成图时,点「✨ 生成」→ 后端 400 `category/name/prompt 缺失`;server.log 显示 `category=character name= model=...`(name 为空)。
- **根因**(两处叠加):①前端 `genBtn` 的 name 参数取自**图片文件名** `(cur.image||"").split("/").pop().split("?")[0]`——image 为空时 name 为空;②后端 `mark_ready.apply` 只用 `image` 文件名匹配,image 为空的资产(首次生成)**永远匹配不上** → 即使传了 name 生成成功,SQLite 也不更新。
- **修复**:①前端 4 处 genBtn(角色主图/身份图/场景/道具)name 改为**资产 name 字段优先、文件名兜底**(身份图无图时传「角色名-身份名」);genSend 加前置校验(空 name → toast 提示不发请求);②后端 `apply` 增加**按对象 name 字段匹配兜底**(image 为空时 `base == obj.name`),身份图循环传入 `extra_names=(f"{角色名}-{身份名}",)`。
- **教训**:新增资产的「首张图」是特殊路径——一切按文件名匹配的逻辑都要考虑 image 为空的首次生成场景;按钮参数应取数据字段(如 name)而非派生值(文件名)。

## 32. 参考图选择器看不到已有图的资产/身份图(2026-08-19)

- **症状**:「📂 选择参考图」列表里没有某些资产图(如多角色群像群像、角色D/角色E/角色F/角色G的身份图),但文件与 SQLite image 字段都正常。
- **根因**:①`refpCollect` 过滤条件 `image_ready && image`——历史数据/上传路径的资产 `image_ready` 可能未置位(文件在但标记 False)→ 不显示;②页面内存数据旧(新增资产后未刷新页面)。
- **修复**:①前端 `refpCollect` 过滤放宽为**只要有 image 路径就显示**(ready 标记不再作为条件;无图资产 image 为空仍不显示,图片缺失由网格 onerror 兜底显示"图缺失"),character 主图/身份图/prop/scene 全部放宽,sketch 分支保持原样;②数据层批量修复:文件存在的资产 `image_ready` 自动置 True(扫描 characters/identities)。
- **教训**：`image_ready` 是冗余派生状态,展示层应以 `image` 路径为准;ready 标记只用于"未生成"占位提示,不该成为列表过滤条件。

## 33. build-data-js.py 在 outputs/xiajing 为空时崩溃(2026-08-19)

- **症状**：新项目初始化(虾镜未开始,`outputs/xiajing/` 空或不存在 ep 目录)跑 build-data-js.py → `NameError: name 'sketch_md' is not defined`(line ~223),随后修好又报 `NameError: name 'ep_beats' is not defined`(line ~410 打印)。
- **根因**：`sketch_md` 与 `ep_beats` 只在 `for ed in ep_dirs` 循环内定义;虾镜阶段未开始时循环体不执行,循环外引用即崩。
- **修复**：①循环外解析 sketch/firstframe 前加兜底 `sketch_md = sketch_md if "sketch_md" in dir() else ""`;②line ~410 打印改用 `sum(len(e["beats"]) for e in all_episodes)`。
- **同步**：templates/build-data-js.py + scripts/build-data-js.py + 某新项目。
- **教训**：build-data-js.py 必须支持"任一模块尚未开始"的**渐进式状态**(虾料先行、虾镜后到);循环内变量被循环外引用的写法在空目录下必然崩,应初始化为空值。

## 34. scene_blocks 类型契约:必须为数组,误写数字致虾料页崩溃(2026-08-19)

- **症状**：新项目虾料页点击报 `Uncaught TypeError: (x.scene_blocks||[]).map is not a function`(renderXialiao line ~3041)。
- **根因**：数据生成侧把 `ingest-result.json` 的 `scene_blocks` 写成了**计数数字**(21),而前端契约要求**数组**——`renderXialiao` 用 `(x.scene_blocks||[]).map(s => ...)` 遍历场景块(字段:episode/scene/location/time_of_day/interior_exterior/header_line/dialogue_lines/action_lines/characters),数字无 `.map` 直接 TypeError。`||[]` 兜底只防 null/undefined,防不了"类型错但 truthy"。
- **修复(三层)**：
  1. **数据侧**:scene_blocks 生成真实场景块数组(按正文归纳,含对白/动作行数统计);`format_check.metrics` 补 `scene_headers/dialogue_lines/action_lines`。
  2. **前端防御**:templates/index.html 两处改 `(Array.isArray(x.scene_blocks)?x.scene_blocks:[]).length/.map`——类型错也不崩(显示 0/空)。
  3. **构建校验**:templates/build-data-js.py 读取 ingest 后 `if not isinstance(ingest.get("scene_blocks"), list)` → 告警并置空,避免带病数据入库。
- **契约固化**:SKILL.md 数据契约明确 `scene_blocks: [{episode,scene,...}]` 是数组。
- **同步**:templates(index.html/build-data-js.py)+ SKILL.md + 某新项目。
- **教训**：`(x||[])` 兜底只防 null/undefined,不防"truthy 但类型错";契约字段必须写明类型;前端对用户可见核心区应 `Array.isArray` 防御,构建脚本对契约字段做类型校验。

## 35. check-assets.py 大小写敏感误报(2026-08-19)

- **症状**：资产自检报 9 处 `身份图缺四视图要素: ['character reference sheet']`、8 处 `主图缺证件照要素: ['ID/passport']`,但提示词实际含 `Character reference sheet: left side...`(句首大写)与 `ID/passport-style...`。
- **根因**：check-assets.py 关键词匹配大小写敏感;`pos.lower()` 后关键词 `k` 未同步小写(`"ID/passport" in "id/passport-style"` 为 False),句首大写的 `Character` 也匹配不到小写关键词。
- **修复**：全部关键词检查改 `k.lower() not in pos_l` / `k.lower() in pos_l`(ID_KEYS/ID_VIOL/SHEET_KEYS/SHEET_WRONG 4 处);SHEET_SIDE_OK/SHEET_BG_OK 的 `any(s in ipos_l)` 已用小写串,OK。
- **同步**：scripts/check-assets.py + templates 无此文件(仅 scripts)+ 某新项目。
- **教训**：做大小写不敏感匹配时,"目标串转小写"与"关键词转小写"必须同时做;先写小样例自测 `"ID/passport" in "id/passport-style"` 这类边界再上全套。

## 36. 模板源残留旧剧名,项目反复被污染(2026-08-19,★ 最高纪律)

- **症状**：某新项目页面再次出现旧项目剧名《旧项目剧名》(title/侧栏/顶部大标题/JS 兜底 4 处),但项目副本早前已清理过。
- **根因(流程级事故)**：**skill 模板源 `templates/index.html`/`templates/server.py`/`scripts/check-assets.py` 本身残留旧项目数据**(旧剧名+角色A/角色C/角色D/角色E/多角色群像示例)。首次建项目只清理了**项目副本**,模板源未清;之后为同步前端/校验修复,`cp templates/* project/*` 把污染又带回了项目——"复制即清理"只做了一半。
- **根治(三层)**：
  1. **模板源清零**:templates/index.html(4 处旧剧名→`{{项目名}}` 占位)、templates/server.py(3 处旧剧名→`{{项目名}}`+示例注释通用化)、scripts/check-assets.py(多角色群像→多角色群像、角色D/角色E→角色A/角色B);grep 复扫模板源=0。
  2. **项目副本同步**:从模板复制后把 `{{项目名}}` 替换为本剧名;全项目 grep 复扫=0。
  3. **进程重启**:server.py 变更后必须重启服务(旧进程跑旧代码),页面/API 验证 title=剧名、0 残留。
- **纪律重申**:①skill 模板/scripts/references 是**唯一源头**,必须零项目数据,新项目复制后统一替换 `{{项目名}}`;②任何"cp 模板→项目"操作后必须重跑全项目 grep;③模板源改动后检查所有已建项目是否被同步覆盖污染。
- **教训**:清理项目污染 = 清理**源头模板**而非只清副本;修模板后从模板同步过的所有项目副本都要复查。

## 37. 批量生图误判"已全部生成"——image 是预期路径非空,应判 image_ready(2026-08-19)

- **症状**：新项目(无任何资产图)点角色/场景/道具「✨ 批量生图」→ toast「✅ XXX 已全部生成」,0 个任务入队;页面统计也显示"未生成 0 个"。
- **根因**：build-data-js.py 生成的资产 `image` 字段是**预期路径**(`assets/characters/角色A.png`,文件不存在也非空);前端 `batchGenImages` 与统计标签用 `!x.image` 判断"未生成"——新项目 image 全非空 → 收集为空 → 误判"已全部生成"。真正表示"文件已存在"的是 `image_ready`(asset_exists 判定)。
- **修复**：批量收集 3 处(scene/prop/character)`!x.image` → `!x.image_ready`(sketch 本来就用 sketch_ready,正确);页面统计标签 3 处(未生成主图/场景/道具)`!x.image` → `!x.image_ready`。
- **同步**：templates/index.html + 某新项目。
- **教训**：`image`=预期路径(展示用),`image_ready`=文件存在(状态用)——凡"判断是否已生成"必须用 ready 标记,不能用 image;新项目初始化数据要区分"路径占位"与"真实就绪"。

## 38. 生图任务提示词被截断到 80 字符——add_task 与执行共用截断字段(2026-08-19,★ 严重)

- **症状**：888 中转平台实际收到的生图提示词只有 80 字符("Create a live-action image with grounded realism. Use natural lighting and restr…"),生成图缺人脸描述/证件照要素/负面词约束,风格完全不对。
- **根因(两处耦合)**：`GenTaskQueue.add_task` 把任务记录 `"prompt": prompt[:80]`(本意是面板摘要),而 `_execute_task` 执行时 `prompt = item["prompt"]`——**执行直接用截断字段**,完整 prompt 在入队时被丢弃,888 只收到 80 字符。
- **修复**：add_task 改存完整 `"prompt": prompt` + 新增 `"prompt_preview": prompt[:80]`(仅诊断/日志摘要);_execute_task 无需改(拿到的已是完整)。前端任务面板不显示 prompt,无影响。
- **验证**：源码断言 add_task 存完整 + 执行取完整,双✅;重启服务器后 /api/info 正常。
- **同步**：templates/server.py + 某新项目。
- **教训**:任务记录字段若被"执行逻辑"消费,就不能为"展示摘要"截断——存完整字段、另建 preview 摘要字段;排查"实际收到什么"必须看渠道侧真实请求,不是面板显示。

## 39. 模板占位符 {{项目名}} 漏替换,项目名变占位符(2026-08-19)

- **症状**：项目台侧栏/顶部标题/浏览器 title 显示 `{{项目名}}`,双击 bat 启动提示"{{项目名}}正在启动..."——页面 h1 会被 JS 用 meta.name 覆盖(所以顶部正常),但**侧栏 sb-prof-name 与 bat 提示无 JS 兜底**,占位符裸露。
- **根因**：模板源(2026-08-19 污染根治后)统一用 `{{项目名}}` 占位符;项目初始化时替换为剧名。但 22:16 修复 image_ready 时 `cp templates/index.html → project/index.html` 把占位符带回了项目,**未重新执行占位符替换**;bat 从建项目起就从未替换过。
- **修复**：项目内 5 处(html 4 处:title/sb-prof-name/h1/JS兜底 + bat 1 处)`{{项目名}}` → 本剧名;grep `{{项目名}}` 项目内=0;页面 title 验证正确。
- **纪律强化(★)**：**任何 `cp templates/* → project/*` 之后,必须重跑 ①占位符替换 ②`grep {{项目名}}` 应为空 ③全项目旧剧名/占位符复扫**——模板占位符是"新项目初始化时一次性替换"的设计,与"模板同步修复"两个动作必须成对出现。
- **教训**：占位符方案下,"从模板复制"与"替换占位符"是原子操作,拆开必出问题;SKILL.md §0.5 已要求 grep 为空才算完成,执行时不得省略。

## 40. 项目→模板方向同步带剧名污染模板(2026-08-19,★ 双向污染)

- **症状**：模板自检发现 `templates/server.py` 3 处「某项目名」(文件头注释/api/info/启动打印)——模板被**当前项目**剧名污染。
- **根因**：22:24 同步 prompt 截断修复时 `cp project/server.py → templates/server.py`——**项目副本已把占位符替换成剧名**,同步回模板时把剧名带进模板;方向与 36 条(模板→项目带旧剧名)相反,同为"复制即清理"只做一半。
- **修复**：templates/server.py 3 处剧名→`{{项目名}}`;删除 templates/__pycache__(pyc 含旧字符串字面量);grep 模板零项目词(当前/旧项目均 0);占位符 8 处分布确认(index 4/server 3/bat 1)。
- **纪律强化(★双向)**：①模板→项目:cp 后必须替换占位符为剧名;②项目→模板:cp 后必须还原剧名为 `{{项目名}}`;**两个方向复制后都要 grep 零残留**。模板与项目副本是"占位符↔剧名"的互逆关系。
- **教训**：模板同步是双向的,每个方向都有自己的清理动作;pyc 缓存也会藏字符串字面量,清理时一并删。

## 41. 任务面板"垫图数"显示数组而非数量 + /tasks 响应过大(2026-08-19)

- **症状**：底部任务面板"任务中"区域信息异常——`垫图数=` 后显示空白(空数组)或文件名串(有垫图时);且 /tasks 每条任务带完整 prompt(1270+ 字符),1s 轮询响应巨大。
- **根因**：①前端 taskRow 用 `垫图数=${t.images || 0}`——`images` 是数组,truthy 直接拼接(空数组 toString 为空),应为 `(t.images||[]).length`;②snapshot() 返回完整任务记录(含完整 prompt,add_task 修 38 条后存的)。
- **修复**：①前端 `垫图数=${(t.images||[]).length}`(显示数量);②snapshot() 返回时 `t["prompt"] = prompt_preview`(80 字摘要)——**仅面板接口瘦身,执行链路 _execute_task 仍用任务记录完整 prompt,不受影响**。
- **同步**：templates(index.html/server.py)+ 新项目;同步后按双向纪律还原剧名占位符,grep 验证 0 残留。
- **教训**：`数组 || 0` 不会得到 0(数组 truthy)——显示数量必须 `(arr||[]).length`;接口返回与执行消费要区分(快照瘦身不影响执行)。

## 33. 场景视角「45°俯视全景」入队失败（2026-08-20）

- **症状**:切换视角选择「45°俯视全景」→ 提示入队失败;server.log 显示 name=`<某场景名>-45°俯视全景` 被 400 拦截。
- **根因**:`handle_gen_image` 的 name 校验正则 `^[\u4e00-\u9fff\w·\-（）()]+$` **不含角度符号 `°`**(U+00B0)→ 视角名带 ° 全部非法名称。
- **修复**:正则加 `°` → `^[\u4e00-\u9fff\w·\-（）()°]+$`(Windows 文件名允许 °)。
- **教训**:自定义视角/命名类功能新增特殊字符时,同步检查后端 name 白名单正则。

## 34. 新端点返回 RemoteDisconnected 但服务器日志显示成功（2026-08-20）

- **症状**:新增 `POST /save-annotation` 端点,客户端请求报 `RemoteDisconnected('Remote end closed connection without response')`,但 server.log 显示处理完成且数据已落库。
- **根因**:`self.send_json({...}, status=...)` 用了关键字 `status`,而 send_json 签名是 `def send_json(self, obj, code=200)` → `TypeError: unexpected keyword argument 'status'` → handler 线程在发送响应前崩溃 → 连接关闭无响应。**数据已在崩溃前落库**,所以日志显示成功。
- **修复**:关键字改为 `code=200 if ok else 500`。
- **教训**:①所有 send_json 调用统一用 `code=`(其唯一关键字参数);②出现「日志成功但客户端断连」先查 handler 是否在 send_json 前抛了关键字/参数异常;③新增端点后用真实 HTTP 客户端做端到端测试(不能只看日志)。

## 35. 沙箱环境 os.remove 静默失败（2026-08-20）

- **症状**:服务端保存标注图后「清理同 beat 旧文件」逻辑不生效,旧文件一直保留(功能无碍,但磁盘堆积)。
- **根因**:沙箱策略对**写文件放行、对删除文件拦截**,os.remove 抛异常被 `except Exception: pass` 吞掉。
- **处理**:清理逻辑保留(try/except 静默),沙箱外运行服务时自然生效;旧文件保留不影响功能(页面始终用时间戳新 URL)。
- **教训**:沙箱内 Python os.remove 不可靠,「删除」类操作验证需在沙箱外(Bash rm + escalation)执行。

## 36. 画面标注弹窗 $("ann-canvas") null 报错（2026-08-20）

- **症状**:点击画面标注 Beat 卡片 → `Uncaught TypeError: Cannot read properties of null (reading 'addEventListener')`（openAnnModal 内 cv 为 null）。
- **排查**:本地/线上 HTML 均有 `id="ann-canvas"`（grep 各 1 处）、HTML 标签完全平衡（python html.parser 校验 0 错误 0 未闭合）、annmodal 深度=2(body 内)——静态结构无问题;判定为用户浏览器缓存旧版 HTML 与新版 JS 混用(同一文件不同版本缓存)或旧标签页 DOM 缺失。
- **修复(根治)**:弹窗 HTML **从静态 DOM 改为 JS 常量 `ANN_MODAL_HTML` + `ensureAnnModal()` 动态注入**——`openAnnModal` 开头调用,若 `#ann-canvas` 不存在则注入 body 并绑定事件(幂等)。彻底免疫「静态 DOM 缺失/缓存旧页/解析错位」。
- **教训**:弹窗类 UI 若会被 JS 频繁重渲染/页面可能缓存混用,优先「动态注入」而非静态 HTML;静态弹窗 + 内联 onclick 依赖「HTML 与 JS 同版本」的隐式契约,缓存会打破它。

## 37. 画面标注 $("id") 误带 # 前缀导致 textContent null（2026-08-20）

- **症状**:动态注入弹窗后,`openAnnModal` 报 `Cannot set properties of null (setting 'textContent')`(3950 行 `$("#ann-title")`)。
- **根因**:本项目 `$ = (id) => document.getElementById(id)`(**不带 #**),而 openAnnModal 等标注函数写成 `$("#ann-title")` → getElementById("#ann-title") → null。共 15 处误用(ann- 前缀 13 + annmodal 2);xiage 区 3011-3013 有同样的 `$("#xiage-...")` 但用 `||{value:""}` 兜底未炸。
- **修复**:全文替换 `$("#ann-` → `$("ann-`、`$("#annmodal")` → `$("annmodal")`;验证 0 残留。
- **教训**:`$` 是本项目自定义 getElementById 简写,**永远不带 #**(带 # 是 querySelectorAll 的用法);新增 ID 操作代码时严格区分 `$("id")` vs `document.querySelectorAll("#sel .cls")`。

## 38. 项目台单文件 index.html 拆分为 css/js 多文件（2026-08-20）

- **背景**:index.html 5166 行/299KB(内联 CSS 1374 行 + 内联 JS 3514 行)过于臃肿 → 项目化拆分。
- **新结构**:`index.html`(264 行骨架:body 静态结构 + 9 个 script src)+ `css/main.css`(1372 行,原 <style> 全部提取)+ `js/` 9 个文件(按原行号区间切割,严格保持原顺序):
  - core.js(顶层常量/openZoom/路由 renderSection)、gen.js(生图弹窗/参考图/设置/历史/上传/批量生图/任务队列)、agent.js(对话+右侧面板)、xiage.js、xialiao.js(虾料/世界观/知识图谱)、xiatang.js、xiajing.js(虾镜/脚本/分镜/调度图/视频/视角/上帝视角/大卡)、ann.js(画面标注)、init.js(主启动 IIFE:loadProjectFromDb→renderSection→initTaskbar,必须最后加载)。
- **关键约束**:①主启动 IIFE 单独 init.js **最后加载**(它调用 renderSection→各模块渲染函数,若在 core 里执行时模块未加载会 ReferenceError);②`let batchLock` 等共享变量**只能声明一次**(切分区间重叠会导致重复声明 TDZ);③CSS 提取零风险,JS 必须「无重叠无遗漏」覆盖原 1626-5139 行。
- **事故记录**:①第一版切分 gen(4494-4668) 与 xiajing(4435-4948) 区间重叠 → batchLock 声明两次;②修复时误从**已同步为新结构的模板**(263 行)重新切分,把 project/js 全毁;幸 既有项目/js 保留第一版完整内容才恢复。**教训:单文件大重构前先备份完整版(不要依赖「模板同步」链路,它会随同步被覆盖);切分脚本必须内置覆盖校验(无缺失行/无重叠区间)**。
- **验证**:node --check 9 文件全过;mock-DOM vm 冒烟(9 文件依次加载无顶层依赖错误);26 个关键函数/常量跨文件可见(SCENE_VIEW_PROMPTS 7 条/SCENE_VIEWS 7 视角);HTML 标签平衡;双服务资源全 200 + API 数据完整。

## 39. 草图/渲染图/调度图分集串数据（2026-08-20）

- **症状**:ep1 生成草图/渲染图后,ep2 里显示同样的图——「第一集生成了第二集也是第一集的内容」。
- **根因**:①`_save_generated_image` 目录 `replace("epNNN","ep001")` **硬编码 ep001**;②`mark_ready` 的 sketch/frame/blocking 分支**遍历所有集按 beat_number 匹配**——ep1.beat1 与 ep2.beat1 同名都命中 → ep2 的字段被写成 ep1 的图路径。
- **修复(ep 贯穿全链路)**:后端 `add_task/_execute_task/_save_generated_image/mark_ready/handle_upload` 全部加 `ep` 参数(目录 `ep{ep:03d}`;sketch/frame/blocking 分支 `if ep is not None and 集number != ep: continue`);前端 `genBtn data-ep / openGenModal(ep) / genSend body.ep / genWatchTask(ep) / markReadyInMemory(...,ep) / batchEnqueue(ep) / batchEp(batchGenBlocking+batchGenImages 记录当前集) / doUpload(ep)`;renderGridCard 传 `window.xjCurEp`。
- **历史数据修复**:清理 ep2+ 中指向 `assets/ep001/` 的 sketch/frame/blocking 字段(40 个)置空+ready=False,等待各自集重新生成。
- **教训**:凡是「跨集同名对象(beatN)」的匹配逻辑,必须携带集维度(ep);「目录按集」「匹配按集」要同时做,只做一个会静默串数据。

## 40. 生图提示词被截断（prompt[:80]）（2026-08-20）

- **症状**:中转平台收到的提示词被截成 80 字符(如 `角色A=图1，场景标注=图2 CINEMATIC FILMIC REALISM. Create live-action Chinese period dram` 断在 dram)。
- **根因**:调度器改造时 `GenTaskQueue.add_task` 存任务 dict 用 `"prompt": prompt[:80]`(原为「任务列表显示」目的),但 `_execute_task` 执行生图时直接取 `item["prompt"]` → **执行用截断版提示词**。
- **修复**:①add_task 存**完整** prompt;②`snapshot()`(/tasks 返回)里才截断 80 用于列表显示——存储/执行/显示三层职责分离。
- **单测**:add_task 存储 539 字符完整 / snapshot 显示 80 / 执行取完整;端到端入队后 tasks 显示 80、生图成功(47s)且提示词完整(测试图已清理)。
- **教训**:任务 dict 里「显示字段」与「执行字段」必须分离——不要在存储时截断会被执行复用的字段;所有 `[:N]` 截断只应出现在渲染/返回层。

## 41. 项目化拆分后底部任务队列面板消失（2026-08-20）

- **症状**:css/js 拆分后页面底部 taskbar（任务队列面板）消失,生图任务照常排队但无面板显示。
- **根因**:拆分脚本 body 骨架提取 `seg(1382,1624)` 的**行号边界漏掉了 body 末尾、script 前的 taskbar HTML**(它是 body 最后一个元素,恰好被切分边界切掉);三处 index.html(project/既有项目/模板)均缺失 → `initTaskbar()` 找不到 `#taskbar` **静默 return**(无报错)→ 面板消失。
- **修复**:按 CSS 类(.taskbar/.tb-line-wrap/.tb-body/.tb-sec/.tb-task) + JS 引用 ID(taskbar-line/taskbar-badge/tb-running/tb-done/tb-queue 等) **重建 taskbar HTML** 插回 body(script 前);HTML 标签平衡校验通过;同步 既有项目+模板;线上验证 8317/8318 均含 `id="taskbar"`。
- **教训**:①拆分脚本 body 提取边界必须校验**关键 UI 元素齐全**(sidebar/taskbar/弹窗),不能只校验标签平衡——「静默 return」类故障无报错极难发现;②所有 JS 里 `$("xxx")` 后接操作前,若元素可能缺失应显式报错而非静默返回。

## 42. 模板残留旧项目剧名（跨项目污染·最高级别事故）（2026-08-20）

- **症状**:新项目《新项目》HTML 项目台打开后,标题/侧栏/顶栏显示《旧项目剧名》——旧项目剧名串台。
- **根因**:templates/ 被旧项目数据污染——index.html 3 处硬编码旧剧名(title/sb-prof-name/h1)、js/gen.js 兜底 `P.meta?.name || "旧剧名"` + 2 处注释示例(角色A/角色C)、server.py 6 处(文件头/api/info 返回/启动打印/3 处注释示例);另有运行残留(templates/server.log、测试残留 templates/xiaji.db、__pycache__)。**模板带项目数据 = 每个新项目都会继承污染**,属最高级别事故。
- **修复**:①模板全部还原为 `{{项目名}}` 占位符(index 3 处 + gen.js 兜底 1 处 + server 3 处),注释示例统一中性占位({{角色名}}/{{场景·名}}/角色A);②当前项目 project/ 同步替换为本剧剧名(某项目名);③删除 templates/ 与 project/ 的 __pycache__、server.log、空 xiaji.db;④SQLite 7 模块快照逐条 grep 旧词验证干净。
- **验收**:①模板旧词 grep 空;②项目旧词 grep 空;③剧名分布 index 3/server 3/gen.js 兜底 1/bat 1;④模板占位符分布 index 3/server 3/bat 1;⑤SQLite meta.name=本剧剧名。
- **教训**:①**拆分/同步模板的任何一步都必须替换剧名**——「模板→项目」复制后必须把 `{{项目名}}` 替换为本剧剧名;「项目→模板」复制后必须还原占位符;双向复制后 grep 零残留才算完成;②模板目录禁止留 server.log/xiaji.db/__pycache__ 等运行残留;③检查项目名要四层全查:HTML 硬编码 + JS 兜底 + server /api/info + SQLite meta.name,缺一即漏。

## 43. build-data-js.py 漏同步 blocking_prompt（调度图提示词丢失）（2026-08-20）

- **症状**:beats.json 已写满 blocking_prompt(26/26),但跑 build-data-js.py 同步 SQLite 后 blocking_prompt 为 0/26——HTML 项目台调度图 Tab 提示词空白。
- **根因**:build-data-js.py 的 beat 字段映射列表(约 L151-169)只有 sketch_prompt/firstframe_prompt/video_prompt,**漏了 2026-08-20 新增的 blocking_prompt/blocking_image/blocking_ready 三字段**;模板 templates/build-data-js.py 同款缺失。
- **修复**:项目 + 模板双修——beat 映射加 `blocking_prompt`(b.get)、`blocking_image`(assets/ep{NNN}/sketches/beat{n}.png,复用 sketches 目录,与 server.py CATEGORY_DIRS blocking=epNNN/sketches 一致)、`blocking_ready`(asset_exists sketches/beat{n}.png)。
- **验收**:重跑 build 后 SQLite blocking_prompt 26/26;四类提示词(sketch/blocking/firstframe/video)全量入库。
- **教训**:新字段加入 beats.json/前后端后,**必须同步 build-data-js.py 的字段映射白名单**,否则数据源丢失;模板脚本与项目脚本要一起改;验收时按「beats.json 计数 vs SQLite 计数」对拍。

## 44. 生图队列去掉批量限制（普通/批量统一排队上限 60）（2026-08-20 用户拍板）

- **需求**:普通生图请求原来达到 5 个（MAX_CONCURRENT）就 429 拒绝；用户要求去掉批量限制——只要队列（执行中+排队）不满 60 条，普通请求也可以再次提交。
- **改动(项目+模板双修)**:
  - `add_task`:入队上限统一 `limit = MAX_QUEUED(60)`（batch 参数仅保留签名兼容，不再影响上限）。
  - `handle_gen_image`:429 判断与错误提示统一用 MAX_QUEUED;入队日志显示 队列占用=X/60。
  - `stats()`:`max` 改为返回 MAX_QUEUED(60)（前端角标 warn 阈值与「队列上限」显示自动跟随）,新增 `max_concurrent` 字段保留并发数 5。
  - `GenTaskQueue` 类注释更新;`js/gen.js` 角标注释同步。
  - 并发执行仍由调度器限制 5(MAX_CONCURRENT),take_next 逻辑未动。
- **单测**:普通请求连续入队 60/60 成功,第 61 条被拒;stats.max=60 / max_concurrent=5;语法检查双过。
- **教训**:「并发执行数」与「排队上限」是两个独立语义——并发数只由调度器 take_next 控制,排队上限才是入队闸门;前端角标阈值应跟随排队上限,不要硬编码并发数。

## 45. 批量生图全局锁 batchLock 拦截提交（2026-08-20 用户拍板移除）

- **症状**:队列上限已放宽到 60（#44），但批量生图进行中点击任何生图按钮仍提示「⚠️ 批量生图中，请稍等！」——前端 `batchLock` 全局锁拦截所有 `genSend()`/批量/场景视角/上帝视角提交。
- **根因**:2026-08-19 设计「批量进行中禁止其他生图提交」（batchLock + batchWatch 单例状态机：batchTaskIds/batchTotal/batchDone/batchFailed/batchWatchTimer/batchCat/batchEp 全局）。#44 只改了后端入队闸门，前端锁未动。
- **修复(项目+模板双修,gen.js+xiajing.js)**:彻底移除 batchLock 机制——①`genSend`/`batchGenBlocking`/`batchGenImages`/`openSceneViewModal`/`sceneViewSend`/`godViewGen` 6 处拦截全删;②`batchEnqueue` 入队成功即 `genWatchTask(task_id, cat, name, ep)` **每任务独立 watch**(复用单任务轮询,完成自动 markReadyInMemory+rerenderCurrent,互不阻塞);③删除 batchLock/batchWatch/batchTaskIds/batchTotal/batchDone/batchFailed/batchWatchTimer/batchEp/batchCat 全部变量与函数;④批量完成 toast 改为入队统计(完成逐个自动应用)。
- **验证**:项目+模板 grep 无功能残留(仅注释)、node --check 双文件通过、项目-模板 diff 仅剩剧名占位差异。
- **教训**:①「批量进度」与「提交闸门」是两回事——任务完成跟踪应每任务独立(genWatchTask 模式),不要用全局单例状态机,否则天然要锁提交;②去锁后后端排队上限(60)成为唯一闸门,语义清晰;③SKILL.md 的机制描述要随实现同步更新,否则下次读 skill 会按旧锁逻辑排查。

## 46. 场景主图与「正面」视角混淆 + 切换视角参考图不可选（2026-08-20 用户拍板）

- **症状/需求**:①场景详情 `.scene-views` 第一张主图标签写「正面」,与额外生成的正面视角（views.正面）混淆;②切换视角弹窗垫图写死主图,无法用正面视角做参考;③正面未生成时无提示。
- **修复(项目+模板双修,index.html+xiajing.js+xiatang.js)**:
  - 场景详情:主图标签「正面」→「**主图**」;7 视角缩略图不再 filter 掉「正面」,views.正面 独立显示。
  - 切换视角弹窗:新增 `sv-ref` 参考图选择区(radio 二选一)——「主图」（s.image,默认）/"正面"（s.views["正面"]）;正面未生成(views.正面 或 views_ready.正面 缺失)→ 选项 disabled+置灰+红字「未生成,不可选」。
  - `sceneViewSend`:按 `sceneViewRef`(main/front)取垫图源;选正面但无图时拦截提示;confirm 文案显示实际参考图。
- **验证**:项目+模板 4 个 JS 语法过、diff 完全一致、sv-ref 容器双端各 1 处;SKILL.md 切换视角描述同步。
- **教训**:「主图」与「正面视角」是不同资产(基准图 vs 派生视角),UI 标签必须区分;参考图来源做成用户可选,不要写死。

## 47. 场景多角度图可设为正面（2026-08-20 用户拍板）+ build 重建丢 views 修复

- **需求**:场景任意多角度图（左侧/右侧/背面/斜侧/俯视/45°）都可「设为正面」——①替换 views.正面；②原角度 views[view]/views_ready[view] 清空；③正面文件名要随正面命名（防缓存）。
- **后端 `POST /scene-set-front`**（server.py）:body {name, view} → 校验场景/角度 → 复制 场景名-{view}.png → 场景名-正面-{ms}.png（时间戳防缓存，沿用 {base}-{视角}-{ms}.png 惯例）→ views.正面 指向新文件 + views_ready.正面=True → 原角度 pop + views_ready[view]=False → SQLite 更新 → {ok, image, cleared_view}。view=正面 直接返回不变。
- **前端**:场景详情 .scene-views 每个非正面视角缩略图加红色「设为正面」小按钮（.sv-front-btn，stopPropagation 不触发放大）；`setSceneAsFront(view)`（xiajing.js）confirm → POST → 内存同步（views.正面 指向新文件、原角度清空）→ rerenderCurrent。
- **★ build 重建丢 views（连带修复）**:build-data-js.py 的 scenes 从 registry 纯重建,**不含 views/views_ready/plan/plan_ready/plan_sketch/plan_sketch_ready 运行时字段**——多视角/上帝视角/设为正面在下次 build 全丢。修复:build 时 merge SQLite 现有 xiatang 快照的这 6 个字段（sqlite3 读旧快照按场景名合并,prompt/image 等静态字段仍以 registry+文件为准）。
- **⚠️ 沙箱事故（教训）**:端到端测试后清理时,`cp xiaji.db.testbak xiaji.db` 在**沙箱外**(escalation)执行,而备份/测试在沙箱内——文件系统视图不一致导致 xiaji.db 被写成 0 字节空库。恢复:build-data-js.py 从 outputs 全量重建(7 模块)+ 扫描磁盘视角图(8 张,3 场景)手动注册回 views。**教训:①数据库文件操作全程保持同一执行环境(sandbox 内外一致),跨沙箱边界的 cp/rm 高风险;②SQLite 丢失可兜底——outputs/ 权威数据源 + 磁盘文件扫描可完整重建,运行时 views 等用文件系统反推注册。**


## 48. 身份图两图制恢复（2026-08-21 用户拍板：推翻单图制）

- **需求**：身份/造型 = ①定妆照 + ②四视图角色卡两张图（此前误改成单图制四视图卡）。
- **四视图卡提示词 = 用户钦定中文模板**（上下两段式：上 1/3 正脸+侧脸特写 / 下 2/3 放大正面服装展示+完整背面全身），**逐字写死**（character-sheet-4view.md §A），豁免英文纯净纪律。
- **数据契约**：identities 带 `prompt`（定妆照）+ `sheet_prompt`（四视图卡钦定模板）；产物命名 `{角色}-{身份id}-sheet.png`（如 角色A-id1-sheet.png）→ build-data-js 组 `sheet_image/sheet_ready`。
- **前端**：身份卡加四视图卡图位 + 【四视图】按钮（`genIdentitySheet`：以该身份定妆照为参考图 + 固定模板入队）。
- **验证**：check-assets 两图制校验全过（定妆照查 FRONT_KEYS+IDN_FULL_KEYS；sheet_prompt 含「请基于参考人物」→ 豁免英文纯净查 5 结构特征：上下两段式/正脸特写/侧脸特写/正面服装展示/背面全身）。

## 49. 身份定妆照 = 正面全身基准（2026-08-21 用户拍板）

- 主图证件照式锚"脸"；**身份定妆照按 02-storyboard-master 全身定义锚"完整造型"**（正面全身站姿 / 双臂自然垂放 / 完整造型一次定死：面容、发型、体型、服装材质剪裁颜色、鞋、随身物件）。
- **遵守资产图通用要求清单（18 项，用户钦定）**：纯中性背景；无场景；无其他人物；无文字；无尺寸标注；无说明标签；无水印；自然中性站姿；身体比例统一；年龄统一；发型统一；面部统一；服装统一；鞋履统一；道具统一；材质真实；正侧背视图结构一致；禁服装漂移；禁左右道具错位；禁多余手指和肢体畸形。
- check-assets：身份定妆照新增 `IDN_FULL_KEYS` 全身要素校验（full body / full-length / full standing / full outfit / standing pose 任一）。

## 50. 🛍 服装参考按钮 + 服装通用参考版（2026-08-21 用户拍板：整体替换，非追加）

- **需求**：身份定妆照支持上传服装参考图；提示词**整体替换**为固定「服装通用参考版」——不做追加段（追加会与原提示词里的服装文字冲突）。
- **前端**：index.html 参考图区加「🛍 服装参考」按钮（仅 identity 弹窗显示）；gen.js 常量 `OUTFIT_REF_PROMPT` **写死**（用户钦定，图1/图2 写法原封不动：发型/妆面/服装全部以 图2 参考图为准、脸锁 图1 主图、ignore the model's face，任何身份通用）；`genOutfitRefPicked` 选图→isOutfit 打标→预览"👗 服装参考"角标→**整体替换** textarea；`genSend` 提交兜底（含服装参考且提示词缺特征句 `Outfit, hairstyle and makeup` → 替换回）；`genRefRemove`/`genRefClear` 移除后恢复标准版（defaultPrompt）。
- **参考图顺序约定**：图1=主图（images[0]，锁脸）、图2=服装参考图（images[1]）。
- 规范固化：character-sheet-4view.md §B2（固定模板逐字）。

## 51. 四视图卡比例 = identity 类别、默认 9:16（2026-08-21 用户拍板）

- `genIdentitySheet` size：`(cfg.default_sizes||{}).identity || "1088x1920"`（原误用 character 类别，导致跟随"角色主图"比例）。
- server.py `DEFAULT_SIZE_MAP.identity`：1920x1088(16:9) → **1088x1920(9:16)**；gen.js `DEFAULT_SIZE_MAP_FE.identity` 同步（设置面板初始默认）。
- 9:16 竖版与钦定上下两段式版式适配。

## 52. 生图成功但资产位不同步（2026-08-21）

- **根因**：server.py `mark_ready` **缺 identity 分支**（身份定妆照生成后 SQLite 快照不更新）；character 分支无四视图卡匹配（`{角色}-{身份id}-sheet` 匹配不到 identities 的 sheet_image/sheet_ready）。
- **修复**：①mark_ready 新增 `elif category=="identity"`（遍历 characters.identities 按 base 匹配 apply）；②character 分支加 `base == f"{c.name}-{idn.identity_id}-sheet"` → 写 idn.sheet_image/sheet_ready；③前端 gen.js `markReadyInMemory` character 分支加四视图卡匹配（即时刷新不重载页面）。
- **⚠️ server.py 改动需重启项目台服务生效**。

## 53. 图生图 base64 报错（2026-08-21）

- **症状**：`images[0] 的 base64 数据无效（本次收到载荷 32 字符）`。
- **根因**：`batchEnqueue` 一键入口把参考图**相对路径字符串**直接入队，后端把非 data:/http(s) 开头字符串当裸 base64 解码。
- **修复**：batchEnqueue 开头统一把相对路径 fetch→FileReader→**data URL**（data:/http 开头透传）；一处修复覆盖全部一键入口（场景切换视角/上帝视角/四视图卡）。

## 54. 图片/JS 缓存（2026-08-21）

- **症状**：重传/重生成后刷新显示旧图；新增函数（imgSrc）报 is not defined。
- **修复**：①core.js 全局 helper `imgSrc(p)`（data: 开头直接返回；其余追加 `?t=Date.now()`，已有 ? 用 &）套用到全部资产 img src + openZoom 参数；②index.html 全部 js/css 引用加 **`?v=20260821` 版本参数**。
- **教训**：模板 JS 改动后必须递增 index.html 版本号，否则浏览器缓存旧 JS（新函数报 not defined 是典型症状）。

## 55. 生图队列卡顿优化 A+C（2026-08-21）

- **卡顿根因**：①任务完成整页重建（rerenderCurrent）+ imgSrc 时间戳导致全部资产图重新下载；②每个任务一个 setInterval 轮询 /tasks（批量 20 任务=20 个定时器并发）。
- **优化 A（防抖）**：任务完成重渲染 300ms 防抖（`scheduleRerender`，连续完成合并为一次 rerenderCurrent）。
- **优化 C（单一轮询）**：genWatchTask 改单一全局轮询——genWatch 存 task_id→{category,name,ep}，一个 2s `pollTasks` 遍历全部监听任务，**无任务自动停 timer**。

## 56. bat 运行不起来（2026-08-21）

- **根因**：UTF-8 无 BOM 的 bat 在中文系统（GBK 代码页）双击时，cmd 按 ANSI/GBK 误读文件字节，中文全角括号字节错位**破坏命令解析**。
- **修复**：bat 转 **GBK/ANSI 编码** + `chcp 936`（GBK 配 936，不能配 65001 否则乱码）+ `where python` 检测（找不到给明确提示+pause 不闪退）+ 显式端口 `python -W ignore server.py 8317`。
- **⚠️ 模板 bat 改动必须用 GBK 编码写回（python 转码），不能用 Write/Edit 直接写（那是 UTF-8）**。

## 57. 无图资产位不可点击（2026-08-21，全资产）

- **规则**：资产位无图 → 不绑 onclick + `cursor:not-allowed` + hover 提示「尚未生成…（点 ✨ 生成）」。
- 覆盖：角色主图/列表头像/身份定妆照/四视图卡/场景主图/道具（网格+详情）/关键场景（列表+详情）；场景视角/平面布局/线稿/历史图/首帧图本就"有图才渲染"。

## 58. 身份卡水平三段式 + 关键场景页改场景页式布局（2026-08-21）

- **身份卡**：`[定妆照 80×96] [四视图卡 80×96（间距 100）] [按钮区右]`；info（身份名）移到卡上方小标题；无图不可点击。
- **关键场景页**：网格卡片 → **左列表+右详情**（复用 scene-page/scene-list/scene-detail CSS）；core.js 列表点击兼容 `data-kname`（`xtCurSel = el.dataset.sname || el.dataset.kname`）。

## 59. 前端组件恢复 + 角色主图 prompt 用 registry（2026-08-21）

- **JS 拆分丢失恢复**：`SCENE_VIEWS` 常量、场景切换视角/上帝视角模块（openSceneViewModal/closeSceneViewModal/sceneViewSend/godViewGen/waitTaskDone/setSceneAsFront/SCENE_VIEW_PROMPTS 7 条）。
- **build-data-js.py**：角色主图 prompt **优先 registry.prompt**（asset-prompts.md 标题解析降级为兜底）；identities 组装带 `identity_id/sheet_prompt/sheet_image/sheet_ready`。


## 60. 分镜拖动 reorder 失败修复（2026-08-22）

- **症状**：分镜脚本页拖动重排提示 `shots/reorder 执行失败（idx/数据不匹配）`。
- **根因**：前端 `renumberShots` 生成**无前导零**镜号（"1","2"），后端 `s_by_num` 按数据库 "01","02" 建映射 → 全部匹配失败 → new_shots 数量不等于原数组 → 判失败。
- **修复**：①前端 `renumberShots` 改 `String(i+1).padStart(2,"0")`；②后端 reorder 加 `_zn()` 镜号归一化（zfill(2) 兼容 "1"/"01"）+ 重编号同样 zfill(2)（双保险）。
- **教训**：前端生成"编号类"字段必须与数据库格式统一（zfill 对齐），后端匹配时做归一化防御。

## 61. 分镜拖动交互：目标行高亮 + 插入式确认弹窗（2026-08-22 用户拍板）

- **拖动中**：目标行高亮（`tr.xj-drag-target`，CSS 浅蓝底+蓝色虚线框），表明"将插入该行后面"（shotDragOver 清除旧高亮→当前目标加类；drop/dragEnd 清除）。
- **松开后**：`confirm` 弹窗「是否将镜 X 插入镜 Y 后？」→ 确认执行**插入式重排**（splice 抽出 → from<to 时目标下标 -1 → splice(to+1,0) 插入目标行后 → 全镜号重排 padStart(2,"0") → 后端 reorder 持久化）；取消恢复原状。
- **语义**：插入式（非互换）——镜 X 抽出后插到镜 Y 后面，原 Y+1~X 段顺延；与 §2.2 原"拖动插入式"一致。

## 62. 整集重置分镜（2026-08-22 用户需求）

- 分镜脚本页标题行新增「**↺ 重置分镜**」红色按钮（`shotResetAll`）：confirm 警示（所有编辑/添加/删除/拖动将全部还原，不可恢复）→ POST `/shots/reset_all` → `reloadDataJs()` 刷新。
- 后端 `handle_shots` 新增 `reset_all` action：删除该集**编辑稿**（`ep.edited_shots` 置空 + 删 `shots.edited.json`）→ 自动回到原始定稿（见 #63 架构）。
- 行级「↺ 重置」（单镜恢复 original_shot）保留不变。

## 63. 编辑副本分离：原始分镜永不动（★ 2026-08-22 用户拍板，核心架构）

- **问题**：原实现 handle_shots 编辑后**直接覆盖写回 shots.json** + 修改 SQLite 原始 shots——违背"原始分镜不做修改、编辑单独存在"原则。
- **新架构**：
  - **原始定稿**（永不被页面编辑修改）：`outputs/xiajing/ep{NNN}/shots.json` + SQLite `ep.shots`（仅 build/数据脚本写入）；
  - **编辑稿**：SQLite `ep.edited_shots`（首次编辑时从原始深拷贝）+ 写回 `outputs/xiajing/ep{NNN}/shots.edited.json`；
  - 前端 `xjShots(ep)` = `(ep.edited_shots || ep.shots) || []`（有编辑稿显示编辑稿，无则原始）；
  - build-data-js.py：读 shots.json → `shots`（原始），若 `shots.edited.json` 存在读入 `edited_shots`（重启/build 后编辑稿不丢）；
  - 行级副本机制 `is_edited` + `original_shot` 在编辑稿内生效；整集重置 = 删除编辑稿。
- **⚠️ server.py 改动需重启项目台服务生效。**


## 64. 拖动"刷新/重启变回去"真根因（2026-08-22，前端 bug）

- **症状**：分镜拖动重排后刷新页面或重启项目，顺序恢复原样（三连反馈）。
- **根因**：前端 shotDrop 用 `shot_number` 传 ordered，但 `renumberShots` 在发送前把镜号重编号成位置序（01,02,03…）→ 后端按"顺序镜号"重建 = 原顺序 → 拖动永远无效。此前两次修复（reorder 写错字段/镜号 zfill）均为必要但不足。
- **彻底修复 = 稳定 uid 机制**（见 #65）。
- **教训**：镜号是"位置标识"（重排必重编号），不能用它传顺序；拖动/排序类操作必须用不随位置变化的唯一标识（uid）。

## 65. 稳定 uid 机制（2026-08-22，核心架构）

- 每镜给稳定唯一标识 `uid`（uuid4 hex[:12]）：build-data-js 读入时补齐（无则生成，编辑稿持久化不重生成）；server handle_shots 编辑稿初始化也补齐。
- **reorder 改 uid 优先匹配**：payload.ordered = 新顺序的 uid 列表；后端按 uid 重建（旧数据无 uid 时降级镜号匹配，zfill 归一化）。
- 前端 shotDrop：`ordered = shots.map(s => s.uid || s.shot_number)`（重编号不影响 uid）。
- 内容级验证：镜01 拖到镜05 后 → 编辑稿第5位=原镜01 内容 ✓ 原始未动 ✓。

## 66. server 启动自愈：编辑稿回填（2026-08-22）

- 问题：磁盘 shots.json 镜号格式（"1"）与 SQLite（"01"）曾不一致 + 重启链路有丢失窗口。
- 修复：server `__main__` 启动时扫描各集 `shots.edited.json` → 回填 SQLite `edited_shots`（只要磁盘编辑稿在，重启/覆盖都丢不了）；build 读入时镜号统一 zfill(2) 归一化。

## 67. 制作页场景名显示（2026-08-22）

- 每镜新增 `scene_name`（SC 编号 → 场景资产名）；ep 透传 `scene_map`。
- 显示链路三级兜底：`scene_name || scene_map[scene_tag] || scene_tag`；旧编辑稿缺 scene_name → build 给 edited_shots 也补。
- scene_map 契约见 scene-assets.md §D4（必须覆盖该集全部 SC，无映射=缺项退回）。

## 68. 生图自动注入资产引用（2026-08-22）

- 首帧/尾帧生成弹窗（openGenModal cat=firstframe/tailframe）自动：
  1. 提示词开头插入 `角色名=图1 场景名=图2` + 换行（角色取出场人物、场景取 scene_name）；
  2. 自动 fetch 角色/场景资产图垫参考图（`fetchAsDataUrl` 通用函数——原 blocking 分支引用的同名函数从未定义，本次补定义）。
- 参考图顺序 = 提示词图号顺序（images[0]=图1 角色、images[1]=图2 场景…）。

## 69. 四视图引用 + 按分镜选身份（2026-08-22 用户拍板）

- **引用图改为身份四视图（sheet_image）优先**，无四视图降级身份定妆照（idn.image）/角色主图。
- **多身份选择**：新增通用函数 `pickIdentityByText`——镜头全文本（characters+visual+action+dialogue+narrative）四级匹配：身份全名 → 短名（去角色名前缀/去身份·造型·装尾缀）→ 短名 2+字连续子串 → 兜底第一身份。
- 验证：文本含身份特征词 → 命中对应身份；无信号 → 兜底第一身份。

## 70. 角色别名机制 aliases（2026-08-22）

- **问题**：角色资产名带职称前缀（如「服务生小王」）vs 分镜 characters 字段用简称（「小王」），完整名包含匹配失败（镜34 该角色未引用）。
- **修复**：registry characters 补 `aliases`（职称+名类角色如「服务生小王」→["小王"]、律师类→["X律师","老X"]、老板类→["X总"]、群演类→["路人"…]，其余空数组）；build 透传；前端匹配 = 资产名或别名包含于文本。

## 71. 注入数据源不一致修复（2026-08-22）

- **问题**：openGenModal 首帧/尾帧注入读 `_ep.shots`（原始数据），而页面显示用编辑稿（edited_shots）——编辑稿改过的出场人物（如镜05 编辑稿 "CH-02 角色B、CH-01 角色A（幻想）" vs 原始 "CH-01 角色A"）被漏引。
- **修复**：注入改 `_ep.edited_shots || _ep.shots`（与前端显示一致）。
- **教训**：前端任何"按当前镜头取数"必须与显示数据源一致（编辑稿优先）。

## 72. 任务队列垫图数显示（2026-08-22）

- **问题**：任务卡 `垫图数=${t.images || 0}`——t.images 是数组，直接显示数组内容。
- **修复**：`Array.isArray(t.images) ? t.images.length : (数字 ? t.images : 0)`。

## 73. 编辑功能迁移：分镜脚本页 → 制作页（2026-08-22 用户拍板）

- Tab1 分镜脚本：去掉行内编辑（✏️编辑/💾保存/✖取消/行级↺重置），操作列只留 🗑删除；保留拖动重排/添加/整集重置。
- 制作页 📄分镜（11 字段）：标题行加「✏️ 编辑」→ 全部字段变 textarea 可编辑（含「时长（秒）」共 12 字段 XJ_MAKE_FIELDS），按钮变【💾 保存】【✖ 取消】；保存走副本机制 → /shots/save；翻镜自动退出编辑态。

## 74. 场景资产补建规则（2026-08-22，摘要登记）

- 完整规则见 scene-assets.md §D（D1 必须建：主叙事/关键戏/视觉锚点/情绪承载/镜数≥2；D2 唯一可省需登记；D3 补建五步；D4 scene_map 契约）。
- 本次为示例项目补建 11 场景资产（registry + asset-prompts.md + scene_map），build 后 scene_name 未映射镜头 = 0。
- **教训**：registry 的 prompt 字段不生效，提示词必须写 asset-prompts.md（build 按标题匹配）。


## 75. 资产下载窗口（2026-08-22 用户需求）

- 顶部新增「📥 下载」按钮 → 资产下载弹窗（gen-mask 复用参考图窗口样式）：6 Tab【角色（主图+身份定妆照+四视图）/道具/场景/首帧/尾帧/视频】、最右【☑ 全选】（仅当前 tab）、底部计数+【⬇ 下载选中】。
- **tab 级隔离（★ 用户拍板）**：切换 tab 清空全部勾选、下载只打包当前 tab、不持久化（窗口关闭/刷新即清空）。
- 后端 POST /download-zip：paths → zipfile 打包；**zip 内扁平化**（arcname 只留文件名，重名自动加 (N) 序号防覆盖）。
- 勾选局部更新卡片样式（不重建 grid）；窗口图片用稳定 src（防 imgSrc 时间戳全量重载闪烁）。

## 76. 顶部改造 + fillTopbar 封装（2026-08-22）

- 顶部按钮区：去【更新】span；「第x集」→「共x集」；新增【📥 下载】。
- **fillTopbar() 封装**（★ 数据加载完成后调用，防顶层执行 P 为空导致空白）：填 顶部 h1 / **浏览器标题 document.title** / **左侧栏 .sb-prof-name 项目名** / 风格 style_label / 共x集。
- 背景：index.html 模板占位符 {{项目名}} 初始化漏替换会字面显示 → JS 兜底三处覆盖（含 .sb-prof-name 与 <title>）。

## 77. 画面标注功能（2026-08-22 用户需求，移植 xiaji-conductor 模板适配虾镜 shots）

- 制作页右列**第 4 产物组【📌 画面标注】**（放首帧上方）：缩略图 + 标注按钮 + 状态提示。
- **ann.js 移植适配**（模板 beat 版 → shots 版）：Canvas 工具全量（文字/编号/圆/矩形/画笔 + 🖱选择拖动缩放 + 缩放/空格平移 + 全屏 + 撤回 + 🎬场景选底图）。
- **底图规则（★ 用户拍板）**：有标注图→加载它；无→有首帧图→首帧；无→**所属场景正面资产（views.正面）→ 场景主图** → 无则提示手动选。
- **保存**：/save-annotation（适配 shot_number，兼容 beat_number）→ 写 `assets/ep{NNN}/annotation/shot{N}-annotated-{ts}.png`（清理该镜旧文件，无历史）→ SQLite 写 edited_shots||shots 的 annotated_image + 磁盘 shots.json。
- **生图引用（★ 用户拍板）**：首帧/尾帧自动引用标注图，**顺序 = 角色资产图1..N → 场景图N+1 → 画面标注图最后**（提示词「画面标注=图N」+ 自动垫参考图）。
- build 反推：shots 扫描 `assets/ep{NNN}/annotation/shot{N}-annotated-*` 最新一张 → annotated_image。

## 78. 任务栏 badge 与按钮重叠（2026-08-22）

- 根因：.tb-mini（"▾任务队列"）是 position:absolute 右上角，覆盖文档流中的 .tb-badge 紫色数字。
- 修复：①.tb-badge 加 position:relative + z-index:2（提升层叠）；②用户方案：.tb-mini padding-left:20px（文字右移避开 badge）+ padding-right:45px（保点击区）——已同步模板。
- 教训：绝对定位元素与文档流元素重叠时，先查层叠顺序（position/z-index），再考虑间距。

## 79. 启动项目台.bat 双击报错"系统找不到指定的路径"（2026-08-24 实战）

- 症状：双击 `启动项目台.bat` 后 cmd 窗口报"系统找不到指定的路径"，随后所有命令（echo/netstat/findstr/timeout/taskkill）都被识别为"不是内部或外部命令"。
- 根因：原 bat 用 `chcp 936` + 中文注释/提示。在 Windows 11 默认启用"全局 UTF-8（Beta）"代码页的机器上，`chcp 936` 切换令后续 UTF-8 编码的中文注释字节错位，整批命令被 cmd 当成外部命令去解析 → 全部失败。另一诱因：`where python` 可能命中 `WindowsApps\python.exe` 桩程序（一闪打开商店）。
- 修复（已固化模板）：① `启动项目台.bat` 改为**纯 ASCII**（去除所有中文注释/提示，`{{项目名}}` 占位符保留且 ASCII 安全），任何代码页下都不错位；② python 改为**绝对路径优先**（C:\Users\123\.workbuddy\binaries\python\versions\3.13.12\python.exe → envs 兜底 → 系统 python），绕过 WindowsApps 桩；③ 启动方式改为 `start ""` 后台启动服务 + 轮询端口就绪后再开浏览器（避免浏览器抢跑/窗口阻塞）；④ 新增 `启动项目台.ps1`（PowerShell 版）作保底，彻底绕过 cmd 编码问题，用户右键"运行 PowerShell"即可。
- 模板修改铁律⑦已同步更新：bat 必须纯 ASCII 写回，禁止 `chcp 936` + 中文混合。

## 80. 知识图谱节点无名称 / 连线不显示（2026-08-24 实战）

- 症状：HTML 项目台知识图谱——节点只有圆点没文字；点之间无线（线全堆在原点）。
- 根因：前端 `xialiao.js` 强依赖特定字段名，而生成 `world.json` 的数据源用了错的名字：① 节点渲染文字读 `n.label`，但数据源只给了 `name` 没给 `label` → 文字空；② 连线 `kgUpdateEdges()` 用 `line.dataset.from/to` 匹配节点，但边数据写的是 `source/target` → 查不到坐标 → 线不设置坐标（默认 0,0 不显示）。
- 修复（已固化 SKILL.md 数据契约段）：① 知识图谱节点对象必须含 `label` 字段（渲染用，建议 `name` 并存但 `label` 必填）；② 边对象必须含 `from`/`to` 字段（NOT `source`/`target`）；③ 主角布局可选：将主角节点 x/y 固定中心 (600,360)，其余按亲密度分层放射。生成脚本 `build_world.py` 已按此契约产出。
- 教训：模板前端字段契约是权威，生成数据源时必须对齐，不能凭直觉命名（曾凭印象用 name/source/target 导致两个渲染 bug）。

## 81. build-data-js.py 因 ep 目录存在但无 shots.json 崩溃（2026-08-28 实战）

- 症状：`outputs/xiajing/ep001/` 目录已创建（如放置 checkpoint-A.md 检查点文档），但尚无 shots.json/beats.json 时跑 `build-data-js.py` 报 `NameError: name '_scene_map' is not defined`（line ~291）。
- 根因：`_scene_map`/`_ch_map` 只在 `shots.json` 存在且解析成功的分支定义；ep 目录存在但无 shots 数据时走 except/beats 分支，两变量从未初始化 → 组装 episode 对象时 NameError。此前 build 成功是因为 outputs/xiajing 目录整体不存在（ep_dirs 为空不进入循环）。
- 修复（已同步模板 templates/build-data-js.py + 项目副本）：except 分支与 beats 分支初始化 `_scene_map, _ch_map = {}, {}`。
- 教训：ep 目录生命周期先于 shots 数据（检查点文档先行）是正常状态，build 必须容忍"有目录无数据"；模板兜底初始化要覆盖所有分支。

## 82. 新模块接入：落库与前端刷新「成对」缺失（2026-09-01，★ 事故固化）

- **症状一**：新模块（项目实例：听风电影）生成空间拓扑图成功、任务队列显示完成，但 SQLite 快照空白/资产位无图。
- **根因一**：server.py mark_ready 只加了新 category 分支（写内存），`if changed:` 落库清单漏加新模块 db_upsert——任务完成但数据永不落库。
- **症状二**：落库修好后，生成完成仍不立即显示，刷新页面才出现。
- **根因二**：前端 gen.js `rerenderCurrent()` 只按既有 section 分发，漏新 section 分支——markReadyInMemory 已写入内存但页面不重绘。
- **修复**：①落库清单补新模块 db_upsert；②rerenderCurrent 补 `else if(curSection==="新section"){ 重绘该页 }`；③已生成的数据直接补写 db。
- **教训**：**新模块接入 = 前后端各一处「成对」**：后端 category 分支 + 落库行；前端 侧栏入口 + renderSection 分支 + rerenderCurrent 分支（含 markReadyInMemory 分支）。任何一处只做一半，症状不同但都指向"任务完成却看不到"。自检清单见 SKILL.md §6.1。
- **同日顺带教训**：①端口迁移（8317→8318）必须全链路一致（bat 启动参数 / 自动打开的 URL / 文档），半改会出现"服务已启动但浏览器打开旧端口"；②模板同步状态：模板 gen.js 已补 `/api/data` no-store、模板 xiajing.js 已补动态风格（xjStyleInstructions/xjAvoidInstructions 从确认风格读取）+ 引用行列组内全部场景 + H3 场景全列；**空间拓扑图 / 听风电影为项目级功能，未回写模板**——后续需要时统一回写，回写按双向复制纪律清理占位符。

## 83. 分镜主力线字段：后端保存覆盖 + 前端设置 UI 缺失（2026-09-01 实战）

- 症状：SKILL.md §0.7 规定 `img_config.json` 的 `storyboard_main_line`（tingfeng/xiajing，默认 tingfeng）为分镜主力线；但① 项目 img_config.json 无此字段；② 后端 `handle_gen_config_save` 重建 cfg 时只保留 4 键（channels/sizes/default_sizes/video_model）——即使手写进 json，前端保存设置也会覆盖丢掉；③ 前端设置弹窗无主力线选择 UI，AI 侧只能手改配置文件。
- 修复（已同步模板 + 项目）：① `img_config.json` 增加 `"storyboard_main_line": "tingfeng"`；② server.py `handle_gen_config_save` 增加保留逻辑（patch 传值仅接受 tingfeng/xiajing，否则沿用现有值，缺省默认 tingfeng）；③ 前端 index.html 设置弹窗加「🧭 分镜主力线」块（`#set-main-line`），gen.js 加 `genMainLine` 变量 + `MAIN_LINE_OPTIONS` + `renderMainLineSelect()`（openSettings 读取、commitChannels 提交、initVideoModel 启动同步）；④ 模板/项目 index.html 的 gen.js `?v=` 递增为 20260901a（防浏览器缓存旧 JS 报 renderMainLineSelect not defined）。
- 教训：**配置字段若想被前端保存不丢，必须在 handle_gen_config_save 的 cfg 重建里显式保留**——这是"写 json 会被覆盖"的经典坑位，与 default_sizes 合并、video_model 保留同一模式；新增设置项 = 后端 cfg 重建保留 + 前端渲染 + 前端保存三处成对。

## 84. 项目台默认端口 8317 → 8320 全链路迁移（2026-09-01 实战）

- 需求：项目台端口从 8317 换为 8320。
- 改动（项目 + 模板双向同步，零残留验收）：① `server.py` 默认 PORT 8320（+文件头注释）；② `启动项目台.bat` 全部 8317→8320（清端口 netstat / 启动参数 / 打开 URL / 提示语）；③ `启动项目台.ps1` 的 `$Port = 8320`；④ 前端 js/gen.js 2 处静态模式提示 URL + js/init.js 1 处迁移提示 → 8320；⑤ 模板 index.html 的 gen.js/init.js `?v=` 递增（20260901b）；⑥ SKILL.md §1.4 目录结构与双模式说明的 8317→8320。platform-fixes.md 历史条目中的 8317 为历史修复记录，保留原样不改。
- 教训：端口迁移涉及 5 类位置（server.py 默认值+注释 / bat / ps1 / 前端提示文案 / 文档），只改一处会导致"服务起来了但浏览器/提示还指旧端口"；改完必须 `grep -rn 8317` 零残留 + `netstat` 确认旧端口无占用（若旧服务进程残留需 taskkill 清理）。

### 82b. 听风电影模块回写模板（2026-09-01 晚，#82 遗留项闭环）

- **背景**：#82 记录「拓扑图/听风电影/主力线为项目级功能，未回写模板」；用户指出其他项目做听风电影无法集成进项目台 → 当晚全部回写。
- **回写清单（templates/）**：① `js/tingfeng.js`（整文件，内置 TF_SPACE_MAP_PROMPT 通用骨架已占位符化——原块是 ep001 布局残留，属项目数据）；② index.html 侧栏「🎬 听风电影」入口 + script 标签 + 版本号（gen/core/tingfeng → 20260901c）；③ core.js renderSection 补 tingfeng 分支；④ gen.js 补 markReadyInMemory 的 tingfeng/tf_space_map/space_map 三分支 + rerenderCurrent 补听风分支 + updateMainLineBadge（⭐ 侧栏标注，变量适配 genMainLine）；⑤ server.py 补 CATEGORY_DIRS 三类目、mark_ready 三分支、`if changed:` 补 db_upsert("tingfeng")（§6.1 成对）、/gen-video 与 /story-video-delete 的 module 路由、_save_generated_video/_mark_video_ready_in_db 的 module 参数、gen-config 返回 storyboard_main_line；⑥ build-data-js.py 补 tingfeng 组装（outputs/tingfeng/ep*/tingfeng.json + db merge storyboards/space_map/space_map_prompt）+ xiajing 拓扑图 merge + identities chapter_range/evidence 透传。
- **虾塘确认门分支（SKILL.md 同日）**：§0 模块表新增听风行、§0.7 新增「确认门二选一（AskUserQuestion，推荐项=设置主力线，禁止默认静默走线）」、§1.1 第 3 步改二选一、§5 新增选线指令两行、§2 新增分镜线分支登记、§4 决策点加分镜线。
- **验证**：node --check ×3、py_compile ×2 过；项目词复扫（含堂屋/卧房/鱼筐等拓扑词）=0；占位符 {{项目名}} 分布完好（index 3/server 3/gen.js 2，bat 用 {{TITLE}}）；db_upsert("tingfeng") 3 处。
- **教训**：项目级功能定型后应**尽快回写模板**，拖到下次「其他项目要用」才回写 = 返工成本翻倍；回写时反向排查模板已有的部分回写（本次主力线已被另一会话先行回写且变量名不同 genMainLine vs storyboardMainLine——回写前必须先 diff 盘点现状，避免重复或冲突）。

## 85. 视距/航拍变体：命名正则前后端必须成对扩展（2026-09-01 晚，★ 功能固化）

- **背景**：视距窗口新增航拍系 4 选项（航拍/45°航拍/高航拍/45°高航拍，用户钦定提示词）。选项名含 `°` 且非「前移X米」格式——mark_ready scene 分支的 dists 正则 `^(.*?)-([^-]+)-(前移|后移)(\d+米)$` **匹配不到航拍名 → 生成成功但永不落库，刷新即丢**。
- **修复**：后端正则扩为 `^(.*?)-([^-]+)-((?:前移|后移)\d+米|(?:45°)?高?航拍)$`（_dk 改为单 group(3)）；**前端 gen.js markReadyInMemory 同步同一正则**（内存写不进 = 完成后页面不更新）。build-data-js 的 scenes merge 已含 dists/dists_ready（重建不丢）。
- **教训**：①「命名类产物」的匹配正则在 server.py（落库）与 gen.js（内存）各一份，**扩展命名时两处必须同一正则改**——只改一边的症状是"任务完成但看不到"，与 §6.1 落库配对同理；②新增带特殊字符的命名选项，先查后端 name 白名单正则（° 已在 #11/#33 扩过）。

## 86. 👀 按钮不可见——CSS class 复用导致绝对定位重叠（2026-09-01 晚，★ UI 纪律）

- **症状**：场景图新增 👀 切换视角按钮后，用户重启+无痕模式都看不到；服务端 curl 字节级对比确认 JS 已是新版（非缓存）。
- **根因**：👀 按钮复用了 👁️ 视距按钮的 `.sv-dist-btn` class——该 class 绝对定位 `bottom:15px left:15px`，**两个按钮完全叠在左下角同一点**，DOM 靠后的 👁️ 把 👀 盖住。代码全在页面上，只是视觉被覆盖，无任何报错。
- **修复**：新增独立 `.sv-sv-btn`（右下角 bottom:10px right:10px 蓝色圆形，原「设为正面」空位）；👀 改用新 class；css/main.css（项目+模板）同步加规则；css 与 js 版本号一起递增。
- **教训**：①**同一卡片上的绝对定位小按钮，每个必须独立 class/独立角位**——复用 class = 同位互盖，静默无错极难排查；②排查「页面上没有 X」先用 curl 拉服务实际返回做字节级对比（排除服务/缓存因素），再查 CSS 层叠——DOM 里有但看不见，十有八九是定位/层叠问题。

## 87. 批量生定妆/批量生四视漏同步模板（2026-09-02，★ 多源同步遗漏自查）

- **症状**：用户主动核查发现——项目 xiatang.js 角色页顶部有 🎭 批量生定妆（`batchGenIdentities`）/ 🀄 批量生四视（`batchGenIdentitySheets`）两按钮 + 完整实现（2026-08-28 新增），**模板完全没有**（模板只有基础 `batchGenImages`）。
- **根因**：2026-08-28 项目侧新增时未回写模板，也未登记 platform-fixes——功能定型与模板回写之间没有强制对账动作，靠用户肉眼捕获。
- **修复（templates/）**：① xiatang.js 角色页按钮区插入两按钮（原样含渐变样式）；② 单角色生四视图函数后插入两函数全文；③ index.html xiatang.js 版本号 20260901h → 20260902a。依赖零缺口：`batchEnqueue`/`findCurrentMainImage`（gen.js）、`IS_SERVER`（core.js）、`IDENTITY_SHEET_PROMPT`（xiatang.js:7）模板本就齐备，node --check 过。
- **教训**：项目侧新增用户可见功能时，**当次任务内必须同步回写模板并登记**——「先做项目里用，等下次想起来再回写」必然产生同步遗漏（本条即第 3 次同类遗漏：#82b 听风、#85 航拍正则、本条批量按钮）。用户核查机制有效但不应作为唯一防线；每次改完项目 js/后端，自查清单固定加一条：模板同名文件 diff。

## #88 模板→项目同步：批量生定妆/批量生四视（2026-09-02 18:22）
- **症状**：阴符箓-2 项目台角色页无「🎭批量生定妆」「🀄批量生四视」按钮（项目 project/ 为 14:05 复制的旧模板；功能 2026-08-28 在某项目新增、2026-09-02 才补同步进模板 templates/js/xiatang.js #87）
- **同步**：备份 project/{index.html,server.py,js} → project_backup_20260902_1800/ → 覆盖 index.html/server.py/js/xiatang.js/js/gen.js（core.js/css 无差异不动）→ node --check 语法 OK → 重启服务
- **坑 1（cp 目标路径）**：`cp T/js/a.js T/js/b.js P/` 会把 js 文件复制到 project 根而非 js/ 子目录——多源 cp 到目录时目标必须是 `P/js/`
- **坑 2（占位符覆盖，双向复制纪律）**：同步覆盖 server.py/index.html/js/gen.js 把初始化时替换好的「阴符箓」带回了 `{{项目名}}`（/api/info 复现）——**模板→项目同步后必须重跑剧名占位符替换 + grep 零残留 + /api/info 验证**，本项目已重替（server.py 3 位/index.html 3 位/js/gen.js 1 位）
- **验证**：/api/info project=阴符箓 ✓；?v=20260902a 新版本号（缓存刷新）✓；服务端交付的 xiatang.js 含 batchGenIdentities/batchGenIdentitySheets ✓；SQLite 数据层（img_config.json/xiaji.db/assets）未动完好 ✓
- **文档滞后教训**：判断"模板有没有某功能"必须 grep 模板代码，不能只看 SKILL.md 旧段落（本次 SKILL.md 340 行已有 #87 描述、339 行残留旧句已修正）

## 89. 听风 H3 双模型提示词：h3 槽位曾是假数据（2026-09-02 晚，★ 方案A 功能固化）

- **症状**：听风生视频弹窗能选海螺 H3 模型、提示词也有 `video_prompts.h3` 槽位，但切到 H3 拿到的仍是 Seedance 格式中文全文——`tfEnsureVP` 懒装填 `h3 = seg.video_prompt` 是**假 H3**（Seedance 文本原样复制），整条听风线没有任何 H3 构建函数。
- **修复（方案A，项目+模板双修 tingfeng.js）**：① 新增 `buildTfVideoPromptH3(ep, seg)`——对齐虾镜 buildStoryVideoPromptH3 六段式骨架（subject_definitions / summary / retention_analysis / detailed_description / overall_soundscape / non_diegetic_music），听风数据适配：引用行「名字=图N」解析（正则 `([^=\s，,]+)=图(\d+)`，兼容空格/逗号分隔）→ `<Subject N>`，分类 character/scene/prop/**spatial（空间拓扑图=空间锚点硬约束：blocking/移动方向/空间关系必须遵循布局图——听风防穿帮核心价值带进 H3）**，Subject 编号=图号（与 tfAutoRefs 垫图顺序同源）；video_prompt 自带的【STYLE】英文风格段直接搬入 detailed_description 头部（懒惰正则止于 `\n## ` 或【NEGATIVE】，注意不能懒到文末）、【NEGATIVE】并入尾部 `Style guardrails (must obey):`；逐镜用 shots 的 ts（"0.0s–3.5s"）起始做 `[Shot N] At MM:SS.mmm` 时间轴（解析不出按 duration/镜数均摊），`Frame/Camera/正文/Dialogue/Sound` 拼接，visual/dialogue 用 `-\s*(音效|对白)[^：]*：` 清理混入尾巴（音效对白有独立字段不丢内容）；无 shots 兜底取 video_prompt 正文（## 起、NEGATIVE 前）。② `tfEnsureVP` 签名 `(seg)` → `(ep, seg)`，h3 为空实时构建回写（对齐虾镜"旧数据实时候算"模式）；三个调用点（openTfVideoModal/tfGvStart/tfBatchGenVideo）同步传 ep，批量生视频同样按当前模型取词。③ 版本号：项目 20260901r→s、模板 20260901c→s（对齐）。server.py 不动。
- **验证**：node --check ×2 过；用 ep001 真实 video_prompt + shots（读 xiaji.db snapshots）在 Node 沙箱实测构建产物——六段齐全、Subject 1-4 分类正确（拓扑图=spatial）、visual 混入的「- 音效/- 对白（画外）」尾巴已清理、独立 Sound 字段保留、At 00:03.500 时间轴正确、STYLE 段搬运成功。
- **教训**：①「双模型槽位」的懒装填若只复制另一模型的文本 = **假双模型**，用户切模型拿到错格式提示词且无任何报错——槽位初始化必须走真实构建函数、为空实时候算（虾镜 xjShotVPArr 模式），新线集成双模型功能时直接抄虾镜模式而不是"先占坑后补"；②听风 video_prompt 自带【STYLE】/【NEGATIVE】段，H3 化时应搬运而非丢弃（丢 NEGATIVE 会风格漂移）；③懒惰正则 `【STYLE】([\s\S]*?)(?=\n## |【NEGATIVE】|$)` 的 lookahead 必须含 `\n## `，只写 `$` 会懒到文末把正文全吞进风格段；④真实数据实测（Node eval 抠函数 + db 读 ep001）能在交付前抓住正则/清理逻辑的隐性 bug，比纯语法检查可靠。

## 90. quality-spec 挂载 + H3「同步双产」定稿 + 函数初稿 v2（2026-09-02 晚，★ 用户两轮拍板）

- **背景**：用户拿 `H3提示词转化` skill 的 quality-spec.md（九类翻车点硬规则）审查 #89 的 buildTfVideoPromptH3——9 节踩 7：中文正文（§1）/ `Frame:/Camera:` 字段残留（§1）/ 台词四件套缺失（§2）/ 拓扑图写成 `<Subject 4>` 应为 `<Picture N>` 规划参考立条（§3）/ retention 四行复制同一模板句（§4）/ 【NEGATIVE】并入正文违反「FORBIDDEN 一律不写」（§6）/ soundscape 指针式空转 `listed with their shots above`（§7 点名反例）。
- **规范挂载（用户指令）**：quality-spec.md 一字不改副本 → `modules/storyboard-cinematic/references/`；storyboard-cinematic SKILL.md 新增 §1.9 + references 表 + 自检清单 H3 合规项；主 SKILL.md 同步。
- **流程定稿（用户两轮拍板）**：**同步双产**——Stage 2 生成每段视频提示词时同步产出 H3 六段式（一次双份、禁止事后补转化）；字段契约 = 每段 `video_prompt` + `video_prompts.h3`；独立交付 md/html 每段双块双复制按钮；工作台 h3 槽位有值直接采用；质量闸 = quality-spec §9 清单全过。
- **函数初稿 v2（六处修正，项目+模板双修 tingfeng.js）**：①去字段标签→英文引导句 + 景别缩写英译（TF_FRAME_EN：ECU/CU/MCU/MS/WS/ELS）；②台词四件套——说话人 `(Sx)` 按发声顺序分配（dialogue 冒号前解析说话人、括号注释剥离）、「画外」检测写 `says in an off-screen voiceover`、`<d>[Chinese] 原话</d>`、在画角色闭嘴声明（说话人≠在画角色时）；③拓扑图 `<Picture N> is a spatial-planning reference...` 立条（不占 Subject 编号），正文在航拍/俯拍/大远景首镜处引用 + summary 提及；④retention 按 role 分模板（character=外观服装 / scene=地标布局 / prop=外观摆放）+ Picture 规划行写「被遵循的空间关系」；⑤NEGATIVE 丢弃 + STYLE 缺 `infer` 防污染句时补规范标准句；⑥soundscape 聚合各镜音效点名（≤3 条去重）。**附修 v1 丢对白 bug**：v1 的 clean 直接剥掉 visual 尾巴导致「dialogue 字段空、对白混在 visual 里」的段丢失对白（ep001 shot02 实例）——v2 `tfH3SplitTail` 把尾巴拆成 主画面/对白/音效 复用。版本号 20260901s→t 双边对齐；弹窗 H3 分支加初稿提示行。
- **验证**：node --check ×2 过；Node 沙箱 + ep001 数据实测 15/15 项全过（含四件套完整形态 `苏老太 (S1) says in an off-screen voiceover: <d>[Chinese] …</d> while <Subject 1>'s lips remain completely closed.`）。
- **教训**：①审查 AI 产出要用独立权威规范逐条对照而不是自我感觉良好——9 节踩 7 全是「格式对、质量不合格」；②程序转换的硬天花板（中文→英文/拆镜判断）要显式划给 AI 并写进流程（同步双产），不要让兜底初稿冒充终稿；③数据清洗（剥尾巴）前先想清楚被剥内容是否有独立字段承接，没有就是丢数据。

## 90. quality-spec 挂载 + H3「同步双产」定稿 + 函数初稿 v2（2026-09-02 晚，★ 用户两轮拍板）

- **背景**：用户拿 `H3提示词转化` skill 的 quality-spec.md（九类翻车点硬规则）审查 #89 的 buildTfVideoPromptH3——9 节踩 7：中文正文（§1）/ `Frame:/Camera:` 字段残留（§1）/ 台词四件套缺失（§2）/ 拓扑图写成 `<Subject 4>` 应为 `<Picture N>` 规划参考立条（§3）/ retention 四行复制同一模板句（§4）/ 【NEGATIVE】并入正文违反「FORBIDDEN 一律不写」（§6）/ soundscape 指针式空转 `listed with their shots above`（§7 点名反例）。
- **规范挂载（用户指令）**：quality-spec.md 一字不改副本 → `modules/storyboard-cinematic/references/`；storyboard-cinematic SKILL.md 新增 §1.9 + references 表 + 自检清单 H3 合规项；主 SKILL.md 同步。
- **流程定稿（用户两轮拍板）**：**同步双产**——Stage 2 生成每段视频提示词时同步产出 H3 六段式（一次双份、禁止事后补转化）；字段契约 = 每段 `video_prompt` + `video_prompts.h3`；独立交付 md/html 每段双块双复制按钮；工作台 h3 槽位有值直接采用；质量闸 = quality-spec §9 清单全过。
- **函数初稿 v2（六处修正，项目+模板双修 tingfeng.js）**：①去字段标签→英文引导句 + 景别缩写英译（TF_FRAME_EN：ECU/CU/MCU/MS/WS/ELS）；②台词四件套——说话人 `(Sx)` 按发声顺序分配（dialogue 冒号前解析说话人、括号注释剥离）、「画外」检测写 `says in an off-screen voiceover`、`<d>[Chinese] 原话</d>`、在画角色闭嘴声明（说话人≠在画角色时）；③拓扑图 `<Picture N> is a spatial-planning reference...` 立条（不占 Subject 编号），正文在航拍/俯拍/大远景首镜处引用 + summary 提及；④retention 按 role 分模板（character=外观服装 / scene=地标布局 / prop=外观摆放）+ Picture 规划行写「被遵循的空间关系」；⑤NEGATIVE 丢弃 + STYLE 缺 `infer` 防污染句时补规范标准句；⑥soundscape 聚合各镜音效点名（≤3 条去重）。**附修 v1 丢对白 bug**：v1 的 clean 直接剥掉 visual 尾巴导致「dialogue 字段空、对白混在 visual 里」的段丢失对白（ep001 shot02 实例）——v2 `tfH3SplitTail` 把尾巴拆成 主画面/对白/音效 复用。版本号 20260901s→t 双边对齐；弹窗 H3 分支加初稿提示行。
- **验证**：node --check ×2 过；Node 沙箱 + ep001 数据实测 15/15 项全过（含四件套完整形态 `苏老太 (S1) says in an off-screen voiceover: <d>[Chinese] …</d> while <Subject 1>'s lips remain completely closed.`）。
- **教训**：①审查 AI 产出要用独立权威规范逐条对照而不是自我感觉良好——9 节踩 7 全是「格式对、质量不合格」；②程序转换的硬天花板（中文→英文/拆镜判断）要显式划给 AI 并写进流程（同步双产），不要让兜底初稿冒充终稿；③数据清洗（剥尾巴）前先想清楚被剥内容是否有独立字段承接，没有就是丢数据。

## 91. MiniMax H3 官方 API 接入（apiFormat=minimax_h3，替换 888 的 H3 视频路径）（2026-09-02 深夜，★ 新协议）

- **背景**：用户提供 MiniMax H3 官方 API（metaso host）文档截图——建任务 POST `/api/minimax/v2/video_generation`（body: model=MiniMax-H3, content 数组 [text / image_url(reference_image) / video_url(reference_video) / audio_url(reference_audio)], resolution, duration:int, ratio），响应 `{task_id}`（顶层）；查询 GET `/api/minimax/v2/query/video_generation/{id}`，响应 `{task:{status:"queued|running|succeeded|failed", content:{url}(succeeded)}}`；**无独立结果接口**，succeeded 后从 `task.content.url` 下载 mp4。
- **实现（项目+模板双修）**：① api_slot.py：PROTOCOLS 加 `minimax_h3`；endpoint_with_protocol 原样返回（路径自带 /api/minimax/v2）；`_generate_video_minimax_h3` 新函数（建任务 → 8s 轮询 1800s 上限 → succeeded 下载 → failed 带 msg 报错）；test_img_channel 探测分支（假任务 id：200/400/404=连通，401/403=Key 无效）；fetch_models 返回固定 ["MiniMax-H3"]。② server.py /gen-video 协议白名单 `{"minimax_h3","up_lk888"}`。③ 前端：gen.js 新增全局 `pickVideoChannel(channels)`（**minimax_h3 优先、up_lk888 回退**）+ 设置页协议下拉/默认 URL（api.metaso.cn）；tingfeng.js（tfGvStart/tfBatchGenVideo）与 xiajing.js（4 处）渠道过滤全部切 pickVideoChannel；tfBatchGenVideo 对 minimax_h3 渠道直接下发 model="MiniMax-H3"。④ 版本号：gen/xiajing/tingfeng → 20260902b（两边 index.html）。
- **模板同步方式**：模板与项目差异大（历史落后），不能整文件覆盖——写锚点切片同步脚本（api_slot 6 处/server 1 处/gen 2 处 + xiajing/tingfeng 正则 6 处 + 手补 tfGvStart 1 处 + toast/注释 3 处），替换计数校验（计数不符即跳过写入的保护机制这次反而把有效替换挡了——同步脚本对「多模式混合替换」要先核对每处模式再决定期望值）。
- **待实测**：图片 data URI 传法（reference_image 的 image_url.url 用完整 data URI）与 duration 合法值（示例 5）需真实跑一次验证；若上游报图片格式错误，剥 data: 前缀传纯 base64 重试。
- **教训**：①新协议接入用「渠道选择器优先级」而不是硬切换——minimax_h3 没配置时自动回退 888，用户零断档；②同步脚本的多模式计数保护要按模式分别期望，否则一处计数错误会连累全部有效替换被跳过。

## #90 听风故事板默认尺寸绑定「草图·首帧」设置（2026-09-03 11:50）
- **需求（用户拍板）**：听风电影·故事板生图的默认尺寸 = ⚙设置里「草图·首帧」（sketch_frame）的配置值；改前单张弹窗（cat=tingfeng）无尺寸映射→默认落候选第一项 auto、批量 tfBatchGenStory 硬编码 1536x768，都不读设置
- **实现（项目+模板同步改）**：① gen.js `openGenModal` catKey 映射增加 `cat === "tingfeng"` → 查 sketch_frame（单张弹窗默认选中该值）② tingfeng.js `tfBatchGenStory` 读 `cfg.default_sizes.sketch_frame`（兜底 1536x768）③ 设置面板 SIZE_CAT_LABELS 标签「草图·首帧」→「草图·首帧/听风故事板」（联动可视化）④ index.html 版本号 bump ?v=20260903a（缓存刷新）
- **范围**：仅听风线；虾镜故事板（storyGenGroup 读 ds.storyboard_frame||ds.storyboard）与空间拓扑图（tf_space_map→auto）未动
- **注意**：sketch_frame 同管首帧/草图类生成——用户若要故事板横版 1920x1088，需把「草图·首帧」档设为 1920x1088（会同时影响首帧默认值）；template 与项目 gen.js/tingfeng.js 存在 H3 功能分叉（模板更新、项目旧），本次为外科手术式双改，未做整体同步
- **验证**：node --check 两文件 OK；curl 8320 实测服务端已交付新版（含新映射与 batch 读取行）；版本号已刷新


## 92. 资产提示词双语展示（prompt_cn 中文参考稿）契约 + 改一处=改四处同步纪律（2026-09-06b 拍板，★ 2026-09-07 补文档进技能库）

- **背景（差分溯源）**：桌面旧副本 v2.10 与技能库 v3.0 差分显示，`prompt_cn` 双语展示的**前端代码两副本本就一致**（index.html/gen.js/xiatang.js/tingfeng.js 逐字相同），但技能库的**文档层缺失**该功能——`references/project-platform.md` 无双语节、`SKILL.md` §1.4.0 无双语条目与触发词、且 project-platform.md 的模板 JS 清单停在「10 文件」未含 `xiaju.js`。属"文档滞后于代码"，非功能缺失。
- **功能契约（数据层）**：资产类提示词同轮双产——`prompt`=英文生图执行版（唯一进生图链、参与 check-assets 指纹），`prompt_cn`=中文理解稿（**只读、不进生图、不参与指纹**，与资产名/标签同级元数据）。身份图 = `prompt`/`prompt_cn`（定妆照）+ `sheet_prompt`/`sheet_prompt_cn`（四视图卡）；听风 = 集级 `storyboard_prompt_cn` + 空间拓扑图 `space_map[i].prompt_cn`。对译纪律：逐段一一对应、禁增删要素；`prompt_cn` 豁免"英文纯净"。
- **前端四处联动（改一处=改四处）**：① `templates/index.html` 弹窗 `<details id="gen-prompt-cn-wrap">` + `#gen-prompt-cn-body`（无中文整块 `display:none`，不显示空壳）；② `templates/js/gen.js` `openGenModal(cat,name,prompt,ep,promptCn)` 第 5 参、`promptBlockDual(cn,en)`（中文默认展开、英文折叠「🖥 生图执行版（EN）」，任一缺失降级单语不报错）、`genBtn(...,promptCn)` 出 `data-prompt-cn`；③ `templates/js/xiatang.js` 5 类资产全走 `promptBlockDual` + `genBtn` 第 5 参；④ `templates/js/tingfeng.js` 拓扑图卡双语折叠 + 故事板传 `ep.storyboard_prompt_cn`。**调 `promptBlockDual`/`gen-prompt-cn-wrap`/`openGenModal` 任一签名或 DOM id → 四处同步核对，且回写 templates/ 并同步 `xiaji-conductor/templates/`；漏一边表现＝"有中文不显示"或"弹窗无中文参考"（静默失效，无报错）**。
- **只读纪律**：弹窗里手改的是**英文**（`/save-prompt` 写 `prompt`），**中文稿不随英文回写**；要改中文必须改数据层 `prompt_cn` 本身。
- **本次修复（2026-09-07）**：把上述双语展示的文档增量外科式补进 v3 技能库——`references/project-platform.md`（标题 + 双语节 + 触发词 + 10→11 文件含 xiaju.js）、`SKILL.md` §1.4.0（双语 bullet + 触发词）；**未动 v3 打戏（seedance-combat-prompt/battle-learner）结构、未回退成 fight-scene-director、未碰运行中项目**。纯文档补记，VERSION 维持 3.0.0。
- **教训**：①"两副本差分"要分清**代码差 vs 文档差**——本例代码本就一致、只缺文档，处置是补文档而非整包覆盖（整包会用 v2.10 旧结构冲掉 v3 打戏）；②契约文档必须与前端实现同步落地，否则"功能在、文档说没有"会误导后续维护判断是否要重写；③双语这类多端联动，签名/DOM id 任一处改动都需四端 + 双模板（templates/ 与 xiaji-conductor/templates/）同步，缺一即静默失效。
