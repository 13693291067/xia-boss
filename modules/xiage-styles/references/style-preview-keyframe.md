# 虾格 · 展示风格图提示词生成规范（关键场景式，★ v3.4.0-风格库）

> 性质：通用方法论，示例一律占位符，禁止写入任何具体项目数据。
> 定位：给**风格挂载库**（`styles-library/`）里每个风格生成一张**展示风格图**的提示词——即虾格 Tab 卡片上那张"人物近景含环境"的样板图。用**关键场景式**（有人物、有代表环境、示范该风格视觉基因）出。
> 触发词：展示风格图、风格预览图、库卡片图、关键场景式提示词、导出风格、写回挂载库。

## 〇 三种"风格图"别混（先分清 scope）

| 图 | 级别 | 用途 | 是否含人 | 正本规范 |
|---|---|---|---|---|
| **展示风格图**（本文件） | 每风格级 | 挂载库 Tab 卡片预览、导出包配图 | **含人**（关键场景式） | 本文件 |
| **定风格图** style_reference_frame | 每剧级 | 全剧美术圣经锚 | 含人（本剧主角） | `style-keyframe-prompt.md` |
| **场景资产图** | 每场景级 | 下游分镜垫图 | **禁人**（空镜） | 虾塘 `scene-assets.md` |

本文件与 `style-keyframe-prompt.md` **同一套组装逻辑**，差别只在取材：定风格图读**本剧** docs 主角卡/世界观；展示图读**风格条目**的 `keyframe{}`（通用、无剧名主角）。

## 一、输入（读挂载条目字段）

- `family` → 取 `render-medium-library.md` 对应族的 STYLE_HEAD / 主图介质锚 / body 强标记 / 负向边界。
- `keyframe.figure` → 代表人物（该风格标志性主体）。
- `keyframe.environment` → 代表环境（该风格标志场景，含广度+纵深+尺度）。
- `keyframe.color_relationship` → 主体与环境色彩关系。
- `visual_references[].infusion` → 视觉参考注入段。
- `avoid_instructions` → 负向基线。

## 二、组装公式（正向顺序拼接）

```
[① 族 STYLE_HEAD 整句（族B 必含真人皮肤锚；族A/C 含 body 强风格化锚）]
+ [② 代表人物：keyframe.figure（脸/发式/服化道/妆容；写实族带真皮肤锚）]
+ [③ 代表环境：keyframe.environment（外景/世界感优先，广度+纵深+天气+尺度参照）]
+ [④ 色彩关系：keyframe.color_relationship（主体 vs 环境饱和/明度对比）]
+ [⑤ 光影氛围：暖金逆光/体积雾/时段等]
+ [⑥ visual_references.infusion]
+ [⑦ FORBIDDEN：族负向 + 展示图专属（禁剪影无脸 / 前景糊满抢主体 / 风格化项目禁 glossy plastic CGI）]
+ [⑧ 构图：人物清晰可辨非剪影、环境有广度、默认 16:9]
```

## 三、三条强制检查（★ 事故固化，逐条过）

1. **写实族真人皮肤锚**（族B）：正向必须含 `real photographed / visible pores / subtle uneven skin tone / no beauty retouching / not a plastic idol face / slightly asymmetric bone structure`；**禁** `porcelain/瓷白/flawless/airbrushed/glass skin`（否则出磨皮网红脸）。详见 `render-medium-library.md` 族B + 跨族通则。
2. **主体/环境色彩反差**：当参考是"主体艳色 + 背景素净"（如敦煌飞天 vs 土砂洞窟），infusion **必须拆成"主体饱和色"与"环境去饱和色"两段并明写对比**（`vivid figure popping against muted environment`），**禁止把主体色并进 overall tone 把整张染糊**。
3. **巨物尺度**：写巨物用"一点透视无边柱廊 + 极小人影/远塔缩成点 + 超广角仰拍 + 尺寸数字（数百米高/绵延数公里）"；**含人影=关键场景（本图允许），纯场景资产不得放人**。

## 四、写回挂载库（每剧虾格定稿后）

1. 定风格图（`style_reference_frame`）完成后，按本公式生成该风格的 `preview_prompt`（关键场景式）。
2. **剥离项目数据**：`keyframe.figure/environment` 用通用描述（"宋代仕女"而非某剧主角名），剔除剧名/角色/专有世界观词；`grep` 命中即脱敏。
3. 组装成 `styles-library/README.md` 的条目 schema，写回**用户级库** `~/.qwenworkcn/xiage-style-library/<style_id>.json`（个人复用）。
4. 要提升进 skill 种子层 / 换机 / 分享 → 用虾格页「📤 导出风格包」（`/api/export-style`）下 zip，解压丢进 `modules/xiage-styles/styles-library/`。

## 五、验收清单

- [ ] 族 STYLE_HEAD 正确（族B 带真人皮肤锚 / 族A·C 带 body 强标记）；
- [ ] 人物清晰可辨、非剪影；环境有广度非单室；
- [ ] 色彩关系按通则③写清（艳主体/素背景要拆两段，巨物要有人影或尺寸锚）；
- [ ] 正向英文纯净、负向 FORBIDDEN、`style_tag` 不进 prompt、16:9；
- [ ] 条目已剥离项目数据（grep 零剧名/角色/专有世界观）；
- [ ] 写回用户级库或导出包 schema 完整（含 preview_prompt + keyframe + preview_image）。
