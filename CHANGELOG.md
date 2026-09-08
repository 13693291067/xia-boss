# CHANGELOG

本文件记录 xia-boss（虾集·总指挥）编排层的规范/流程变更。方法论正文在各 `modules/*/SKILL.md` 与 `references/shared-*.md`，此处只记"改了什么、为什么、影响面"。

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
