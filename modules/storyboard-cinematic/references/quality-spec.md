# H3 提示词质量规范（Quality Spec）

> 定位：`ref2va-guide.md` 与 `shared-format-rules.md` 之上的**质量层**。格式规则管"合规"，本规范管"优秀"。
> 生成或评审任何 H3 Ref2VA 提示词时，先过格式规则，再逐条过本规范；两关全过才允许交付。
> 本规范来源于多轮真实评审中沉淀的高频翻车点，每条均为可检查的硬规则，附可直接抄写的修正句。

## 0. 一句话总纲

**字段名对了不等于写对了**：六段全英文、H3 原生语法、标签双向绑定、retention 三段式齐全、summary 有流程、零幽灵元素、参数有精度、剪辑音频同标尺、修订必回归。

## 1. 语言铁律（最高优先级）

- 六段正文 **100% 英文**；中文只允许出现在 `<d>` 内的台词/歌词与画面可见文字里。
- 专有名词处理：人名、地名用拼音或音译（如 Su Wanwan、Qingshi Village），不写汉字；如需锚定原文，可在首次出现时括注一次。
- **禁止 Seedance 字段残留**，已知变体逐类扫描：
  - 冒号字段引导：`Frame:` / `Camera:` / `Dialogue:` / `Sound:` / `Diegetic sound:` 等一律改写为镜头内自然英文句。声音示例：写 `Low waves moan and distant gulls cry over the water.`，不写 `Diegetic sound: the low moan of waves`。
  - 景别缩写括号：`(ELS)` `(WS)` `(CU)` `(MS)` 及 `The shot is framed as a close-up (CU)` 模板句式——H3 不依赖缩写，直接写自然名词短语 `an extreme long shot` / `a close-up`；景别随运镜的变化由运镜句本身表达，不单独写 `then reframes to a wide shot`。
  - 切点标点：`At 00:03.500, The shot...` 逗号后应小写 `the`。
- 常见中文泄漏点（逐处扫描）：subject_definitions 里的 "in图片1"、括号内中文注释（如 `（微尘光斑）`）、中文引号「」、中文顿号。
- **画面可见文字写法**：画面中实际可见的招牌/横幅/字幕/霓虹灯文字，放入英文双引号内**逐字保留原文与标点、不翻译**：`A red neon sign reading "营业中" glows above the doorway.`；并确保该文字在对应镜头的画面描述中真实出现（否则即幽灵元素）。
- **文字通读**：交付前整稿通读一遍，清除同句重复短语（如 `the voice stabs in, joined by a ring that stabs in with the voice` 中 `stabs in` 出现两次）、与运镜句语义重复的景别句等冗余。
- 判定方法：把六段正文粘贴到纯文本检查器，除 `<d>...</d>` 包裹内容外出现任何 CJK 字符即为违规。

## 2. 台词四件套（画外音/对白必查，缺一即翻车）

1. **说话人编号** `(Sx)`，按目标视频实际发声顺序一次性分配、全篇复用；
2. **画外声明** `says in an off-screen voiceover`（画外音必写）；
3. **语言标签 + 原话** `<d>[Chinese] …</d>`，逐字保留、只保留基础标点；
4. **闭嘴声明** `while <Subject N>'s lips remain completely closed`（画外音落在在画角色身上时必写）。

- 缺第 4 项 = 高概率口型翻车（模型会让在画角色对画外音对口型）。
- 说话人不对应任何参考资产时，用稳定声音描述 + `(Sx)`（如 `An elderly woman's sharp, piercing voice (S1)`），提供年龄/性别/音色/音高中至少两项。
- 说话人边界规则：**从不发声的角色不编号**（只露脸、只被提及不给 `(Sx)`）；同一说话人跨镜头保持同 ID；多人齐声写 `(S1,S2)`。
- 台词跨切点：在两部分衔接处用 `<scenetrans>`，并明确声明音频跨切点延续（`continues seamlessly across the cut` / `carries over from the previous shot`）；台词被视频结尾截断：用 `<cutoff>`。
- 反例 → 正例：
  - 反例：`Dialogue: 老妇（尖锐）：「丫头！你个扫把星！」`
  - 正例：`An elderly woman's sharp, piercing voice (S1) says in an off-screen voiceover: <d>[Chinese] 丫头！你个扫把星！</d> while <Subject 1>'s lips remain completely closed.`（示例台词为虚构，仅演示四件套形态）

## 3. 标签纪律

- 图像**仅作来源**（角色定妆/场景参考）→ 写进 `<Subject N>` 定义内（`the young woman in <Picture 1>`），**不单独立条**。
- **Subject 定义自带最小识别特征集**：在标签来源之外，用 2–3 个文字特征兜底（发型/服装/显著标记，如 `with long dark hair, a blue cardigan, and a thin silver necklace`）。只写 `the character Su Wanwan in <Picture 1>` 而无任何文字特征 = 锚定单点故障——参考图解析不佳时没有兜底。
- 图像充当**具体帧锚点**（首帧/关键帧/尾帧）→ 单独立条：`<Picture 2> is the first frame of [Shot 1], showing ...`；正文用自然措辞挂接：`the shot begins from <Picture 1>` / `the shot's keyframe corresponds to <Picture 2>` / `the shot ends on <Picture 3>`；retention 标注对应帧位（如 `[Shot 1] first frame`）。
- 图像充当**规划参考**（分镜板、空间拓扑俯视图、走位图）→ `<Picture N>` 单独立条，声明映射的镜头与提供的规划信息。
- 规划参考写法模板：
  `<Picture 4> is a spatial-planning reference (a top-down floor plan of the set) for [Shot 1] to [Shot 4], defining the relative positions of ..., the camera flight path, and all character blocking.`
  并在正文规划**实际生效处**引用一次（如 `[Shot 1]` 的航拍路径），retention 单独一行。
- **全篇标签可回溯**：出现的每个 `<Subject/Picture/Video/Audio N>` 必须在 subject_definitions 有定义；禁止裸写 "图片1 / 图2 / image N / 图 N" 等未定义引用。
- **绑定是双向的（标签断链 = 参考锚定失效）**：不但正文出现的标签必须已定义（正文→定义），**每个已定义的 Subject 也必须在其内容实际出现的镜头正文里被显式引用**（定义→画面挂接）。正文只写内容不挂标签时，H3 失去"该画面元素即参考图元素"的锚定，一致性显著下降。
  - 高频翻车样例：石屋、黄泥墙、屋梁干鱼都写了，`<Subject 2>` / `<Subject 3>` 却一次没出现。
  - 修正句模板：`the low stone houses of <Subject 2>` ／ `the mottled, peeling yellow-mud wall of <Subject 3>` ／ `the three strings of dried fish of <Subject 3>`。
  - 检查方法：逐个数每个已定义标签在 detailed_description 中的出现次数，**为 0 即违规**。
- `<Video N>` / `<Audio N>` 独立编号，不编码配对。

## 4. retention_analysis 针对性规则

- **每行必须完整三段式**：`<标签> (appears in [Shot N]...): 标记 - 解释`。标记词（`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`）**不可缺省**——缺标记即格式违规，无论解释写得多好；规划类参考也要有标记（写"被遵循的空间关系/路径"，不写"外观被保留"）。
- 每行解释必须写**该标签自己**被保留/修改/迁移了什么；**禁止多行复制粘贴同一句模板文**（如四行都是 "the referenced appearance, costume, spatial layout, and set landmarks are retained"）。
- 每行标注**实际出现的镜头**；身体部位特写（手、眉眼入画下缘）与 POV 视角同样算出现，不得漏标。
- 参考图健康态 vs 剧本状态（病容/伤妆/变装/wet hair）矛盾时，必须在 Subject 定义里**显式声明状态叠加**（`in the target video she appears gaunt, with sunken cheeks...`），retention 对应写 `with the gaunt, sallow on-script condition applied`——不许定义说 preserve exactly、正文却写病容。
- **定义作用域覆盖全部出现形态**：`<Subject N>` 的定义不得窄于正文用法——定义写 `house (interior)` 而正文中该屋以**外观**出现（村边破屋、檐下干鱼）即错位。修正：定义不限定内外（`the most run-down house of <Subject 2>`），或对内外两种形态分别说明。
- 完整三段式正例：`<Subject 1> (appears in [Shot 2], [Shot 3], [Shot 4]): fully_preserved - her facial identity, hair, and appearance from <Picture 1> are retained, with the gaunt, sallow on-script condition applied.`
- 边界：目标视频**新增的动作/背景/剧情事件不算保真损失**——Subject 标 `fully_preserved` 与镜头里出现新动作并不矛盾，不要因新增节拍而降级标记。

## 5. 镜头结构与 summary 质量

- **summary 三要素齐备**：主体（谁在做什么）+ 镜头流程（从什么到什么）+ 关键声音事件与素材角色；禁止只罗列标签 + `in a cinematic scene` 式空泛表述。
  - 反例：`shows <Subject 1>, <Subject 2>, <Subject 3> in a cinematic scene.`
  - 正例：`shows <Subject 1> waking up in distress inside <Subject 3> at the edge of <Subject 2>, moving from an aerial approach over the morning sea to a close view of her dazed awakening, while one off-screen elderly female voice scolds her; spatial blocking follows <Picture 4>.`
- 运镜写成镜头内自然英文动作句（类型 + 幅度 + 速度），禁止 `Camera: 航拍式缓慢前推` 字段式堆叠。
- **固定机位 ≠ 切镜**：`Static shot` 与 `cuts on her eyeline / eyeline match` 不能出现在同一镜头；视线匹配必须拆成两个镜头——`[Shot N]` 视线上抬/闭眼，`[Shot N+1] the shot cuts on her eyeline to ...`。
- **末镜承载时长**：单镜 > 5 秒时，镜内必须有动作递进（A→B→C）或拆镜；否则节奏塌陷。
- `[Shot 1]` 无时间戳；后续切点严格递增且在时长内；每次切镜引入新信息，仅改变距离/微角度用运镜不用切镜。
- 主体状态叠加（病容、湿发）在镜头首次出现处与 Subject 定义一致，不得前后矛盾。
- **节拍完整性对照原稿**：转换稿与 Seedance 原稿逐节拍核对——既不新增（如原稿没有的"撑起身/扶额"收尾动作），也不删减（原稿有的节拍被漏写）；无法确认时向用户标注待核对项，不擅自取舍。

## 6. 幽灵元素扫描（交付前必做）

- **正文没有的元素，禁止声明存在**：凡写了 `MUST be rendered / must appear / 一定要出现` 的元素，必须在某个镜头的正文里有对应描述；对不上号即为幽灵元素，删除声明或补写镜头。
- **剧本上下文残留**：转换只针对当前片段节拍；后续情节的道具（外挂界面、金手指、信物）、未出场角色、未到节拍的事件不得带入六段正文。
- **负面清单/禁令不是 H3 合法段落**：`FORBIDDEN: ...` / 负面提示词段落一律不写；关键防污染需求融进风格开场句：
  `this look applies only to the rendering medium, materials, lighting, and finish, and must never be used to infer or change faces, ages, genders, body proportions, clothing, accessories, props, or environments, which always follow the reference pictures and the on-script descriptions.`
- 自查方法：列出正文声明的全部"必须/一定"元素清单，逐个回正文找镜头归属，找不到即违规。

## 7. 声音组织

- **逐镜均有当前声音，含末镜**（环境/动作/人声），写成镜头句的自然成分或镜头末尾短句；末镜纯画面无声音 = 违规。
- `overall_soundscape` 必须是**内容汇总**（至少点名 2–3 个全片主环境声 + 1 个特征动作声）；禁止"specific effects listed with their shots above / 见上文"这类**指针式空转**写法。
- 台词、歌唱只出现在正文 `<d>` 内；soundscape / music 不重复。
- `N/A` 仅用于：soundscape = 全片完全静音（需用户明确要求）；music = 无画外配乐。

## 8. 参数精度（优秀与平庸的分水岭）

- 色温给数值：晨光/日光 `5600K daylight tint`，室内暖光 `3200K warm tungsten`。
- 机位角度给数值：`tilted about 15 degrees downward` / `looking up at about 25 degrees`。
- 声音给物理质感与时间行为：`A tinnitus-like high-pitched ring stabs in with the voice and slowly decays`，不写"一声巨响"式抽象词。
- 运镜幅度/速度在有意义时显式（`at slow speed` / `with large amplitude`），中等幅度正常速度可省略。

## 9. 视频与音频参考场景（出现 `<Video N>` / `<Audio N>` 时逐条过）

- **`<Video N>` 只用于整片级关系**：剪辑原片、从原片结尾续接、引用整片运镜/切点/节奏结构。从参考视频里复用具体可见内容（人/物/场景/动作）仍归 `<Subject N>`——高频错误：给参考视频里的角色直接用 `<Video N>` 说话。
- **剪辑/续接任务 summary 固定开头句**：`The target video is an edited version of <Video 1>.`；任务前缀判定——直接剪辑=video editing、续接=video continuation、只借运镜/切点/节奏不剪原片仍是 reference generation（素材存在 ≠ 任务类型成立）。
- **音频四标记与画面四标记分开，不得混用**：`fully_copy`（源音频=完整最终音轨）/ `partially_copy`（部分复制，或复制后增删替换）/ `reference`（只引用音色/风格/台词内容/节拍）/ `weak_reference`（只保留类别或氛围）。
- **`<Audio N>` 绑定说话人时复用全局 `(Sx)`**，不得在音频定义里独立分配新编号：`<Audio 1> is the voice-timbre reference for <Subject 1> (S1).`；retention 中不写 `(Sx)`。
- **BGM/音轨里的歌词不是独立声源**：无人 physically 发声的歌词，以 `<Audio N>` 为可闻声源，**不新增 `(Sx)`**——高频翻车：把 BGM 歌词写成某个角色在唱（给纯音乐轨虚构歌手）。示例：`When <Audio 1> reaches the phrase <d>[English] ...</d>, <Subject 1> performs the corresponding gesture without becoming a separate speaker source.`
- **复用音频的台词/歌词逐字保留**在 `<d>` 内；听不清写 `[unclear]`，禁止猜测改写；只引用音色/节奏/情绪时，不得把源音频的台词带入目标视频。
- **音频关系按可听层归属**：环境/音效层 → `overall_soundscape`；仅观众可闻的配乐层 → `non_diegetic_music`；同一音频提供两层内容时在两段中分别声明。
- 音频不能作唯一输入（必须与图像或视频同用）。

## 10. 交付前追加自检清单（在 ref2va-guide 第 7 节之上叠加）

**语言与格式**
- [ ] 正文零中文（`<d>` 内台词/画面文字除外；拼音专名除外）
- [ ] 无 Seedance 字段残留：`Frame:/Camera:/Dialogue:/Sound:/Diegetic sound:` 引导、`(ELS)/(CU)` 景别缩写、`The shot is framed as` 模板句式
- [ ] 画面可见文字在双引号内逐字保留；正文词数 350–500；时长/画幅/分辨率/帧率已外置为生成参数
- [ ] 文字通读通过：无同句重复短语、无 `At 00:XX, The` 大写等标点瑕疵

**标签与 retention**
- [ ] **标签双向绑定**：正文出现的标签均已定义；每个已定义 Subject 在正文出现次数 > 0（数次数，0 即断链）
- [ ] 规划类/帧锚点类参考单独立条并在生效处引用
- [ ] 每条 retention 为完整三段式：镜头标注 + 标记词 + 针对性解释（身体部位/POV 算出现；新增动作不算保真损失）
- [ ] 参考图状态 vs 剧本状态矛盾已显式声明（on-script condition）；定义作用域覆盖全部出现形态（无内外景错位）

**台词与说话人**
- [ ] 台词四件套齐全：`(Sx)` + `off-screen voiceover`（如画外）+ `<d>[Language]</d>` + 闭嘴声明（如画外）
- [ ] 不发声角色无编号；跨镜头同 ID；跨切点台词有 `<scenetrans>` 与延续声明；截断有 `<cutoff>`

**结构与内容**
- [ ] summary 三要素齐备（主体+镜头流程+声音事件），非标签罗列
- [ ] 无幽灵元素（声明的"必须出现"都能在正文找到镜头）；无 FORBIDDEN/负面清单段落
- [ ] 固定机位镜头内无切镜描述；视线匹配已拆为两镜
- [ ] 逐镜（含末镜）均有当前声音；soundscape 是内容汇总而非指针，`N/A` 使用正确
- [ ] 色温/角度/声音有数值或物理质感；单镜 > 5 秒有内部动作递进
- [ ] 节拍已对照 Seedance 原稿核对（不新增、不删减，存疑项已标注）
- [ ] 输入限制核对：图像 ≤9、视频 ≤3（每段 2–15 秒、总 ≤15 秒）、音频 ≤3（不作唯一输入）、文件总数 ≤12

**视频/音频任务（出现 `<Video N>`/`<Audio N>` 时加查）**
- [ ] 剪辑/续接 summary 用固定开头句；`<Video N>` 未被误用于可见内容；任务前缀判定正确
- [ ] 音频四标记正确且未与画面标记混用；BGM 歌词未误设说话人；复用台词逐字保留、`[unclear]` 处理听不清片段

## 11. 使用方式

- **生成时**：完成 ref2va-guide 五步流程后，用本规范第 1–8 节逐节过稿（涉及 `<Video N>`/`<Audio N>` 时加过第 9 节），再跑第 10 节清单。
- **评审时**：对既有提示词按第 10 节清单逐项打勾，不合规项按各节正反对照给出修正句。
- **修订必回归**：每次修改提示词后，重跑第 10 节**全部**清单项，不只查改动点。实战教训：修复常在下一轮改稿中回退（如第三稿丢失了第一轮已修复的标签引用、状态声明与镜头标注），只验改动处必然漏掉回归；本规范自身修订时同理，删除/合并条目前先比对，防止规则静默丢失。
- **冲突裁决**：本规范与用户显式要求冲突时，以用户要求为准并在交付说明中标注偏离项。
