# 虾格 · 风格挂载库（styles-library，★ v3.4.0-风格库 新增）

> 用途：把"已验证的风格"以**文件挂载**的形式沉淀成可复用库。加一个风格 = 往本目录丢一个 `<style_id>.json`（+ 同名预览 png），**零改 SKILL.md / 零改 build-data-js 逻辑**。
> 触发词：风格挂载库、风格库、已验证风格、导出风格、加载风格、styles-library。

## 一、双层库结构（v3.4.0-风格库 拍板）

| 层 | 位置 | 内容 | 谁写 |
|---|---|---|---|
| **种子层（skill 内）** | `modules/xiage-styles/styles-library/` | 通用、可复用、**无项目数据**的风格（如 宋式美学/云景仙宫/敦煌神话） | 人工经"导出→解压放入"提升 |
| **用户层（skill 外）** | `~/.qwenworkcn/xiage-style-library/` | 每剧虾格定稿后自动写回的风格（个人跨项目复用） | 虾格 §0.2.6 写回步骤 |

`build-data-js.py` 的 `load_style_library()` **合并两层**（style_id 冲突时用户层覆盖种子层）→ 输出独立字段 `xiage.style_library`（与项目在用风格 `xiage.styles` 分开，**不灌 `outputs/styles/`、不动当前风格权威链**）。

## 二、条目 schema（`<style_id>.json`，自包含）

```json
{
  "style_id": "real_song",
  "style_label": "写实电影·宋式美学",
  "family": "B",                         // 关联 render-medium-library 族 A/B/C（复用 STYLE_HEAD/锚/禁则）
  "style_tag": "CINEMATIC FILMIC REALISM",
  "style_instructions": "<族 STYLE_HEAD 整句>",
  "avoid_instructions": "FORBIDDEN: ...",
  "visual_references": [{"name","note","infusion"}],
  "tonal_direction": "...",
  "keyframe": {"figure","environment","color_relationship"},   // 喂"展示图=关键场景"生成逻辑
  "preview_prompt": "<关键场景式展示图提示词（见 style-preview-keyframe.md）>",
  "preview_image": "<style_id>.png",
  "is_library_entry": true,
  "tier": "skill | user",
  "source": "参考图验证 YYYY-MM-DD",
  "confirmed_by_user": true
}
```

- 预览图放同名 `<style_id>.png`（与 json 并列）。
- 展示图提示词的生成逻辑见 `references/style-preview-keyframe.md`。

## 三、写回与导出（★ 禁项目数据最高纪律不破）

- **自动写回（用户层）**：每剧虾格定稿后，按 `style-preview-keyframe.md` 生成 `preview_prompt` → **剥离项目数据**（剧名/角色名/专有世界观词一律不进 keyframe/figure/infusion，用通用描述）→ 追加 `~/.qwenworkcn/xiage-style-library/<style_id>.json`。
- **手动导出（提升进种子层）**：虾格页「📤 导出风格包」→ `POST /api/export-style` 打 **zip**（含 `<id>.json` + 预览 png + 定风格图 png），**导出前脱敏校验**（命中项目专有词即提示）→ 用户解压丢进本 `styles-library/` 即被 `load_style_library()` 读到。
- **红线**：本目录内**禁止任何具体项目数据**。写回/导出都必须先把风格降到"通用风格层"（族+三要素+视觉参考+基调+通用 keyframe），主角名/剧名/专有设定不进库。grep 验收：`grep -rn "<旧项目关键词>" styles-library/` 应为空。

## 四、应用一条库风格 = 走正常落地

Tab 里点库条目的「应用」→ 把该 `<id>.json` 拷进项目 `outputs/styles/` + 写 `creation-direction.json`（与"从零生成"的落地路径一致）→ 下游虾塘/虾镜正常消费。库只是**候选源**，用户逐项拍板才应用（防趋同靠"用户选择"，不靠"禁止复用"）。
