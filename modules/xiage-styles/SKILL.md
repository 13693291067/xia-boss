---
name: xiage-styles
description: |
  虾格（视觉风格模板管理）功能 100% 还原专用 skill。基于 DramaClaw（虾导）开源项目源码逐文件提炼，目标是把项目里「虾格」——即虾集主线第五个子页的视觉风格模板管理——完整复刻到任何新项目。
  触发词：虾格、风格模板、视觉风格、风格指令、避免指令、style_instructions、avoid_instructions、style_tag、风格标签、正向提示词、负向提示词、预设风格、自定义风格、参考图分析、style_analyze、风格预览、风格应用、visual_style、应用到项目、设为默认、风格统一、创作方向、视觉参考、影片基调、基调方向、三步向导、剧本分析、风格类型、奇观场景、克制场景、固定风格库、FS 编号、FS-01、天气时段风格、全片情绪曲线、情绪曲线、情绪节点、呼吸区、BGM 重点、P1 基线、风格锁定、摄影系统、声音圣经。
  适用场景：用户说"把虾格功能做出来/还原出来/复刻一下"、"做一个风格模板管理模块"、"上传参考图自动提取风格"、"手动配置项目风格指令"、"统一全片风格"、"建一个像 DramaClaw 那样的风格系统"、"100%还原虾格"。本 skill 提供：功能全景（模板三要素/当前风格/分析/管理/应用五域）、原项目完整代码地图（文件级路径+职责+关键实现）、StyleAnalyzer 提示词原文、还原验收清单。
  还原方式：两种模式——①源码克隆模式（原项目在本机，对照 code-map.md 按文件搬运）；②从零重写模式（按规格文档逐模块实现）。两种模式都以"行为等价"为验收标准：同样参考图产生同样风格字段结构、同样风格存储与回退行为、同样计费闭环。
agent_created: true
---

# 虾格（视觉风格模板管理）功能 100% 还原

> 本 skill 把 DramaClaw（虾导）项目里「虾格」——虾集主线第五个子页的**视觉风格模板管理**——完整还原到目标项目。
> 覆盖范围：项目级风格模板三要素（风格指令/避免指令/风格 Tag）+ 每剧从零生成或参考图反推（★ 无预设库）+ 风格预览管理 + 应用到项目 + 设为项目默认。

## 0.1 权威定位（以产品手册为准）

> **产品手册（第十章）原文："虾格：风格模板——创作前设定好项目风格模板、提示词和避免指令。统一视觉风格。"**

**→ 虾格核心 = 项目级风格模板三要素（风格指令 style_instructions / 避免指令 avoid_instructions / 风格 Tag style_tag），在创作前设定，贯穿整条流水线统一视觉风格。**
**★ 创建方式（v3.1.0·无预设库）：每部剧【按本剧剧情从零生成一种全新风格】（默认，走 agent-chat），或【上传参考图 AI 反推】；两种方式都走三步向导确认。系统预设库已废弃，不再内置/同步/固化预设。**
**★ 三要素格式规范（强制）：任何新风格的 style_instructions 与 avoid_instructions 必须按 `references/style-format-spec.md` 撰写——正向用「总-分」5 层递进（Create a 开头→光影→场景→主体→技术质感），负向用「平行排除」5 类（风格边界→质感→技术→人体→杂物），全部否定句式。不合规不得入库。**

## 0.2 第一阶段：理解剧本并提供创作方向（创作方向确认门 ★ 强制）

**虾格 = 创作方向确认门（第一阶段）**：正式输出分镜/资产之前，先完整阅读并理解剧本 → 分析 → **只向用户提供三组可选方案，等待用户选择**；用户逐项拍板后，才根据所选方案生成风格三要素，进入正式制作阶段（虾塘建资产）。

### 0.2.1 前置动作：剧本理解分析（输入 = 虾剧成稿 `outputs/xiaju/`；世界观以虾料摄入成稿后的 docs / 知识图谱为准。输出任何风格方案前必做）

完整阅读并理解剧本，分析以下八项内容：

1. 故事的核心矛盾
2. 主角和主要人物的情感变化
3. 剧情的起承转合与高潮位置
4. 每场戏的叙事功能
5. 世界观、时代、地域、季节和天气
6. 适合影片的摄影、美术、色彩和光影表达
7. 哪些场景需要强化视觉奇观（奇观场景清单）
8. 哪些场景应采用克制、普通、生活化的镜头（克制场景清单）

**分析产出纪律（强制）**：
- 分析完成后**不要立即制作分镜/资产**，只转化为三组可选方案 + 简短推荐理由，**不输出大段分析**。
- 奇观/克制清单作为项目数据写入 `outputs/`（**禁止**写入预设模板与 skill），随 handoff 注入虾镜镜头设计。

### 0.2.1.1 全片情绪曲线（★ 2026-09-03 集成，八项分析后自动执行一次）

八项分析（尤其第③步起承转合与高潮位置）完成后、**给出③基调候选方案之前**，加载 `references/emotion-curve.md` 自动计算全片情绪曲线（8-16 节点 0-10 强度 + 幕区/最高峰/反转/呼吸区/BGM 重点/全片原则）并展示：

- **不单独询问、不单独设确认门**——曲线与③基调候选一起展示、一起拍板；
- 曲线是③基调推荐依据与分镜线情绪段标注的数据源；节点表落盘 `outputs/creation-direction.json` 的 `emotion_curve` 字段（权威数据），图为呈现层；
- 整剧级算一次，分镜阶段按集取弧段消费；节拍实质变化自动重算。

### 0.2.2 三组可选方案（必选维度，等待用户选择）

| 组 | 方案 | 候选数 | 推荐依据 | 是否必选 |
|---|---|---|---|---|
| ① | 风格类型 | 三来源：（a）从挂载库选已验证风格 /（b）从零生成 1 种 /（c）参考图反推 1 种 | **挂载风格库（v3.4.0-风格库）**：`styles-library/`（skill 种子层）+ `~/.qwenworkcn/xiage-style-library/`（用户层）合并为候选，**opt-in、不自动套用**；也可按本剧剧情从零生成或参考图反推；三种均走三步确认 | 必选 |
| ② | 视觉参考 | 3-5 组（现有电影/电视剧/成熟影像作品） | 基于①已定风格推荐 | 必选 |
| ③ | 影片类型 / 基调方向 | 3-5 种（轻喜反差喜剧/正剧史诗/暗黑悬疑等） | 基于①② + 核心矛盾与**全片情绪曲线**（§0.2.1.1）推荐 | 必选 |

- 每种方案只需提供**名称 + 一句简短说明**；方案之间必须存在明显差异。
- **等待用户选择后，才进入正式制作阶段（虾塘建资产）**。
- 视觉参考/影片基调为**必选维度**，仅用户明确要求跳过时才可跳过。
- 除非用户明确要求，否则**不跳过方案选择阶段**（最高纪律）。
- **三步向导顺序锁死**：确定前一个，后一个才能做具体推荐。

### 0.2.3 用户选择 → 风格三要素落地（★ 强制：三要素必须依据用户选定的方案生成，禁止 AI 绕过选择自行定风格）

```
用户拍板 ①风格类型 ─→ 无预设可加载：按本剧剧情从零生成 / 或参考图反推 → 按 references/style-format-spec.md 产出全新三要素
        ·★ v3.2.0：介质层（STYLE_HEAD 正向介质句 + 主图介质锚 + 负向风格边界）从 references/render-medium-library.md
         取族（A 3D国漫CG / B 写实 / C 二维赛璐璐）固定句整句内联、逐字不改；本剧只在"调性层（光影/色彩/材质倾向）"微调，不从零发明介质
用户拍板 ②视觉参考 ─→ visual_references（作品名 + 一句说明）
用户拍板 ③影片基调 ─→ tonal_direction
        ↓
三件套全部拍板 → 写 style 三要素 + visual_references + tonal_direction
        ↓
写实线：P1 风格锁定深化（见 0.2.4，非写实跳过）→ 生成项目 FS 固定风格库（见 0.2.5）
        ↓
handoff-xiage.md → 注入虾料 visual_style + 虾镜生成链路
```

### 0.2.4 P1 写实线风格锁定深化（★ 2026-09-03 集成，条件性，先于 FS 库执行）

- **触发条件**：三件套拍板后、FS 库生成前执行；**仅当①拍板风格的渲染介质为真人实拍/写实 CG** 时启用（数字/胶片摄影机、镜头家族、实拍光影规则）；动画、风格化 3D、二维**自动跳过**，禁止把实拍规则混进非写实提示词。
- **执行**：加载 `references/p1-cinematic-baseline.md`，交付 1 套完整推荐（主要影视参考+借鉴维度 / 摄影系统与画幅帧率 / 全片风格锁定段 / 环境色彩策略 / 主要人物声音气质 / 环境声原则+音乐圣经）；随三件套一并确认，不填空表、不倾倒多套互斥方案。
- **落盘**：`outputs/creation-direction.json` 新增 `p1_cinematic_baseline` 字段（非写实项目 `enabled=false`）。
- **下游**：虾镜/听风首帧①风格段与视频 STYLE 段以锁定段为母本；虾塘声线以人物声音气质为输入；FS 库数值可引用 P1 参数（曝光/色彩/纹理）。

### 0.2.5 FS 固定风格库生成（★ 三件套拍板后、虾塘建资产前执行；写实线在 P1 深化之后）

- 按 `references/fs-library-spec.md` 模板，根据最终风格三要素 + 剧本实际天气/时段生成**项目级 FS 固定风格库**（12 类编号 × 18 项参数，只生成本项目用到的类，未用到的注明"本剧未用"）。
- 项目产物写入 `outputs/fs-library.md`（**禁止**写入 skill / 预设模板）；虾镜写首帧提示词时注明「调用 FS-XX」。
- 模板文件（编号 + 参数项 + 流程）跨项目通用；具体 FS 数值为项目产物；写实线 FS 的曝光/色彩/纹理参数引用 P1 锁定段。

### 0.2.6 全剧定风格图（Art-Direction Keyframe，★ 三件套+曲线+FS 落 creation-direction.json 后、进虾塘前执行）

- 按 `references/style-keyframe-prompt.md` 的规范，从 `creation-direction.json` 的字段组装出**一条定风格图提示词**：一张图同时示范 **人物 / 环境 / 光影 / 色彩 / 质感** 五要素的全剧视觉基因。
- 硬要求：**外景优先（环境要有广度，别只画一间屋）**；**人物必须清晰可辨（脸/服化道/皮肤光/衣料质感，禁剪影/无脸）**；只放 spectacle_plan 里的**克制级**奇观（大特效留分镜）；正向"总-分5层"英文 + 负向 `FORBIDDEN:`；`style_tag` **不进 prompt**（仅元数据、保持介质+成色纯净）；默认 16:9；`p1_cinematic_baseline.enabled=false` 时不写实拍摄影机/镜头参数。
- 定位提醒：定风格图**允许有人**（示范人物渲染），与虾塘"场景资产空镜禁人物"是两套规则，勿混。
- 产出后把图路径回填 `creation-direction.json` 的 **`style_reference_frame`** 字段，作为虾塘资产与虾镜 STYLE LOCK 的统一美术锚；**改 JSON 风格要素则此图必须重出**。
- **★ 写回挂载风格库（v3.4.0-风格库）**：定风格图完成后，按 `references/style-preview-keyframe.md` 的公式生成该风格的**关键场景式 `preview_prompt`**，**剥离项目数据**（剧名/角色/专有世界观不进 keyframe/figure），组装成 `styles-library/README.md` 条目 schema → 写回**用户级库** `~/.qwenworkcn/xiage-style-library/<style_id>.json`（个人跨项目复用）；要提升进 skill 种子层/换机/分享，用虾格页「📤 导出风格包」（`/api/export-style`）打 zip 解压丢进 `styles-library/`。

## 0. 还原目标（一句话）

**虾格让"全片风格统一"变成项目级配置：创作前设定风格模板（三要素）→ 保存到项目 → 草图/首帧/视频全部引用同一风格。★ 无预设库：每部剧按本剧剧情从零生成一种全新风格，或上传参考图让 AI 反推。**

100% 还原 = 行为等价，验收标准：

```
同样的参考图 → 同样的风格字段结构（style_instructions/avoid_instructions/style_tag/suggested_name/suggested_label）
同样的保存请求 → 同样的风格持久化（★ 无预设库：只存项目 outputs/styles/<style_id>.json）
同样的查询 → 只返回本剧当前风格（无预设合并列表；默认回退到项目 visual_style）
同样的应用 → 项目 visual_style 被草图/首帧/视频生成引用
同样的边界 → 同样错误响应（No file uploaded / Style analysis failed）
```

---

## 1. 功能全景（四域）

```
┌────────────────────────────────────────────────────────────────┐
│ ① 模板域  项目级风格模板三要素（风格指令/避免指令/风格Tag）     │
│ ② 当前风格域  本剧从零生成的唯一风格（★ 无预设库；存 outputs/styles/）  │
│ ③ 分析域  参考图 → StyleAnalyzer → 5 字段风格参数（创建快捷方式）│
│ ④ 管理域  自定义风格 CRUD + 预览图管理 + 风格家族分类           │
│ ⑤ 应用域  应用到项目 + 设为项目默认 → 虾镜全链路风格统一        │
│ ⑥ 创作方向域（★） 剧本理解分析 → 三步向导（风格→参考→基调）    │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. 还原工作流

### 2.1 开工前：选择还原模式

- **源码克隆模式**（原项目在本机，如 `C:/Users/123/Desktop/AI学习资料/dramaclaw`）：
  1. 读 `references/code-map.md` 拿到文件级代码地图
  2. 按地图逐个文件搬运/适配（★ 预设体系已废弃、不搬运预设；保留 StyleAnalyzer 提示词、端点、计费逻辑）
  3. 用 §3 验收清单逐条核对
- **从零重写模式**（无原项目）：
  1. 先做"按剧情从零生成风格"链路（agent-chat 生成三要素 + 参考图反推；★ 无预设体系）
  2. 再实现 StyleAnalyzer（LLM 结构化输出，提示词用 code-map 中的原文）
  3. 再实现管理端点（CRUD/预览/分析/上传）
  4. 再接入项目配置（visual_style 引用 + 回退）
  5. 用 §3 验收清单逐条核对

### 2.2 执行纪律（强制）

1. **无预设库·每剧从零做风格（★ v3.1.0）**：不再内置或同步系统预设（`presets/` 已废弃为空占位），每部剧**按本剧剧情生成一种全新风格**（或上传参考图反推），只存项目 `outputs/styles/`；**不再固化回 skill 的 presets/。**（★ v3.2.0 澄清：新增的 `references/render-medium-library.md` 只是"渲染介质词组库"、**不是成品风格预设**——调性层与项目 infusion/影片基调仍每剧现做，防趋同不变；固化介质层只为防风格漂。）（★ v3.4.0-风格库 更新：新增 `styles-library/` **双层挂载风格库**——skill 种子层（通用无项目数据）+ 用户级 `~/.qwenworkcn/xiage-style-library/`（每剧定稿回写）。它是 ①风格类型的 **opt-in 候选源之一**（另两路=从零生成/参考图反推），**不自动套用**，用户逐项拍板才应用 → **防趋同改由"用户选择"保证，不再靠"禁止复用"**。加风格=丢文件、零改 SKILL；库条目**必须剥离剧名/角色/专有世界观**（禁项目数据最高纪律不破），写回/导出前 grep 脱敏。）
2. **标签纯净性**：style_tag 只描述介质+成色（CINEMATIC FILMIC REALISM 等），**禁止携带时代/地域/服化道**（禁词：PERIOD/REPUBLICAN/ERA/DYNASTY/MODERN/ANCIENT/DRAMA/古装/民国）——这是防止风格标签覆盖剧情设定的关键约束。
3. **计费闭环**：风格分析是 LLM 调用，走 reserve→confirm/settle_cancelled 完整闭环。
4. **图片压缩**：分析前压缩到最长边 1024px / JPEG quality 60（降 token）。
5. **行为等价优先**：允许换 LLM 模型，但输出字段结构与约束必须一致。
6. **还原后再交付**：完整实现 + 自测后，输出验收清单核对结果。
7. **资产正面统一（应用侧约定）**：风格模板应用于资产生图时，**资产类图片输出视角统一正面**（角色定妆=正面全身/半身面向镜头；身份图=**两图制（定妆照 + 四视图角色卡，2026-08-21 拍板）**；道具=**五宫格（★ 2026-08-21：正面/背面/左侧面/右侧面/材质细节特写，上 2 下 3）**）；style_instructions 不得引入遮挡面部/非正面朝向的默认倾向，视角规范以虾塘 skill「资产输出统一正面」为准。
8. **创作方向三步向导（★ 强制）**：虾格确认 = 剧本理解分析（含**全片情绪曲线自动计算与展示，§0.2.1.1**）→ 三步向导（①风格类型 → ②视觉参考 → ③影片基调，曲线随③一起拍板）→ **写实线 P1 深化（§0.2.4）** → FS 库（§0.2.5）→ **全剧定风格图（§0.2.6）**，**顺序锁死**——确定前一个，后一个才能做具体推荐；每步给出 3-5 个候选（名称 + 一句说明），方案间差异明显，**不输出大段分析**。
9. **视觉参考/基调必选（★ 强制）**：风格、视觉参考、影片基调三件套均为**必选维度**；仅用户明确要求时才可跳过；「除非用户明确要求，否则不跳过方案选择阶段」为最高纪律，与决策域「禁止代选」并列执行。
10. **奇观/克制清单为项目数据（★ 强制）**：剧本理解分析产出的奇观场景/克制场景清单写入项目 `outputs/`（随 handoff 注入虾镜），**禁止**写入预设模板、三要素格式规范或本 skill 任何文件（数据污染纪律）。
11. **写实族真人皮肤铁律（★ v3.2.2 事故固化）**：写实（族 B）风格的三要素与下游资产提示词，正向段**必须内建真人皮肤锚**——`real photographed / visible pores / subtle uneven skin tone / no beauty retouching / not a plastic idol face / slightly asymmetric bone structure`；**禁用** `porcelain skin / 瓷白肌 / flawless / baby skin / airbrushed / beauty retouch / ultra-smooth / glass skin` 这类把脸推向磨皮网红 AI 脸的词（事故：宋式美学主图写 `fair porcelain skin`，出图变磨皮网红脸、失去真实韵味）。写实族 STYLE_HEAD 已内建真人皮肤锚，详规见 `references/render-medium-library.md` 族 B。

---

## 3. 验收清单（100% 还原判定）

### 当前风格域（★ 无预设库）
- [ ] **不内置系统预设**：`presets/` 已废弃为空占位（仅 README），build 不再 `sync_xiage_presets` 把预设灌进项目
- [ ] 每部剧**按本剧剧情从零生成一种全新风格**（`xiageGenByTopic`/agent-chat），或上传参考图反推；两者均走三步向导确认
- [ ] 风格只存项目 `outputs/styles/<style_id>.json`（三要素必填 + style_tag 纯净性 + Create… 开头 + FORBIDDEN 负向）
- [ ] **不再固化回 skill 的 presets/**（跨项目复用机制取消，避免风格趋同）
- [ ] 项目台虾格页**只显示当前确定的这一种风格**（无多风格列表）

### 分析域
- [ ] `POST /projects/{project}/styles/analyze`：multipart file + style_id（可选）
- [ ] 返回 5 字段：style_instructions / avoid_instructions / style_tag / suggested_name / suggested_label
- [ ] style_instructions ≤100 词，"Create..." 开头；avoid_instructions ≤60 词，"FORBIDDEN:" 前缀
- [ ] style_tag 2-4 词大写，禁词约束生效（PERIOD/REPUBLICAN/ERA/DYNASTY/MODERN/ANCIENT/DRAMA/古装/民国）
- [ ] 图片压缩（1024px / q60）后上传分析
- [ ] 计费：reserve_feature_start_credits（mainline.style_analysis）→ 成功 confirm / 失败 settle_cancelled
- [ ] 指定 style_id 时 stage_style_preview 返回 preview_token

### 管理域
- [ ] `GET /styles` 返回本剧当前风格（★ 无预设合并列表）；`GET /styles/{style_id}` 单查
- [ ] `POST /styles` 创建 / `DELETE /styles/{style_id}` 删除
- [ ] `GET /styles/{style_id}/preview` + `POST /styles/{style_id}/preview` 预览管理
- [ ] `POST /projects/{project}/styles/preview-upload` 预览上传
- [ ] StyleService：get_style_or_default（默认回退）、list_all_styles、get_style_family、is_animation_style、is_live_action_style

### 应用域
- [ ] **应用到项目**：风格模板应用到当前项目（写入项目配置）
- [ ] **设为项目默认**：项目级默认风格（新集/新项目继承）
- [ ] 项目配置 `visual_style` 字段引用风格 id
- [ ] 虾料设置层 visual_style 下拉用 `useStyles(project)`（虾格列表）
- [ ] 虾镜草图/首帧/视频生成引用项目 visual_style

### 边界
- [ ] 空文件 → `{ok:false, error:"No file uploaded"}`
- [ ] 分析失败 → `{ok:false, error:"Style analysis failed: {e}"}`（且计费 settle_cancelled）

### 决策域（强制，风格选择必须用户拍板）
- [ ] ①风格类型**不再是选预设**：按本剧剧情**从零生成一种全新风格**（或上传参考图反推），展示三要素交用户确认；**禁止套用任何系统预设、禁止 AI 代选**（推荐项仅指生成方案里的推荐，非旧 6 预设）
- [ ] **给出推荐方向**：依据本剧题材/世界观推荐"从零生成的风格方向"（如玄幻仙侠→水墨玄幻、都市悬疑→冷冽写实），说明理由；不点名任何旧预设
- [ ] 用选择控件（AskUserQuestion）让用户决策，推荐项标注 (Recommended) 排第一
- [ ] **禁止未经用户确认直接套用默认风格**；用户选定后才写 style 三要素 → handoff-xiage.md → 注入链路
- [ ] **创作方向三步向导（★）**：①风格类型（按剧情从零生成 1 种 / 或参考图反推，交确认）→ ②视觉参考（3-5 组+推荐）→ ③影片基调（3-5 种+推荐），顺序锁死，确定前一个后一个才做具体推荐
- [ ] 每步方案只给「名称 + 一句说明」，方案间差异明显，不输出大段分析
- [ ] 视觉参考 / 影片基调为**必选**维度；仅用户明确要求时可跳过；「不跳过方案选择阶段」为最高纪律
- [ ] 剧本理解分析（八项）完成且奇观/克制场景清单写入项目 `outputs/`（不写预设/模板），随 handoff 注入虾镜
- [ ] **三要素落地链路**：style_instructions / avoid_instructions / style_tag 依据本剧剧情从零生成 / 或参考图反推（均按 style-format-spec 格式规范），禁止套用任何预设、禁止绕过用户确认自行定风格
- [ ] **FS 固定风格库**：三件套拍板后、虾塘前按 fs-library-spec.md 生成项目 `outputs/fs-library.md`（12 类 × 18 项，只生成本项目用到的类，模板进 skill、数值进项目）
- [ ] **全剧定风格图（★）**：按 `references/style-keyframe-prompt.md` 产出定风格图提示词并回填 `creation-direction.json.style_reference_frame`——五要素齐（人物/环境/光影/色彩/质感）、外景有广度、人物清晰非剪影、正向总-分5层英文 + 负向 FORBIDDEN、`style_tag` 不进 prompt、写实开关正确（enabled=false 未混入实拍参数）
- [ ] **全片情绪曲线（★ 2026-09-03）**：八项分析后已自动计算并随③基调一起展示拍板；节点表落盘 `creation-direction.json` 的 `emotion_curve`（呼吸区/BGM 重点复用节点编号，强度有文本依据）
- [ ] **P1 写实线深化（★ 2026-09-03）**：写实线已交付 6 件套（参考+维度/摄影系统/锁定段/环境色彩/声音气质/声画圣经）并落盘 `p1_cinematic_baseline`；非写实线已确认跳过，未混入实拍规则

---

## 4. References 索引

| 文件 | 内容 | 何时加载 |
|---|---|---|
| `references/code-map.md` | **原项目完整代码地图**（styles.py/StyleService/StyleAnalyzer 提示词原文/预设清单） | 开工必读；逐域实现时对照 |
| `references/reference-mapping.md` | **题材→视觉参考映射表**（三步向导第二步推荐源，10 大题材类） | 三步向导第二步推荐时加载 |
| `references/tonal-directions.md` | **影片基调方向池**（三步向导第三步推荐源，6 种通用基调 + 情绪曲线联动表） | 三步向导第三步推荐时加载 |
| `references/fs-library-spec.md` | **固定风格库 FS 规范**（12 类天气时段 × 18 项参数模板 + 生成流程 + 数据纪律） | 三件套拍板后、虾塘建资产前生成项目 FS 时加载 |
| `references/emotion-curve.md` | **全片情绪曲线**（★ 2026-09-03 集成：0-10 节点计算规则 + 呼吸区/BGM 重点 + 呈现降级 + 落盘契约） | 八项分析完成后、③基调方案推荐前加载 |
| `references/p1-cinematic-baseline.md` | **P1 写实线风格锁定深化**（★ 2026-09-03 集成：摄影系统/风格锁定段/环境色彩/声音圣经 + 落盘契约 + 下游消费） | ①风格拍板且为真人实拍/写实 CG 时加载 |
| `references/style-keyframe-prompt.md` | **全剧定风格图提示词生成规范**（美术圣经锚：人物/环境/光影/色彩/质感五要素 + 组装公式 + 常见偏差修正 + 回填 style_reference_frame） | 三件套+曲线+FS 落 creation-direction.json 后、进虾塘前加载 |
| `references/render-medium-library.md` | **渲染介质词组库**（★ v3.2.0：族A 3D国漫CG / 族B 写实 / 族C 二维赛璐璐，各含 STYLE_HEAD + 主图介质锚 + body 强标记 + 负向风格边界；防风格漂底座、非成品预设） | ①风格类型选族、写三要素介质层时加载；虾塘按族套介质锚 |
| `references/style-preview-keyframe.md` | **展示风格图提示词生成规范**（★ v3.4.0-风格库：关键场景式组装公式 + 三条强制检查（真人皮肤/色彩反差/巨物）+ 写回挂载库 + 导出脱敏；区分展示图/定风格图/场景空镜三 scope） | 给 styles-library 条目生成/重拼展示图、虾格定稿写回库、导出风格包时加载 |

**不要重复加载已读过的 reference；实现细节不确定时读 code-map.md，不要编造机制。**

---

## 5. 与其它 skill 的关系

- 本 skill 只负责**还原虾格（风格模板）这一个功能模块**。
- 下游消费：虾镜（xiajing-episodes）草图/首帧/视频生成引用风格参数；虾料（xialiao-ingest）设置层 visual_style 下拉。
- 数据契约：风格 id（如 `guoman_fantasy`）存于项目配置 `visual_style` 字段；风格参数以 style_instructions/avoid_instructions/style_tag 形式注入生成调用。

---

## 6. 输出交接（Handoff）★ 完成本 skill 后必做

**本 skill 的最终产出必须落成一份标准交接物（handoff 文档），让下一个 skill 拿到就能直接注入生成链路。** 交接物 = 数据契约 + 状态 + 下一步 三合一。

### 6.1 交接物统一模板（与其它虾系 skill 一致）

```markdown
# Handoff: <from-skill> → <to-skill>

## 元信息
- from: <来源 skill 名>
- to: <目标 skill 名>
- project: <项目名>
- module_status: ok | warning | blocked
- handoff_time: <ISO 时间>

## 验收摘要
- 本 skill 验收清单通过项：全部 / 部分（列未过项）

## 数据契约（下游直接消费的 JSON）
\`\`\`json
{ <结构化数据，见 6.3> }
\`\`\`

## 产物文件清单
| 路径 | 说明 |
|---|---|
| ... | ... |

## 下一步（交给谁做什么）
- 调用 <目标 skill> 的 <首个动作>，传参：...
- 前置已满足：...
```

### 6.2 本 skill（虾格）的交接物输出字段

| 字段 | 内容 |
|---|---|
| `style_id` | 生效风格 id（本剧从零生成 / 或参考图反推；无预设） |
| `style_instructions` | 正向提示词（注入草图/首帧/视频） |
| `avoid_instructions` | 负向提示词（同上） |
| `style_tag` | 风格标签（每面板注入，仅介质+成色） |
| `suggested_name` / `suggested_label` | 命名 |
| `visual_style_config` | 已写入项目配置的 visual_style 值 |
| `visual_references` | 选定的视觉参考组（作品名 + 一句说明 + **infusion 英文可执行注入段**，见下方契约） |
| `tonal_direction` | 选定的影片基调（名称 + 一句说明） |
| `emotion_curve` | 全片情绪曲线节点表（★ 2026-09-03：nodes/acts/peak/reversals/breathing_zones/bgm_focus/principle；权威数据，分镜线情绪段标注与 BGM 取舍消费） |
| `p1_cinematic_baseline` | P1 写实线基线（★ 2026-09-03：摄影系统/风格锁定段/环境色彩/人物声音气质/环境声+音乐圣经；非写实 enabled=false） |
| `spectacle_plan` | 奇观/克制场景清单（供虾镜镜头设计） |
| `fs_library` | 项目固定风格库（outputs/fs-library.md，12 类 × 18 项；虾镜首帧按 FS-XX 引用） |
| `style_reference_frame` | 全剧定风格图（美术圣经锚）路径 + 其提示词；虾塘资产/虾镜 STYLE LOCK 统一引用（见 `references/style-keyframe-prompt.md`） |
| `style_library_writeback` | ★ v3.4.0-风格库：按 `style-preview-keyframe.md` 生成的关键场景式 `preview_prompt` + 已剥离项目数据的库条目，写回用户级 `~/.qwenworkcn/xiage-style-library/<style_id>.json`；可经虾格页导出 zip 提升进 skill `styles-library/` 种子层 |
| `next_action` | 建议交给虾镜（应用风格到生成链路） |

**视觉参考 infusion 契约（★ 2026-09-02 用户拍板，方案 B）**：
- 三步向导落地时，`outputs/creation-direction.json` 的 `visual_references` 每项 = `{name, note, infusion}`——**infusion = 该参考可取之处（note）转化的英文可执行注入段**（一一对应可追溯，禁止脱离 note 自由发挥）。
- 顶层 `asset_infusion_template` = 三版组合模板（characters/scenes/props），**角色版必须带生效范围限定句**（`Apply to garment colors, material rendering and overall tone only; keep composition and plain solid background unchanged`），防与人物/构图描述冲突。
- 下游消费：虾塘按模板把各参考 infusion 合并注入每条资产提示词（标记 `Visual reference infusion`，check-assets 校验）；虾镜首帧按同一 infusion 作构图/氛围语言。**参考≠复刻**：只提取色彩体系/材质质感/构图氛围，禁搬 IP 元素。

### 6.3 交接物 JSON 数据契约示例

```json
{
  "module": "xiage-styles",
  "style_id": "guoman_fantasy",
  "style_instructions": "Create 3D guoman fantasy ...",
  "avoid_instructions": "FORBIDDEN: photorealism ...",
  "style_tag": "3D GUOMAN FANTASY",
  "suggested_name": "Guoman Fantasy",
  "suggested_label": "国漫幻想",
  "visual_style_config": {"visual_style": "guoman_fantasy"},
  "visual_references": [{"name": "《示例参考片》", "note": "一句说明"}],
  "tonal_direction": "示例基调方向",
  "emotion_curve": {
    "scale": "0-10 观众紧张度/情感冲击度",
    "acts": [{"name": "第一幕·建置", "node_range": [1, 3]}],
    "nodes": [{"no": 1, "name": "开场", "intensity": 3.5}],
    "peak": {"no": 8, "note": "全片最高峰"},
    "reversals": [{"no": 5, "note": "关键反转"}],
    "breathing_zones": [{"no": 4}],
    "bgm_focus": [{"no": 5}, {"no": 8}],
    "principle": "一句全片导演判断",
    "chart_image": null
  },
  "p1_cinematic_baseline": {"enabled": false},
  "spectacle_plan": {"spectacle": ["场景A"], "restrained": ["场景B"]},
  "next_action": {"to": "xiajing-episodes", "action": "apply style to sketch/frame/video", "params": {"project": "..."}}
}
```

### 6.4 交接链位置

```
虾格 ──handoff（风格参数包）──▶ 虾料设置层 visual_style + 虾镜草图/首帧/视频生成链路
```

**产出方式**：风格确认/应用后，在工作区写 `handoff-xiage.md`（按 6.1 模板），并在最终回复中给出路径与核心 JSON，提示用户可直接交给虾镜或虾料消费。
