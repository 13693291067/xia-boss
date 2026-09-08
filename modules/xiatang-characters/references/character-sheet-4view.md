# 四视图角色卡模板（身份图第二图 · 独立调度文件）

> 来源：虾塘「身份图两图制」+ 剧本转分镜人物资产规范（§11.3），2026-08-21 提取为独立文件。
> **★ 2026-08-21 用户拍板（两图制）**：身份图 = ① 定妆照 + ② 四视图角色卡两张图；**四视图角色卡的提示词固定为用户钦定模板（本文 §A，中文，逐字复制，不得改写/精简/翻译）**。做身份图第二图（四视图角色卡）的提示词时，加载本文件；第一图（定妆照）规范见 `character-assets.md`。

## 0. 定位

每个身份的「四视图角色卡」= 上下两段式定妆参考板：**上段 1/3 = 正脸特写 + 侧脸特写两张面部图；下段 2/3 = 放大正面服装展示图 + 完整背面全身图**。与定妆照同一人物、同一套服装、同一配饰。

**调度方式**：
- 虾塘产出身份图第二图时，提示词**固定为 §A 用户钦定模板**（逐字复制，不自行发挥）。
- **生成时自动引用该身份定妆照作参考图**（锁脸：面部特征/发型/妆容/头饰与定妆照高度一致）——前端「四视图」按钮已内置此逻辑。
- 前端「四视图」按钮：身份区【生成】按钮后置；点击后以该身份定妆照为参考图 + §A 固定提示词入队生图，产物显示在身份卡后方的四视图卡图位。

---

## A、固定提示词模板（★ 用户钦定，逐字复制，禁止改写）

> 以下为四视图角色卡提示词唯一标准，**原样使用**（含中文，豁免"英文纯净"纪律——钦定模板不受 AI 生图英文纯净约束）：

```
请基于参考人物，输出一张真人角色定妆参考板四视图，采用干净的摄影棚灰背景，整体呈现为专业级别的真人形象设定参考图，排版工整、视觉简洁——注意这不是宣传海报，也不是杂志大片，画面中不要出现剧情动作，不要复杂环境布置。
版面需严格按上下两段式划分：上段占据整体高度的三分之一，下段占据剩余三分之二。上段展示两张高精度面部特写，左边是正脸特写、右边是侧脸特写，两张图均以头部加肩颈为主体，构图要紧凑，把五官细节、骨相结构、妆容效果、发型走向、头饰配件与神情状态都清晰呈现出来。人物的面部特征、发型、妆容与头部饰品必须和参考图高度一致。皮肤要呈现真实质感，毛孔、细纹、绒毛、睫毛与碎发都要保留，皮肤受光后的细微起伏也不能磨掉，不允许磨皮、过度锐化或人像美容处理，最终效果要接近高清真人棚拍定妆照的质感。
下段展示两张身体与穿搭参考图，左右并排。左边这张必须是被放大处理过的正面服装展示图，人物保持标准A字站姿，重点不在于展示完整全身，而是要让角色在画面里的占比明显更大——采取更近距离的正面取景，从肩颈以下开始入画一直到鞋子，头部因为构图放大会被自然裁切出画面外。请特别注意，这不是常规的远景全身照，而是刻意拉近放大后的正面服装图：人物在画面中的身形比例要显著更大，上身与下身穿搭都需要被放大呈现，整体感觉更像是时装定妆照里那种服装主体展示效果。双臂、双肩、双手、躯干、腰线、腿部与鞋子这些部位都必须完整入镜，画面边缘只能裁掉头部，绝不能裁掉手部、脚部或身体主干。左图相比右侧背面图，必须显得更"近"、更"满"、更"放大"，让服装的细节和身材比例更加突出。不允许把左图处理成普通小比例的全身照，不允许人物在左图中显得渺小，不允许头部残留 in 画面里，也不允许只裁掉半个头部而留下下巴、嘴唇、鼻子或发梢边缘。
右边这张图是标准A字站姿的完整背面全身照，人物背对镜头，从头顶到鞋底的背面细节需要完整呈现，包括发型背部走向、服装背面结构、鞋子样式和整体轮廓，用来展示角色的背面造型。这张图属于常规比例的完整背面展示，不需要像左图那样做放大裁切处理。
下段的两张图必须是同一人物、同一套服装、同一配饰、同一身体比例。整体维持修长的超模式身材比例，但不要做出夸张变形的效果。服装款式、面料层次、鞋履、穿搭风格、服装结构与配饰细节都必须严格还原原图设定。所有服装配饰都要呈现出真实的物理材质感——布料要有自然的褶皱、垂坠感和厚薄层次变化，金属要有真实反光效果，皮革、丝绸、纱料等材质的质感都要表现真实自然。如果原图中的服装是开叉长裙款式，左侧放大正面图里可以让人物自然地把一条腿向前迈出半步，展示开叉结构与露腿效果，但整体姿态仍要维持定妆照式的稳定感，不能做成走秀动作。
灯光只使用简洁统一的摄影棚三点布光：主光源在正左侧，辅助光源在正右侧，轮廓光源在后右侧。不要杂乱的光效组合，不要使用彩色灯光，不要加入强烈的氛围效果。背景统一为纯净的无缝灰色摄影棚背景。
强制要求：上段两张脸部特写占据画面上三分之一区域；下段两张身体图占据画面下三分之二区域；左下图必须是"放大处理后的正面服装展示图"，人物占比要明显更大，头部因近距取景被完整裁切出画面外；右下图必须是完整的背面全身图。不允许左下图变成普通比例的全身小图；不允许左下图出现任何头部信息；不允许左右两图的服装出现不一致；不允许人物身体比例出现漂移；不允许出现AI油腻感、塑料皮肤感、过度美颜感或廉价CG质感。
```

**固定模板使用规则**：
1. 生成任何身份的四视图角色卡，提示词 = 上述模板**逐字原样**，不增删、不改写、不翻译成英文、不拼接妆造段。
2. 参考图 = 该身份**定妆照**（`{角色}-{身份id}.png`），不是主图——四视图卡与定妆照保持同一造型。
3. 产物命名：`{角色}-{身份id}-sheet`（如 `角色A-id1-sheet.png`），build-data-js.py 按此前缀匹配 `sheet_image/sheet_ready`。
4. 豁免纪律：本模板为中文钦定模板，不受虾系「提示词英文纯净」约束；其余身份图（定妆照）提示词仍须英文纯净。

---

## B、定妆照（身份图第一图）参考

- **★ 2026-08-21 用户拍板：身份/造型定妆照 = 正面全身定妆照基准（按 02-storyboard-master 全身定义，非证件照式）**——主图证件照式已锚定"脸"，身份定妆照负责锁定该身份的**完整造型**。
- **正面全身站姿**：正面朝向镜头、双臂自然垂放、完整呈现全身造型（不画多角度/转面/动作）。
- **一次定死**：面容 / 发型 / 体型 / 服装（材质+剪裁+颜色）/ 鞋子 / 随身物件——该身份全部造型细节在此锁定，作为该身份后续所有生成（含四视图卡）的基准。
- **镜头与光**：85mm 人像镜头 f/1.8 浅景深；单一主光源柔和均匀正面光（正前方偏上，色温 5600K）；简洁中性背景（浅灰/白，`plain solid background`）。
- **妆造设计段**（写在定妆照提示词内，英文纯净）：妆面（底妆质感/眼妆层次/眉形/腮红/唇色）+ 发型 + 服装 + 配饰 + 色彩基调；**保持角色面部结构不变**（脸型轮廓/三庭五眼/五官结构不动），妆容只为区分身份气质。
- 示例：`Makeup and styling: natural dewy base with light brow, soft neutral lips, low ponytail, beige knit and camel coat, minimal accessories, warm neutral tone.`
- **与主图同一面容**（锁脸指令 + 主图作 ref）。
- **遵守资产图通用要求（★ 用户钦定清单）**：纯中性背景；无场景；无其他人物；无文字；无尺寸标注；无说明标签；无水印；人物采用自然中性站姿；身体比例统一；年龄统一；发型统一；面部统一；服装统一；鞋履统一；道具统一；材质真实；正、侧、背视图结构一致；禁止服装漂移；禁止左右道具错位；禁止多余手指和肢体畸形。
- **英文纯净**：定妆照提示词正文英文纯净，中文只进元数据（四视图卡 §A 钦定中文模板除外）。

**定妆照提示词模板（英文，可直接生图）**：

```
Full-body character sheet style portrait, front-facing full standing pose, arms naturally relaxed at sides,
complete outfit fully visible. [身份一句话，如: the daily-housewife look of 角色A]

Face identical to the reference image, same facial features, only change outfit / accessories / styling, NOT face.
Hair: [发型]. Body: [体型]. Outfit: [服装材质+剪裁+颜色]. Shoes: [鞋]. Belongings: [随身物件].
Makeup and styling: [妆造段].

Plain light-grey solid background, no scene elements, no other people. Single soft even frontal light from
front-above, 5600K. 85mm portrait lens f/1.8 shallow depth of field. natural lens sharpness, subtle film grain,
not over-retouched, not plastic.
negative: text, watermark, logo, labels, size marks, captions, other people, scene elements, clothing drift,
misplaced accessories, extra fingers, deformed limbs.
```

### B2、有服装参考图版 = 服装通用参考版（★ 2026-08-21 用户拍板：固定写死，整体替换，非追加）

用户上传服装参考图时（前端「🛍 服装参考」按钮，参考图第 2 张，**图1=主图（images[0]，锁脸）、图2=服装参考图（images[1]）**），**提示词整体替换**为下述**固定「服装通用参考版」**（用户钦定，逐字写死，**图1/图2 写法原封不动**，对任何身份通用——发型/妆面/服装全部以参考图为准，不写任何身份专属妆造文字）：

```
Full-body character sheet style portrait, front-facing full standing pose, arms naturally relaxed at sides, complete outfit fully visible.
Face identical to 图1 (main portrait), only change styling, NOT face.
Outfit, hairstyle and makeup: strictly replicate 图2 (clothing reference) — garment fabric, cut, color, silhouette, hairstyle and makeup all identical to the reference; do not redesign, do not alter sleeve or hem length. Only take the look itself from 图2, ignore the model's face, scene, lighting and background in it.
Plain light-grey solid background, no scene elements, no other people, no text, no watermark, no labels.
Single soft even frontal light from front-above, 5600K, 85mm portrait lens f/1.8 shallow depth of field, natural lens sharpness, subtle film grain, not over-retouched, not plastic.
negative: text, watermark, logo, labels, size marks, other people, scene elements, clothing drift, misplaced accessories, extra fingers, deformed limbs, no redesign of the outfit, no altering the reference garment.
```

**规则**：
- 提示词 = 上述固定模板**整体替换**（不是追加段、不拼接原提示词），杜绝与身份专属服装文字冲突；
- 发型/妆面/服装**全部以参考图为准**（图2=images[1]）；**脸仍锁主图**（图1=images[0]，`ignore the model's face` 忽略参考图模特的脸）；
- 对任何身份通用，无需按身份改写；
- 移除服装参考图 → 前端恢复标准版（原身份提示词）。
- 前端实现：`gen.js` 常量 `OUTFIT_REF_PROMPT`（写死，含中文「图1/图2」）；`genOutfitRefPicked()`（选图→isOutfit 打标→预览"👗 服装参考"角标→**整体替换** textarea 为该模板）；`genSend` 提交前兜底（含服装参考且提示词缺特征句 `Outfit, hairstyle and makeup` → 替换回）；`genRefRemove`/`genRefClear` 移除后恢复标准版；按钮仅身份图弹窗显示。

---

## C、硬性规则

1. 四视图卡提示词**固定**为 §A 模板，不得用其他布局/描述替换。
2. 上段两张面部特写、下段左放大正面服装图 + 右完整背面全身图——版式必须符合 §A 的上下两段式，不可改成等大 2×2 或 1:1 四宫格。
3. 锁脸：四视图卡以**定妆照**为参考图（非主图）；定妆照以**主图**为参考图——三级锁脸链：主图 → 定妆照 → 四视图卡。
4. 若用户追加"给英文版"，仅在 §A 模板基础上翻译，不改布局与约束语义。
