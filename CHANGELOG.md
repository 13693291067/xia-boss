# CHANGELOG

本文件记录 xia-boss（虾集·总指挥）编排层的规范/流程变更。方法论正文在各 `modules/*/SKILL.md` 与 `references/shared-*.md`，此处只记"改了什么、为什么、影响面"。

---

> **★ 2026-09-09 回填说明（读这三条再看下面的条目）**
> 1. **依据**：以下条目为补记，逐条以**包内可核对证据**（文件头 ★ 标记、带后缀版本标签、契约字段、脚本注释）反推，并在每条末尾列 `证据` 路径；不写包内查无实据的内容。
> 2. **日期**：有 ★ 日期者照记；3.2.0 / 3.2.1 / 3.2.2 包内只有版本号无日期，标「日期未标」不猜。
> 3. **编号约定报备**：`3.4.0` 当次出现**两个并行标签**——裸 `3.4.0`（画面语法横切）与 `v3.4.0-风格库`（虾格风格挂载库，包内 25 处引用）。这是并发会话撞号后按"带后缀不裸用版本号"约定的处置，**保留现状不重编号**：重编号会断掉 25 处已落地的带后缀引用。

## 3.5.11-模板卫生门禁 — 2026-09-10

> 触发：渔村项目接手自检。性质：新增机械门禁 + 模板脱敏，**不动任何生成链与项目产出**。

### 🔴 查出的真问题

1. **模板被本剧剧名写死**：`templates/index.html`（title / 侧栏项目名 / 顶部大标题）与 `templates/server.py`（文件头 / `/api/info` / 启动打印）共 **6 处 `{{项目名}}` 被替换成具体剧名**，占位符计数归零。既有验收「grep `{{项目名}}` 应为空才算替换完成」在这种情形下**天然通过**——污染随每次「复制模板开新剧」静默传染，正是纪律 8「违反后果」写的那种最高级别事故。查证为**未提交的工作区改动**（HEAD 与 origin/master 均为正确占位符），故本次只还原工作区 6 行、不产生提交差异。
2. **模板注释含项目角色名**：`templates/js/gen.js:565` 用真实角色名/身份名举例说明子串误匹配修法 → 已脱敏为 `角色A`/`某某主`。
3. **references 残留项目词（P1，未处置）**：`references/platform-fixes.md`（验证记录引原文）、`modules/storyboard-cinematic/references/quality-spec.md`（台词正反例）命中项目角色名。二者是**证据/示例**性质，脱敏会牺牲可追溯性，留待用户拍板。

### ➕ 变更

- 新增 `scripts/check-template-hygiene.py`：占位符功能位计数（少=被顶掉、多=复制方向反）+ 功能位锚点存在性 + 从项目 `xiaji.db` **动态取词**扫全包（templates/scripts 命中=P0、其余=P1，锚定示例/styles-library/CHANGELOG 按纪律 1 豁免，**脚本内零硬编码项目词**）+ 纪律 8 ⑦⑧（bat/ps1 纯 ASCII、CRLF）一并机械执行；`--selftest` 三例投毒。
- SKILL.md：§0.5 步骤 3 验收升级为跑本门禁；纪律 8 新增 ⑨「机械门禁兜双向复制」。

### ✅ 回归

`--selftest`：污染一处→报、占位符多余一处→报、干净模板→不报，且还原后与原文逐字节一致（exit 0）。真包扫描：还原+脱敏后 **P0 0 / P1 2**（即上述 references 两项）；`py_compile` 过；gen.js 改动仅 1 行注释。

### 📎 证据

- `templates/index.html` / `templates/server.py`（还原前后 `{{项目名}}` 计数 0→3 / 0→3，剧名 3→0 / 3→0）
- `git diff templates/js/gen.js`（1 行注释脱敏）

---

## 3.5.10-拓扑图侧别锁与回填门禁 — 2026-09-10

> 触发：冒烟测试 + 「场景提示词 ↔ 生视频提示词」传递链核查。性质：新增门禁与规范条款，**不动任何既有成图**（三场拓扑图本就未回填，改的是提示词文本）。

### 🔴 查出的两处真问题

1. **镜像侧别错误**：场2 表4 写「CAM1–4 在轴线**北侧**，苏晚晚恒画面右」——但机位在北侧即朝南拍，**面向南时东在画面左**，断言与机位侧自相矛盾；且 51 镜构图字段**零处**画面侧别断言，等于"该锁的写错、该传的没传"，跳轴完全交给模型。
2. **引用齐全而图全空**：三场 `space_maps` 的 `image` 全空、`ready=false`，51 镜引用行却都指向它们；`check-scenes` D 查只看引用行文本、不看图存在性 → **报 0 问题静默放行**。（`check-fidelity ⑫` 其实一直在报，但虾镜阶段门禁跑的是 check-scenes，两闸口径不通。）

### ➕ 变更

- `check-scenes.py` 新增 **D2 查**：被引用的 `空间拓扑图·场N` 必须已登记且 `image` 非空、`ready=true`，否则 P0。三向实测：真项目报 3 条 / 图回填后 0 条（不误报）/ 幽灵引用「场9」被抓。
- `shared-spatial-blocking.md` 新增 **§十六·一 侧别推导律**（机位朝向→画面左右对照表 + 三条纪律：断言前先推朝向、侧别必须落到镜次、改机位侧＝整场重推）与 **§十六·二 D2 由来**。
- 派生脚本补 `same side` / `no text labels` 字面要素（⑫ 靠字面短语判语义，措辞一换即误报——已按 §十 模板词对齐）。

### 📌 项目侧落地（渔村 ep001，方案乙）

- 场2 机位统一改到**主轴南侧半区、朝北拍**：苏晚晚(东)=画面右、苏老太(西)=画面左、陆沉/阿福(南院门)=画面下，断言与机位自洽，且堂屋门口与门槛留在演员身后入画（门槛绊脚戏才拍得出来）。
- 场1 随 DISC-01 裁决连带改判：门由「西墙」移到「南墙居中」，西墙回退实墙，主光方位同步。
- 侧别锁注入 **51 镜 composition + 51 条 video_prompt + 51 条 seedance + 21 条段级提示词**（幂等，已备份）。
- 发现并修正一处双写：`shots.json` 内嵌的 `space_maps` 与 `space_maps.json` 是两份拷贝，改源文件不会自动进 shots —— 已按"json 为源"单向回同步。

### ✅ 回归

`check-scenes` D2 生效（3 条待回填）；`check-fidelity ⑫` 由 8 条降到 3 条（只剩未回填成图）；`check-space-truth` 八道全过；改动前后基线对比确认零新增误报。

### 📎 证据

- `modules/scene-consistency/scripts/check-scenes.py`（D2 段）
- `references/shared-spatial-blocking.md` §十六·一 / §十六·二
- 项目：`outputs/xiajing/ep001/{space_maps.json, shots.json, 空间拓扑图.md}`

---

## 3.5.9-空间基准图并存 — 2026-09-10

> 性质：**纯新增**。既有场景资产（主图 / §A 全景鸟瞰 / §B 九宫格 / §C 总览 / 上帝视角 plan·plan_sketch）与全部既有生图**一概不动**；`plan_sketch` 自动垫图逻辑保留原样，不下线、不降级。

### ➕ 新增（New）

- **空间基准图 layout（第四类场景资产）**：`modules/xiatang-characters/references/scene-assets.md` 追加 §A2——带风格 3/4 轴测 16:9，同时锁布局＋外观，是场景一致性（跨集跨机位）的唯一图级载体。三条实测硬约束：围合四面必填（实测只写西墙、模型必自补东墙）、外部地标方位钉死（实测海被画到东北角且像地上一摊水）、基准图不携带时段（影子方向归镜次）。反增殖定为共识投票：同词出 3~4 张取共同物件，比对基准=物件集合**相等**（多一个就报，不是"包含"）。
- **真理图数据化＋八道门禁**：`modules/scene-consistency/scripts/check-space-truth.py`（新文件）——G1 出处必填／G2 围合四面／G3 海向可达／G4 方位词表／G5 基准光无时段／G6 物件白名单闭合／G7 确认门／G8 跨母版同名锚点自洽。`--selftest` 内置 11 个投毒样本＋1 干净样例，实测全命中（防空转门禁）。
- **派生单源脚本**：`modules/scene-consistency/scripts/gen-layout-prompt.py`（新文件）——从 `space-truth.json` 逐字生成 layout 双语提示词与拓扑图锚点带（`--topology-band`），两条链不再各写一遍；FS 风格段经 `--fs-from-keyscene` **逐字**取合同「风格质感：」行（实测手抄删减会让画风漂向写实）；`approved != true` 拒绝出词。
- **真理图模板 §六**：追加"本层不出图"实测裁决（出图空间增益为零、且与 layout 双写）＋ json 契约要点＋沉默规则（原文沉默＝无开口实墙，防"海景窗"）。
- **四层权威表**：`references/shared-spatial-blocking.md` 追加 §十六（真理图／基准图／拓扑图／氛围图职责与"病-图"分诊），并暂挂拓扑图 §十 实测补丁三条（轴线无箭头／图上禁人名／副轴灰虚线），待 §十 修订时并入。

### 📌 真例（渔村 ep001 首跑即抓到东西）

- `outputs/xiajing/ep001/space-truth.json`（新文件）：四母版、围合四面、海＝南门外（L13）、物件白名单、光态与边界类锚点以 `role` 排除于基准图。
- **DISC-01（已裁决 2026-09-10）**：SC-01 记「西墙屋门→通院」vs SC-02 记「屋门朝南开→门槛→院心」且居中——同一扇门两处方位互斥，由 G8 跨母版自检浮出。用户裁决＝**门在屋子南墙居中**：SC-01 S 面改 door、W 面回退实墙、新增 `south_window` 锚点、adjoin 出射墙改 S↔N，`approved=true` 已解锁派生。遗留人工待办：`checkpoint-A.md` 原文「西墙屋门→通院」一行需订正，S003/S026 入画方向按南墙门复核。
- 首跑门禁另抓 4 条真缺陷（母版缺白名单／锚点未入册／「柴堆-干柴捆」别名漂移／光态混入物件），均已回写修正——证明门禁对本项目有效而非只挡构造样例。

### 🔍 同日自检修复（自查抓出四处自身缺陷）

1. **派生脚本不认 `sides`**：`enclosure_lines` 只读 `enclosure`，`linear`/`open` 母版（SC-03/SC-04）被派生成"四面皆无"的垃圾段——门禁放行、派生输出空话。已改为按 kind 回落 `sides`+`axis`；视角也随母版类型走（线性空间沿通路轴向看，不再一律"南侧朝北"）。
2. **`空间真理图模板.md` 历史未闭合围栏**：§2 模板骨架的 ``` 块内含 ASCII 图的嵌套 ```，致 §三/§四/§五 三张表整体被吞进代码块（**该缺陷在本次改动前即存在**，我追加的 §六 恰好落进同一个块里）。已把外层改四反引号并在 §五 末尾正确闭合。
3. **口径错字**：门禁实为 G1~G8 八条，文档／docstring／打印语四处误写"七道"，已全部订正。
4. **G8／G3 规则自身缺陷**：共享门在两空间内方位本应相反（屋南墙＝院北缘）被误报为冲突；海向可达被误套到室内母版。均已修，自检扩为 11 投毒＋1 干净＋**1 合法反向正面用例**（防"修过头变成永远不报"）。

### 📎 证据

- `modules/xiatang-characters/references/scene-assets.md` §A2（文件尾）
- `references/shared-spatial-blocking.md` §十六（文件尾）
- `modules/scene-consistency/references/空间真理图模板.md` §六（文件尾）
- `modules/scene-consistency/scripts/check-space-truth.py`、`gen-layout-prompt.py`（新文件）

---

## 3.5.8-虾镜空间拓扑图接线 — 2026-09-09

主题：把**空间拓扑图（调度层）**接进虾镜，让 51 镜引用行的「空间拓扑图=图N」不再悬空（此前虾镜只有文字空间真理图=布局层，无调度层拓扑图资产）。
- **改法**：① 新增机读单一真源 `space_maps.json`（每场 name/scene/prompt 英文生图/prompt_cn 中文/image/ready + scene_to_map 映射），配套人读四表见项目 `空间拓扑图.md`；② 虾镜 `build_prompts` 读它，给每镜打 `space_map`（所属场），引用行末位由通用「空间拓扑图」改为**场名「空间拓扑图·场N」**（多镜段列段内涉及的场），STYLE LOCK 锚定行同步；③ `build-data-js` 透传 ep 级 `space_maps` + 镜级 `space_map`（scripts/templates/项目三副本同步）；④ `check-scenes.py` D 查放宽为**前缀匹配**（`空间拓扑图·场N` 视为合法拓扑图引用且须末位）。
- **影响面**：check-scenes.py（D 查）+ build-data-js.py 三副本；虾镜 build_prompts/space_maps.json 为项目侧。证据：ep001 三场（场1屋子/场2院子/场3村道树后）拓扑图四表+双语生图提示词已产，caps 对齐，引用行末位=场名，保真门禁 PASS、场景一致性 A/B/C/D=0。
- **待办**：三场拓扑图 `image/ready` 仍空——需按 prompt 生图后回写，前端方可真正垫图（当前"存在才引用"会跳过空图，不报错）。

## 3.5.7-制作故事板同源 — 2026-09-09

主题：让**制作页（单镜）与故事板（多镜）的生视频提示词同源**——同一 STYLE LOCK 模板，唯一差别是镜数与 Shots 模式（用户纠偏：不该是两套不同质量的生成器）。
- **背景**：制作 video_prompt 是离线定稿（精细 STYLE LOCK），故事板是前端 `buildStoryVideoPrompt*` 实时粗拼（引用行+每镜一行摘要）→ 不同源、详略不一致。
- **改法（离线为唯一源，seedance-only）**：① 新增共享配置 `outputs/xiajing/storyboard-config.json`（board_max/board_min/seg_max_s），前端 `storyBoardSplit`/`splitStory15s` 与离线 `build_prompts` 都读它（经 build-data-js 注入快照）；② 离线 `build_prompts` 用同一 `build_video_prompt(shots[], mode)` 既产单镜稿（写 `shot.video_prompt`+`video_prompts{seedance,h3}`）又产每板 ≤15s 段稿（写 shots.json 顶层 `storyboard_video_prompts`）；③ `build-data-js` 透传 config + 段稿，按板号权威合并进 `ep.storyboards[].video_prompts`（旧快照 merge 仅在离线缺时兜底）；④ 前端故事板改为**离线段稿为准**（有 seedance 直接读、按 seg_ranges 建视频段，不再实时重算），并加**段边界一致性自检**（离线 seg_ranges vs 当前镜独立切段不符则提示重跑）。
- **对齐 3.5.6 STYLE LOCK 规范**：段稿/单镜稿统一——台词 `{}`、音效 `<>`、BGM `（）`（shots.json dialogue 仍「」，保真门禁不受影响）；一镜到底用"开场→随后→结尾"语义节拍、时长标"软参考·不承诺逐秒"；人物锚定行复述 2–3 稳定静态特征。
- **影响面**：三份脚本双副本同步（templates/build-data-js.py、templates/js/gen.js、templates/js/xiajing.js）。证据：ep001 全片 51 镜单镜稿 + 6 板 21 段段稿，caps=[9,9,9,9,9,6] 双端一致；保真门禁 PASS、场景一致性 A/B/C/D=0。

## 3.5.6-STYLELOCK消重 — 2026-09-09

主题：消除 Seedance STYLE LOCK 的双份正本债（#31）+ 补 ⑤ 符号自检跑出的门禁。
- **⑤ 符号自检产物**：冒烟实测发现"把 `{}` 误写进分镜 `dialogue`（顶掉「」）会让 `check-script-fidelity` C2 静默失效"→ 给 `scripts/check-script-fidelity.py` **新增 D 符号越界检测**（dialogue 含 `{}` 且无「」→ FAIL，四查），并在 stylock §1.5 补"硬约束"。夹具三案例实测 PASS/FAIL(C1C2)/FAIL(D)，投毒对照证明门禁不空转。
- **#31 消重**：`storyboard-method.md` §九.12 原与 `seedance-stylock.md` 逐段重复（每次改 ②③⑤ 要同步两遍）→ 用断言脚本（命中唯一才落盘）**删 3122 字符 → 塌缩为指向 stylock 的单源指针**；§九.1–11（分镜字段格式）保留不动。同步修两处会悬空的引用：§9.0 公式 A "即 §九.12 本体"→"正本 = stylock"；stylock §1.5 符号"与 storyboard §九.12 同步"→"本条为唯一正本"。
- **验证**：`grep` 确认 stylock 为 STYLE LOCK/关键约束唯一规范正本（`example-shotlist-36.md` 里的"关键约束"是示例产物、非规范副本，属锚定示例豁免）；无残留指向已删 §九.12 正文的引用。
- **影响面**：虾镜纪律 2/§9.0 加载 Seedance 模板时以 stylock 为准；无项目数据。证据：`scripts/check-script-fidelity.py`、`modules/xiajing-episodes/references/storyboard-method.md` §九.12/§9.0、`seedance-stylock.md` §1.5。

## 3.5.5-公式门与符号约定 — 2026-09-09

主题：依《Doubao Seedance 2.0 系列提示词指南》逐条对照后落地 4 项（用户"先做①②③⑤"）。
- **① 公式选择门（新增强制纪律）**：`storyboard-method.md` 新增 §9.0，定义 Seedance video_prompt 两套组织法——公式 A（虾集现行分层导演式，默认）/ 公式 B（官方八要素平铺式）；`xiajing-episodes/SKILL.md` 新增纪律 18：模型=Seedance 时每集写 video_prompt 前**必须 AskUserQuestion 问 A/B、得到答复才继续、禁止静默默认**，推荐 A；纪律 2 Seedance 分支加指针。模型=H3 不触发。
- **② 删硬秒拍（修未跟上的旧文件，非新增知识）**：Seedance「一镜到底」的 `0–2s / 2–5s` 硬 beat → 语义节拍，指回 `shared-performance-realism.md` §6 单源（不写死精确秒、总时长开头提一次、精确时码仅留分镜表）；多分镜"约X秒/持续时长"标为软参考。**stylock §3 与 storyboard-method §九.12 两份同步改**。
- **③ 素材上限 + 锚定强化**：Stylock §2 / storyboard §九.12「参考图锚定」改为人物合计 1–4 张（四视图卡算一张·一人一图不动）+ 每条写 2–3 稳定静态特征复述 + 场景 1 + 可选音频 1 + 保留色卡；运镜/风格/画质走文字不占素材位；重要素材前置；按需用少不用堆（**采纳用户"去掉运镜视频、人物放宽到1-4"的修改**）。
- **⑤ 信息类型符号约定**：`seedance-stylock.md` §1 新增第 5 条 + `storyboard-method.md` §九.12 写作规则新增第⑤条——Seedance 投喂正文用 音乐`（）`/音效`<>`/台词`{}`（小语种标语种）/字幕`【】`，**符号只在组装最终 video_prompt 时加、分镜表裸文本不受影响**；H3 不套用。**自检冒烟发现**：把 `{}` 误写进分镜 `dialogue`（顶掉「」）会静默致盲 `check-script-fidelity` 的 C2「防自创台词」→ 已在 ⑤ 两份加"硬约束"注 + 给 `check-script-fidelity.py` 新增 **D 符号越界检测**（dialogue 含 `{}` 且无「」即 FAIL）。夹具三案例实测：正例 PASS(exit0) / 改写台词 FAIL(C1+C2) / `{}` 误入 dialogue FAIL(D)，投毒对照证明门禁不空转。
- **撤回项（用户否决，未落地）**：弃四视图/无表情大头照（继续用四视图卡）、纪律 1b 群像自动垫图裁剪、`gvAutoRefs` model-gating 核查——均不改。
- **影响面/待办**：两份 STYLE LOCK 现仍双份（stylock vs storyboard §九.12），本轮已同步改、**消重列另轮**（唯一真欠项）。⑤ 符号已实测闭环（正例 PASS、D 检测兜住误用），无需再专门跑回归。
- 证据：`modules/xiajing-episodes/references/storyboard-method.md` §9.0/§九.12、`modules/xiajing-episodes/references/seedance-stylock.md` §1/§2/§3、`modules/xiajing-episodes/SKILL.md` 纪律 2/纪律 18。

## 3.5.4-身份按剧情章节匹配 — 2026-09-09

主题：落实用户原则「**角色资产的引用要匹配当前剧情的身份**」——身份选择从"镜头文本模糊子串"升级为"按当前章节命中 chapter_range"。
- **背景**：角色资产的多身份带 `chapter_range`（如 `ch001-ch004`/`ch005-ch024`/`ch025-`，按章升序）。旧注入靠镜头文本子串匹配身份，既会撞名误判（3.5.3），也无法在角色形态演进后选对当前形态。
- **改法**：① 虾镜 `build_shots` 为每镜打 `chapter`（本集改编自 ch001+ch002：循环1/2=ch001，循环3=ch002）；② `build-data-js` 透传镜级 `chapter`（双副本）；③ `gen.js` 新增 `pickIdentityByChapter(c, chapter)`：命中区间→取之，否则取起点≤当前的最大者（当前所处形态），都无→回退文本匹配。调用点改为 `pickIdentityByChapter(c, _sht.chapter) || pickIdentityByText(...)`。
- **影响面**：三份脚本双副本同步（gen.js / build-data-js.py + 项目副本 + build_shots 镜级 chapter）。证据：章节驱动模拟 → 镜001 ch001 苏晚晚=渔村村妇、镜044/046 ch002 阿福=傻大个帮工（非 ch090 大管家）、镜051 ch002 林秀儿=村中少女；保真门禁 PASS、场景一致性 0。

## 3.5.3-身份选择误判修复 — 2026-09-09

主题：修 `templates/js/gen.js` 的 `pickIdentityByText` 子串误判（3.5.2 只修了"加载兜底"，没修"选错身份"）。
- **背景**：为多身份角色按镜头文本选身份时，旧逻辑对身份短名做 2+ 字连续子串匹配，但**没排除"子串其实是角色名自身的一部分"**。实例：角色「苏晚晚」含叠字"晚晚"，其未来身份「晚晚楼主」短名的子串"晚晚"命中了角色名 → 误选**尚未生成的 id3**，其 image 路径是空字符串占位（文件不存在但字符串非空），叠加旧注入无加载校验 → 苏晚晚整条被丢，明明已做定妆照+四视图却引用不上。
- **改法**：① 新增 `notSelf(frag)`——凡候选片段是角色名 `c.name` 的子串即忽略，杜绝"角色名叠字误命中未来身份"；② 无命中时兜底改为**优先第一个有图的身份**（`sheet_ready&&sheet_image` 或 `image`），不再盲目取 `ids[0]`。真实上下文命中（如后续集数出现"楼主/晚晚楼"）不受影响。
- **影响面**：两份 gen.js（项目 + 模板）同步。证据：忠实复刻前端逻辑跑镜001 → `苏晚晚 选身份「渔村村妇」用sheet ← 苏晚晚-id1-sheet.png`（此前误选 id3）。

## 3.5.2-首帧资产引用兜底 — 2026-09-09

主题：修 `templates/js/gen.js` 首帧/尾帧自动注入的"存在资产漏引用"缺陷（用户原则：**不存在的资产不自动引用，但存在的资产一定要被引用**）。
- **背景**：旧注入对每个角色只按 `sheet_ready` 标志取**单张**首选图（四视图），一旦该路径失效（如重新生成后注册表仍指旧时间戳文件名）fetch 404 就把整个角色**静默丢弃**，连定妆照/主图都不回退；且无论图能否加载都先把 `角色=图N` 名字拼进提示词 → 出现"引用了却没有图"。实例：苏晚晚四视图已生成却没被垫上。
- **改法**：① 每个资产带**多张候选图**（四视图→身份图→主图），在 async IIFE 里**逐个试加载**，取第一张能加载的；② 只有加载成功的资产才编号 `=图N` 并垫图，全加载不到=不存在→**不引用、不占号**；③ 补上**道具**注入（镜头文本命中且有图的道具）；④ 场景匹配改子串（兼容"母版 › 分区"）。赋值在同步 `genRefClear()` 之后完成，时序安全。
- **影响面**：前端注入逻辑，两份 gen.js（项目 + 模板）同步。数据侧配套：`outputs/xiatang/repair-asset-paths.py` 把"文件在、注册表路径错位"的 3 条纠正到真实文件（改前自动备份）。证据：模拟注入对镜001 输出 `苏晚晚=图1 ← 苏晚晚-id1-sheet.png`；镜014/024 道具无图 → 正确不引用。

## 3.5.1-场景一致性分区适配 — 2026-09-09

主题：修 `modules/scene-consistency/scripts/check-scenes.py` 与「母版 › 分区」命名规范脱节的假阳性。
- **背景**：虾镜镜级 scene_name 按数据契约写成「母版 › 分区」（如 `苏晚晚家院子 › 院心（外·日）`），生图靠 `sn.includes(母版全名)` 子串命中；但 check-scenes.py 的 B 查用**精确集合相等**、C 查用**全串不等**判换景，导致 B 把每镜都判「资产缺失」、C 把同院不同分区（院心↔堂屋门口）判「换景无据」。
- **改法**：新增 `scene_base()`（分区名按资产母版前缀/子串归一到母版，否则取 ` › ` 前段）与 `scene_in_assets()`（母版子串命中即合法）；B 改用 scene_in_assets；C 改在**母版层**比对，跨母版才要求转场词——同母版不同分区=机位移动，不算换景。
- **影响面**：纯工具修正，不改方法论；令 ep001 分镜在合规写法下不再假报警（B 51→0、C 18→0，A/D 保持 0）。证据：`outputs/xiajing/ep001/矛盾扫描报告.md` 问题总数 0。

## 3.5.0-虾镜剧本保真门禁 — 2026-09-09

主题：虾镜"按剧本来"从自觉变成机械门禁（事故：shots 凭记忆/大纲拆镜，自创拍+台词改写+秒段无映射，用户肉眼发现）。

- 新增 `scripts/check-script-fidelity.py`：**A 剧本秒段覆盖**（每个秒段至少被 1 镜 source 引用）/ **B 出处合法**（source 必须精确指向真实秒段）/ **C 台词双向逐字**（剧本台词→镜头防漏改写；镜头台词→剧本防自创）。
- 配套纪律：xiajing 纪律14⑦ 固化门禁+要求输出「逐句落位核对表」证据；根 SKILL 0.7 虾镜线口径由"暂无脚本"改为有门禁；使用说明脚本清单补行。
- 引号制式兼容：ASCII "..." / 弯引号 / 「」三式归一后逐字比对。
- 门禁不空转实证：当前 ep001 旧 shots 实跑 FAIL 38 处（27 秒段无 source 映射 + 2 条台词丢失）；投毒对照（假 source + 假台词）B/C2 双命中 exit 1。
- 影响面：新增 scripts/check-script-fidelity.py（单副本）；xiajing SKILL 纪律14⑦；根 SKILL 0.7；使用说明。

## 3.4.9-资产闸门行首分隔 — 2026-09-09

主题：修 check-assets.py `pos_part()` 子串分隔符假阴性——与 3.4.8 同族坑在资产闸门的再现。

- 实战：渔村项目 15 条旧场景提示词为超长单行且行中含 "negative:" 子串，`pos_part` 用子串 find 截断，
  正向段被截短 → 指纹句/CG body 锚点全部误报缺失（44 条假 ❌）。
- 修复：分隔符改为**行首匹配**（Negative prompt/negative:/FORBIDDEN 行首才算负面段开始）。
- 双副本：scripts/ 与 modules/xiatang-characters/scripts/ 已 cp 同步 diff SAME。
- 门禁不空转实证：渔村项目 ❌ 161 → 98（非 prompt_cn 107 → 44）；修复后残余非 prompt_cn 项均为真实缺失。
- 同批项目侧配套：outputs/xiatang/inject-style.py（幂等注入器）同规则修复，身份图定妆照纳入注入、
  dedupe 修复强制落盘（曾因 ch 为空丢弃）。

## 3.4.8-风格库词表去风格域 — 2026-09-09

主题：修 check-style-library.py 的项目词表污染——风格域元数据被当"项目特定词"，挂载库回写被自家门禁误杀。

- 实战触发：渔村项目把「国漫3D·暖调烟火」写回用户级库时 P0 阻断；且 build 会把挂载库（含 3 条种子条目）并入项目 xiage 快照，
  种子条目自己的参考名（如"宋韵美学参考"）也被判为项目词——4 条目全 P0，其中 3 条是种子。
- 修复：`project_words()` 采集时 **xiage 模块整体排除**（风格 label/tag/参考名 = 可复用元数据，不是项目叙事词），
  `meta.style_label` 一并排除（style_id/style_tag 的 leaf 本就不在采集集）。
- 门禁不空转实证：修复后干净库 4 条目 P0=0 PASS(exit0)；投毒条目（style_label 塞「苏晚晚」）P0=1 + P1(style_id 与文件名不符) FAIL(exit1)。
- 影响面：仅 scripts/check-style-library.py 单文件；条目 schema 与门禁阈值不变。

## 3.4.7-补丁先校验 — 2026-09-09

主题：把本包改文件时的"半套契约"风险堵成纪律（源于 3.4.6 落档时的一次真实撞号）。

- 新增执行纪律 **§8 第 21 条**：脚本批量改动一律「全量读入 → 内存断言 → 全过才统一落盘」，禁止边替换边写；
  断言集含锚点命中数=1、VERSION 起点==本次读到的值、路径存在、改后表格列数一致；失败即不写、退出码非 0。
- 同条写入并发处置：VERSION 起点不符=有并发会话在改，**让号不让内容**（递增到未占用的带后缀号，CHANGELOG 记理由），
  禁止整文件覆盖对方改动（本次实测：`3.4.5-情绪双轨` 与 `3.4.6-风格库脱敏门禁` 并行，双方内容互不吞噬）。
- 触发事故：3.4.6 那次补丁脚本按"逐处替换即缓存、末尾统一写"的顺序写，版本断言失败时前三处文档改动已落盘，
  形成"改动落了、版本号没落"的中间态（本次靠人工核对与让号收尾，未污染包）。教训固化为第 21 条。
## 3.4.6-风格库脱敏门禁 — 2026-09-09（号位说明：本版原拟 3.4.5，与并发会话的 3.4.5-情绪双轨 撞号，按"递增前 grep 占用"纪律改让为 3.4.6）

主题：补最高纪律的位置漏洞——**风格库条目此前无机械脱敏校验**。

- **背景（自检揪出的洞）**：禁止项目数据纪律的锚定示例白名单（2026-09-02 定）只覆盖 `modules/<模块>/references/`，
  而 v3.4.0-风格库 新增的 `modules/xiage-styles/styles-library/` 不在名单内；库自身"入库前必须剥离剧名/角色/
  专有世界观词"的规则只靠人自觉，无脚本把关。现有 3 条种子条目实测干净（`style_label` 为美学流派名、
  `visual_references.name` 标「通用占位」、`source` 只有"参考图验证 <日期>"），属**规则文字滞后于特性**，非数据污染。
- **新增 `scripts/check-style-library.py`**：结构校验 + 脱敏校验。项目词表**动态取自项目自身数据**
  （`project/xiaji.db` 的 `snapshots` 表 meta/xiatang 名称 + `pipeline-state.json` 的 project，可用 `--word` 追加），
  脚本内零硬编码项目词，符合生成脚本零硬编码纪律；`--layer seed|user|all`、`--dir` 可校任意目录；
  输出无 emoji（GBK 控制台安全）。
- **最高纪律第 1 条白名单**：显式纳入 `styles-library/`，并写明豁免**以条目已脱敏为硬前提**、验收以该脚本退出码 0 为准。
- **虾格 §0.2.6 写回步骤**：加"入库硬门禁"条——写回用户层/提升种子层前必须跑该脚本且退出码 0。
- **门禁不空转实证**（改脚本必复跑真实数据的纪律）：真种子层 3 条 → P0=0 P1=0 PASS；另建投毒条目
  （含《剧名》、角色名、场景名）→ 同一命令下 P1=2（书名号）、加词表后 P0=3（style_label/figure/environment 命中），
  报错数随输入变化，确认检出真实生效。

## 3.4.5-情绪双轨 — 2026-09-09（★ 由 3.4.7 会话按包内痕迹回填补记；**未经当事会话确认**）

> **回填依据与边界**：VERSION 曾为该号 + `references/` 内 6 处「★ 2026-09-09 补入」标记。本节只记"动了哪些位置、正文写了什么口径"，
> **不推断**改动动机、验收口径与未见于文字的影响面；当事会话若有原始说明，以其为准修订本档。

- `references/shared-performance-realism.md` §通用纪律「时码与组限」新增第 6 条：单镜 AI 视频提示词正文用**语义节拍**、不写精确秒数
  （本规范内部的 `0-1.5s` 式时码属表演规格，不等同于投喂提示词的秒数写法）。
- 同文件新增小节「★ 减法式微表情三件套：强度控制 + 动作归因 + 时间顺序」（L108）。
- 同文件 §七「情绪 → 微表情映射表」扩至 **23 种**并补「混合情绪」三行（L215）。
- 同文件新增小节「★ 情绪转折速查五式（选型菜单）」（L344）。
- 同文件新增 **§十一附「双轨长镜头与波浪式失守」**：外部任务不变量 + 8~15s 单镜情绪主戏（本档号名的字面出处应为该节，L415）。
- `references/shared-duration-control.md` §十四 补一句与表演横切的边界（L197）：本规范管**分镜层**时长账（组数/逐镜时码/首尾相接对账），
  单镜 AI 视频生成层的写法归表演横切。
- **未确认项（照实记）**：该档当时未写 CHANGELOG（正是 §8 第 21 条「留痕要求」的触发案例）；是否配套改过项目台/分镜脚本，包内无痕迹，不作推断。

## 3.4.4-Xuan酱速查 — 2026-09-09

主题：《AI视频做电影感》（B 站 Xuan酱 11 集）学习笔记评估与**最小增量接入**——该课为入门菜单型，与已有三横切（老白/造梦师/运镜层）高度重叠，仅两处按其"速查表"形态值得捞。

- **`shared-storyboard-craft.md` §五附**：新增「情节型景别组接速查八式」（P11 蒸馏，八种情节类型的默认景别序列 + 入场/离场镜像口诀），定位为 §五第 3 点"渐松渐紧"的整场速查版、**默认起点非硬约束**；四条让位裁决写死（战斗段不走本表→`shared-fight-dispatch`/R31、同景别同角度回"两坑"、对话式先定 i 型五机位、时长交回 `shared-duration-control`）。§十四自检清单加对应核对项。
- **`shared-frame-image-grammar.md` §四附**：新增「六大现成光型速查」（P3 蒸馏，顶/侧/逆/伦勃朗/硬/体积光 × 英文词 × 脸上效果 × 情绪 × 光源动机常例；"伦勃朗"此前全库零命中）。边界写明：**只是命名/选型菜单**，光的合理化仍回光源地图五项并过 `shared-quality-gate.md` §三第 3 条动机场，一次只选一型、不覆盖已选风格卡/摄影卡。
- **两项显式拒收（防后续重复评估与被带偏）**：① **全局青橙调色**——与造梦师"色彩由光源材质推导、不做无因全局调色"直接冲突，按后者为准，已作为「不采纳项」写进 §四附；② **V.I.D.E.O. 提示词框架**——与首帧 5 段式 / Seedance STYLE LOCK 重复造第三套分格法。P2 构图七法、P7 十五种角度亦不纳入（已由 §六/§七/§九/§十/§十二 + 运镜层覆盖）。
- **挂接（同批）**：根 `SKILL.md` §0 两行登记 + 画面语法 §八落点表两条新指针 + 4 个下游消费点（`modules/xiajing-episodes/SKILL.md` 两行、`modules/storyboard-cinematic/SKILL.md` 两行、`modules/xiajing-episodes/references/storyboard-method.md` §挂接行、`references/shared-quality-gate.md` 注册表行）。VERSION 3.4.3-运镜单源 → 3.4.4-Xuan酱速查。
- **版本号动态化（同批，修漂移）**：§0 版本纪律删写死的"（当前 2.0.0）"（实际早已 3.4.x），改为"`VERSION` 文件是唯一版本源、正文/模块/references/模板/状态文件一律不写死当前版本号"，并补"递增禁止裸用主版本号、特性用带后缀标签、改前 grep 防撞"；§2 `pipeline-state.json` 示例 `skill_version` 由 `"3.1.0"` 改为占位符 `<现读本包根目录 VERSION 文件逐字填入>`，新增写入口径禁止照抄示例/凭记忆填/只写主版本号（写死曾让 §3.1 续集版本比对形同虚设）。
- **本档同时回填**：CHANGELOG 缺失的 3.2.0 / 3.2.1 / 3.2.2 / 3.3.0 / 3.4.0（画面语法）/ 3.4.0-风格库 / 3.4.1 / 3.4.2-运镜 / 3.4.3-运镜单源 共 9 档（依据见文首回填说明，逐条附包内证据路径）。

## 3.4.3-运镜单源 — 2026-09-08

主题：把运镜判断层**单源化**，根治"英文运镜词多头、dolly/Truck 术语打架"。

- `shared-camera-movement.md` §八 升格为**跨模型英文映射唯一权威**（`dolly ≡ H3 Truck/Push`、Seedance 另拼），听风本地词表退役；H3 §3.3 与 `seedance-stylock.md` 只留本模型执行拼法并以 §八 为映射准绳，不建第二份判断表/自建映射。
- 纪律固化：判断层不锁英文词（中文概念/选型/辨误/边界）+ 英文集中一处。证据：`references/shared-camera-movement.md` 文件头与 §八、`SKILL.md` §0 运镜行。

## 3.4.2-运镜 — 2026-09-08

主题：**运镜手艺横切单源**（⑭）首次落地——蒸馏自《最核心的 15 种 AI 影视运镜手法》学习笔记。

- 新增 `references/shared-camera-movement.md`：三轴判别法（机位/镜头/焦距谁在动）、15 手法总表、叙事目的→运镜反推表、易混对比、环绕幅度代价提示（非禁令）、兜底写法。
- **只管非战斗段**：战斗段运镜权威 = seedance-combat **R31**，冲突时本层整段让位；分工裁决"老白管镜头间、本源管单帧内、本层管单镜怎么动"。挂接：听风表+Stage2、虾镜拆镜④、scene-assets 空镜、quality-gate §四、根表、storyboard-method。

## 3.4.1 — 2026-09-08

主题：打戏外协模块**内部编号统一为上位原则 P1–P7 + 执行规则 R1–R32**（seedance-combat-prompt 自身升 v3.0.0）后的跨模块回灌。

- xia-boss 与 storyboard 侧对"32 条铁律"的跨模块引用一律改指 **R1–R32**；`SKILL.md` §0 打戏行加注 P/R 编号口径。
- 双拷贝（`skills/seedance-combat-prompt` 与 `modules/seedance-combat-prompt`）逐字节同步；证据：`modules/seedance-combat-prompt/SKILL.md` R31 条目与 P1–P7 章节、`SKILL.md` §0 打戏行。

## 3.4.0 — 2026-09-08（画面语法横切）

主题：**画面语法横切单源**（⑬）——《电影感镜头构建原理》（《造梦师》v2.0.0，CC-BY-NC-4.0）全量内联蒸馏。

- 新增 `references/shared-frame-image-grammar.md`：场景母版不变量（`SYNTAX MAY CHANGE. SCENE LOGIC MAY NOT.`）/ 五条成画原理 / 摄像机决策六步 + 焦段表 / 光源地图五项（全介质母法，P1 §6.4 光线防假为其实写线强制裁量、不废）/ 风格卡 16 + 摄影卡 8 决策系统 / 反 AI 味清理（无因不造 + 删词检验，口径同步 `shared-quality-gate.md`）。
- 分工裁决：**老白管镜头间、本源管单帧内**；导演法经拍板不纳入，视觉参考注入以虾格 infusion 契约为准。

## 3.4.0-风格库 — 2026-09-08（与上一档并行的特性标签）

主题：虾格**风格挂载库**（双层）+ 展示风格图规范 + 导出/应用端点。

- `modules/xiage-styles/styles-library/`（skill 种子层）+ 用户级 `~/.qwenworkcn/xiage-style-library/`（每剧定稿回写）：①风格类型新增"从已验证库选"这条 opt-in 候选路径，**不自动套用**，防趋同改由"用户选择"保证（不再靠"禁止复用"）；库目录单一来源 `style_library_paths.py`。
- 新增 `modules/xiage-styles/references/style-preview-keyframe.md`（关键场景式展示图规范）；`render-medium-library.md` §四 跨族通则（真人皮肤禁磨皮词，check-assets 反向校验落地）。
- 项目台：`/api/export-style`（zip + proj_name 脱敏 400）与 `/styles/apply-library`；库不进项目页、走 agent 选择。
- **编号说明**：本特性与"画面语法横切"同日落地且都占 `3.4.0`，为避免撞号改用带后缀标签，包内 25 处引用一致。

## 3.3.0 — 2026-09-08

主题：**分镜手艺横切单源**（⑫）——《老白的分镜课》17 集全量蒸馏，用户拍板"重叠处以老白为准"。

- 新增 `references/shared-storyboard-craft.md`：两条工作流 + 主镜工作法 / 叙事三原则与强调弱化 / 轴向形状体系（i/l/a/a2）/ 跳轴三类与对联补救 / 景别六点 / 视高六点 / 构图四规则 / 视觉焦点与眼线 / 透视两原则 / 空间感 / 动势 / 视角 / 蒙太奇 + §十四交付自检。
- 与 `shared-spatial-blocking.md` 分工（本文件管"何时该跳"，那边管"怎么合法越"）；虾镜 `storyboard-method.md` 词表**降为术语库**、决策依据改指本单源。
- 证据：`references/shared-storyboard-craft.md` 文件头、`modules/xiajing-episodes/references/storyboard-method.md` §挂接行（本档无裸 `3.3.0` 标记，编号按当次会话记录补记）。

## 3.2.2 — 日期未标（回填）

主题：**写实族真人皮肤铁律**（事故固化：主图写 `fair porcelain skin` → 出图磨皮网红脸、丢真实韵味）。

- 写实（族 B）三要素与下游资产提示词正向段必须内建真人皮肤锚（`real photographed / visible pores / subtle uneven skin tone / no beauty retouching / not a plastic idol face / slightly asymmetric bone structure`），禁 `porcelain skin / flawless / airbrushed / glass skin` 等；`check-assets.py` 加反向禁词校验分支。证据：`modules/xiage-styles/SKILL.md` 纪律 11、`modules/xiage-styles/references/render-medium-library.md` §族B、`modules/xiatang-characters/scripts/check-assets.py`。

## 3.2.1 — 日期未标（回填）

主题：**虾镜线打戏落位方案 A**——战斗段在虾镜数据结构里的合法形态定稿。

- 战斗子段 = `shots[]` 特殊镜行（`route:"武戏"`，不带 11 字段/首尾帧/H3）+ `shots.json` 顶层 `battle_segments`；`build-data-js.py` 双副本透传（顶层新增字段必须透传，否则项目台静默丢字段）。
- 铁则两条：听风段式 ≠ 虾镜平铺 shots，补横切条款前先核模块数据契约；虾镜打戏无脚本门禁，走人工 5 项验收。证据：`modules/xiajing-episodes/SKILL.md` 拆镜检查点 A 与验收段、`references/shared-fight-dispatch.md` §登记落盘、`scripts/build-data-js.py`。

## 3.2.0 — 日期未标（回填）

主题：**渲染介质词组库**（防风格漂底座）+ 虾塘介质锚按风格族分支。

- 新增 `modules/xiage-styles/references/render-medium-library.md`（族A 3D 国漫 CG / 族B 写实 / 族C 二维赛璐璐，各含 STYLE_HEAD + 主图介质锚 + body 强标记 + 负向风格边界）；澄清它**不是成品风格预设**，调性层与 infusion/基调仍每剧现做。
- 虾塘 `character-assets.md` 三条事故规则：CG 族必带正向主动风格化锚（只靠负面 `FORBIDDEN: photorealism` 压不住写实漂移）、禁写腰以下诱导词（`metal clasp`/腰封等致半身胸像）、**子串陷阱**（`non-photorealistic` 含 `photorealistic` 被 `ID_REALISM_BAN` 误判，改写 `not photographic`）。
- 证据：`modules/xiage-styles/SKILL.md` 风格库表与纪律 1、`modules/xiatang-characters/references/character-assets.md` §渲染介质分支、`scripts/check-assets.py` 第⑥项 CG 分支。

---

## 3.1.0 — 2026-09-08


主题：**剧本输出格式统一为「虾剧格式」+ 全入口剧本先行 + 场景主键链收口**。经真实解析器（DramaClaw `screenplay_scene_parser` / `screenplay_quality`）实测驱动。

### 1. 剧本输出格式（虾剧格式）
- **秒段全字段化**：`xiaju-script` 与横切 `shared-script-writing.md` §九 的每集输出格式，秒段由旧"裸 `△画面` + `人物A：台词`"改为六字段 bullet：`【场景】【出场角色】【画面】【台词】【情绪功能】【可拍性】`；循环头元数据（人物/剧情功能/情绪目标/循环结尾爆点）保留。
- **标准场景头（解虾料 blocking）**：每个场景（含循环内换场）首次进入，输出**独立一行** `场景：<纯地点名> <日/夜> <内/外>`——实测证明旧循环头 `## 循环N · 场景 / 时间 / 内外景` **不被虾料识别**，drama 模式 `require_scene_headers` 下 `total_scene_headers=0 → blocking missing_scene_headers`；补此独立行后过门。
- **循环头写法硬规则（实测）**：`## 循环N · …` 行尾内外**必须写完整"内景/外景"**（裸"内/外"会让循环头被松解析器抢注成"有头无证据"、把下行 `场景：` 吞进块内 → 仍 missing）。
- **场景主键链收口**：统一"地点名 = 下游虾塘 `scenes[].name`"；分区/道具锚点只写进正文 `【场景】`（空间证据/建议，不锁死、不另立母版），不得写进头行；镜级 `scene_name` 可带"母版名 › 分区"但须含母版全名前缀（保 `sn.includes(全名)` 垫图 + `未映射=0`）。
- **出场角色行写法（实测）**：`【出场角色】` 行尾必须以句号收口、勿停在一个以"内/外"结尾的人名上（如"王员外"），否则被误判成假场景头。

### 2. 全入口剧本先行（流程统一）
- 根 `SKILL.md` §0.5 / §0.6 / §0.8 / §1.1 与 `xiaju-script` 交接层：所有入口（大纲 / 整本小说 / 单章 / 已有成稿）**第 1 步一律虾剧**；小说→先剧本化，虾料一律**摄入成稿剧本**（非小说原文）。
- 修正 `§0.6 小说入口`旧正文（虾料先于剧本）与 frontmatter/§0.8"剧本先行"的矛盾；`§1.1 DAG 表`对调为 虾剧=1、虾料=1.5。
- **"已有成稿 → skipped" 改为"规范化改写进虾剧格式"（不 skip）**：§0.8 新增"规范化规则"，只对齐体例、不擅改剧情；`xiaju-script` 交接层同步。

### 3. 前端 / 下游联动
- `templates/js/xiaju.js`：新集模板改为虾剧格式（循环头"内景" + `场景：` 头 + 六字段）；台词气泡判定收紧（首字符类加 `*\-`、排除名单补 `人物/剧情功能/情绪目标/…/【/△`，消除 `**人物：**` 假气泡）；新增六字段渲染分支。
- `references/shared-spatial-blocking.md` §〇：加"剧本层边界"——剧本只给空间证据/建议，锁定分区/机位/CAM/站位/轴线/越轴仍由空间真理图 + 拓扑图推导。
- `modules/xiajing-episodes/SKILL.md`：数据契约补"镜级场景命名含母版全名前缀 + 分区不新增母版（守 `未映射=0`）"两条。
- `modules/xialiao-ingest`：`references/parsers.md` 新增 §2.4「xia-boss 剧本先行：场景头权威源约定」——场景边界只绑显式 `场景：` 头 + 传统 slugline，禁止对 `【` 开头六字段正文行跑 SIMPLE_LOCATION/多地点启发式（根治"王员外"式假 scene_blocks，实测两场景成稿虚增 11→3）；`SKILL.md` 校验层补对应验收项。与上游"出场角色行加句号"构成双保险。

### 4. 项目台 / 状态机同步剧本先行（本轮追加）
- `templates/index.html`：侧栏 tab 重排为 **虾剧→虾料→虾格→虾塘→虾镜→听风**，虾剧设 `active`（并修正原虾剧被排在虾塘之后的错位）。
- `templates/js/init.js`：加载后默认落地页 `xialiao → xiaju`。
- `templates/js/gen.js`：默认 `curSection = "xiaju"`；`rerenderCurrent()` 补上缺失的 **xiaju 分支**（否则默认落虾剧时快速重渲染落空）。
- `templates/server.py`：`/api/data` 组装 `order` 把 `xiaju` 提前到 `meta` 后、`xialiao` 前（此前仅在字母兜底里排在末尾）。
- `SKILL.md §2` `pipeline-state.json` 模板：模块顺序 xiaju 前置、**初始 `current` `xialiao-ingest → xiaju-script`**、示例 `skill_version` 对齐 3.1.0；推进顺序注记与 §3"小说入口特例"同步改为剧本先行。
- `templates/build-data-js.py` 与 `scripts/build-data-js.py`（两份脚手架）：`resume_guide` 引导链翻成剧本先行（虾剧=第1步→confirm-xiaju→虾料摄入成稿→虾格…），并把未设 `current` 的兜底默认改为 `xiaju-script`。
- **（自检补对齐）执行纪律层旧顺序清除**：`SKILL.md §6` 纪律2（主线顺序补全为 虾剧→虾料→虾格→虾塘→分镜线）、纪律7（小说入口=第①步虾剧、图谱从成稿派生）、纪律8（★最高级"流程顺序"改为剧本先行）；`§1.2` 虾格支线表行"第1.5步"→"第3步(虾料后)"与"时机"句、`§5` 用户指令表"开始写第一章"效果、`§0` 门控落点引用"§0.6 步骤⑥"→"步骤①虾剧"——一并纠正为剧本先行（前一轮只改了流程表、漏了纪律层）。
- **新增工具 `scripts/backfill-pipeline-xiaju-first.py`**：把**存量旧项目** `pipeline-state.json`（含 `xiaji.db` 的 `pipeline` 快照）里 `current` 仍停在**四种旧值 `xialiao-ingest` / `chapter-1` / `confirm-xialiao` / 空**、且虾剧未 completed 且还没进虾格的项目，回填为 `current=xiaju-script` 并把 `modules` 里 xiaju 前置。**默认 dry-run，加 `--apply` 才写、写前自动备份 `.bak`、幂等（重跑自动跳过、不重复改）**；`xiaji.db` 按真实布局在 `<项目根>/project/` 优先查找。

### 5. 虾格新增「全剧定风格图」能力（★ 把定风格提示词生成逻辑固化）
- 新增 `modules/xiage-styles/references/style-keyframe-prompt.md`：定风格图（美术圣经锚）提示词生成规范——五要素（人物/环境/光影/色彩/质感）硬要求、外景优先且人物清晰非剪影、只放克制级奇观、正向总-分5层英文 + 负向 FORBIDDEN、`style_tag` 不进 prompt、写实开关 `enabled=false` 不写摄影参数、常见偏差→修正词表、回填与验收。
- `modules/xiage-styles/SKILL.md` 五处挂钩：新增流程步 **§0.2.6 全剧定风格图**（三件套+曲线+FS 落 `creation-direction.json` 后、进虾塘前）；纪律8 链补该步；§3 验收清单加项；§4 references 索引登记；§6.2 handoff 新增 **`style_reference_frame`** 字段（图路径+提示词，虾塘/虾镜统一引用，改 JSON 则重出）。

### 6. 虾格改造：去预设库 + 每剧从零做风格 + 定风格图入口（★ 本轮）
- **删预设库**：`modules/xiage-styles/presets/` 8 json+7 png 已备份移出、留空占位 README；`build-data-js.py`（scripts/ + templates/ 两份）`sync_xiage_presets` 调用置 0，不再把预设灌进项目 `outputs/styles/`。
- **SKILL.md 全面去预设**：§0.1/§0/§0.2.2/§0.2.3/§1功能全景/§2.1工作流/§2.2纪律1/§3当前风格域·决策域·管理域·三要素链路/§6.2 handoff —— 统一为"无预设库·每剧按剧情从零生成一种全新风格（或参考图反推），走三步确认，只存项目 outputs/styles/，不再固化回 presets"。
- **`templates/js/xiage.js` 重写**：去掉左栏多风格列表 → 左=「当前风格卡 + 全剧风格图（图位 + 🎨生成按钮，调 `openGenModal('style','style_keyframe', 预填定风格提示词)` 存 assets/styles/style_keyframe.png）」，右=「做新风格工作区（按剧情生成 / 上传参考图反推）+ 三步向导」。`node --check` 通过、build-data-js `py_compile` 通过。
- **（自检修复）全剧风格图显示**：① 占位图初始 `display:none`（原 `flex` 会与图叠加）；② 重生成带时间戳名导致固定路径 404——`server.db_sync_xiage` 与两份 `build-data-js` 新增 `keyframe`/`keyframe_ready`（扫 `assets/styles/style_keyframe*.png` 取最新），`xiage.js` 图位 src 改用 `xi.keyframe` 回退固定名，"生成→显示→再生成→显示最新"闭环打通。

### 影响面 / 兼容
- 剧本 tab 整篇存取、`check-fidelity.py`、`postprocess_tingfeng.py`：**零影响**（不逐段解析剧本正文）。
- **存量项目**：旧格式 `outputs/xiaju/ep{NNN}.md` 重跑虾料会撞 `missing_scene_headers` + 灌假场景块；新格式仅对**新成稿/回填后**生效。历史稿需按虾剧格式回填（补 `场景：` 头 + 循环头内景/外景 + 出场角色行收口）。
- 未改动 DramaClaw 原解析器源码；`xialiao` §2.4 为本包**还原/摄入时的行为约定**。

---

## 3.0.0 — 2026-09-07
打戏改造：`fight-scene-director` 归档；`seedance-combat-prompt` 整包挂载为唯一正本；新增 `shared-fight-dispatch.md` 八字段调度单与 `modules/battle-learner/` 学习官改造；check-fidelity/postprocess 战斗段早退分支。
