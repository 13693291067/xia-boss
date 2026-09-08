# 虾格 · 渲染介质词组库（★ v3.2.0 新增，跨项目通用，非预设）

> 定位：只固化"用什么介质/成色画"这一层（渲染介质句 STYLE_HEAD + 主图介质锚 + 负向风格边界 + body 强标记），**不含**本剧色彩/材质/情绪调性。
> 三要素 = 本库取族固定介质句（复用）+ 本剧调性微调（每剧不同）+ 项目 infusion / 影片基调（每剧不同）。
> 与"无预设库"不冲突：本库不是成品风格，只是防趋同之外的**防风格漂**底座。
> 触发词：渲染介质、介质词组、风格族、防风格漂、STYLE_HEAD、主图介质锚、body 强标记。

## 为什么有这个库（事故根因）

资产提示词里，STYLE_HEAD 首句自带 `stylized / 3D / CG / painterly` 等词，但角色主体段（④）一旦堆大量写实人像词
（almond-shaped eyes / defined jawline / even studio lighting / matte fabric / soft specular），会把介质基调淹没，
出图漂成真人写实——而 check-assets ⑥ 只查"指纹句在不在"，**指纹句在 ≠ 风格不漂**（假校验）。
本库把"介质层"从"每剧临场手写"升级为"取族固定词组"，并配 **body 强标记硬校验**堵这个洞。

---

## 一、族定义（每族五件套：STYLE_HEAD / 主图介质锚 / body 强标记 / 负向风格边界 / 禁则）

### 族 A：3D 国漫 CG（guoman_fantasy 等；detect_style → is_cg=True）

- **正向介质句 STYLE_HEAD**（整句逐字内联到提示词最前，也是 check-assets 指纹来源）：
  `Create a premium stylized 3D Chinese animation (guoman) CG render with cinematic volumetric lighting, layered atmospheric depth, and painterly yet physically believable materials; only the rendering medium is affected, not the described wardrobe, era, or setting.`
- **主图介质锚**（证件照正向段必含，走 check-assets `CG_ANCHOR_ANY`）：`guoman CG character render`
- **角色 body 强标记**（正向 body 必含其一，防漂写实）：
  `guoman CG character render, stylized painterly 3D animated-feature look, cel-influenced soft shading with volumetric rim highlights, idealized smooth skin, visibly CG not photographic`；眼睛用 `anime-styled eyes`
- **场景 body 强标记**：`stylized painterly 3D CG environment, cel-influenced volumetric light, not photographic`
- **道具 body 强标记**：`stylized 3D CG asset render, painterly PBR materials, not photographic`
- **负向风格边界**（并入 avoid_instructions 风格边界类）：`FORBIDDEN: photorealism, live-action photograph look, photograph.`
- **禁则**：正向段禁 `film grain / realistic skin pores / subsurface / 85mm / f/1.8`（check-assets `ID_REALISM_BAN`）。

### 族 B：写实实拍（realistic / chinese_period_drama / republican_era_drama；is_cg=False）

- **正向介质句 STYLE_HEAD**（写实族必须内建真人皮肤锚，防 AI 磨皮网红脸）：
  `Create a live-action cinematic image with grounded physical realism, natural lighting appropriate to the time of day with soft realistic falloff and restrained contrast, realistic human skin with visible pores, subtle uneven tone and minor imperfections, no beauty retouching, not a plastic idol face, natural slightly asymmetric bone structure, a natural cinematic lens feel with moderate depth of field, restrained color grading with film texture; only the rendering medium is affected, not the described wardrobe, era, or setting.`
- **主图介质锚**：`85mm f/1.8`（写实族专属，CG 族禁用）
- **负向风格边界**：`FORBIDDEN: anime, cartoon, illustration styles.`
- **★ 真人皮肤禁则（v3.2.2 事故固化）**：写实族正向段**禁用** `porcelain skin / 瓷白肌 / flawless / baby skin / airbrushed / beauty retouch / ultra-smooth skin / glass skin` 这类把脸推向磨皮网红 AI 脸的词——它们与"真人感"直接冲突（事故：主图写 `fair porcelain skin`，出图变磨皮网红脸、失去宋式真实韵味）。要真实感一律用 `real photographed / visible pores / subtle uneven skin tone / no beauty retouching / not a plastic idol face / slightly asymmetric bone structure`。
- **追加**：§10.1 骨相锁定段（写实族专属）。body 强标记校验**不触发**（is_cg=False）；防"写实漂成 CG"靠 `85mm f/1.8` 强制 + avoid 前两条含 `anime / cartoon` 已进 `avoid_keys` 校验。

### 族 C：二维赛璐璐（anime 2D；is_cg=True）

- **正向介质句 STYLE_HEAD**：
  `Create a 2D cel-shaded anime illustration with clean confident line art, flat cel coloring with bold rim highlights, a limited palette, hand-painted background, and a crisp animated-feature look; only the rendering medium is affected, not the described wardrobe, era, or setting.`
- **主图介质锚**：`2D cel-shaded anime render`（走 `CG_ANCHOR_ANY`）
- **角色 body 强标记**：`2D cel-shaded anime character render, flat cel coloring, clean line art, not photographic`
- **场景 body 强标记**：`2D cel-shaded anime background, hand-painted, flat cel light, not photographic`
- **道具 body 强标记**：`2D cel-shaded anime prop render, flat cel coloring, not photographic`
- **负向风格边界**：`FORBIDDEN: 3D render, photorealism, live-action, photograph.`

---

## 二、生成规则（虾格三步向导 ①风格类型落地时）

1. 先选族（A/B/C，或把自定义归到最近族），从本库取该族 **STYLE_HEAD + 主图介质锚 + 负向风格边界**，**整句内联、逐字不改**。
2. 调性层（光影调色 / 色彩倾向 / 材质氛围）按本剧剧情在 STYLE_HEAD 之后微调，不从零发明介质。
3. 项目差异走 `visual_references.infusion`（进资产图，只改色彩/材质）与 `tonal_direction`（不进资产图，留分镜）。
4. 虾塘出资产图时，按 `detect_style` 判定族 → 把该族对应资产类型的 **body 强标记**并进正向段（STYLE_HEAD 之外）。
5. 自定义风格若介质不属 A/B/C：新增一族进本库（族名 + STYLE_HEAD + 主图介质锚 + body 强标记 + 负向边界），并同步 check-assets 的 `CG_ANCHOR_ANY` / `CG_STRONG_STYLE` 判定集。

---

## 三、下游消费

- **虾格**：写三要素时 STYLE_HEAD 与负向风格边界从本库取族固定句。
- **虾塘**：主图 / 身份定妆照 / 场景 / 道具按族套介质锚 + body 强标记（见 `modules/xiatang-characters/references/character-assets.md` §1）。
- **check-assets.py**：`is_cg` 判定、主图介质锚（`CG_ANCHOR_ANY`）、CG body 强标记（`CG_STRONG_STYLE`）以本库族定义为准。

---

## 四、跨族通则（★ v3.4.0-风格库 事故固化，对所有风格通用）

> 这三条不分族、不分项目，任何风格出资产图/展示图/定风格图都必守。各条的落地细则见对应族定义与 `style-preview-keyframe.md`。

1. **真人皮肤锚（写实族族B 强制）**：写实风格正向段必含 `real photographed / visible pores / subtle uneven skin tone / no beauty retouching / not a plastic idol face / slightly asymmetric bone structure`；**禁用** `porcelain skin / 瓷白肌 / flawless / baby skin / airbrushed / beauty retouch / ultra-smooth / glass skin`（事故：写 `fair porcelain skin` → 出磨皮网红脸、丢真实韵味）。

2. **主体/环境色彩反差**：当参考是"主体艳色 + 背景素净"（如敦煌飞天 vs 土砂洞窟），infusion **必须拆成"主体饱和色"与"环境去饱和色"两段并明写对比**（`vivid figure popping against muted environment`），**禁止把主体色并进 overall tone 把整张染成同调**（事故：矿物色塞进 overall tone → 人和背景糊成一片土褐）。主体与背景同调的风格（如宋式素净）则不强求反差。

3. **巨物尺度**：写"大到不可理喻"的巨构，靠**具体尺度线索**而非形容词堆——一点透视无边柱廊 + 尺寸数字（数百米高/绵延数公里）+ 远景缩成尘埃点 + 超广角低机位仰拍 + **极小人影当参照**；**含人影=关键场景/定风格图（允许），纯场景资产仍守空镜禁人**。

> 注：以上通则与"三族定义"配套；新增风格条目（含 `styles-library/` 挂载库）时逐条对照。
