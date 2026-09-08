---
name: xiaodao-assistant
description: |
  虾导（对话式 AI 导演助理 / SuperChat）功能 100% 还原专用 skill。基于 DramaClaw（虾导）开源项目源码逐文件提炼，目标是把项目里「虾导」——即虾集主线第四个子页的对话式 AI 导演助理——完整复刻到任何新项目。
  触发词：虾导、AI导演助理、对话助手、SuperChat、聊天面板、对话式制作、查进度、推进任务、下一步建议、dramaclaw_pipeline_status、dramaclaw_plan_episodes、dramaclaw_generate_script、dramaclaw_generate_sketches、dramaclaw_generate_audio、dramaclaw_start_single_video、dramaclaw_compose_episode、ChatScope、MCP桥、hermes、claude、codex。
  适用场景：用户说"把虾导功能做出来/还原出来/复刻一下"、"做一个对话式AI导演助理模块"、"AI对话驱动短剧制作"、"建一个像 DramaClaw 那样的制作助手"、"100%还原虾导"。本 skill 提供：功能全景（前端面板/后端调度/34工具/行为规则四域）、原项目完整代码地图（文件级路径+职责+关键实现）、逐模块实现规格、还原验收清单。
  还原方式：两种模式——①源码克隆模式（原项目在本机，对照 code-map.md 按文件搬运）；②从零重写模式（按规格文档逐模块实现）。两种模式都以"行为等价"为验收标准：同样输入产生同样流式事件、同样状态流转、同样工具调用结果。
agent_created: true
---

# 虾导（对话式 AI 导演助理）功能 100% 还原

> 本 skill 把 DramaClaw（虾导）项目里「虾导」——**对话式 AI 导演助理（SuperChat）**——完整还原到目标项目。
> 覆盖范围：前端对话面板（结构化 UI 渲染/附件/语音/断点恢复）+ 后端调度（三后端/并发锁/存储）+ 34 个 dramaclaw_* 流水线工具 + 12 条行为规则。

## 0.1 权威定位（以产品手册为准）

> **产品手册（第十章）原文："虾导：查询进度、检查缺失、建议下一步，也可在虾画右侧面板中使用。"**
> "让 AI 协助查进度或推进任务"

**→ 虾导有两个官方入口：①虾集主线第四个子页（assistant）；②虾画无限画布右侧面板（freezone_assistant）——自由创作时在虾画里随时唤起虾导。还原时两个入口都要保留。**

---

## 0. 还原目标（一句话）

**虾导是 DramaClaw 的"对话大脑"：用户打字对话，它用 34 个流水线工具查进度、推进脚本/镜头任务、检查交付完整性并给出下一步建议。**

100% 还原 = 行为等价，验收标准：

```
同样的用户消息 → 同样的流式事件序列（assistant.delta/tool.call/tool.result/chat.done）
同样的查询请求 → 同样的工具调用与结果（pipeline_status 等）
同样的作用域 → 同样的历史隔离（home/project/asset/task）
同样的并发请求 → 同样的 run lock 行为（锁/心跳/过期）
同样的边界输入 → 同样的错误与收口（错误即停/单轮一步/覆盖二次确认）
同样的下游 → 34 个工具能正确驱动虾镜/虾塘/虾料流水线
```

---

## 1. 功能全景（四域）

```
┌────────────────────────────────────────────────────────────────┐
│ ① 前端域  SuperChatPanel（结构化UI渲染/附件/语音/缓存断点）      │
│ ② 调度域  WebSocket /chat/ws + /chat/cancel + 三后端 + 并发锁    │
│ ③ 工具域  34 个 dramaclaw_* 工具（进度/规划/资产/草图/音视频）   │
│ ④ 规则域  身份/静默执行/单轮一步/状态驱动/错误即停/媒体纪律      │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. 还原工作流

### 2.1 开工前：选择还原模式

- **源码克隆模式**（原项目在本机，如 `C:/Users/123/Desktop/AI学习资料/dramaclaw`）：
  1. 读 `references/code-map.md` 拿到文件级代码地图
  2. 按地图逐个文件搬运/适配（保留帧协议、事件类型、工具清单、行为规则）
  3. 用 §3 验收清单逐条核对
- **从零重写模式**（无原项目）：
  1. 先实现 34 个工具（DramaClaw API 封装）——这是虾导的"手"
  2. 再实现 WebSocket 通道 + 三后端适配（或等价 LLM 后端）
  3. 再实现前端对话面板（结构化 UI 渲染）
  4. 最后注入行为规则（单轮一步/静默执行/错误即停）
  5. 用 §3 验收清单逐条核对

### 2.2 执行纪律（强制）

1. **单轮一步**：一次用户消息最多启动 1 个写操作/异步任务；启动成功立即收口"已进入队列"。
2. **状态驱动**：任何"继续/做完"请求先读 pipeline/status；有 running 任务→告知等待；否则只执行 next_step 对应的一个写任务。
3. **身份约束**：自称"虾导"，不暴露底层框架（Hermes/供应商）。
4. **剧本入口限制**：不提供生成剧本功能；引导到虾料上传。
5. **错误即停**：任一写工具失败 → 立即停止所有后续调用，转述后端 error，不重试不猜路径。
6. **覆盖二次确认**：重新摄入/覆盖项目 → 两次确认。
7. **grounding**：只确认实际 API 成功返回的字段。
8. **媒体纪律**：媒体必须走展示工具 + API 返回的 *_url；禁本地路径/禁拼 host/禁手写 markdown 图片。
9. **工具约束**：禁 bash/curl；只用 MCP 工具；摄入只有 /ingest/upload 和 /ingest/start。
10. **资产正面统一（工具调用约定）**：调度 generate_portrait / generate_identity_image / 道具参考图等资产类工具时，**输出视角统一正面**（角色定妆=正面面向镜头；身份图=**两图制（定妆照 + 四视图角色卡，2026-08-21 拍板）**；道具=**五宫格（★ 2026-08-21：正面/背面/左侧面/右侧面/材质细节特写，上 2 下 3）**）；提示词内显式写视角词，规范以虾塘 skill「资产输出统一正面」为准。
11. **还原后再交付**：完整实现 + 自测后，输出验收清单核对结果。

---

## 3. 验收清单（100% 还原判定）

### 前端域
- [ ] **两个入口**：虾集子页（assistant）+ 虾画右侧面板（freezone_assistant，手册第十章）
- [ ] WebSocket 流式对话（assistant.delta 打字机效果）
- [ ] 结构化 UI 渲染（spec-extract：媒体卡片/列表/表格/视频预览）
- [ ] 附件上传（local/openclaw 两目标）
- [ ] 语音输入（Mic）、AI 头像、等待状态、任务通知标签
- [ ] 消息本地缓存（7 天/50 条）+ 断点恢复（active-turn）
- [ ] 会话指令（agents/compact/fast/kill/model/steer/think/usage/verbose）

### 调度域
- [ ] `WebSocket /api/v1/chat/ws` 帧协议完整（ClientFrame/ServerFrame）
- [ ] `POST /api/v1/chat/cancel` 中断当前回合
- [ ] ChatScope 四作用域（home/project/asset/task）历史隔离
- [ ] run lock：获取/心跳保活/过期回收/释放
- [ ] SQLite 存储：消息/trace/输入历史
- [ ] 三后端：Hermes / Claude(SDK+CLI) / Codex 自动选择

### 工具域
- [ ] 34 个工具全部可用，名称与 code-map 完全一致
- [ ] 进度类：pipeline_status / list_tasks / get_task
- [ ] 规划类：plan_episodes / plan_identities / plan_scenes / plan_props / generate_script
- [ ] 资产类：build_characters / update_character_face_prompt / generate_portrait / generate_identity_image / get_character_media
- [ ] 场景类：generate_scene_master / generate_scene_reverse / get_scene_images
- [ ] 草图首帧类：generate_sketches / detect_sketch_identities / get_sketches / get_sketch_candidates / render_first_frames / get_first_frames
- [ ] 音视频类：generate_audio / optimize_video_global / start_single_video / get_final_video / compose_episode / get_episode_media
- [ ] 其它：get_episode_script / list_ingest_uploads / get/post/patch/delete

### 规则域
- [ ] 身份回答："我是虾导"（不附加头衔）
- [ ] 剧本创建入口限制（引导虾料上传）
- [ ] 静默执行（单步不叙述，完成一次性输出）
- [ ] 单轮一步（防超时硬规则）
- [ ] 笼统大任务先澄清拆解
- [ ] 错误即停
- [ ] 覆盖二次确认
- [ ] 音频字段更新固定顺序（先beat→重做音频→再合成）
- [ ] 媒体展示纪律（_url 原样透传）

---

## 4. References 索引

| 文件 | 内容 | 何时加载 |
|---|---|---|
| `references/code-map.md` | **原项目完整代码地图**（前端 superchat 6 文件 + 后端 chat 7 文件 + 34 工具全清单 + 行为规则） | 开工必读；逐域实现时对照 |

**不要重复加载已读过的 reference；实现细节不确定时读 code-map.md，不要编造机制。**

---

## 5. 与其它 skill 的关系

- 本 skill 只负责**还原虾导（对话助理）这一个功能模块**。
- 工具集消费虾镜（xiajing-episodes）流水线 + 虾塘（xiatang-characters）资产 + 虾料（xialiao-ingest）摄入数据。
- 身份与工作区：`hermes_workspace.py` 注入"虾导"身份与技能同步（.hermes/skills → agent workspace）。
- 产品面：`assistant`（虾集子页）与 `freezone_assistant`（**虾画右侧面板**）——手册第十章明确虾导"也可在虾画右侧面板中使用"，两入口默认未开放，需配置启用。

---

## 6. 输出交接（Handoff）★ 完成本 skill 后必做

**虾导是"对话大脑"，它的交接物不是静态产物，而是"本轮对话的执行记录 + 当前流水线状态 + 建议下一步"——供用户/下一个 skill 无缝续跑。** 交接物 = 执行记录 + 状态 + 下一步 三合一。

### 6.1 交接物统一模板（与其它虾系 skill 一致）

```markdown
# Handoff: <from-skill> → <to-skill>

## 元信息
- from: <来源 skill 名>
- to: <目标 skill 名>
- project: <项目名>
- module_status: ok | warning | blocked
- handoff_time: <ISO 时间>

## 验收摘要
- 本 skill 验收清单通过项：全部 / 部分（列未过项）

## 数据契约（下游直接消费的 JSON）
\`\`\`json
{ <结构化数据，见 6.3> }
\`\`\`

## 产物文件清单
| 路径 | 说明 |
|---|---|
| ... | ... |

## 下一步（交给谁做什么）
- 调用 <目标 skill> 的 <首个动作>，传参：...
- 前置已满足：...
```

### 6.2 本 skill（虾导）的交接物输出字段

| 字段 | 内容 |
|---|---|
| `conversation_summary` | 本轮对话做了什么（执行记录，grounding 只记实际发生） |
| `pipeline_state` | 查得的 pipeline/status（next_step 定位断点） |
| `executed_tools` | 本轮实际调用的工具与结果摘要 |
| `pending_items` | 因单轮一步未执行、留给下一轮的待办 |
| `next_action` | 建议下一步（调用哪个工具/等哪个任务完成） |

### 6.3 交接物 JSON 数据契约示例

```json
{
  "module": "xiaodao-assistant",
  "conversation_summary": "用户询问进度，已查 pipeline_status",
  "pipeline_state": {"next_step": "tts", "current_episode": 1, "episode_status": {"tts": false}},
  "executed_tools": [{"tool": "dramaclaw_pipeline_status", "ok": true}],
  "pending_items": ["待用户确认后启动 audio/generate"],
  "next_action": {"to": "xiajing-episodes", "action": "audio/generate", "params": {"episode": 1}}
}
```

### 6.4 交接链位置

```
虾导 ──handoff（执行记录+状态+建议）──▶ 用户/任意虾系 skill
（虾导每次对话收口后都产出交接物，保证"继续"无缝续跑）
```

**产出方式**：每次对话回合收口后，在工作区写 `handoff-xiaodao.md`（按 6.1 模板），并在最终回复中给出路径与核心 JSON。**交接物中的 pending_items 是"单轮一步"纪律的落点——下一轮从这里继续。**
