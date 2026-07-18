# DeerFlow 当前源码与综合实战阅读地图

> 调研日期：2026-07-14  
> 官方仓库：`bytedance/deer-flow`  
> 固定提交：[`4af617835805dd7cd78162ebed02fd6b782ea8bf`](https://github.com/bytedance/deer-flow/tree/4af617835805dd7cd78162ebed02fd6b782ea8bf)  
> 提交时间：2026-07-14T08:58:06+08:00  
> 提交主题：`feat(trace): add agent observability with Monocle (#4024)`

本文件只使用 DeerFlow 官方源码作为易变实现事实源。提交号是可复现的阅读锚点，不代表课程应复制该目录结构，也不代表 `main` 之后没有变化。

## 1. 先建立三层心智模型

| 层 | 当前源码入口 | 主要问题 |
|---|---|---|
| LangGraph runtime | `backend/langgraph.json` | graph factory、auth、checkpointer 如何注册 |
| DeerFlow Harness | `backend/packages/harness/deerflow/` | Lead Agent、State、Middleware、Tools、Subagents、Sandbox、MCP、Skills 如何组合 |
| Gateway 产品运行时 | `backend/app/gateway/` + Harness `runtime/` | Thread/Run、worker、journal、event store、stream bridge、SSE 如何交付 |

不要把三层压成“一个大 Graph”。LangGraph checkpoint 保存图恢复事实；Gateway Run/Event 保存产品运行事实；trace/span 保存诊断调用树。三者可以共享关联 ID，但生命周期、读者与一致性要求不同。

## 2. 四条推荐阅读路线

### 路线 A：从注册入口到 Lead Agent 组合根

1. [`backend/langgraph.json`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/langgraph.json)：确认 `lead_agent` 指向 `deerflow.agents:make_lead_agent`，并独立注册 auth/checkpointer。
2. [`agents/lead_agent/agent.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/agents/lead_agent/agent.py)：沿 `make_lead_agent → _make_lead_agent → create_agent` 阅读模型、工具、Middleware、Prompt 和 State 的装配。
3. [`models/factory.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/models/factory.py)：观察 `create_chat_model(..., attach_tracing=False)` 为什么由 graph root 统一挂 tracing callback，避免重复 root。
4. [`agents/thread_state.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/agents/thread_state.py)：确认业务状态是在 `AgentState` 上扩展，而不是把所有 runtime context 都塞入 checkpoint。

### 路线 B：从状态到 Middleware 与能力治理

1. 先列出 `ThreadState` 字段、reducer 和持久化边界。
2. 回到 `agent.py` 的 `build_middlewares(...)` 调用，记录 Middleware 的实际顺序。
3. 按“输入清洗 → 动态 Context → 权限/guardrail → 工具路由/执行 → 结果治理 → 摘要/预算/终止”分组阅读 `agents/middlewares/`。
4. 再进入 `tools/`、`guardrails/`、`mcp/` 和 `skills/`，判断能力发现、应用授权、运行时执行是否被分开。

这条路线的目的不是记住几十个类名，而是回答：身份从哪里注入、模型能否自行扩大权限、失败如何进入可解释状态、Middleware 顺序为何属于架构契约。

### 路线 C：从 task tool 到隔离 Subagent

1. [`tools/builtins/task_tool.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/tools/builtins/task_tool.py)：读取配置、父级 runtime context、tool groups、skills allowlist、sandbox/thread 数据和 trace metadata 的显式传播。
2. [`subagents/executor.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/subagents/executor.py)：观察 specialist 如何创建自己的 `create_agent`、加载 skills、限制递归 task、处理 timeout/cancel/token/turn cap。
3. [`subagents/config.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/subagents/config.py) 与 builtins：区分配置/注册、执行与具体 specialist。
4. 回看 `task_tool` 的 terminal `Command(update=ToolMessage(...))`：Subagent 结果以结构化状态返回 Lead，而不是把完整内部消息史合并进父图。

### 路线 D：从 HTTP/SSE 到 worker、journal 与 graph

1. [`gateway/app.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/app/gateway/app.py)：确认 router 与 `langgraph_runtime` 生命周期的装配。
2. [`routers/thread_runs.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/app/gateway/routers/thread_runs.py)：沿 create/stream/join/cancel 接口进入服务层。
3. [`gateway/services.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/app/gateway/services.py)：观察 HTTP DTO 如何转为 Run、Graph input 或 `Command(resume=...)`。
4. [`runtime/runs/manager.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/runtime/runs/manager.py) 与 [`worker.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/runtime/runs/worker.py)：理解 Run 生命周期、owner/lease、取消、恢复和 graph streaming。
5. [`runtime/journal.py`](https://github.com/bytedance/deer-flow/blob/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/runtime/journal.py) → event store → [`runtime/stream_bridge/`](https://github.com/bytedance/deer-flow/tree/4af617835805dd7cd78162ebed02fd6b782ea8bf/backend/packages/harness/deerflow/runtime/stream_bridge)：区分持久化事件事实和实时传输。

## 3. 两条不可混淆的观测链

当前提交的重要变化是 graph invocation root 在 `make_lead_agent` 组合时统一添加 tracing callbacks，而内部 chat model 与 subagent model 传 `attach_tracing=False`。它形成诊断链：

```text
graph root callback → chain/model/tool/subagent child spans → tracing backend
```

产品事件链则是：

```text
RunManager/worker → RunJournal callback → RunEventStore → StreamBridge → SSE consumer
```

前者回答“为什么慢、在哪个调用失败、token 花在哪”；后者回答“这个 Run 对客户端已经发生了哪些可重放事件”。不能用 trace backend 代替产品 journal，也不能把 event journal 当作完整调用树。

## 4. Mini DeerFlow 到 DeerFlow 的关键映射

| Mini DeerFlow | DeerFlow 当前源码 | 迁移问题 |
|---|---|---|
| `app.py` / `agents/` | `agents/lead_agent/agent.py` | 组合根如何解析动态产品配置 |
| `state.py` | `agents/thread_state.py` | 哪些事实可 checkpoint，哪些只能在 runtime context |
| `middleware/` | `agents/middlewares/` + `guardrails/` | 顺序、权限与错误是否有可测试契约 |
| `subagents/` | `task_tool.py` + `subagents/executor.py` | 父上下文如何裁剪并保持身份归因 |
| `sandbox/` | `sandbox/` + community providers | 本地路径护栏与真正执行隔离有何差别 |
| `mcp/` / `skills/` | `mcp/`、`skills/`、deferred tools | 发现、披露、授权、执行是否分层 |
| `persistence.py` | `runtime/checkpointer/`、`runtime/store/` | Thread checkpoint 与跨线程 Store 的语义区别 |
| `runtime/` / `api/` | Gateway routers/services + `runtime/runs/` | 产品 Run/Event 为什么不能只靠 Graph State |
| `observability.py` | `tracing/` + `RunJournal` | trace root 与 event journal 的所有权边界 |

## 5. 故障驱动的阅读问题

- 进程在 interrupt 后退出：恢复依赖 checkpointer、Run repository 还是 StreamBridge？各自丢失会怎样？
- 同一 resume 请求重放：Graph 节点重执行时，远端副作用靠什么幂等？源码中是否只有本地意图记录？
- 一个 Subagent 超时：Lead 收到什么 status/stop reason？兄弟任务和 token budget 怎么处理？
- SSE 客户端断线：worker 是否继续？重连的数据来自实时 bridge 还是 event store？
- 工具来自 MCP/Skill：被发现是否等于被授权？tool groups 与 allowlist 在哪一层生效？
- trace backend 不可用：产品 Run/Event 是否仍能完成？若不能，说明两条链错误耦合。

## 6. 来源与复核命令

```bash
git ls-remote https://github.com/bytedance/deer-flow.git HEAD
git clone --depth 1 https://github.com/bytedance/deer-flow.git /tmp/deerflow-current
git -C /tmp/deerflow-current rev-parse HEAD
git -C /tmp/deerflow-current show -s --format='%H%n%cI%n%s' HEAD
```

复核结果为 `4af617835805dd7cd78162ebed02fd6b782ea8bf`。所有链接均固定到该提交；之后更新课程时应先重新运行命令，再记录“旧锚点 → 新锚点”的结构变化，而不是静默替换结论。
