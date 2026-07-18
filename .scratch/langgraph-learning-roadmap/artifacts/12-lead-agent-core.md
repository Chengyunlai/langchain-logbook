# Mini DeerFlow Lead Agent 核心实现记录

> 完成日期：2026-07-13  
> 对应任务：[实现 Mini DeerFlow 的 Lead Agent 核心](../issues/12-implement-lead-agent-core.md)  
> 学习入口：[`mini_deerflow/LEAD_AGENT_CORE.md`](../../../mini_deerflow/LEAD_AGENT_CORE.md)  
> 架构入口：[`mini_deerflow/ARCHITECTURE.md`](../../../mini_deerflow/ARCHITECTURE.md)

## 1. 结论

Mini DeerFlow 已经从“能够运行一次工具循环的工程骨架”推进为一个可恢复的 Lead Agent 核心纵切面。现在可以在无 API Key 环境中验证：

```text
同一 thread 第一次调用工具并写 Artifact
→ 关闭 SQLite 连接并销毁 application/graph 对象
→ 新连接和新 application 使用同一 thread 继续调用
→ Checkpointer 恢复历史消息与治理轨迹
→ reducer 用同路径新事实替换旧 Artifact
→ 摘要、动态 Context、PII、权限、错误、Artifact 与调用预算按固定顺序治理
→ v2 update 被投影为严格 JSON-safe StreamEvent
→ 从真实 compiled graph 导出 Mermaid 拓扑
```

这条闭环没有把产品 Gateway、完整 Sandbox 或最终 SSE 协议塞进 Agent 核心。它先固定 Graph 一侧必须长期稳定的 State、Runtime Context、Middleware、持久化和事件接缝，后续任务 13/14 可以分别扩展执行环境与产品运行时。

## 2. 核心实现

### 2.1 跨应用实例恢复

- `MiniDeerFlowApplication.state_for()` 通过 `thread_id` 读取最新 checkpoint values，不向调用方泄露 `StateSnapshot` 内部结构。
- `open_sqlite_checkpointer()` 每次创建独立 SQLite 连接，测试用关闭并重开连接模拟进程对象重建。
- `JsonPlusSerializer` 只 allowlist `ArtifactRef` 与 `MiddlewareTraceEvent` 两个已审查领域类型，不打开全局 pickle fallback 或任意模块反序列化。
- thread identity 与 request identity 保持分离：第二轮沿用 thread，但使用新的 request id 和本轮 Runtime Context。

### 2.2 有业务语义的 Artifact reducer

`ThreadState.artifacts` 从机械 `operator.add` 改为 `merge_artifacts()`：

- path 未出现时按稳定顺序追加；
- path 已出现时在原位置用新 `ArtifactRef` 替换；
- 所有输入都再次经过 Pydantic 领域校验；
- reducer 只解决 State identity，不冒充文件存在性、Sandbox 隔离或跨进程事务。

端到端测试让两轮真实 `record_artifact` tool call 写入同一路径、不同 media type，最终 State 只保留第二轮事实。

### 2.3 默认 Middleware 治理链

组合根现在按精确顺序装配：

```text
LifecycleTrace
→ Summarization
→ ContextPrompt
→ PII
→ ToolPermission
→ StructuredToolError
→ ArtifactTracking
→ ModelCallLimit
```

- `ApplicationSettings` 增加摘要 trigger/keep 预算并校验 `trigger > keep >= 1`。
- `ApplicationDependencies` 区分 Lead model 与 summary model，避免离线摘要消费主模型脚本 iterator；生产环境也能单独配置摘要成本、超时和观测。
- `ArtifactTrackingMiddleware` 校验工具 `Command(update.artifacts)` 的列表形状、`ArtifactRef` 领域约束和 checkpoint-safe JSON 投影。
- 外层 `StructuredToolErrorMiddleware` 把 Artifact 校验异常转成模型可读的 `invalid_tool_input`，非法 State 不进入 checkpoint。
- 测试既锁定 8 个默认组件的声明顺序，也用 lifecycle trace 验证 before/wrap/after 的实际进入与退出方向。

### 2.4 稳定、严格 JSON-safe 的流式事件

`MiniDeerFlowApplication.stream()` 固定使用 LangGraph v2 `updates`，再由 `normalize_stream_part()` 建立应用协议投影：

- `StreamEvent` 固定 `type / namespace / data`；
- `as_dict()` 返回可直接交给 JSON/SSE adapter 的字段；
- Mapping、Sequence、Pydantic model、dataclass、Enum、时间、Path 和 UUID 被递归转换为 JSON 类型；
- set 使用确定排序；非有限浮点和未知对象明确失败并报告数据路径，不用 `str(value)` 静默掩盖协议缺口；
- 未知 event type 原样保留，旧 tuple 继续带 v2 迁移提示失败。

当前只承诺经过测试的 `updates` 和 JSON-safe 投影。message chunks、interrupt、heartbeat、event id、取消和断线重连仍属于任务 14 的 SSE wire protocol。

### 2.5 Graph 可视化

`draw_mermaid()` 从真实 `compiled_graph.get_graph()` 导出 Mermaid。测试要求拓扑含 model/tools 节点；教程同时说明 wrap hook 不一定成为独立图节点，必须用 Middleware trace 补足动态证据。

## 3. 教学交付

新增中文专题 `mini_deerflow/LEAD_AGENT_CORE.md`，按下面结构组织，而不是粘贴最终工厂：

1. 四次真实 TDD 红灯：恢复/reducer、治理链、JSON 事件、拓扑；
2. 业务边界和五类所有权判断；
3. 跨应用实例恢复的公共 seam 实验；
4. Artifact 冲突流程图与 reducer 选择；
5. Middleware 顺序、独立摘要模型和 ToolRuntime/Command 边界；
6. JSON-safe 事件与 Graph 可视化；
7. 五个失败实验、工程权衡、练习和延迟回忆题；
8. 当前 DeerFlow 固定提交的 `make_lead_agent / ThreadState / middleware / runtime` 对照路径。

专题包含 3 张可版本化 Mermaid 图及文本替代，并已进入 Astro 文档站和 Pagefind 搜索索引。精确依赖 patch 不在专题重复手写，以 `uv.lock` 为唯一事实源。

## 4. TDD 与审查证据

- 第一次恢复测试红灯：`MiniDeerFlowApplication` 缺少 `state_for()`；加入 SQLite 后又暴露领域类型 serializer 注册边界。
- 第一次流式测试红灯：application 缺少 `stream()`。
- 第一次摘要测试红灯：`ApplicationSettings` 不接受摘要预算。
- 第一次 Artifact 安全测试红灯：缺少 `ArtifactTrackingMiddleware`。
- 审查补强红灯：`StreamEvent` 缺少 `as_dict()`，Graph update 不能严格 JSON 序列化。
- Standards 初审发现 2 项：专题重复精确 patch 版本、任务状态与“已交付”文字不同步；前者已改为链接版本策略，后者随本记录和任务 resolution 同步关闭。
- Spec 初审发现 3 项：默认全链顺序测试、JSON-safe event data、显式渐进演进不足；三项均已补实现、测试与教学说明。

## 5. 验证结果

- 全量离线测试：`96 passed, 1 skipped`；跳过项是显式 external integration case。
- 唯一 pytest warning 来自 LangSmith 依赖使用 Python 3.14 将弃用的 `ast.Str`，不来自本任务代码。
- 教程契约：`0 new / 0 known / 0 stale`。
- CLI smoke：offline profile、5 个工具、最终回答和 6 个 Middleware events 正常输出。
- Lock：`uv lock --check` 通过。
- Wheel：`uv build --wheel` 成功，核心 app/state/persistence/middleware/streaming 均进入 package。
- 文档站：26 页构建成功；Pagefind 索引 16 页、3872 词；链接检查 `0 broken`。
- Astro 保留 2 个既有未使用 icon hints；Vite 保留 Mermaid 大 chunk 提示，均不是本任务引入的功能错误。

## 6. 有意延后的范围与下一前沿

- 任务 13：实现真实线程工作区 Sandbox、文件工具、副作用审计，以及可选 MCP/Skills adapter；这些工具返回的 Artifact 必须继续经过本任务的 reducer 和 Middleware。
- 任务 14：实现 thread/run repository、API、取消/恢复和完整 SSE wire protocol；它复用本任务的 `RunDescriptor`、`state_for()` 与 JSON-safe `StreamEvent`。
- 任务 15：扩展 trajectory evaluation、外部 tracing 和安全回归矩阵。

任务 13 与任务 14 在本任务解决后同时解除阻塞。按编号优先原则，默认先进入任务 13，但二者架构上可以独立推进。
