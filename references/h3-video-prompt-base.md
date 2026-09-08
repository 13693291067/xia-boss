# MiniMax H3 生视频提示词 · 基础模式规范（T2VA / I2VA / FL2VA / L2VA）

> 来源：MiniMax 官方开源仓库 `MiniMax-H3/skills/h3-prompt-writing/references/base-en.txt`（2026-08 版），2026-08-24 转写为 xia-boss 可直接调度的独立参考文件。**生成 MiniMax-H3 模型的生视频提示词（基础模式：文生视频 / 首尾帧）时，加载本文件。**

## 0. 定位

本规范对应 **MiniMax H3** 全模态生视频模型的「基础模式」提示词写法。H3 支持 4–15s、最高 2K、原生立体声音频、多宽高比；基础模式含四种任务：

- **T2VA**：纯文生视频，从文本构建完整视听时间线。
- **I2VA**：首帧参考生视频（第一帧 = 参考图，向前发展）。
- **FL2VA**：首尾帧参考生视频（首帧 + 尾帧两张图锚定，连续插值）。
- **L2VA**：尾帧参考生视频（末帧 = 参考图，收敛到该帧）。

> 虾镜生视频走 `hailuo-h3-cankaosheng【参考生】` / `hailuo-h3-quannengcankao【全能参考】`，底层即 MiniMax H3。多参考图生视频请改用 `h3-video-prompt-ref.md`（全参考模式六段式）。

## 1. 最终提示词结构

### 1.1 第一部分：指令行（Instruction）

**T2VA** 无对齐指令，直接以三个核心字段开头。

**I2VA** 固定用：
```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
```

**FL2VA** 固定用：
```
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.
```

**L2VA** 固定用：
```
How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.
```

`N` 为实际末镜索引，`S.SS` 为有效视频时长（保留两位小数）。指令必须是最终提示词**第一行**，其后空一行再接核心字段。

### 1.2 第二部分：三个核心字段

```
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- **integrated_multimodal_description**：沿时间线描述视觉、动作、镜头、说话人、对白、歌唱、画内音。
- **overall_soundscape**：总结全片环境音、物理动作音、非语言人声（1–4 句英文）。
- **non_diegetic_music**：角色听不到、仅观众能听见的背景乐（1–3 句英文，描述配器/速度/节奏/动态）。

## 2. 关键帧融入多模态描述

- **I2VA**：先建立首帧图的风格/主体/构图/场景锚点，再描述后续动作。结构：`首帧锚点 → 动作起始 → 连续发展 → 结果或反应`。
- **FL2VA**：图1 是开头、图2 是结尾，重点写主体如何运动、姿态如何变化、物体如何被操作、构图如何演化、场景或光线如何过渡。FL2VA 通常**单镜**以便模型从首帧连续插值到尾帧。结构：`首帧状态 → 可观测中间变化 → 差异渐进收窄 → 尾帧状态`。
- **L2VA**：图1 是末帧，推断一个合理的更早状态，再描述人物/物体/镜头/场景如何逐步逼近参考图。结构：`合理前态 → 明确动作与过渡路径 → 末镜渐进收敛 → 尾帧落定`。

## 3. 三个共享核心段写法

### 3.1 沿时间线展开多模态描述

`integrated_multimodal_description` 是主体。每个细节都应对应可见或可听：视觉风格、初始构图、主体外观与位置、场景与关键道具、动作与反应、镜头切换、口语、同步画内音。

`[Shot 1]` 开头先声明整体风格与初始构图。常见风格：`Cinematic` / `live-action` / `2D-animated` / `3D CG` / `claymation` / `watercolor` / `vintage film`。关键帧任务从参考图推导风格；T2VA 从用户文本选。

### 3.2 镜头与切

首镜不加时间戳。后续镜用递增切镜时间（落在视频时长内）：
```
[Shot 2] At 00:03.500, the camera cuts to...
```
普通切用 `the camera cuts to` / `the shot cuts to` / `the shot transitions to` / `the shot changes to` / `the shot switches to`。仅当距离或轻微角度变化时才用镜头运动替代切。

### 3.3 运镜：运动类型 + 幅度 + 速度

> **运镜选型 / 三轴辨误 / 环绕代价 / 战斗段让位 R31，见中立层 `shared-camera-movement.md`（模型无关）；下表只登记 MiniMax H3 的英文方言词。**

完整运镜表达含三维度：**运动类型**定义相机怎么动，**幅度**定义构图变化范围，**速度**定义节奏。仅在有意义时加幅度/速度（中幅/常速通常省略）。

| 维度 | 可用表达 |
|---|---|
| 运动类型 | `Zoom In / Zoom Out`（焦距变、机身不动）；`Push In / Pull Out`（相机前/后移）；`Pan Left / Pan Right`（机身不动镜头水平转）；`Truck Left / Truck Right`（相机水平平移）；`Tilt Up / Tilt Down`（机身不动镜头垂直转）；`Pedestal Up / Pedestal Down`（整机升降）；`Arc Shot`（绕主体弧移）；`Tracking Shot`（跟拍运动主体）；`Static Shot`（机身与镜头静止）；`Shake Slightly / Shake Strongly`（轻/强抖）；`POV`（主观视角）；`Roll Clockwise / Roll Counterclockwise`（绕光轴滚转）；`Whip Pan`（甩摇·极快水平转带动态模糊）；`Crash Zoom`（急推·极快变焦逼近）；`Dolly Zoom / Vertigo`（希区柯克变焦·机位前后移+反向焦距，选型见中立层） |
| 幅度 | `with small amplitude`（小范围）/ `with large amplitude`（大范围） |
| 速度 | `at slow speed` / `at fast speed` |

运镜要写成镜头内自然的英文动作，而非句尾堆叠标签：
```
The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.
The camera pans right with large amplitude at fast speed, revealing the open doorway.
The camera holds a static shot as the runner exits the frame.
```

### 3.4 说话人 / 对白 / 歌唱

发声主体用稳定 ID 如 `(S1)`、`(S2)`；多人同说用复合 ID `(S1,S2)`。同一说话人跨镜保持同一 ID；不发声者不给 ID。

首次出现时从视觉/音频上下文给出稳定身份（角色类型/年龄/性别/是否出镜/音高/音色/语速/口音），把身份短语、ID、动作、语气放在 `<d>` 外；`<d>` 内只放语言标签与原始口语内容，逐字保留不翻译不改写：
```
The young woman with a quiet, breathy voice (S1) says: <d>[English] I get off at the next station.</d>
The two children (S1,S2) shout together, <d>[English] Wait for us!</d>
```
画外音用 `says in an off-screen voiceover`，并在 `<d>` 后注明对应出镜角色嘴唇闭合：
```
The man (S1) says in an off-screen voiceover: <d>[English] I still remember that road.</d> while his lips remain completely closed.
```
对白跨切用 `<scenetrans>` 标注接续点并声明音频连续；语音被视频结尾截断用 `<cutoff>`。

### 3.5 屏幕可见文字

真实可见的横幅/招牌/标签/字幕/霓虹文字用英文双引号包裹，逐字保留原文不翻译：
```
A red neon sign reading "营业中" glows above the doorway.
```

### 3.6 overall_soundscape

1–4 句英文连续段落，总结全片环境音、物理动作音、非语言人声（风/雨/交通/脚步/布料摩擦/撞击/呼吸/笑声/喘息）。对白/歌唱/画内乐已在多模态描述中，此处不重复。`N/A` 仅当用户明确要求全程静音。

### 3.7 non_diegetic_music

1–3 句英文，描述角色听不到、仅观众能听见的背景乐，聚焦配器/速度/节奏/动态变化，不用抽象情绪词。角色能听见的歌唱/乐器/广播/电视/手机乐是画内事件，归多模态描述。`N/A` 表示无背景乐。

## 4. 完整示例

### Case T2VA
```
integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium-wide shot frames a baker opening the shutters of a small street bakery before sunrise. The camera pushes in with small amplitude at slow speed as the middle-aged baker with a calm, slightly raspy voice (S1) places a fresh loaf on the wooden counter and says: <d>[English] First batch of the morning.</d> [Shot 2] At 00:05.000, the camera cuts to a close-up of steam rising from the sliced bread while the baker's final words carry over from the previous shot.

overall_soundscape: Wooden shutters scrape open over a quiet street as trays clink softly inside the bakery. The doorbell rings once, followed by light footsteps and the crisp sound of bread being sliced.

non_diegetic_music: A soft acoustic-guitar pattern at a moderate tempo, joined by sparse upright-bass notes and a gentle fade at the end.
```

### Case I2VA
```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, the young woman shown in <Picture 1> remains beside the rain-covered train window, preserving her appearance, clothing, seat position, and the carriage layout. The camera trucks right with small amplitude at slow speed as she lifts her gaze from the folded letter toward the passing city lights. Her reflection moves across the glass while the quiet, breathy young woman (S1) says: <d>[English] I get off at the next station.</d> She folds the letter along its existing crease.

overall_soundscape: The train wheels produce a steady metallic rhythm beneath a low ventilation hum. Rain ticks against the window while paper rustles softly in her hands.

non_diegetic_music: Sustained cello notes at a slow tempo with widely spaced piano tones, gradually decreasing in volume.
```

### Case FL2VA（8 秒单镜）
```
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the 8.00-second mark of the target video.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, a rain-soaked cyclist begins in the position and framing established by Picture 1, holding a closed black umbrella beside a silver bicycle. The camera pulls out with small amplitude at slow speed as she releases the bicycle handle, raises the umbrella above her shoulder, and presses the runner upward until the canopy opens. Water rolls from the expanding fabric while she steps beneath it, rotates the handle into the final angle, and settles into the pose, spacing, and composition established by Picture 2 at the end of the shot.

overall_soundscape: Rain falls steadily on the pavement, followed by the metallic click of the umbrella runner and the soft snap of the canopy opening. Water drips from the bicycle frame as distant traffic passes.

non_diegetic_music: N/A
```

## 5. 调度方式

| 时机 | 谁 | 动作 |
|---|---|---|
| 生成 MiniMax-H3 基础模式生视频提示词 | 虾镜（制作 Tab / 故事板生视频） | 加载本文件 → 按任务类型（T2VA/I2VA/FL2VA/L2VA）输出对应结构 |
| 多参考图生视频 | 虾镜 | 改用 `h3-video-prompt-ref.md`（全参考六段式） |

> 配套：全参考模式见 `h3-video-prompt-ref.md`；Seedance 2.0 模式见 `seedance-stylock.md`。
