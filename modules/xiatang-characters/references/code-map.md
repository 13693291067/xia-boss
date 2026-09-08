# 原项目代码地图 — 虾塘（角色/场景/道具资产）

> 文件级代码地图：原路径 → 职责 → 关键实现要点。克隆模式按此搬运；从零模式按此对照。
> 项目根：`C:/Users/123/Desktop/AI学习资料/dramaclaw`（用户本机克隆）

---

## A. 前端

### A1. 主页面 — `frontend/src/routes/_app/projects.$project/characters.lazy.tsx`（3381 行）
| 行段 | 内容 | 关键实现要点 |
|---|---|---|
| 1-120 | imports | useCharacters / useCreateCharacter / useGeneratePortraitAsync / useGenerateIdentityImageAsync / useCharacterIdentities / useCharacterVoicePanel 等 20+ hooks |
| 160-210 | 常量 | CHARACTER_PORTRAIT_FEATURE_KEY=`mainline.character_portrait`、IDENTITY_IMAGE_FEATURE_KEY=`mainline.identity_image` |
| 500-650 | 角色卡片 | 显示 portrait_url（resolveMediaUrl）；CharacterImageSourceSelect 图源选择；SlidingTabs 切换 |
| 920-990 | 肖像生成 | useTaskController 跟踪异步任务（scope=`character:{name}:portrait`）；计费 useGenerationCreditCost |
| 其余 | 身份面板/声线面板/编辑弹窗 | 集成 CharacterVoicePanel、NarratorVoicePanel、CharacterStatsStrip |

### A2. 组件 — `frontend/src/components/assets/`
| 文件 | 职责 |
|---|---|
| `character-search.tsx` | 角色搜索 + filterCharacters 过滤 |
| `character-image-source-select.tsx` | 图源选择（AI 生成/手动上传） |
| `character-stats-strip.tsx` | 角色统计条（角色数/主角/有声线数等） |
| `character-voice-panel.tsx` | **角色声线面板**（上传/录制/裁剪） |
| `narrator-voice-panel.tsx` | **解说声线面板**（narrated 旁白） |
| `scenes-panel.tsx` | 场景面板（场景卡片列表） |
| `scene-asset-card.tsx` | 场景资产卡（master/reverse/pano/custom） |
| `scene-environment-prompt.tsx` | 场景环境提示词编辑 |
| `props-panel.tsx` | 道具面板 |
| `prop-asset-card.tsx` | 道具资产卡 |
| `usage-count-badge.tsx` | 使用次数徽章 |
| `asset-beat-references.tsx` | 资产在 beat 中的引用 |
| `copy-asset-link-button.tsx` / `project-style-chip.tsx` / `asset-search-box.tsx` | 辅助组件 |

### A3. API 封装 — `frontend/src/lib/queries/`
- `characters.ts`：useCharacters / useCreateCharacter / useUpdateCharacter / useDeleteCharacter / useGeneratePortraitAsync / useGenerateIdentityImageAsync / useCharacterIdentities / useCreateIdentity / useUpdateIdentity / useDeleteIdentity / useUploadCostumeImage / useUploadIdentityImage / useUploadIdentityPortrait / useUploadPortrait / useIdentityAttempts / useBuildCharacters / useCharacterAssetHistory / useRestoreCharacterAsset / useIdentityOwnerIndex
- `character-image-selection.ts`：useCharacterImageSelection

---

## B. 后端 API

### B1. 角色 — `src/novelvideo/api/routes/characters.py`（2068 行）
| 端点 | 方法 | 职责 |
|---|---|---|
| `/projects/{project}/characters` | GET | 角色列表（含肖像/声线/资产链接；启动修复重复主角） |
| `/projects/{project}/characters` | POST | 手动添加（重名拦截；is_main unset 其他） |
| `/projects/{project}/characters/build` | POST | 图谱补充缺失角色（build_characters 任务） |
| `/projects/{project}/character-image-selection` | GET/PATCH | 项目级图源选择 |
| `/projects/{project}/image-source-selection/{asset_kind}` | GET/PATCH | 资产级图源选择 |
| `/projects/{project}/characters/{name}/identities` | GET | 身份列表 |
| `/projects/{project}/characters/{name}/asset-history` | GET | 资产历史 |
| `/projects/{project}/characters/{name}/asset-history/restore` | POST | 历史回滚 |
| `/projects/{project}/characters/{name}` | PATCH | 角色编辑 |
| `/projects/{project}/characters/{name}/delete` | POST | 角色删除 |
| `/projects/{project}/characters/{name}/voice-samples` | GET | 声线样本列表 |
| `/projects/{project}/characters/{name}/voice-samples/{slot}/upload` | POST | 声线上传 |
| `/projects/{project}/characters/{name}/voice-samples/{slot}/record` | POST | 声线录制 |
| `/projects/{project}/characters/{name}/voice-samples/{slot}/trim` | POST | 声线裁剪 |
| `/projects/{project}/characters/{name}/voice-samples/{slot}/delete` | POST | 声线删除 |
| `/projects/{project}/characters/{name}/identities` | POST | 创建身份 |
| `/projects/{project}/characters/{name}/identities/{identity_id}` | PATCH/DELETE | 编辑/删除身份 |
| `/projects/{project}/characters/{name}/portrait-async` | POST | 肖像异步生成（character_portrait 任务） |
| `/projects/{project}/characters/{name}/portrait` | POST | 肖像同步生成 |
| `/projects/{project}/characters/{name}/portrait/upload` | POST | 肖像上传 |
| `/projects/{project}/characters/{name}/identities/{identity_id}/upload` | POST | 身份图上传 |
| `/projects/{project}/characters/{name}/identities/{identity_name}/upload` | POST | 服装图上传 |
| `/projects/{project}/characters/{name}/identities/{identity_id}/attempts` | GET | 生成尝试记录 |
| `/projects/{project}/characters/{name}/identities/{identity_id}/generate` | POST | 身份图生成 |

关键实现：
- `_resolve_character_project`：权限 + store 装配
- `_repair_duplicate_main_characters`：主角唯一性修复（启动时）
- `_unset_other_main_characters`：设主角时 unset 其他
- `_resolve_character_image_model`：生成模型解析
- `_character_image_billing_metadata`：按模型计费元数据
- `_backup_character_asset` / `_character_asset_history_entries`：资产备份与历史
- `_voice_slot_metadata` / `_voice_samples_payload`：声线槽位结构

### B2. 场景 — `src/novelvideo/api/routes/scenes.py`（1551 行）
| 端点 | 方法 | 职责 |
|---|---|---|
| `/projects/{project}/scenes` | GET | 场景列表（含 base_scene_id 派生 + 变体） |
| `/projects/{project}/scenes/plate-preview` | GET | 场景板预览 |
| `/projects/{project}/scenes/{name}/pano/manifest` | GET | 全景清单 |
| `/projects/{project}/scenes/{name}/pano/correction` | PATCH | 全景修正 |
| `/projects/{project}/scenes/{name}/director-stage/manifest` | GET | 导演舞台清单 |
| `/projects/{project}/scenes/{name}/director-stage/world` | POST | 建世界模型 |
| `/projects/{project}/scenes/{name}/director-stage/world/source` | POST | 世界源 |
| `/projects/{project}/scenes/{name}/director-stage/world/clear` | POST | 清世界 |
| `/projects/{project}/scenes` | POST | 创建场景 |
| `/projects/{project}/scenes/{name}` | PATCH | 编辑场景（含变体编辑） |
| `/projects/{project}/scenes/{name}/delete` | POST | 删除场景 |
| `/projects/{project}/scenes/build` | POST | 图谱自动提取（build_scenes） |
| `/projects/{project}/scenes/{name}/master/upload` | POST | master 图上传 |
| `/projects/{project}/scenes/{name}/master/delete` | POST | master 图删除 |
| `/projects/{project}/scenes/{name}/master/generate-async` | POST | master 图生成 |
| `/projects/{project}/scenes/{name}/reverse/generate-async` | POST | reverse 图生成 |
| `/projects/{project}/scenes/{name}/pano/upload` | POST | 全景上传 |
| `/projects/{project}/scenes/{name}/pano/delete` | POST | 全景删除 |
| `/projects/{project}/scenes/{name}/custom/upload` | POST | 自定义图上传 |
| `/projects/{project}/scenes/{name}/custom/delete` | POST | 自定义图删除 |
| `/projects/{project}/scenes/{name}/3gs/master-ply/generate-async` | POST | 3GS 主点云 |
| `/projects/{project}/scenes/{name}/3gs/reverse-ply/generate-async` | POST | 3GS 反向点云 |
| `/projects/{project}/scenes/{name}/3gs/pano-ply/generate-async` | POST | 3GS 全景点云 |
| `/projects/{project}/scenes/{name}/pano/generate-async` | POST | 全景生成 |

**场景变体（手册 7.1）/ 导演世界（手册 7.2）/ 3GS（手册 7.3）**：场景资产支持多视觉变体（导演世界的基础）；导演舞台 world + 3GS ply 点云用于自由视角探索与渲染图（7.3.3）。**还原时场景域必须含"变体 + 导演世界"能力，不能只做四视图上传。**

### B3. 道具 — `src/novelvideo/api/routes/props.py`（332 行）
| 端点 | 方法 | 职责 |
|---|---|---|
| `/projects/{project}/props?scope=global\|local\|all` | GET | 道具列表（global 全局 + local 单集） |
| `/projects/{project}/props` | POST | 创建道具 |
| `/projects/{project}/props/{name}` | PATCH | 编辑道具 |
| `/projects/{project}/props/{name}/delete` | POST | 删除道具 |
| `/projects/{project}/props/{name}/reference/generate-async` | POST | 参考图生成 |

关键：`_local_episode_prop_payloads` 读取单集局部道具；scope 过滤逻辑。

---

## C. 任务执行器

### C1. `src/novelvideo/task_backend/runners/graph_build.py`
- `run_build_characters` → `_run_build_characters`：从知识图谱提取角色补充入库
- `run_build_scenes` → `_run_build_scenes`：从图谱提取场景
- `run_build_props` → `_run_build_props`：从图谱提取道具
- `run_build_episodes` → `_run_build_episodes`：分集（虾镜用）
- 注册：`register_project_task_runner("build_characters"|"build_scenes"|"build_props"|"build_episodes", ...)`

### C2. 角色肖像任务
- task_type：`character_portrait`（scope=`character:{name}:portrait`）
- payload：mode="portrait" / character_name / style / model / scope / output_dir / billing

---

## D. 数据契约

### D1. 角色对象（GET /characters 项）
```json
{
  "name": "角色A", "aliases": [], "description": "", "role": "主角",
  "gender": "女", "age_group": "青年", "body_type": "", "face_prompt": "",
  "is_main": true, "portrait_path": "...", "portrait_url": "/static/projects/{p}/assets/characters/角色A/portrait.png",
  "updated_at": "...", "asset_links": {...}, "voice_fields": {...}
}
```

### D2. 资产目录结构
```
{project_dir}/assets/
  characters/{name}/portrait.png + identities/ + .history/
  scenes/{name}/master.png + reverse.png + pano/ + custom/
  props/{name}/reference.png
```

### D3. 声线槽位
```json
{"voice_samples": {"slot1": {"url": "...", "duration": 3.2, "status": "ready"}}}
```

### D4. 前置依赖链
`虾料摄入 → build_characters 自动提取 → 人工确认/补充 → 肖像/身份图 → 声线 → 虾镜消费`
