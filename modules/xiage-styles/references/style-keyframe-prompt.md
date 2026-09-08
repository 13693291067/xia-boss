# 全剧定风格图（Art-Direction Keyframe）提示词生成规范

> 性质：通用方法论，示例一律占位符，禁止写入任何具体项目数据。
> 定位：三件套 + 情绪曲线 + 奇观/克制清单落 `creation-direction.json` 后、进虾塘建资产前，产出**一条"定风格图"提示词**——一张示范全剧美术风格的样板图（美术圣经锚），供虾塘资产与虾镜镜头统一引用。

## 〇 定风格图是什么、不是什么

- **是**：一张图同时示范 **人物 / 环境 / 光影 / 色彩 / 质感** 五要素的全剧视觉基因；是"风格圣经封面"。
- **不是**：① 不是场景资产（场景母版**空镜禁人物**，本图**必须有人**以示范人物渲染，两套规则别混）；② 不是某一集某一镜的分镜首帧；③ 不是海报（不追求构图好看，追求"风格信息最全"）。

## 一、触发与输入

- **触发**：`creation-direction.json` 已生成（含 style 三要素 / visual_references / tonal_direction / emotion_curve / spectacle_plan / p1_cinematic_baseline / fs_library）。
- **取材**（读 JSON 字段 → 决定画面）：
  - `style_instructions` → 正向总纲（光影/构图/质感）。
  - `avoid_instructions` → 负面基线。
  - `visual_references[].infusion` → 把每组参考的英文可执行注入段织进画面（美学/气质/奇观）。
  - `tonal_direction` → 整图情绪。
  - `spectacle_plan` → 定调图只放**克制级**奇观（如一件发光道具），大特效（墨龙/地宫）留给分镜，别把定调图堆成特效秀。
  - `p1_cinematic_baseline.enabled`：`true` 才写实拍摄影机/镜头家族/画幅帧率；`false`（风格化）则**不写**这些，只写风格化质感词。
  - 人物外观取自 **docs 主角卡**（年龄/落魄或英气/服化道/皮肤与衣料质感）；环境取自 **docs 世界观**里最具代表性的**外景 + 天气**。

## 二、硬性要求（验收线，缺一即返工）

1. **五要素齐**：人物 + 环境 + 光影 + 色彩 + 质感，一项都不能缺。
2. **环境要有广度**：优先**外景/世界感**（建筑、街市/山野、天气、纵深、远景），不要局限单个室内角落。
3. **人物要清晰可辨**：脸、发型、服化道、皮肤光、衣料织纹都要看得见——**禁止只给剪影/背光无脸**；这是示范"这类人以后怎么渲染"。
4. **承载全片基调**：体现 `tonal_direction`，是整剧级而非单集级。
5. **英文纯净**：正向"总-分5层"（Create… 总述 → 光影 → 场景/环境 → 主体/人物 → 技术质感）；负向 `FORBIDDEN:` 平行排除；无中文、无台词、无六要素设定段。
6. **`style_tag` 不进 prompt**：只当元数据标签，且保持"介质+成色"纯净（禁时代/地域/服化道词），防止标签反过来覆盖剧情设定。
7. **宽画幅**：默认 16:9，利于同时容纳人物与环境。
8. **可追溯**：画面每个视觉特征都能回指某个 JSON 字段。

## 三、提示词组装公式

**正向 = 顺序拼接：**
```
[① 风格总纲：一句点明"这是为〈某剧〉定全剧美术风格的样板图，覆盖人物/环境/光影/色彩/质感"]
+ [② 环境（外景优先，广度+纵深+天气）：主体人物所处的世界观代表场景，远景元素做尺度参照]
+ [③ 人物（清晰）：docs 主角外观 + 表情/体态 + 服化道材质 + 打在脸/衣上的主光]
+ [④ 参考 infusion：把 visual_references 各 infusion 织入（美学/气质/奇观点缀）]
+ [⑤ 基调与克制：tonal_direction 情绪 + 只用克制级奇观点缀（spectacle_plan）]
+ [⑥ 技术质感：near-monochrome/色板 + 体积雾 + 胶片颗粒 + 浅景深 + 冷暖对撞；写实线才加摄影机/镜头]
+ [⑦ 画幅：16:9 cinematic]
```
**负面 = `avoid_instructions` + 定风格图专属：**
```
FORBIDDEN: <avoid_instructions 全文>
+ faceless or silhouette-only protagonist / backlit unreadable figure
+ cluttered over-detailed foreground（前景糊满抢主体）
+ （风格化项目）glossy plastic CGI / 过度写实皮肤
+ （如涉恐怖基调）explicit gore / flowing blood / visible ghost faces
```

## 四、首轮常见偏差 → 修正词（迭代用）

| 常见跑偏 | 修正方向/词 |
|---|---|
| 只给一个室内、环境面太窄 | 换外景：`exterior … wide establishing frame … receding depth … distant architecture` |
| 人物只是剪影/无脸 | 强制清晰：`face and upper body clearly lit and in focus, visible fabric/skin texture` + 负面 `silhouette-only` |
| 太电影写实、丢了"水墨/风格"身份 | 提纯度：`near-monochrome ink-wash tonality, paper/ink bleed texture, large negative space`（或明确选"写实+风格调色"路线） |
| 主角太英气、不符 docs 人设 | 按人设补：`haggard / unkempt / weary posture / dark circles`（示例，实际以主角卡为准） |
| 发光道具像霓虹/像血 | `matte pigment, faint inner glow only` + 负面 `neon, flowing blood` |
| 定调图堆满大特效 | 只留克制级点缀，大奇观交分镜（读 spectacle_plan） |

## 五、落盘与下游

- 生成图后，把其路径回填进 `creation-direction.json` 的 **`style_reference_frame`** 字段，作为全剧美术锚。
- 下游引用：虾塘角色/场景/道具资产按"同一风格"对齐此图（但**场景资产仍守空镜禁人物**）；虾镜首帧的 STYLE LOCK 段以本图风格为准。
- **改 JSON（换风格/参考/基调）→ 定风格图必须重出**，保持"规格→图"一一对应。

## 六、验收清单

- [ ] 五要素齐（人物/环境/光影/色彩/质感）；
- [ ] 外景或足够环境广度，非单室；
- [ ] 人物清晰可辨、非剪影；
- [ ] 体现 tonal_direction 与克制级奇观（spectacle_plan）；
- [ ] 正向总-分5层英文、负向 FORBIDDEN、style_tag 不进 prompt、16:9；
- [ ] 写实线开关正确（enabled=false 未混入实拍参数）；
- [ ] 已回填 `creation-direction.json.style_reference_frame`。
