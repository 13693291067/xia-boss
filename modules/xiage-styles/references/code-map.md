# 原项目代码地图 — 虾格（视觉风格模板管理）

> 文件级代码地图：原路径 → 职责 → 关键实现要点。克隆模式按此搬运；从零模式按此对照。
> 项目根：`C:/Users/123/Desktop/AI学习资料/dramaclaw`（用户本机克隆）

---

## A. 后端 API — `src/novelvideo/api/routes/styles.py`（440 行）

| 端点 | 方法 | 职责 | 关键实现 |
|---|---|---|---|
| `/styles` | GET | 全部风格列表（预设+自定义合并） | `list_styles` |
| `/styles/{style_id}` | GET | 单风格详情 | `get_style` |
| `/styles/{style_id}/preview` | GET | 风格预览图 | `get_style_preview`（FileResponse） |
| `/styles` | POST | 创建自定义风格 | `create_style` |
| `/styles/{style_id}` | DELETE | 删除风格 | `delete_style`（清理预览） |
| `/styles/{style_id}/preview` | POST | 更新风格预览图 | `preview_style` |
| `/projects/{project}/styles/analyze` | POST | **核心：参考图分析提取风格** | `analyze_style`（见 B1） |
| `/projects/{project}/styles/preview-upload` | POST | 上传风格预览图 | `upload_style_preview` |

### B1. analyze_style 完整流程（还原基准）
1. 权限 editor；读取 file bytes（空 → `No file uploaded`）
2. 指定 style_id → `StyleService.stage_style_preview` 暂存预览图（extension 取文件后缀或 .png）
3. **计费预留**：`reserve_feature_start_credits`（feature_key=`mainline.style_analysis`，resource_kind="script"，task_type=`style_analysis`，require_price_rule + require_positive_cost）
4. `StyleAnalyzer().analyze(content, mime_type)` → StyleAnalysisResult
5. 异常 → settle_cancelled 计费 + 返回 `Style analysis failed: {e}`
6. 成功 → settle confirm 计费；返回 data（+ preview_token）

---

## B. 核心分析器 — `src/novelvideo/generators/style_analyzer.py`（144 行）

### B1. 输出结构（StyleAnalysisResult，还原基准）
```python
class StyleAnalysisResult(BaseModel):
    style_instructions: str   # 正向提示词：渲染技法/配色/布光/质感/镜头感/氛围，"Create..." 开头，≤100 词
    avoid_instructions: str   # 负向提示词："FORBIDDEN:" 前缀，≤60 词
    style_tag: str            # 2-4 词大写标签：仅介质+成色
    suggested_name: str       # 英文风格名
    suggested_label: str      # 中文显示名
```

### B2. ANALYSIS_PROMPT（原文，还原时逐字保留）
```
You are a visual style analyst for an AI image generation system.

Analyze this image's visual style and generate two sets of prompts for reproducing this style:

1. **style_instructions**: A detailed positive prompt describing how to recreate this visual style.
   Include: rendering technique, color palette, lighting setup, texture quality, camera/lens feel,
   atmosphere/mood. Write as action instructions starting with "Create...".
   Keep it under 100 words — specific enough to anchor the style, concise enough to avoid context dilution.

2. **avoid_instructions**: A negative prompt listing what to FORBID to protect this style.
   Use "FORBIDDEN:" prefix. List conflicting styles, unwanted artifacts, and quality issues.
   Keep it under 60 words.

3. **style_tag**: A short 2-4 word uppercase tag injected near EVERY generated panel.
   Describe ONLY the medium and the grade/finish (lens feel, color grade, rendering quality).
   It must NOT carry era, period, location, wardrobe, ethnicity, or any story content — those
   come from the beat/scene/character/prop, and a per-panel tag would silently override them.
   FORBIDDEN words: PERIOD, REPUBLICAN, ERA, DYNASTY, MODERN, ANCIENT, DRAMA, 古装, 民国.
   Good examples: "CINEMATIC FILMIC REALISM", "NATURAL PHOTOREALISTIC, CLEAN GRADE", "3D GUOMAN FANTASY".

4. **suggested_name**: A concise English name for this style (e.g. "Watercolor Fantasy").

5. **suggested_label**: A Chinese display label (e.g. "水彩幻想风").

Return ONLY valid JSON with no markdown formatting:
{
  "style_instructions": "...",
  "avoid_instructions": "...",
  "style_tag": "...",
  "suggested_name": "...",
  "suggested_label": "..."
}
```

### B3. 模型与图片预处理
- 模型：默认 `gemini-3.5-flash`（`STYLE_ANALYZER_MODEL` 环境变量可覆盖）；pydantic_ai Agent + structured output
- 压缩：最长边 >1024 → thumbnail(LANCZOS)；RGBA/P → RGB；JPEG quality=60 optimize=True
- 上传：`upload_image_bytes`（media relay）→ ImageUrl 传给 LLM

---

## C. 风格服务 — `src/novelvideo/services/style_service.py`（500+ 行）

| 方法 | 职责 |
|---|---|
| `get_preset(style_id)` | 读预设 JSON（PRESETS_DIR = styles/presets；_preset_cache 缓存；is_preset=True） |
| `get_custom_style` / `save_custom_style` / `delete_custom_style` / `list_custom_styles` | 自定义风格 CRUD（存项目配置映射） |
| `get_style` / `get_style_or_default` | 风格查询 + 默认回退 |
| `list_preset_styles` / `list_all_styles` | 预设列表 / 全量合并列表 |
| `get_style_family` / `get_animation_subtype` / `get_style_branch` | 风格家族分类（动画/写实等） |
| `is_animation_style` / `is_live_action_style` | 风格类型判定 |
| `format_style_family_label` | 家族显示名 |
| `stage_style_preview` / `finalize_style_preview` / `find_style_preview` / `remove_style_previews` | 预览图生命周期（按 style_id 分目录） |
| `validate_style_preview_path` | 预览路径安全校验 |
| `load_project_custom_style_map` / `save_project_custom_style_map` | 项目自定义风格映射持久化 |

---

## D. 预设清单 — `src/novelvideo/styles/presets/`

| 文件 | 风格 | 用途 |
|---|---|---|
| `anime.json` + `.png` | 日漫 | 二次元 |
| `chinese_period_drama.json` + `.png` | 古装 | 中文古装剧 |
| `guoman_fantasy.json` + `.png` | 国漫幻想 | 玄幻仙侠 |
| `post_apocalyptic.json` + `.png` | 废土 | 末世 |
| `realistic.json` + `.png` | 写实 | 现实向 |
| `republican_era_drama.json` + `.png` | 民国 | 民国剧 |

---

## E. 前端 — `frontend/src/routes/_app/projects.$project/styles.tsx`（1140 行）

### 页面结构
- 预设风格网格（每个带预览图）
- 自定义风格区（创建/编辑/删除/预览）
- **参考图上传 + 分析**：上传 → 显示 5 字段分析结果 → 确认保存
- 预览管理：生成/上传/替换预览图

### 关键联动
- `useStyles(project)`：虾料设置层 visual_style 下拉直接使用虾格风格列表
- 风格应用：草图/首帧/视频生成引用项目 visual_style

---

## F. 数据契约

### 风格 JSON 结构（presets/*.json）
```json
{
  "id": "guoman_fantasy",
  "label": "国漫幻想",
  "name": "Guoman Fantasy",
  "style_instructions": "Create...",
  "avoid_instructions": "FORBIDDEN: ...",
  "style_tag": "3D GUOMAN FANTASY",
  "is_preset": true
}
```

### 分析响应（analyze_style）
```json
{
  "ok": true,
  "data": {
    "style_instructions": "Create...",
    "avoid_instructions": "FORBIDDEN: ...",
    "style_tag": "CINEMATIC FILMIC REALISM",
    "suggested_name": "Cinematic Filmic Realism",
    "suggested_label": "电影写实风",
    "preview_token": "..."  // 仅指定 style_id 时
  }
}
```

### 项目配置键
`visual_style`（风格 id 引用）+ 自定义风格映射（`load/save_project_custom_style_map`）

### 前置依赖
- LLM 模型（默认 gemini-3.5-flash，走 NewAPI 网关）
- 计费：mainline.style_analysis feature credit 闭环
