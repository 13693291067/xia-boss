# 原项目代码地图 — 虾导（对话式 AI 导演助理）

> 文件级代码地图：原路径 → 职责 → 关键实现要点。克隆模式按此搬运；从零模式按此对照。
> 项目根：`C:/Users/123/Desktop/AI学习资料/dramaclaw`（用户本机克隆）

---

## A. 前端（frontend/src/features/superchat/）

| 文件 | 行数 | 职责 | 关键实现要点 |
|---|---|---|---|
| `superchat-panel.tsx` | 131KB | 主对话面板 | 结构化UI渲染（spec-extract）、附件上传、语音Mic、消息操作（复制/下载/搜索/置顶）、等待状态、任务通知 |
| `use-superchat.ts` | 38KB | 对话交互核心 | WebSocket 连接（/api/v1/chat/ws）、消息缓存（localStorage 7天/50条）、断点恢复（active-turn 1h TTL）、上传目标设置（openclaw/local）、隐藏工具静默执行（freezone_emit_canvas_command） |
| `spec-extract.ts` | 19KB | 结构化UI提取 | extractStructuredBlocks / isUiSpec / UiSpec 类型；从助手回复文本提取可渲染组件 |
| `ai-avatar.ts` | 3.6KB | AI 头像 | 助手头像 URL |
| `composer-waiting-status.tsx` | 6.5KB | 等待状态 | 提交中/思考中提示 |
| `task-notification-label.ts` | 4.3KB | 任务通知 | buildChatTaskLabel 任务标签 |
| `timeline-scroll.ts` | 0.6KB | 时间线滚动 | calculateTimelineContextDelta |
| `types.ts` | 2.8KB | 类型定义 | ClientFrame/ServerFrame/ChatScope/ChatMessage/ApprovalRequest/SuperChatSettings |

### 帧协议（types.ts，还原基准）
```typescript
ClientFrame = { type:"chat.message", scope?, text, turn_id?, attachments? } | { type:"scope.set", scope }
ServerFrame = scope.changed | chat.busy | chat.ping | thread.started | assistant.delta | assistant.message | tool.result | tool.call | chat.done | project.created | error
ChatScope = { kind:"home"|"project"|"asset"|"task", id? }
```

### 路由
- `frontend/src/routes/_app/projects.$project/assistant.tsx` → `<SuperChatPanel />`（**虾集子页入口**）
- `frontend/src/features/freezone/` 虾画右侧面板复用同一 `SuperChatPanel`（**虾画入口**，产品手册第十章：虾导"也可在虾画右侧面板中使用"）
- 产品面：`assistant` 与 `freezone_assistant` 两个入口，默认未开放，需配置启用

---

## B. 后端（src/novelvideo/chat/ + api/routes/chat.py）

### B1. `api/routes/chat.py`（845 行）
| 端点 | 方法 | 职责 |
|---|---|---|
| `/api/v1/chat/cancel` | POST | 中断当前回合（close_user + force_release_chat_run_lock） |
| `/api/v1/chat/notifications` | POST | 通知上报 |
| `/api/v1/chat/ui-events` | POST | UI 事件上报 |
| `/api/v1/chat/ws` | WebSocket | 主对话通道（类型化 JSON 事件；前端不感知后端是 Hermes/Claude/Codex） |

### B2. `chat/service.py`（139KB，核心）
关键函数：
- `_acquire_chat_run_lock` / `_heartbeat_chat_run_lock` / `_release_chat_run_lock`：**每项目一把 run lock** + 心跳保活 + 过期回收（防并发）
- `stream_assistant_reply`：主入口——拿锁→心跳→确定性回复 or 三后端分流→finally 释放锁
- `_frontend_context_reply`：前端上下文场景直接返回（不调模型）
- `_script_creation_model_reply_prompt`：剧本创建场景的模型提示词
- `_stream_assistant_reply_hermes` / `_claude` / `_codex`：三后端流式实现
- `list_messages` / `add_user_message` / `add_assistant_message` / `add_trace_message(s)`：SQLite 消息存取
- `_sync_project_skills`：`.hermes/skills` → agent 工作区同步
- `_extract_media` / `_normalize_media_items` / `_filter_markdown_duplicate_images`：回复媒体提取与规范化
- `_strip_media_rendering_leaks` / `_redact_local_filesystem_paths`：防泄漏（不暴露本地路径）
- `_ui_spec_json` / `_wrap_ui_spec_bundle` / `_merge_tool_ui_specs_by_type`：UI spec 打包/合并/去重
- `_extract_display_tool_call` / `_infer_display_tool_call_from_text`：工具调用展示提取
- `generate_assistant_reply`：同步回复接口（非流式）
- 技能/工作区：`ensure_user_claude_workspace` / `ensure_user_codex_workspace` / `_build_claude_env` / `_build_codex_env` / `_dramaclaw_mcp_servers`

### B3. `chat/backend_sdk.py`（50KB）
- `ClaudeSdkClient` / `ClaudeSdkThread`：Claude SDK 流式解析（assistant.delta/tool 追踪/session）
- `ClaudeCliClient` / `ClaudeCliThread`：Claude CLI 模式
- `CodexClient` / `CodexThread`：Codex 线程（plan trace/guardian review/diff 着色）
- 中断：`register_live_codex_turn` / `interrupt_live_claude_client` 等

### B4. `chat/hermes_pool.py`（19KB）
- `HermesPool`：Hermes worker 槽位池（_WorkerSlot 按用户隔离）
- `close_user(username)`：取消用户活跃回合

### B5. `chat/hermes_workspace.py`（24KB）
- 虾导身份注入：自称"虾导"，不暴露 Hermes/底层框架
- 记忆/技能/角色配置注入 agent 工作区

### B6. `chat/hermes_sdk.py`（26KB）
- Hermes 会话 SDK（流式/工具/中断）

### B7. `chat/store.py`（12KB）
- ChatScope 存储：home（用户级）/project（项目级）/asset/task 的聊天历史 DB 管理

### B8. `chat/dramaclaw_mcp.py`（3.4KB）
- stdio MCP server：加载 `.hermes/plugins/dramaclaw/__init__.py` 的 TOOLS
- Hermes 直接用插件；Claude/Codex 走此 stdio 桥

---

## C. 34 个工具全清单（.hermes/plugins/dramaclaw/__init__.py）

| 分组 | 工具 |
|---|---|
| 进度/任务 | `dramaclaw_pipeline_status` `dramaclaw_list_tasks` `dramaclaw_get_task` |
| 前期规划 | `dramaclaw_plan_episodes` `dramaclaw_plan_identities` `dramaclaw_plan_scenes` `dramaclaw_plan_props` `dramaclaw_generate_script` |
| 角色/资产 | `dramaclaw_build_characters` `dramaclaw_update_character_face_prompt` `dramaclaw_generate_portrait` `dramaclaw_generate_identity_image` `dramaclaw_get_character_media` |
| 场景 | `dramaclaw_generate_scene_master` `dramaclaw_generate_scene_reverse` `dramaclaw_get_scene_images` |
| 草图/首帧 | `dramaclaw_generate_sketches` `dramaclaw_detect_sketch_identities` `dramaclaw_get_sketches` `dramaclaw_get_sketch_candidates` `dramaclaw_render_first_frames` `dramaclaw_get_first_frames` |
| 音频/视频/合成 | `dramaclaw_generate_audio` `dramaclaw_optimize_video_global` `dramaclaw_start_single_video` `dramaclaw_get_final_video` `dramaclaw_compose_episode` `dramaclaw_get_episode_media` |
| 其它 | `dramaclaw_get_episode_script` `dramaclaw_list_ingest_uploads` `dramaclaw_get` `dramaclaw_post` `dramaclaw_patch` `dramaclaw_delete` |

---

## D. 行为规则（源码内嵌，还原时必须实现）

1. **身份**：自称"虾导"，不附加头衔，不提 Hermes/底层框架
2. **剧本入口限制**：不生成剧本、不一句话建项目 → 引导虾料上传
3. **静默执行**：单步执行过程不叙述，完成后一次性输出
4. **单轮一步**：一次用户消息最多 1 个写操作/异步任务；启动成功即收口
5. **状态驱动**：先读 pipeline/status；有 running 任务告知等待；否则只执行 next_step 一个写任务
6. **笼统大任务先澄清**："完成第N集"类 → 列出小任务+询问，不自动启动
7. **错误即停**：任一写工具失败 → 停止所有后续调用，转述 error，不重试不猜路径
8. **覆盖二次确认**：重新摄入/覆盖 → 两次确认
9. **音频字段顺序**：先更新 beat → 重做音频 → 重新合成
10. **grounding**：只确认实际成功的字段
11. **媒体纪律**：展示工具 + *_url 原样透传；禁本地路径/禁拼host/禁手写markdown图片
12. **工具约束**：禁 bash/curl；摄入只有 /ingest/upload + /ingest/start

---

## E. 数据契约

### 消息（ChatMessage）
```json
{ "id":"...", "role":"user|assistant|system|tool", "text":"...", "turnId":"...", "displayName":"...", "attachments":[...], "timestamp": 0, "raw": {} }
```

### 附件（ChatAttachment）
```json
{ "id":"...", "type":"...", "kind":"...", "mimeType":"...", "fileName":"...", "fileSize":0, "content":"(base64)", "url":"...", "path":"...", "label":"..." }
```

### UI spec（结构化渲染）
助手回复中嵌入的 UI spec JSON（spec-extract 提取）→ 渲染成媒体卡片/列表/表格/视频预览

### 环境依赖
- `DRAMACLAW_API_URL` / `DRAMACLAW_AGENT_TOKEN` / `DRAMACLAW_PROJECT_ID`（MCP 配置注入）
- 三后端任选：Hermes（默认）/ Claude(SDK|CLI) / Codex
