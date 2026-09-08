---
name: xialiao-ingest
description: |
  虾抖（虾料 / ingest）功能 100% 还原专用 skill。基于 DramaClaw（虾导）开源项目源码逐文件提炼，目标是把项目里「虾料」——即虾集主线第一个子页的小说/剧本导入与结构化摄入功能——完整复刻到任何新项目。
  触发词：虾抖、虾料、ingest、剧本导入、小说导入、小说摄入、上传剧本、章节检测、场景头解析、格式检查、FormatCheck、知识图谱构建、Cognee、ingest_fast、ChapterDetector、剧本结构化、导入预览、生产事实、国家年代、人物小传、空间链、威胁规则、视觉母题。
  适用场景：用户说"把虾抖/虾料功能做出来/还原出来/复刻一下"、"做一个剧本导入功能"、"小说上传转结构化数据"、"建一个像 DramaClaw 那样的摄入模块"、"100%还原虾抖"。本 skill 提供：功能全景（输入→校验→预览→设置→执行→结果→恢复→边界八层）、原项目完整代码地图（文件级路径+职责+关键实现）、逐模块实现规格（前端 2420 行主页面、后端 3 端点、解析器、Cognee 三步流水线）、还原验收清单。
  还原方式：两种模式——①源码克隆模式（原项目就在本机，直接对照 code-map.md 按文件搬运）；②从零重写模式（没有原项目，按 references 中的规格文档逐模块实现）。两种模式都以"行为等价"为验收标准：同样输入产生同样输出、同样状态流转、同样错误提示。
agent_created: true
---

# 虾抖（虾料 / ingest）功能 100% 还原

> 本 skill 把 DramaClaw（虾导）项目里「虾料」——虾集主线第一个子页的**小说/剧本导入与结构化摄入**功能——完整还原到目标项目。
> 覆盖范围：前端交互页（ingest.tsx 2420 行）+ 后端 3 个 REST 端点 + 确定性解析器（章节/场景头/格式检查）+ Cognee 三步流水线（add→cognify→memify）+ 知识图谱可视化 + 状态机与断点恢复。

## 0.1 权威定位（以产品手册为准）

> **产品手册（第五章）原文："虾料是项目的内容源头。所有解说剧或精品剧项目，都需要先建立文本来源。"**
> "选择项目类型与风格：类型（精品剧或解说剧）、视觉风格（古装风格、动漫风格等等），**人种（用于未明确设定角色时人物的默认外观方向）**，项目类型上传后会锁定，如需切换通常需要重新导入。"
> "虾料会根据文本结构识别章节、人物和剧情线索。"

**→ 虾料设置层三要素（手册权威）：①项目类型（精品剧/解说剧，上传后锁定）；②视觉风格；③人种（未明确设定角色时的默认外观方向）。**

---

## 0. 还原目标（一句话）

**虾料 = 小说/剧本的"入口"：上传 → 格式体检 → 章节预览 → 选项目类型 → 一键导入（构建知识图谱+向量索引）→ 变成后续虾塘（角色资产）、虾镜（剧集）能用的结构化地基。**

100% 还原 = 行为等价，验收标准：

```
同样的输入文件 → 同样的解析结果（章节/场景块/格式检查）
同样的用户操作 → 同样的状态流转（uploaded→importing→completed/stopped/failed）
同样的边界输入 → 同样的报错文案与错误码（unsupported/file_too_large/text_too_large/parse/screenplay_format）
同样的下游 → novel.txt 落库标志、知识图谱快照、项目配置（spine_template 等）完全一致
```

---

## 1. 功能全景（八层）

```
┌────────────────────────────────────────────────────────────────┐
│ ① 输入层   上传(.txt/.md/.docx, 拖拽/点击) / 粘贴(≤1000字)     │
│ ② 校验层   格式检查 FormatCheck（ok/warning/blocking 三级）     │
│ ③ 预览层   章节检测 + 场景块解析 + StatCard 统计 + 抽屉详情      │
│ ④ 设置层   项目类型 drama/narrated + 视觉风格 + 解说人称 + 族裔  │
│ ⑤ 执行层   ingest_fast 异步任务 + Cognee 三步流水线 + 进度 SSE  │
│ ⑥ 结果层   知识图谱力导向可视化（节点/边/详情/缩放）            │
│ ⑦ 状态机   上传→导入→完成/停止/失败 + 挂载对账 + 失败重试        │
│ ⑧ 边界     大小/字数/格式/环境变量/硬性限制清单                 │
└────────────────────────────────────────────────────────────────┘
```

八层的**完整规格**在 `references/` 下分文件定义（见 §4），实现时必须逐层对照。

---

## 2. 还原工作流

### 2.1 开工前：选择还原模式

**先问或自查**：目标项目里是否已有 DramaClaw 源码？

- **源码克隆模式**（原项目在本机，如 `C:/Users/123/Desktop/AI学习资料/dramaclaw`）：
  1. 读 `references/code-map.md` 拿到文件级代码地图（原路径 → 职责 → 关键实现要点）
  2. 按地图逐个文件搬运/适配到目标项目（保留所有常量、正则、错误文案、状态机）
  3. 用 §3 验收清单逐条核对
- **从零重写模式**（无原项目）：
  1. 按 `references/frontend-behavior.md` 还原前端交互与状态机
  2. 按 `references/backend-api.md` 还原 3 个 REST 端点与 payload 契约
  3. 按 `references/parsers.md` 还原确定性解析器（章节/场景头/格式检查）
  4. 按 `references/cognee-pipeline.md` 还原 Cognee 三步流水线（或等价的知识图谱实现）
  5. 按 `references/limits.md` 还原全部边界与错误码
  6. 用 §3 验收清单逐条核对

### 2.2 执行纪律（强制）

1. **逐层还原**：严格按 输入→校验→预览→设置→执行→结果→状态机→边界 顺序实现，每层完成即自测，不要跳层。
2. **常量不漂移**：所有限额/正则/错误码/文案必须与 references 完全一致（这是"100%还原"的核心），禁止"差不多就行"。
3. **行为等价优先**：允许技术栈不同（如后端不用 FastAPI），但 API 语义、状态流转、错误响应结构必须等价。
4. **失败不留痕**：还原"novel.txt 最后写"的语义——只有图谱构建成功后才落"已导入"标志，失败不得让前端误报成功。
5. **格式检查不软化**：blocking 级问题必须拦截导入，禁止为了"好用"降级。
6. **还原后再交付**：完整实现 + 自测通过后，输出验收清单核对结果与代码地图差异说明，再向用户汇报。
7. **资产正面统一（下游约定）**：虾料产出的角色/道具条目最终会进入虾塘资产，**资产类图片输出视角必须统一正面**（角色定妆=正面全身/半身面向镜头；身份图=**两图制（定妆照 + 四视图角色卡，2026-08-21 拍板）**；道具=**五宫格（★ 2026-08-21：正面/背面/左侧面/右侧面/材质细节特写，上 2 下 3）**）；本模块只保证提取字段完整（face_prompt 等含正面描述），视角落实由虾塘 skill「资产输出统一正面」规范约束。
8. **生产事实六项（★ 2026-09-03 集成，世界观梳理后强制补齐）**：知识图谱/世界观确认材料就绪后，加载 `references/production-facts.md` 补齐六项生产事实（国家年代地域 / 季节时间轴 / 语言声音文化 / 世界威胁规则 / 人物小传含声音气质与资产依赖 / 状态链与视觉母题），每条带四级事实标注（剧本事实/强推断/导演提案/待定冲突，提案禁止伪装成原文事实）；并输出空间链表 `outputs/scene-chain.md`（scene-consistency 空间真理图的上游输入）。**国家年代、主要人物关系、核心世界规则、人物小传未确认前，虾格不得输出正式三件套、虾塘不得输出正式角色确认稿。**

---

## 3. 验收清单（100% 还原判定）

实现完成后逐条打勾，全部通过才算 100% 还原：

### 输入层
- [ ] 支持 .txt/.md/.docx，UTF-8 优先 GBK 回退，CRLF 归一
- [ ] 拖拽 + 点击选择 + 键盘可操作；粘贴模式上限 1000 字符
- [ ] 文件名清洗防路径穿越；上传流式写入超限即中断删残片

### 校验层
- [ ] 上传即返回 FormatCheck（level/summary/issues/metrics/scene_header_status）
- [ ] 精品剧场景头缺失 → blocking 拦截；repairable → warning
- [ ] 每个 issue 带 code/line/message/fix 四字段
- [ ] 场景头解析支持 中文制片/分字段/Fountain/插入场 等全部格式
- [ ] **（xia-boss 剧本先行适配）场景边界只绑显式 `场景：` 头 + 传统 slugline；`【` 开头的六字段正文行不得被计为场景头**（防"王员外"式假 scene_blocks，见 `references/parsers.md §2.4`）

### 预览层
- [ ] 章节检测支持 第X章/第X集/Chapter N/Episode N + 中文数字复合解析 + 防误切
- [ ] 无章节时单章回退（B档剧本裁掉前言区）
- [ ] 5 个 StatCard（文件名/总字数/计费字数/章节数/预估集数）
- [ ] 章节表格（前20章）+ 点击开抽屉（场景卡片/正文）

### 设置层
- [ ] 项目类型 drama/narrated 二选一，**上传后锁定**，仅重导入可改（手册五章）
- [ ] 视觉风格选项完整（古装/动漫等）+ **人种设置**（未明确设定角色时人物的默认外观方向）
- [ ] 解说人称仅 narrated 显示且不落库脏值
- [ ] 设置变化才保存

### 执行层
- [ ] blocking 时不启动；启动前保存设置
- [ ] ingest_fast 入队返回 task_id/task_key；SSE 实时进度
- [ ] Cognee 三步：add → cognify（校验有节点）→ memify；每阶段重试1次
- [ ] 进度里程碑 2%/6%/10%/25%/30%/65%/70%/85%/90%/95%/98%/100%
- [ ] rebuild 时先失效 novel.txt 再清旧图谱；成功后才写 novel.txt
- [ ] 缺 LLM_API_KEY/OPENAI_API_KEY 时报错并指明

### 结果层
- [ ] 图谱快照有界（节点≤80默认48、边≤160、去 embedding）
- [ ] **每个节点含 x / y 初始坐标（★ 2026-08-21）**：按类型分环预分配（如以 600/360 为中心，角色内环/地点势力中环/物品概念外环）；前端无 force simulation，缺坐标会全部堆在中心（模板虽有环形兜底，但数据层必须主动预分配，保证分层可读）
- [ ] 力导向可视化：类型着色/节点大小按degree/详情/缩放拖拽/全屏

### 状态机
- [ ] uploaded→importing→completed/stopped/failed 全流转
- [ ] 上传期间全屏遮罩防切页
- [ ] 挂载时与服务端任务列表对账恢复进度视图
- [ ] 失败后复用已上传文件重试（不必重新上传）
- [ ] 重新导入有二次确认弹窗

### 边界
- [ ] 上传≤512KB / 导入≤1MB / 单次≤100,000计费字数
- [ ] 全部错误码文案一致（unsupported/file_too_large/text_too_large/parse/screenplay_format）

---

## 4. References 索引

| 文件 | 内容 | 何时加载 |
|---|---|---|
| `references/code-map.md` | **原项目完整代码地图**（文件路径/职责/关键实现要点） | 开工必读（克隆模式）；从零模式用于对照 |
| `references/frontend-behavior.md` | 前端交互规格（组件树/状态机/缓存/对账/UX细节） | 还原前端时 |
| `references/backend-api.md` | 后端 3 端点契约（upload/start/graph）与 payload 结构 | 还原后端时 |
| `references/parsers.md` | 确定性解析器规格（章节检测/场景头/格式检查） | 还原解析层时 |
| `references/cognee-pipeline.md` | Cognee 三步流水线 + 进度里程碑 + 图谱快照 | 还原执行层时 |
| `references/limits.md` | 全部边界限制、常量、错误码文案 | 还原边界层/验收时 |
| `references/production-facts.md` | **生产事实六项 + 四级事实标注 + 空间链表**（★ 2026-09-03 集成：国家年代/季节时间轴/语言声音/威胁规则/人物小传/状态母题 → docs/；空间链 → outputs/scene-chain.md） | 世界观梳理完成后、交虾格前加载 |

**不要重复加载已读过的 reference；不要回翻历史找过期状态；实现细节不确定时先读对应 reference，不要编造机制。**

---

## 5. 与其它 skill 的关系

- 本 skill 只负责**还原虾料（ingest）这一个功能模块**，不覆盖虾塘/虾镜/虾格/虾导等下游。
- 还原出的虾料应向下游（角色资产、剧集规划）输出与 DramaClaw 一致的数据契约：`novel.txt` + 项目配置（`spine_template`/`visual_style`/`narration_style`/`ethnicity`/`ingest_source_filename`）+ 章节/场景块结构 + 知识图谱快照。
- 若同时使用 `dramaclaw` skill（虾导流水线），本 skill 的产出可直接被其消费——两者数据契约一致。

---

## 6. 输出交接（Handoff）★ 完成本 skill 后必做

**本 skill 的最终产出必须落成一份标准交接物（handoff 文档），让下一个 skill 拿到就能直接接着干。** 交接物是"数据契约 + 状态 + 下一步"三合一的交付物。

### 6.1 交接物统一模板（所有虾系 skill 共用）

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

### 6.2 本 skill（虾料）的交接物输出字段

| 字段 | 内容 |
|---|---|
| `format_check` | 三级检查结果（level/summary/issues/metrics/scene_header_status） |
| `chapters` | 章节+场景块结构（number/title/scene_blocks/字数） |
| `total_chars` / `billable_chars` | 计费数据 |
| `spine_template` | 项目类型（drama/narrated） |
| `knowledge_graph` | 图谱快照（nodes/edges） |
| `project_config` | 落库的项目配置键（visual_style 等） |
| `production_facts` | 生产事实六项登记状态（★ 2026-09-03：confirmed/partial + docs 路径；含四级标注） |
| `scene_chain` | 空间链表路径（★ 2026-09-03：outputs/scene-chain.md，scene-consistency 上游输入） |
| `next_action` | 建议交给虾塘的 build_characters |

### 6.3 交接物 JSON 数据契约示例

```json
{
  "module": "xialiao-ingest",
  "format_check": {"level": "ok", "summary": "上传成功，剧本格式校验通过。"},
  "chapters": [{"number": 1, "title": "第1集 标题", "scene_blocks": 3}],
  "total_chars": 2828, "billable_chars": 2717,
  "spine_template": "drama",
  "knowledge_graph": {"nodes": 48, "edges": 120, "truncated": true},
  "project_config": {"visual_style": "guoman_fantasy", "ingest_source_filename": "ch001-drama.md"},
  "production_facts": {"status": "confirmed", "items": {"country_era": "confirmed", "season_timeline": "confirmed", "language_voice": "confirmed", "threat_rules": "confirmed", "character_bios": "confirmed", "state_motifs": "confirmed"}, "docs_paths": ["docs/02-world-*.md", "docs/03-characters/*.md"]},
  "scene_chain": {"path": "outputs/scene-chain.md", "spaces": 6, "confirmed": true},
  "next_action": {"to": "xiatang-characters", "action": "build_characters", "params": {"project": "..."}}
}
```

### 6.4 交接链位置

```
xialiao-ingest ──handoff──▶ xiatang-characters ──handoff──▶ xiajing-episodes
      ▲                                                          │
      └──────────── 虾格注入风格 + 虾导对话驱动 ──────────────────┘
```

**产出方式**：完成验收后，在工作区写 `handoff-xialiao-to-xiatang.md`（按 6.1 模板），并在最终回复中给出该文件的路径与核心 JSON，提示用户可直接交给下一个 skill。
