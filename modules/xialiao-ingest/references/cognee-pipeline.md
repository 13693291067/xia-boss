# Cognee 摄入流水线规格 — ingest_fast

> 虾料执行层的核心：把上传的小说变成知识图谱 + 向量索引 + novel.txt 落库。
> 本文件定义流水线的**完整行为**：顺序、进度、失败处理、落库时序。技术栈（Cognee）可等价替换，但行为语义必须一致。

---

## 1. 任务入队

- 任务类型：`ingest_fast`
- 队列：`queue_kind="default"`，`episode=0`，`product_surface="mainline"`
- payload：
```json
{
  "novel_path": "/abs/path/uploads/novel.txt",
  "config": { "rebuild": false, "spine_template": "drama" },
  "billing": { "billable_chars": 11000, "billing_quantity": 11000 }
}
```
- 运行器 `run_ingest_fast`：必须支持取消（包装 cancel watch）、进度/日志回调
- 进度回调语义：`update(progress, task)`——progress 为 `None` 时只写日志不重置进度

---

## 2. 三步流水线（ingest_novel_fast）

全程持有项目图谱写锁（Ladybug `ladybug_graph_access(state_dir, read_only=False)`），防止并发写坏图谱。

### 2.1 前置校验（0-2%）
1. `novel_path` 存在（否则 FileNotFoundError「文件不存在」）
2. 内容非空（否则 ValueError「小说内容为空，无法导入」）
3. **drama 模式**：`assess_screenplay_scene_headers(content).status == "missing"` → ValueError「精品剧必须包含场景头，请补充后重新导入」
4. 环境变量：`LLM_API_KEY` 或 `OPENAI_API_KEY` 必须存在 → 否则 ValueError「LLM API key 未设置。请在 .env 文件中添加: OPENAI_API_KEY=your_key_here」

### 2.2 rebuild 清理（6%）
**顺序敏感**：必须先失效"已导入"标志再清数据——
1. `unlink(project_dir/novel.txt)`（旧标志失效）
2. `delete_graph_preview(state_dir)`
3. `_prune_cognee_only()`（清 Cognee 图谱数据）

> 设计意图：即使清理中途失败，也不能让界面继续显示成功。

### 2.3 三步主线（进度见 §3）
| 步骤 | 操作 | 失败处理 |
|---|---|---|
| Step 1 原文入库 | `cognee.add(content, dataset_name)` | 每阶段重试 1 次瞬时失败（`_run_cognee_pipeline_with_retry`），重试仍败则抛 |
| Step 2 知识图谱 | `cognee.cognify(datasets=[dataset])` | 完成后校验 `_dataset_graph_has_nodes()`，无节点 → RuntimeError「知识图谱构建失败：未生成任何图谱节点」 |
| Step 3 向量索引 | `cognee.memify(dataset=dataset)` | 同上重试 |

> 注意：`cognee.add` 后 `cognify` 会做实体/关系/三元组提取（LLM），`memify` 创建向量索引（语义检索用）。

### 2.4 图谱预览（90-95%）
`materialize_graph_preview()`：读图谱 → `get_graph_snapshot(max_nodes=48)` → `write_graph_preview(state_dir)`（sidecar 文件）
- 无节点 → RuntimeError「知识图谱预览生成失败：未读取到任何图谱节点」

### 2.5 落库（98%）— 最后一步 ★
`save_novel_content(content)`：写入 `project_dir/novel.txt`
> **失败不留痕**：原文落库必须放在图谱构建成功之后。失败时不留下"已导入"的痕迹，前端不会误报成功，也不会锁死重新上传入口。

### 2.6 完成（100%）
返回：`{ "char_count": N, "dataset": "novelvideo_{project}", "status": "graph_ready" }`

---

## 3. 进度里程碑（前端 SSE 展示，必须一致）

| key | 进度 | 日志文案 |
|---|---|---|
| read | 2% | 读取并校验原文... |
| prune | 6% | 清理旧图谱... |
| parse | 10% | 解析原文... |
| parsed | 25% | 原文解析完成 |
| graph | 30% | 构建知识图谱... |
| graph_validated | 65% | 知识图谱校验完成 |
| index | 70% | 创建向量索引... |
| indexed | 85% | 向量索引创建完成 |
| preview | 90% | 生成图谱预览... |
| preview_saved | 95% | 图谱预览已保存 |
| save | 98% | 保存导入结果... |
| complete | 100% | 导入完成 |

---

## 4. 初始化与隔离（initialize）

1. `ensure_cognee_embedding_binding_in_state_dir(state_dir)` — 绑定 embedding 模型/维度
2. `init_cognee()`
3. 项目 SQLite `_ensure_db()`（data.db：章节/角色/剧集/道具项目事实）
4. **项目级上下文隔离** `cognee_project_context(state_dir)` — Cognee 1.0.5 的 base/relational 上下文按项目隔离，不同项目可安全并发初始化
5. `setup()` — "already exists" 错误容错（cognee 重复初始化 bug）
6. dataset 权限注册 `resolve_authorized_user_datasets` — "UNIQUE constraint failed" 容错（非致命）

---

## 5. 图谱快照（get_graph_snapshot，供 /ingest/graph）

### 5.1 有界化
- 节点：`max(20, min(max_nodes, 80))`，默认 48
- 边：`min(max_nodes * 3, 160)`
- 排序：`degree*10 + type_priority*3 + has_name`，取 top
- 类型优先级：Entity=6 > EntityType=5 > TextSummary=4 > Document=3 > DocumentChunk=1（其它 2）

### 5.2 属性压缩
- 字符串 ≤500 字符（超出截断加 `...`）；深度 ≥2 转字符串截断
- list 取前 12；dict 取前 16 键
- **剔除键名含 embedding/vector 的字段**
- 节点 label ≤160、type ≤80、relation ≤120

### 5.3 响应结构
```json
{ "nodes": [{"id","label","type","degree","properties"}],
  "edges": [{"id","source","target","relation","properties"}],
  "total_nodes", "total_edges", "truncated" }
```

---

## 6. 数据落盘契约

```
{project_dir}/
  uploads/{safe_name}     # 原始上传文件（用户可见/可重导入）
  novel.txt               # ★已导入标志（图谱成功后最后写）
{state_dir}/
  data.db                 # SQLite 项目事实
  graph-preview.json      # 图谱快照 sidecar
  cognee_data/            # Cognee 图谱/向量数据
```

## 7. 关键设计原则（还原时不可妥协）

1. **失败不留痕**：novel.txt 最后写
2. **顺序敏感**：rebuild 时先失效标志再清数据
3. **独占锁**：整个 ingest 持有项目图谱写锁
4. **可取消**：任务支持 cancel watch，取消要能安全清理
5. **重试 1 次**：每阶段瞬时失败重试一次，不无限重试
6. **环境依赖显式化**：缺 LLM key 直接报错指明，不静默降级
7. **图谱有界**：快照永远不把完整图/embedding 返回浏览器
