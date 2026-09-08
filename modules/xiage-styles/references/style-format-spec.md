# 虾格 · 风格三要素格式规范（★ 创建/固化任何风格的强制格式）

> 来源：用户 2026-08-18 以「写实古装剧」为例确立的专业 AI 绘图提示词格式规范。
> **任何新风格（预设/自定义）的 style_instructions 与 avoid_instructions 必须按本规范撰写**，否则视为不合规，不得固化进虾格。

---

## 一、正向创作提示词 style_instructions（「总 - 分」分层递进结构）

**结构**：遵循「宏观定调 → 场景搭建 → 主体聚焦 → 质感落地」的逻辑顺序，共 **5 个层级**：

1. **开篇锚定核心风格**：以 `Create a + 风格定位` 开头，一句话明确画面品类与整体视觉基调（如电影感动漫半写实），先划定创作的核心方向。
2. **光影调色层**：明确画面光影规格与色彩标准（电影级布光、调色），决定整体质感档次。
3. **场景环境层**：交代背景空间与标志性环境元素（如玻璃摩天楼都市、霓虹+全息光晕），搭建画面空间载体。
4. **主体动效层**：描述核心主体动作状态与视觉亮点（如忍者动态战斗感、发光查克拉点缀），是画面视觉焦点。
5. **技术质感收尾**：补充摄影与介质参数（体积光氛围、色调情绪、景深、35mm 胶片颗粒），落地最终成像细节质感。

**书写格式**：以冒号、逗号分隔，逻辑顺承：
`定风格 → 搭环境 → 放主体 → 加氛围 → 调参数`

**示例（写实古装剧）**：
> Create a live-action Chinese period drama image with grounded historical realism when the beat or scene context calls for a period setting. Use natural lighting appropriate to the time of day with soft realistic falloff and restrained contrast. Ensure realistic skin texture with visible pores, subtle imperfections, and no beauty-retouching. Use a natural 50mm cinematic lens feel with moderate depth of field, not glossy fashion photography. Follow the beat, scene, character, and prop descriptions for exact era, wardrobe, architecture, technology and materials; do not override explicit modern, exotic, or time-travel settings. Restrained color grading with film texture, avoid poster-style over-retouching or painterly haze.

---

## 二、负面约束提示词 avoid_instructions（「平行排除式结构」）

**结构**：遵循「从大风格到小瑕疵」的优先级逻辑，全部以否定句式呈现，共 **5 类排除维度**（从高到低）：

1. **风格边界排除**：先否定大的品类方向（动漫、卡通、插画），从根源锁定画面品类底线。
2. **质感缺陷排除**：排除虚假皮肤与修图质感（塑料感皮肤、喷枪磨皮效果）。
3. **技术瑕疵排除**：排除 AI 成像常见技术问题（AI 生成伪影、过饱和 HDR 效果）。
4. **人体硬伤排除**：排除结构崩坏类错误（多余肢体、畸形手部、面部变形）。
5. **杂物元素排除**：排除画面冗余元素（文字、水印、标签）。

**书写格式**：全部用 `NOT / No / 禁止 + 禁止项` 的短句并列，优先级从高到低，先卡风格边界，再补细节避坑。

**示例（写实古装剧）**：
> FORBIDDEN: anime, cartoon, illustration styles. NOT plastic skin or airbrushed texture. No AI artifacts, oversaturated HDR, or poster-grade retouching. No extra limbs, mutated hands, or deformed faces. No text, watermarks, or labels on image.

---

## 三、配对逻辑（二者互补，缺一不可）

- **正向提示词**（style_instructions）负责**搭建画面、定义审美**；
- **负面提示词**（avoid_instructions）负责**排除错误、守住底线**。
- 二者互补，是专业 AI 绘图提示词的标准组合范式。

---

## 四、强制校验清单（固化任何新风格前逐项检查）

- [ ] style_instructions 以 `Create a + 风格定位` 开头（≥2 个层级要素按 光影→场景→主体→技术 顺序展开）
- [ ] style_instructions 明确"只影响渲染介质，不擅自改服饰/场景/时代"（场景/时代细节交给 beat/scene/character 描述）
- [ ] avoid_instructions 覆盖 5 类排除（风格边界→质感→技术→人体→杂物），全部否定句式
- [ ] style_tag 满足标签纯净性（只描述介质+成色，禁时代/地域/服化道词）
- [ ] 含 style_id / style_label / recommended_for；自定义风格附 confirmed_by_user + confirmation_note
