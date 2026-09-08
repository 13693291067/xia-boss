# MiniMax H3 生视频提示词 · 全参考模式规范（Ref2VA，多图参考生视频）

> 来源：MiniMax 官方开源仓库 `MiniMax-H3/skills/h3-prompt-writing/references/ref-en.txt`（2026-08 版），2026-08-24 转写为 xia-boss 可直接调度的独立参考文件。**生成 MiniMax-H3 模型的生视频提示词（全参考模式：角色/场景/道具多图参考）时，加载本文件。**

## 0. 定位

本规范对应 **MiniMax H3** 全模态生视频模型的「全参考模式（Ref2VA）」——即虾镜生视频最常用的形态：**角色四视图 + 场景图 + 道具图**作为参考资产，生成视频时通过标签引用锁定角色形象与场景，提示词正文只描述动作与调度。

全参考模式六段式输出，**全部用英文**；仅 `<d>` 内的对白/歌词与场景中真实可见文字保留原语言。

> 虾镜生视频默认走 `hailuo-h3-cankaosheng【参考生】` / `hailuo-h3-quannengcankao【全能参考】`，底层即 MiniMax H3。基础模式（首尾帧/文生视频）见 `h3-video-prompt-base.md`。

## 1. 整体结构（六段，按序）

| 段 | 作用 |
|---|---|
| `subject_definitions` | 定义被引用的内容与引用标签 |
| `summary` | 概括任务类型、目标视频、主要引用关系 |
| `retention_analysis` | 描述各引用内容如何被保留/转移/复用 |
| `detailed_description` | 按播放顺序描述视觉、动作、镜头、声音、对白 |
| `overall_soundscape` | 总结环境音与物理音 |
| `non_diegetic_music` | 仅观众能听见的背景乐 |

## 2. 引用标签与定义（subject_definitions）

全参考模式用四类标签标识引用内容的来源与角色：

| 标签 | 含义 |
|---|---|
| `<Subject N>` | 从参考资产抽象出的、可在目标视频中复用或修改的可见内容 |
| `<Picture N>` | 作为具体目标帧/镜头规划的参考图 |
| `<Video N>` | 提供剪辑源、续写起点或整片时间结构的参考视频 |
| `<Audio N>` | 被复制或引用的音频信号 |

标签一旦分配，在 `subject_definitions` / `summary` / `retention_analysis` / `detailed_description` / 音频段中含义保持一致。

`subject_definitions` 给每个需单独追踪的引用内容（人/环境/源视频结构/音轨）单独一行，说明标签含义、引用角色、需遵循的主要特征；来源资产明确时注明对应源。若 `<Picture N>` / `<Video N>` 仅用于标识另一引用项的来源且后续不单独分析，在该项定义内引用即可，不单独成行。

### 2.1 `<Subject N>`

可复用可见内容：人/动物/物体、场景/背景/环境、服装/道具/界面/特效、风格/动作/表情/姿态。代表**将在目标视频中实际使用的內容单元**，而非源文件本身。一个主体可由多个参考资产定义，一个资产也可提供多个主体。
```
<Subject 1> is the young woman in <Picture 1>, with long dark hair, a blue cardigan, and a thin silver necklace.
```
同一主体来自多资产时合并来源并说明各自提供什么：
```
<Subject 1> is the woman whose appearance comes from <Picture 1> and whose walking motion comes from <Video 1>.
```

### 2.2 `<Picture N>`

当参考图本身作为某镜首帧/关键帧/尾帧/编辑关键帧/构图锚点时用独立 `<Picture N>`：
```
<Picture 2> is the first frame of [Shot 1], showing a woman seated beside a café window.
```
若图片仅用于定义角色/场景/服装/风格，**不要**建独立 picture 项，在对应 `<Subject N>` 定义内引用图源即可。图片作故事板/镜头规划参考时，说明映射到哪些镜、提供何种规划信息：
```
<Picture 3> is a storyboard reference for [Shot 1] and [Shot 2], defining their viewpoint, subject placement, and shot order.
```

### 2.3 `<Video N>`

仅用于整片关系：编辑原视频 / 从原视频末尾续写 / 引用其运镜·切·节奏·时间结构。
```
<Video 1> is the source video for the target video edit.
```
若参考视频中的人/物/景/动作/特效作为可见内容复用，仍归 `<Subject N>`；`<Video N>` 标识资产或结构源，不替代主体标签。

### 2.4 `<Audio N>`

独立音频资产，或参考视频中启用的同步音轨。常用：复制全部/部分音频信号、引用背景乐风格、引用说话人音色与语气、使用原音频的对白/歌词/音效、引用节拍/节奏/音频连续性。当 `<Audio N>` 明确对应目标说话人时，定义中复用该说话人全局 ID：`<Subject N> (Sx)` 或稳定声音描述后跟 `(Sx)`。
```
<Audio 1> is the voice-timbre reference for <Subject 1> (S1).
```

### 2.5 同参考视频的视轨与音轨

`<Video N>` 与 `<Audio N>` 各自独立编号，索引仅表示本类标签顺序，不编码两类配对。同一参考视频可同时对应 `<Video 1>` 与 `<Audio 2>`。普通参考视频不因含声音就自动建 `<Audio N>`。

### 2.6 ⚠️ 虾镜硬约束：参考图自动引用顺序 = 提示词 `<Picture N>` 编号顺序

**核心规则**：`buildStoryVideoPromptH3` 给每个主体分配的 `<Picture N>` 编号，**严格等于「打开生视频窗口时 `gvAutoRefs` 自动匹配的引用图片顺序」**。两者必须一致，否则引擎会把错误的图当某主体的参考。

**为什么是自动的**：虾镜生视频不直接手写垫图，而是打开生视频弹窗时由 `gvAutoRefs(ep, seg)` 按以下固定顺序自动收集该段涉及的资产图（上限 5 张）：

| 自动引用顺位 | 收集内容 | 对应 `<Picture N>` |
|---|---|---|
| 第 1…k 张 | **角色参考图**（按当前场景选身份：四视图 → 定妆照 → 角色主图） | `<Picture 1>`…`<Picture k>` |
| 第 k+1 张 | **场景图**（首个匹配到的场景） | `<Picture k+1>` |
| 第 k+2 张 | **道具图**（首个匹配到的道具） | `<Picture k+2>` |

`buildStoryVideoPromptH3` 的 `subjLabels` 分配顺序同样是 **角色 → 场景 → 道具**（`names.forEach` 先、`scenes` 次、`props` 最后），从 1 累进。因此：

- `<Subject 1>`（第一个角色）绑定的 `pic:1` → `referenced from <Picture 1>` → 指向自动引用收集到的**第 1 张图（该角色四视图）**；
- `<Subject 2>`（场景）绑定的 `pic:2` → `referenced from <Picture 2>` → 指向**第 2 张图（场景图）**；
- 依此类推。

**后果与注意**：
- 这套编号对齐是**代码保证**的（`gvAutoRefs` 与 `subjLabels` 同一套角色→场景→道具顺序），正常走自动引用时无需人工干预，`<Picture N>` 天然指向正确资产。
- **手动增删参考图会破坏对齐**：若在弹窗里手动调整了引用图顺序（增/删/换位置），`<Picture N>` 的编号含义就会偏移——例如把场景图手动挪到第 1 张，而提示词仍写「`<Subject 1>` 陈凯 referenced from `<Picture 1>`」，引擎就会把场景图当陈凯的脸去锁。手动改图后，应确认提示词引用行与实际上传顺序一致，或重新生成提示词。
- 参考图上限 5 张；超出部分不会被纳入 `<Picture N>` 编号体系。
- 角色多身份（如苏晚有「日常/职场/礼服」身份）时，`gvAutoRefs` 按段落场景关键词选最匹配的身份四视图，故同一角色在不同故事板段可能引用不同身份图——`<Picture N>` 指向的是「该段自动选中的那张」，而非固定某身份。

## 3. summary

一段简短英文概括目标视频与引用关系，**以方括号任务类型前缀开头**：
```
[reference generation] ...
[video editing + reference generation + audio reuse] ...
```
按各引用资产实际角色选任务类型：

| 任务类型 | 使用时机 |
|---|---|
| `keyframe completion` | 图片作为目标视频首帧/关键帧/尾帧/编辑关键帧等具体帧锚点 |
| `reference generation` | 图片/视频/音频为角色/场景/风格/动作/运镜/故事板等提供生成指导，但不作具体帧或待编辑/续写的源视频 |
| `video editing` | 直接修改现有源视频 |
| `video continuation` | 新内容从现有源视频续写/延伸/过渡 |
| `audio reuse` | 完整或部分复用同一音频信号 |
| `audio reference` | 不直接复制音频，仅引用其音乐风格/音色/对白歌词内容/音效质感/节拍/连续性 |

多关系用 ` + ` 组合不重复。仅因含视频/音频不自动生成对应任务类型；参考视频仅提供运镜/切/节奏通常归 `reference generation`。编辑源视频且原音频仍可闻时用 `audio reuse`；续写源视频但未直接复制音频时用 `audio reference`。

summary 用已定义的四类标签描述主体/镜头流/资产角色，**不引入新标签**。编辑任务在前缀后写 `The target video is an edited version of <Video 1>.`

## 4. retention_analysis

描述各引用内容如何被保留/转移/复制/引用，每个标签一行，保留 `subject_definitions` 中确立的含义。

### 4.1 可见内容

`<Subject N>` / `<Picture N>` / `<Video N>` 关系标记（固定英文值）：

| 标记 | 含义 |
|---|---|
| `fully_preserved` | 引用内容的定义角色被完整保留 |
| `partially_preserved` | 仍使用，但部分定义特征被改变或仅部分保留 |
| `attribute_transfer` | 引用特征转移到另一可辨识目标主体 |
| `weak_reference` | 仅保留风格/类别/构图/氛围的宽泛相似 |

```
<Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - ...
<Picture 2> ([Shot 1] first frame): fully_preserved - ...
<Video 1> (cut and pacing structure): weak_reference - ...
```

### 4.2 音频

`<Audio N>` 关系标记：

| 标记 | 含义 |
|---|---|
| `fully_copy` | 完整源音频作为目标视频完整最终音轨 |
| `partially_copy` | 仅复制部分时间线或音层，或复制后增删替换其他声音 |
| `reference` | 不直接复制信号，仅引用音色/节奏/音乐风格/对白内容/音效质感 |
| `weak_reference` | 仅保留类别或氛围的宽泛相似 |

```
<Audio 1>: fully_copy - <Audio 1> is reused 1:1 as the target video's complete final audio track.
<Audio 2>: reference - the target speaker follows <Audio 2>'s voice timbre and measured delivery without copying the original signal.
```
仅在 `subject_definitions` 已定义的引用角色内选标记；不把目标视频新加的动作/背景/剧情当引用 fidelity 损失。

## 5. detailed_description

全参考重写主体，按播放顺序逐镜描述视觉/动作/声音/对白，在适用处插入引用标签。

### 5.1 基本格式

遵循基础模式（base-en）：正文英文，对白/歌词/可见文字保留原语言；`[Shot 1]` 无时间戳，后续镜用 `[Shot N] At MM:SS.mmm, ...`；运镜写成镜头内自然英文（含类型/幅度/速度）；发声源用稳定 `(S1)`/`(S2)`；对白歌词 `<d>[Language] ...</d>`；跨切/截断/连续音频用 `<scenetrans>`/`<cutoff>`/连续性描述。

全参考差异：

| 维度 | 基础模式 | 全参考模式 |
|---|---|---|
| 主字段 | `integrated_multimodal_description` | `detailed_description` |
| 风格开头 | 写在 `[Shot 1]` 后 | `[Shot 1]` 前用 1–2 句英文确立 |
| 引用信息 | 不用全参考标签 | 在首次出现与角色适用处插入 `<Subject N>`/`<Picture N>`/`<Video N>`/`<Audio N>` |
| 音频关系 | 描述目标视频自身声音 | 在对应镜或音频相位引用 `<Audio N>` 并说明复制或引用 |

开头示例：
```
The target video is in a cinematic, literary music-video style with soft lighting and a slightly desaturated color palette.
[Shot 1] The scene opens in a crowded urban street...
[Shot 2] At 00:09.000, the shot cuts to an extreme close-up...
```
生成任务 `detailed_description` 通常 350–500 英文词；对白密集优先塞满口语时间线。单镜不自动缩短，按信息负载分布到多镜。

### 5.2 镜内使用引用标签

重要 `<Subject N>` 首次清晰出现时，描述其被引用特征、画面位置、当前动作（均在镜内实际可见），后续镜继续用同标签不再重定义。具体帧锚点用自然表达：
```
the shot begins from <Picture 1>
the shot's keyframe corresponds to <Picture 2>
the shot ends on <Picture 3>
```
编辑/续写原视频时在源状态/结构/续写关系适用处自然引用 `<Video N>`；音频关系活跃处引用 `<Audio N>`。

### 5.3 说话人 / 音频源 / 对白

物理发声的引用主体同时保留视觉标签与说话人 ID：
```
<Subject 2> (S1) turns toward the woman and says, <d>[English] Last summer, I went to my grandfather's house. He talked about you.</d>
```
`<Subject N>` 标识引用主体，`(Sx)` 标识实际说话人。同主体画外音保持同形式并标 `off-screen`。说话人不对应已定义主体时用稳定声音描述后跟 `(Sx)`。

直接复用的 BGM/完整音轨中仅作提示的言语线索、无具体人/角/旁白独立声源产出时，用 `<Audio N>` 作可闻源，不另造 `(Sx)`；具体人/角/旁白/独立声源发声时分配并复用 `(Sx)`。

对白/旁白/歌词直接复用或明确要求重演时，在 `<d>` 内逐字保留源词与原语言；听不清写 `[unclear]` 不猜不改写；标点规范到基本书写符（`,`/`.`/`?`/`!`），去重复波浪号/emoji/项目符；完整句以 `.`/`?`/`!` 收尾。仅引用音色/节奏/情绪/语气时不把原对白带入目标视频。

`(Sx)` 按目标视频实际发声事件顺序分配一次，在 `detailed_description` 每次实际发声复用；`subject_definitions` 中绑定目标说话人的 `<Audio N>` 也复用同 `(Sx)`，绝不独立新派。`retention_analysis` 不写 `(Sx)`。

## 6. overall_soundscape 与 non_diegetic_music

定义同基础模式。对话/歌唱/绑定某镜的音效事件留在 `detailed_description`；`overall_soundscape` 总结全片环境音与物理音，`non_diegetic_music` 描述仅观众可闻的背景乐。引用音频时仅在匹配可闻层声明复制/引用关系：环境音效归 `overall_soundscape`，观众专属配乐归 `non_diegetic_music`；同一音频两类内容都有则在两段分别描述。完整对白歌词只在 `detailed_description` 的 `<d>` 内，不在此两段重复。

## 7. 完整示例

```
subject_definitions:
<Subject 1> is the coffee-shop environment in <Picture 1>, featuring an exposed brick wall, an orange tufted sofa with patterned pillows, a neon sign, and a wooden coffee table.
<Subject 2> is the fluffy white Samoyed in <Picture 2>, <Picture 3>, and <Picture 4>, with thick white fur, pointed ears, a dark nose, and a curved tail.
<Subject 3> is the young blonde woman in <Video 1>, with long blonde hair and a light-pink button-down shirt with rolled-up sleeves.
<Subject 4> is the young man in <Video 2>, with short wavy brown hair and a dark-grey hoodie with drawstrings.
<Audio 1> is the voice-timbre reference for <Subject 3> (S1), containing a spoken English vocal layer.

summary:
[reference generation + audio reference] The target video shows <Subject 3> eating a cookie in <Subject 1>. <Subject 4> enters with <Subject 2>, which lunges toward the cookie. The three-shot exchange uses <Audio 1> as the voice-timbre reference for <Subject 3> and ends with a canned audience laugh.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 2], [Shot 3]): fully_preserved - the exposed brick wall, orange tufted sofa, patterned pillows, neon sign, and wooden coffee table are retained.
<Subject 2> (appears in [Shot 1], [Shot 2]): fully_preserved - the Samoyed's thick white fur, pointed ears, dark nose, and curved tail are retained.
<Subject 3> (appears in [Shot 1], [Shot 2], [Shot 3]): fully_preserved - the blonde woman's identity, long hair, and light-pink shirt are retained.
<Subject 4> (appears in [Shot 1], [Shot 2]): fully_preserved - the young man's short wavy brown hair and dark-grey hoodie are retained.
<Audio 1>: reference - its vocal timbre guides the dialogue delivery of <Subject 3> without copying the original signal.

detailed_description:
The target video uses a realistic multi-camera sitcom style with warm indoor lighting.
[Shot 1] A medium shot establishes <Subject 1>, the coffee shop with its exposed brick wall, orange tufted sofa, patterned pillows, neon sign, and wooden coffee table. <Subject 3> (S1), the young woman with long blonde hair and a light-pink button-down shirt with rolled-up sleeves, sits on the sofa holding a chocolate-chip cookie. From the left, <Subject 4>, the young man with short wavy brown hair and a dark-grey hoodie with drawstrings, enters holding the leash of <Subject 2>, the thick-furred white Samoyed with pointed ears, a dark nose, and a curved tail. The dog lunges toward the cookie and pulls the leash taut. <Subject 3> (S1) jerks her hand back and, using the clear youthful voice timbre referenced from <Audio 1>, exclaims with light annoyance, <d>[English] Hey! Watch your dog!</d> She closes her lips and guards the cookie while <Subject 4> pulls the dog back.
[Shot 2] At 00:03.000, the shot cuts to a close-up of <Subject 4> (S2), the young man in the dark-grey hoodie from Shot 1, sitting beside <Subject 3> on the sofa and holding <Subject 2> securely in his arms. <Subject 4> (S2) says in a casual young male voice with a playful tone and an easy conversational pace, <d>[English] He just likes cookies more than me.</d> He closes his mouth into an apologetic smile and strokes the dog's thick white fur.
[Shot 3] At 00:05.000, the shot cuts to a close-up of <Subject 3> (S1), the blonde woman in the light-pink shirt from Shot 1. Her annoyance softens as she looks toward the Samoyed. <Subject 3> (S1) replies in the same clear youthful voice referenced from <Audio 1> with an amused cadence, <d>[English] Well, he has good taste at least.</d> She smiles and raises the cookie in a small toast-like gesture. A classic canned audience laugh begins immediately after the line and continues through the final frame.

overall_soundscape:
Soft indoor coffee-shop room tone continues throughout the scene.

non_diegetic_music:
N/A
```

## 8. 调度方式

| 时机 | 谁 | 动作 |
|---|---|---|
| 生成 MiniMax-H3 全参考模式生视频提示词 | 虾镜（制作 Tab / 故事板生视频） | 加载本文件 → 按六段式输出，角色经 `<Subject N>` 引用四视图，正文只写动作/运镜/对白/音效 |
| 基础模式（首尾帧/文生视频） | 虾镜 | 改用 `h3-video-prompt-base.md` |
| Seedance 2.0 模型 | 虾镜 | 改用 `seedance-stylock.md`（中文 STYLE LOCK 模板） |

> 虾镜实现要点：当前 `buildStoryVideoPrompt` 已是「中文视觉描述 + 中文 refs 引用行」形态。切到 MiniMax-H3 时，应将 refs 引用行（角色=图N）映射为 `<Subject N>` 标签体系，并按本文件六段式用英文重组输出（保留分镜原意，不删用户 visual/action 内容）。
