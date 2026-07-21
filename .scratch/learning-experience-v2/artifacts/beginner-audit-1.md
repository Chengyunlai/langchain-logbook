# 初学者盲读验收报告 1

## 结论摘要

结论：**BLOCKED**。

正式课程的概念递进总体成立。我只依靠 README、01–11 章正文与 Notebook，就能从 Message/Runnable 解释到 Agent 工具循环、State/Reducer、Command/Send/Subgraph、Checkpoint/Store、interrupt/resume 和 Subagent-as-tool；继续阅读六篇 Mini DeerFlow 工程专题后，也能闭卷写出组合根、四类数据边界、Lead→task→Executor、Sandbox、Run/Event/SSE、Evaluation/Trace 的关系。

但验收不能判 PASS，原因有三项：第 06 章 Notebook 有一个原样运行必失败的异步单元；第 11 章有十个同类异步单元直接失败，并使最后的 Ledger 实验级联失败；按 `DEERFLOW_GUIDE.md` 拉取固定 DeerFlow commit 时两次长时间无输出，无法完成四条外部源码路线的固定版本证据复核。前两项是课程/Jupyter 的本地阻塞，第三项是外部环境阻塞。

## 验收边界与执行方式

- 按 README 的正式顺序阅读 01–11，没有跳章。
- 01–11 完成前没有打开 `mini_deerflow` Python 源码。
- 每个 Notebook 都使用仓库锁定环境通过 `jupyter nbconvert --execute` 原样执行，输出只写入 `/tmp`。
- 第 06、11 章原样失败后，额外用 `--allow-errors` 继续检查后续单元；这只用于判断阻塞范围，不把失败算作通过。
- 工程专题按 `ARCHITECTURE → LEAD_AGENT_CORE → SANDBOX_EXTENSIONS → RUNTIME_GATEWAY → EVALUATION_OBSERVABILITY → CAPSTONE → DEERFLOW_GUIDE` 阅读。
- 只打开正式文章明确要求追踪的 Mini DeerFlow 公共源码位置：`app.py`、`agents/lead_agent.py`，以及 Runtime 主链的 `api/gateway.py`、`runtime/manager.py`、`runtime/repository.py`、`runtime/sse.py`。
- 没有读取 `.scratch` 中既有材料、`TODO.md`、git log/diff、`tests/`、`quality/`、`scripts/`、`CONTEXT.md` 或任务讨论。
- 没有修改正式课程或源码。`make mini-deerflow-capstone` 产生的 `.capstone-demo` 已在命令完成后删除。

## 01–11 逐章学习记录

### 第 01 章：模型、消息与第一次可观察调用

**我预计本章要解决什么：**区分“调用模型”“固定程序管道”和“模型表达工具意图”，并让我能正确读取流事件。

原样 Notebook：通过。

本章新增能力：我能把 System/Human/AI Message 当作有角色的协议对象；Runnable 的步骤由程序固定；`bind_tools` 只让模型返回 `tool_calls`，没有执行函数；v2 stream 先读 `type/ns`，再按类型解释 `data`。下一章需要把自然语言计划变成程序能验证和持久化的对象，否则 Graph 仍要猜文本格式。

### 第 02 章：结构化输出

**我预计本章要解决什么：**让模型输出从脆弱字符串升级为带类型、范围和领域约束的业务契约。

原样 Notebook：通过。

本章新增能力：Pydantic 负责候选数据的类型与领域校验；`with_structured_output` 把模型结构化 tool call 解析成对象，但不执行业务工具；`TaskPlan` 校验依赖；`ArtifactRef` 约束工作区相对路径；失败也应有稳定对象。下一章需要解决“计划结构正确但事实过时、无来源”的问题。

### 第 03 章：RAG 2.0

**我预计本章要解决什么：**在上下文预算内选择相关证据，并让来源从 Loader 一直保留到回答。

原样 Notebook：通过。

本章新增能力：Document 同时携带正文和 metadata；Splitter 不能丢 source；Retriever 是 `query → Document[]`，不是 Agent；格式化阶段要把 source/chunk 映射带入 Prompt；零相关结果应成为 `insufficient_evidence`，不能强塞最近邻；recall@k 独立衡量召回。下一章需要把固定“每次检索一次”升级为模型在受控 registry 中选择工具。

### 第 04 章：工具意图到完整 Agent 循环

**我预计本章要解决什么：**亲手补齐 tool call 的执行与回传，再理解 `create_agent` 自动接管了什么。

原样 Notebook：通过。

本章新增能力：工具 args schema 同时服务模型可见约束与运行时校验；应用必须把工具结果写成与 call ID 配对的 `ToolMessage`；`create_agent` 自动执行 `HumanMessage → AIMessage(tool_calls) → ToolMessage → AIMessage`；`ToolRuntime` 注入应用拥有的身份/依赖，模型不可填写；标准输入键是 `messages`。下一章需要给 State、Context、Store 和业务数据库划定所有权。

### 第 05 章：Context Engineering

**我预计本章要解决什么：**把都被口语称作“上下文”的数据按所有者和生命周期拆开。

原样 Notebook：通过。

本章新增能力：Runtime Context 保存一次调用的可信身份、权限、连接和 Secret；Graph State 保存当前 thread 会演进并 checkpoint 的事实；Store 用 namespace/key 保存跨 thread 的应用数据；余额、订单等权威事务仍在业务数据库；Checkpointer 的主键语义是 thread，而 Store 的主键语义是应用 namespace/key。下一章需要把权限、脱敏、预算和错误等重复治理收回统一生命周期。

### 第 06 章：Agent Middleware

**我预计本章要解决什么：**把散落在每个工具和模型调用点的横切规则，收敛到可组合、可测试的 Middleware 链。

原样 Notebook：失败。使用 `--allow-errors` 后确认只有实验 9 的异步取消单元直接报错，其余单元可继续执行。

本章新增能力：`before_model/after_model` 有进入/退出顺序；`wrap_model_call` 可以改请求、换已授权模型或在 handler 前短路；`wrap_tool_call` 可在副作用前拒绝权限，或把普通工具异常转成配对的结构化 `ToolMessage`；取消不能被普通错误吞掉；摘要、HITL 和 Runnable listener 分属不同生命周期。下一章需要把确定性的业务阶段、条件分支和并行合并显式写成 Graph。

局部阻塞不妨碍我理解概念，但会阻止一名只按 Jupyter 操作的学习者完成本章正式实验，详见 B1。

### 第 07 章：StateGraph

**我预计本章要解决什么：**把藏在 Prompt 中的固定流程写成节点、边和可验证的状态变化。

原样 Notebook：通过。

本章新增能力：节点读取快照并返回 patch；边定义可达关系；router 只决定后继；并行节点写同一字段时必须由字段 reducer 明确合并；append-only 列表可用 `operator.add`，任务表则应按 ID 合并；显式 ReAct 本质是 model/tools 的条件循环；业务预算应产生可解释终态，recursion limit 只是保险丝。下一章需要处理运行时任务数量、局部状态边界和更复杂路由。

### 第 08 章：动态研究工作流

**我预计本章要解决什么：**让规划阶段在运行时展开任务，并把路由、动态并行和局部子流程表达清楚。

原样 Notebook：通过。

本章新增能力：`Command(update, goto)` 适合一个业务决定同时更新并选路；`Send` 为运行时产生的每个 section 创建同一节点定义的 task，fan-in 仍依赖 reducer；Subgraph 提供固定拓扑与 State schema 边界，但不等于 Subagent；循环要有进度、终止条件和上限；Functional API 用 task future 给过程式代码增加 durable runtime。下一章需要让这些执行现场跨进程保存。

### 第 09 章：持久化与恢复

**我预计本章要解决什么：**区分返回值与可恢复现场，并用真实持久后端证明跨重建恢复。

原样 Notebook：通过。

本章新增能力：Checkpointer 在 superstep 边界保存 `StateSnapshot(values/next/tasks/config/metadata)`；`thread_id` 是 checkpoint lineage 地址而不是用户身份；新 `InMemorySaver` 无法恢复旧数据，重开同一 SQLite 文件可以；history 要按 `next` 或业务状态定位，不能靠下标；time travel 创建新 lineage，不能撤销外部副作用；旧 checkpoint 需要显式 schema migration。下一章需要在暂停/重放条件下保护高风险副作用。

### 第 10 章：Human in the loop

**我预计本章要解决什么：**让人工审批释放 worker、跨时间恢复，并避免 resume/time travel 重复副作用。

原样 Notebook：通过。

本章新增能力：`interrupt(value)` 把暂停点写入 checkpoint 并结束当前调用；同一 thread 上用 `Command(resume=...)` 恢复，节点从开头重入；resume payload 仍要 Schema 与权限校验；副作用应移到 interrupt 之后的独立节点；稳定 operation ID 和事务 ledger 使同一意图重放返回 `already_recorded`，同 key 不同 payload 必须冲突。下一章需要控制 Lead 长历史和 specialist 能力边界。

### 第 11 章：Subagent 模式

**我预计本章要解决什么：**让 Lead 动态委派专业任务，同时隔离输入、控制并发/超时/输出并保留最终综合权。

原样 Notebook：在实验 10 首次失败。使用 `--allow-errors` 检查到 10 个直接 `RuntimeError`，最后一个 Ledger 实验又因上游委派均未执行而 `IndexError`。

本章新增能力：普通函数分工不等于 Subagent，边界要由 TaskRequest/Result、allowlist 输入投影和有界输出建立；Router 只选分支，Handoff 改变后续会话所有者，Subgraph 固定父图控制，Subagent-as-tool 则由 Lead 委派后收回控制；Executor 拥有 semaphore、timeout、部分失败归一化、输出预算和 ledger；task tool 只向模型暴露任务描述和 specialist 类型。工程上下一步必须由组合根装配 Lead、task、Executor、Store 和 Checkpointer。

本章核心后半段无法在正式 Jupyter 中原样运行，属于全局学习阻塞，详见 B2。

## 进入 Mini DeerFlow 前的闭卷解释

### `create_agent` 工具循环

输入先被规范化为 messages。模型返回 AIMessage；如果其中有 tool calls，Agent runtime 按名字找到已注册工具，验证 args 与权限，执行并生成带相同 call ID 的 ToolMessage，再把完整历史交给模型。模型返回不含 tool calls 的 AIMessage 时循环结束。`bind_tools` 只提供 Schema 和产生意图，不执行任何工具。

### State 与 Reducer

State 是一个 thread 内节点共同读取、通过 patch 演进、可被 checkpoint 的事实集合。Reducer 是某个 channel 在旧值和一个或多个更新之间的领域合并协议，尤其决定同一 superstep 的并行 patch 如何汇合。列表类型不自动意味着追加；Artifact 可以按 path 替换，任务可以按 ID upsert，审计轨迹才适合 append-only。

### Command、Send 与 Subgraph

- Command：一个节点在一次业务决定中同时返回 State update 和 goto；也承载 resume 等控制值。
- Send：根据运行时数据生成多个同一节点定义的 task；每个 task 有独立输入，结果仍由父 State reducer fan-in。
- Subgraph：一张可复用的 compiled Graph，拥有固定拓扑和可独立声明的 State schema。共享 schema 时不会自动隐藏父 State，也不自动成为独立 Agent。

### Checkpointer 与 Store

Checkpointer 以 thread/checkpoint/namespace 保存 Graph 的 values、next、tasks 和 lineage，回答“从哪里继续”。Store 由应用以 namespace/key 主动保存跨 thread 事实，回答“不同会话要复用什么”。两者都不是订单/余额等权威业务数据库，也都不是产品 Run/Event repository。

### interrupt 与 resume

interrupt 把等待事实持久化并释放当前 worker；resume 必须针对同一 thread 发送 `Command(resume=...)`。包含 interrupt 的节点从开头重入，因此 interrupt 前不应执行不可幂等副作用，interrupt 调用数量和顺序要稳定；发布还需要稳定 operation ID、ledger/outbox 或 provider idempotency key。

### Subagent-as-tool 的差异

Router 由分类结果选择一次分支；Handoff 让目标 Agent 接管后续对话；Subgraph 由父图固定控制拓扑；Subagent-as-tool 让 Lead 保持主会话与最终综合权，只把裁剪后的任务交给临时 specialist，并收回有界结果。它的隔离来自请求投影、独立 Agent/工具策略和执行 seam，不来自“多画了一个节点”。

## 工程专题逐篇记录

### ARCHITECTURE

**我预计本篇要解决什么：**把前 11 章的零件装成唯一应用，找到组合根和依赖方向。

`python -m mini_deerflow` 离线真实工具循环成功。按文章要求追到 `build_application → _assemble_graph → create_lead_agent → graph.invoke` 后，我能解释：`app.py` 拥有配置、活依赖、工具表、Executor、Middleware 和持久化装配；Lead factory 只消费注入对象，不应自行扫描扩展或读取环境；`make_graph()` 为 Agent Server 留空本地 persistence；Harness 不能反向 import API。

下一篇需要证明这套装配在跨重建恢复、Artifact reducer、Middleware 顺序和稳定事件上真的成立。

### LEAD_AGENT_CORE

**我预计本篇要解决什么：**让 State、Tools、Middleware、Checkpointer 和 Streaming 在同一纵切面受压。

我能解释同 thread/不同 request 的两轮调用如何经同一 SQLite checkpoint 恢复；Artifact reducer 为什么按 path 替换；独立 summary model 为什么不能与脚本化 Lead model 共用 iterator；工具 `Command(update)` 为什么必须经 Artifact middleware；v2 StreamPart 为什么先归一化成严格 JSON-safe `StreamEvent`；Mermaid 静态拓扑为什么仍不能证明所有 wrap hook 的动态顺序。

下一篇需要给文件与扩展能力建立实际能力边界。

### SANDBOX_EXTENSIONS

**我预计本篇要解决什么：**让 Lead/Subagent 使用工作区、MCP 和 Skill，而不等同于获得宿主环境权限。

我能区分路径护栏、本地 workspace provider 和进程/容器 Sandbox。模型只提供相对 path/content，ToolRuntime 注入 user/thread，provider 返回 ArtifactRef，Command 同时形成 ToolMessage 与 State patch。Subagent 只继承 opaque `sandbox_id`；MCP discovery 之后仍需应用 allowlist；Skill 启动时只展示 metadata，正文由 `load_skill(name)` 按需加载。

下一篇需要把 Graph 提升成客户端可创建、查询、取消、恢复和重连的产品任务。

### RUNTIME_GATEWAY

**我预计本篇要解决什么：**在 Graph 外增加产品 Thread/Run/Event 与可重放 SSE，不污染 Harness。

按文章给出的调用链追到 `Gateway.start_run → RunManager.start_message/_execute → Repository.append_event → Gateway.iter_run_events/SSEEncoder`。我能解释产品 Thread 做 ownership、Run 做不可逆状态机、Event journal 做单调 sequence 与 replay、Checkpointer 做 Graph 恢复、Store 做跨 thread 事实、Workspace 保存大对象。resume 创建新 Run 但复用 checkpoint thread；event 先落库再发 SSE；heartbeat 无 ID；Last-Event-ID 是 at-least-once 游标；disconnect 与 cancel 不是同一动作。

下一篇需要区分运行成功、交付质量和单次诊断。

### EVALUATION_OBSERVABILITY

**我预计本篇要解决什么：**分别验证结果、路径、预算和安全，并把评测、Trace、Runtime Journal 分开。

`make mini-deerflow-eval` 成功，真实离线轨迹是 `model → search_knowledge → model`，outcome/trajectory/budget 均通过。我能解释 Dataset/Target/Evaluator、稳定 AgentObservation、exact 与 ordered-subsequence、关键案例新失败门禁，以及唯一 trace root 的所有权。Trace 是工程诊断树，Journal 是客户端持久事件，Evaluation 是对版本化案例应用质量标准；任何一个都不能替代另外两个。

下一篇需要把所有 seam 装成研究交付闭环。

### CAPSTONE

**我预计本篇要解决什么：**装配检索、并行 specialist、草稿、审批重建、幂等发布和最终评测，而不发明第二套框架。

`make mini-deerflow-capstone` 成功：两个 specialist 完成、checkpointer 真实重开、effect count 为 1，结果/轨迹/预算通过；命令产生的演示目录已清理。主链为：Lead 检索 → Executor 并行委派 → workspace 草稿 → approval interrupt → 重开 SQLite → resume → pre-publish gate → ledger → 正式 Artifact → final evaluation。草稿正文进入 Workspace，checkpoint 只存恢复所需的小事实和引用。

下一篇需要用这套坐标在固定 commit 的 DeerFlow 真实源码中逐箭头验证。

### DEERFLOW_GUIDE

**我预计本篇要解决什么：**不用目录漫游，而从 manifest、组合根、数据边界、task 和 Gateway 四条调用链读真实工程。

课程内给出的路线、检索题和证据表足够让我知道“要找什么”。但固定 commit `4af617835805dd7cd78162ebed02fd6b782ea8bf` 的浅 fetch 两次长时间无输出，已终止；没有改读 `main`。因此我能复述路线，却不能声称已经用外部固定源码验证每个箭头。

## 工程专题后的闭卷架构图

```text
langgraph.json / CLI / Gateway
        |
        v
app.py 组合根
  settings + live dependencies
  ├─ model / summary model
  ├─ core tools + task + optional MCP/Skill tools
  ├─ SubagentExecutor + policy + DelegationLedger
  ├─ Middleware chain
  ├─ Store
  ├─ Checkpointer
  └─ SandboxProvider
        |
        v
create_lead_agent -> create_agent compiled graph
        |
        ├─ ThreadState
        |    messages / artifacts / middleware trace
        |    reducers define merge identity
        |
        ├─ RuntimeContext (per invocation)
        |    authenticated user / request / permissions / workspace handles
        |
        ├─ Store (cross-thread preferences)
        |
        └─ Runtime DB (outside Graph)
             product Thread ownership / immutable Run history / Event journal

Lead model --tool call: task--> task tool
  task tool --safe context + sandbox handle--> SubagentExecutor
  Executor --registry/policy/semaphore/timeout--> ephemeral specialist
  specialist --bounded SubagentResult/ArtifactRef--> ToolMessage --> Lead synthesis

SandboxProvider --acquire(user, thread)--> SandboxSession
  relative-path read/write -> durable workspace + bounded audit
  ArtifactRef -> Middleware validation -> ThreadState reducer

Gateway -> RunManager -> Worker -> compiled graph
  Worker -> Runtime DB Journal (event sequence)
  Journal -> SSEEncoder/StreamBridge -> id/event/data
  Last-Event-ID -> sequence > cursor replay
  Checkpointer separately owns graph resume

AgentObservation <- graph state/trace adapter
  Outcome evaluator: delivered content contract
  Trajectory evaluator: allowed/required execution path
  Budget evaluator: model/tool/token bounds
Trace: one root + child spans for diagnosis
Runtime Journal: durable client-visible product events
Evaluation store: versioned quality decisions
```

## 使用 DEERFLOW_GUIDE 证据表的最终判断

由于固定 checkout 未成功，下面把“正式课程提供的候选入口”和“我实际从固定源码核验的证据”分开。没有源码核验的格子不会伪装成完成。

| 路线 | 可执行入口 | 调用者 → 被调用者 | 经过的数据/能力 | 没有该边界时的失败 | 固定源码核验 |
|---|---|---|---|---|---|
| Lead 组合根 | `backend/langgraph.json` 的 `deerflow.agents:make_lead_agent` | manifest → `make_lead_agent/_make_lead_agent` → model/tools/middleware/prompt/state → 两处 `create_agent` | runtime config、允许工具、Middleware、ThreadState、tracing callback | 入口各自装配导致工具、Store、权限和 trace owner 漂移 | **未完成：fetch 阻塞** |
| State/Context/Middleware | `agents/thread_state.py` 与 `build_middlewares` | worker/runtime context → Lead graph → Middleware → model/tool | checkpoint State、可信 Runtime context、产品 Thread/Run record | 把用户正文中的 role 当认证事实；Secret/连接进入 checkpoint；治理顺序漂移 | **未完成：fetch 阻塞** |
| task/Subagent | `tools/builtins/task_tool.py::task` | Lead tool call → policy/config → `SubagentExecutor` → ephemeral `create_agent` → structured ToolMessage | 裁剪 Context、sandbox/thread handle、允许工具/skills、稳定终态 | 共享完整父消息、递归 task、兄弟失败抹掉成功结果、输出挤爆 Lead | **未完成：fetch 阻塞** |
| Gateway/Run/SSE | `gateway/app.py` 的 run routers | router → services → RunManager → worker → Graph + RunJournal/EventStore → StreamBridge/SSE | auth ownership、Run record、Command(resume)、RunEvent、replay cursor | 断线丢事件、resume 改写旧 Run、checkpoint 被误当产品状态、trace 被误当 SSE 日志 | **未完成：fetch 阻塞** |

判断：**我已经能沿四条路线提出正确问题和定位候选 symbol，但尚不能宣布“能阅读并以固定源码证据证明架构”，因为外部源码没有成功 checkout。**

## Blockers

### B1 — 高：第 06 章 Jupyter 异步取消实验原样不可运行

- **精确位置**：`tutorials/06_Observability_Persistence.ipynb`，实验 9“验证异步取消不会被错误 Middleware 吞掉”，调用 `asyncio.run(run_cancelled_agent())`。
- **当时已知内容**：前八个实验已经建立同步/异步工具错误边界；本实验应证明 `CancelledError` 沿 Graph 控制边界传播为 `NodeCancelledError`。
- **无法推导的跳跃**：正式材料给出预期 stdout，但在真实 Jupyter kernel 中已有事件循环，`asyncio.run()` 在进入 Agent 实验前即抛 `RuntimeError: asyncio.run() cannot be called from a running event loop`。这不是学习者代码或 Agent 语义错误。
- **做过的无答案尝试**：先用标准 nbconvert 原样执行并保留完整 traceback；再用 `--allow-errors` 继续全本，确认只有该单元直接失败，后续实验本身可运行。没有修改正式 Notebook，也没有用源码答案替代实验。
- **继续所需的最小补充**：Notebook 中改用顶层 `await run_cancelled_agent()`，或在单元前明确说明该代码必须作为普通 Python 脚本运行并提供 Jupyter 等价写法。两种做法任选其一即可。

### B2 — 严重：第 11 章核心 Subagent 后半程在 Jupyter 中系统性失败

- **精确位置**：`tutorials/11_Multi_Agent_Patterns.ipynb`：实验 10、11、12、13、17、19、20、21、22、23 的代码单元均调用 `asyncio.run(...)`；实验 24“Ledger 保存 context key、预览、长度与 digest”因前面的 demo executor 委派未执行而进一步 `IndexError: tuple index out of range`。
- **当时已知内容**：前九个实验已经建立 TaskRequest/Result、输入投影、Router/Handoff/Subgraph/Subagent-as-tool 的控制权差异。后半程本应通过真实异步实验建立 semaphore、部分失败、timeout、Lead→task→ToolMessage、Mini DeerFlow Executor 和输出预算。
- **无法推导的跳跃**：在 Notebook 自带事件循环中，第一个 `asyncio.run(run_unbounded())` 就失败；允许错误继续后共有十个直接 RuntimeError，最后 Ledger 实验又因前置状态缺失失败。学习者无法仅靠原 Notebook得到核心运行证据，也无法判断 Ledger 失败是实现问题还是前置实验没有执行。
- **做过的无答案尝试**：标准 nbconvert 原样运行；随后 `--allow-errors` 执行到末尾并逐一统计 error cell，确认十个同根错误和一个级联错误。没有编辑 Notebook 或读取测试答案。
- **继续所需的最小补充**：在 Notebook 环境统一把顶层 `asyncio.run(coro)` 改为 `await coro`，并让每个实验自己建立所需 fixture，或至少在依赖前序状态的实验前加明确前置检查。还应同步修改第 06 章和工程专题中面向 Jupyter 复制的异步示例，避免同一陷阱重复出现。

### B3 — 外部高：无法 checkout `DEERFLOW_GUIDE` 锁定 commit

- **精确位置**：`mini_deerflow/DEERFLOW_GUIDE.md` 第 1–2 节，固定提交 `4af617835805dd7cd78162ebed02fd6b782ea8bf` 的 fetch 与四条证据路线。
- **当时已知内容**：六篇 Mini DeerFlow 工程专题已经完成；我已能闭卷解释四条阅读路线和证据表需要的列。
- **无法推导的跳跃**：没有固定 checkout，就无法用 import/调用/factory 参数证明 `manifest→make_lead_agent`、State/Context/Middleware、task→Executor、Gateway→RunManager→Journal→SSE 的真实箭头；只复述指南不算源码验收。
- **做过的无答案尝试**：在空 `/tmp/deerflow-course` 初始化并按指南执行 `git fetch --depth 1 origin <commit>`；第一次与第二次都长时间无输出，超过运行时合理等待后中止。没有退回 `main`，没有使用其他 commit，也没有向主 Agent索取结论。
- **继续所需的最小补充**：恢复可用的 GitHub fetch 通道，或提供该固定 commit 的只读本地 checkout/archive。只需要源码本身，不需要解释或答案。

## 非阻塞观察

1. README 的四部递进和每章“上一刻/下一刻”非常有效；即使局部实验失败，我仍知道为什么要继续下一章。
2. 失败→修复成对实验让边界比 API 定义更容易记住，尤其是 source 丢失、并行 reducer 冲突、interrupt 前副作用和 Store 陈旧业务事实。
3. `05_Agent_Middleware.md` 实际讲 Context Engineering、`06_Observability_Persistence.md` 实际讲 Middleware，文件名保留旧主题痕迹；README 链接和正文标题足以导航，因此不构成 blocker，但初学者在书签或搜索结果中可能短暂困惑。
4. Sandbox 和 Capstone 正文也给出含 `asyncio.run(...)` 的“可运行实验”。作为 `.py` 脚本它们成立；若课程期望学习者继续在 Jupyter 复制执行，应明确改用顶层 await 或标注运行介质。
5. `make mini-deerflow`、`make mini-deerflow-eval`、`make mini-deerflow-capstone` 都走真实框架边界而非字符串假演示，这对理解组合关系很有帮助。

## 按学习顺序排序的最小修复清单

1. 修正第 06 章 Notebook 的 `asyncio.run` 单元，给出 Jupyter 原生顶层 `await` 版本。
2. 统一修正第 11 章十个异步单元；确保最后 Ledger 实验在前置失败时不会以无关 `IndexError` 掩盖根因。
3. 检查工程专题中标为可运行、且预期在 Jupyter 复制的异步代码，统一标注“脚本运行”或提供 Notebook 版本。
4. 为 `DEERFLOW_GUIDE` 提供固定 commit 的可访问 checkout/archive，之后按证据表完成四条源码路线复核；不要用 `main` 代替。

完成 1–3 后，课程本地学习链有条件判 PASS；完成 4 后，才能对最终 DeerFlow 固定源码阅读路线判 PASS。

---

## 后续 Spec 审查补充（不改写首轮历史）

本节是首轮报告提交后的补充证据。上面的首轮结论、Blocker 编号和 **BLOCKED** 判断保持原样；下面的实验不是首轮已经完成却漏写的内容，也不表示 Notebook 问题已经修复。

补充方法：从 01–11 每章各选择一个正文中的“动手修改”，在独立临时代码 `/tmp/beginner-audit-1-hands-on.py` 中做最小变体，并使用仓库环境运行。没有修改正式 Markdown、Notebook 或 Python 源码。

## 01–11 “动手修改”补充实验

### 第 01 章：去掉 `StrOutputParser`

- **正文实验**：Runnable 管道后的“去掉 `StrOutputParser()`，预测返回类型”。
- **最小修改**：把 `prompt | model | StrOutputParser()` 改为 `prompt | model`。
- **运行前预测**：结果不再是 `str`，而是保留角色和 metadata 的 `AIMessage`；模型不能跳过 prompt。
- **实际输出**：

  ```text
  result_type = AIMessage
  result_content = 保留消息元数据
  ```

- **边界解释**：Parser 是应用固定管道的一步。去掉它改变下游数据形状，不改变模型步骤或 Runnable 顺序；需要读取 `tool_calls`、usage 或其他消息字段时，应保留完整 Message。

### 第 02 章：把整数改成不可转换字符串

- **正文实验**：`ResearchRequest` 后的“把 `max_sources` 改成无法转换的字符串”。
- **最小修改**：`max_sources="many"`。
- **运行前预测**：Pydantic 不会把任意英文转成整数，会在 `max_sources` 字段报 `int_parsing`，不会等到 Graph 节点才失败。
- **实际输出**：

  ```text
  invalid_field = ('max_sources',)
  error_type = int_parsing
  ```

- **边界解释**：Schema 边界负责候选数据的确定性类型转换；“字符串可转整数”和“任意字符串可接受”是两件事。错误位置可以被 API/Graph 稳定消费。

### 第 03 章：交换零分文档顺序

- **正文实验**：强制最近邻失败后的“交换两个文档的顺序”。
- **最小修改**：知识列表由 `persistence, middleware` 反转为 `middleware, persistence`，查询仍为与两者都无词项重叠的 `quantum gravity`。
- **运行前预测**：两个文档分数都为 0；`max()` 会选择列表中先出现的文档，因此所谓“证据”会随存储顺序改变。
- **实际输出**：

  ```text
  before_swap = ('persistence', 0)
  after_swap = ('middleware', 0)
  ```

- **边界解释**：最近不等于相关。Prompt 无法修复 Retriever 把零分候选包装成证据的问题；召回边界必须允许显式空结果。

### 第 04 章：让第二条 AIMessage 再调用一次工具

- **正文实验**：首次完整 `create_agent` 循环后的“让第二条 AIMessage 继续调用同一工具，再准备第三条最终回答”。
- **最小修改**：scripted model 从“一次 tool call + final”改为“两次 tool call + final”。
- **运行前预测**：消息序列为 Human、AI、Tool、AI、Tool、AI；模型调用三次，工具执行两次，第三条无 tool call 的 AIMessage 才终止。
- **实际输出**：

  ```text
  message_types = ['HumanMessage', 'AIMessage', 'ToolMessage', 'AIMessage', 'ToolMessage', 'AIMessage']
  tool_message_count = 2
  final = 两轮检索完成
  ```

- **边界解释**：`create_agent` 不是固定只跑一个工具回合；循环终止取决于模型最终不再产生 tool call。每次结果仍必须用各自 call ID 配对。

### 第 05 章：两个调用复用同一 `thread_id`

- **正文实验**：偏好放进 Thread State 失败后的“把两个 config 改成相同 `thread_id`”。
- **最小修改**：保存偏好和随后读取都使用 `same-thread`；第二次输入不再提交 `language`。
- **运行前预测**：第二次调用会从同一 checkpoint 继承 `zh-CN`，所以看起来实现了记忆；但这只是同一 thread 的延续，不是跨 thread 用户偏好。
- **实际输出**：

  ```text
  first_observed = zh-CN
  second_observed = zh-CN
  ```

- **边界解释**：复用 thread 能恢复该线程 State，却不能满足“新会话仍记住用户偏好”。用同一 thread 冒充 Store 会破坏会话隔离和产品 thread 语义。

### 第 06 章：给 Runnable listener 增加 `on_end`

- **正文实验**：正确 listener 实验后的“增加 `on_end` 并记录顺序”。
- **最小修改**：在 `with_listeners` 中同时注册 `on_start`、`on_end`，业务函数在中间追加 `business`。
- **运行前预测**：顺序为 start → business → end，结果仍为 2。
- **实际输出**：

  ```text
  business_result = 2
  event_order = ['start:RunnableLambda', 'business', 'end:RunnableLambda']
  ```

- **边界解释**：listener 包围任意 Runnable 的局部运行，适合计时和日志；它没有 Agent Runtime Context，也不能取代 `before_model/after_model` 的治理职责。

### 第 07 章：给 Reducer 初始值加入 cached result

- **正文实验**：`operator.add` 并行修复后的“把初始 results 改成 `['cached:checkpoint']`”。
- **最小修改**：初始 State 包含一条 cached 结果，两个并行节点仍分别提交 docs/web patch。
- **运行前预测**：Reducer 会把输入 channel 与两个新 patch 一起合并，最终长度为 3。
- **实际输出**：

  ```text
  result_count = 3
  results = ['cached:checkpoint', 'docs:checkpoint', 'web:checkpoint']
  ```

- **边界解释**：Reducer 不只处理两个并行节点之间的冲突，也定义已有 State 与新更新的合并。若 cached 项需要去重，`operator.add` 就不再是正确领域规则。

### 第 08 章：加入最大修订次数

- **正文实验**：可进展循环后的“加入 `max_revisions=1`，未达标以 `needs_review` 结束”。
- **最小修改**：review 始终给 0 分；router 在修订次数达到 1 时进入 `needs_review` 节点，而非继续循环。
- **运行前预测**：轨迹是 review:0 → revise:1 → review:0 → needs_review；结果是正常业务终态，不触发 recursion error。
- **实际输出**：

  ```text
  status = needs_review
  revision_count = 1
  trace = ['review:0', 'revise:1', 'review:0', 'needs_review']
  ```

- **边界解释**：循环要同时拥有进度、质量条件和预算耗尽后的可解释出口。recursion limit 仍保留为拓扑错误保险丝，但不应充当产品终态。

### 第 09 章：重启时换另一个 SQLite 文件

- **正文实验**：SQLite 重开修复后的“使用另一个 SQLite 文件路径重启”。
- **最小修改**：第一轮写 `first.sqlite`，第二个 saver 连接空的 `other.sqlite`，thread ID 保持 `same-id`。
- **运行前预测**：新后端没有该 checkpoint，`values` 为空；相同 thread ID 本身不能跨错误数据库恢复。
- **实际输出**：

  ```text
  recovered_values = {}
  same_thread_id_was_enough = False
  ```

- **边界解释**：恢复地址由 thread identity 和持久后端共同决定。“换 thread”和“换数据库”都会表现为找不到旧 State，但前者是 lineage 选择，后者是数据源选择，诊断层次不同。

### 第 10 章：审批选择 reject

- **正文实验**：把副作用移到 interrupt 后的修复实验中的“reject 后确认 external effects 为空”。
- **最小修改**：同一安全图第一次 interrupt，随后以 `Command(resume="reject")` 恢复。
- **运行前预测**：进入 reject 终态，不可达 publish 节点，外部副作用列表长度为 0。
- **实际输出**：

  ```text
  status = rejected
  effects = []
  ```

- **边界解释**：reject 是正常业务终态而不是异常。把 publish 放在 interrupt 后的独立节点，使拒绝路径从拓扑上不触发副作用；批准路径仍需要幂等 ledger 防重放。

### 第 11 章：把 Semaphore 容量改为 1 和 4

- **正文实验**：并发限制修复后的“把容量改为 1 和 4，分别观察峰值”。
- **最小修改**：同一批四个 coroutine 分别经容量 1、容量 4 的 Semaphore 执行。该变体在独立 `/tmp` Python 脚本中运行，不把脚本成功伪装成正式 Jupyter 已修复。
- **运行前预测**：容量 1 时真实峰值为 1；容量 4 时峰值为 4；`asyncio.gather` 仍按输入顺序返回结果。
- **实际输出**：

  ```text
  capacity_1_peak = 1
  capacity_4_peak = 4
  capacity_1_order = ['done:0', 'done:1', 'done:2', 'done:3']
  capacity_4_order = ['done:0', 'done:1', 'done:2', 'done:3']
  ```

- **边界解释**：Semaphore 控制执行入口的同时运行数，`gather` 的返回顺序不代表完成顺序。它仍不限制队列长度、租户总量、CPU/进程或外部副作用。

## 首轮发现的四类归档

这是对首轮已记录事实的重新归类，不把上面的后续动手实验倒填成首轮证据。一个问题若同时影响多个维度，下面指定主要类别，并在说明中标出次生影响。

### 1. 阻断理解：2 项

1. **B1，第 06 章异步取消实验不能在正式 Jupyter 原样运行。** 它阻断“取消是否越过普通工具错误 middleware”的直接运行证据；虽然前后文字足以继续阅读，但初学者只能猜预期 stdout 是否真实。
2. **B2，第 11 章十个异步单元直接失败。** 它覆盖并发、timeout、部分失败、Lead→task、Executor、输出预算等本章核心后半程，因此是实际的概念验收阻断，而不只是排版问题。

依据：两项都满足首轮约定的 blocker 标准——正式代码无法运行，学习者不能仅靠课程自身完成预期实验。B3 属外部环境问题，按要求不计入本类。

### 2. 造成错误心智模型：0 项

首轮没有发现正式材料在概念上互相矛盾，或会稳定诱导出错误架构结论的内容。相反，以下关键区别在正文和可运行实验中保持一致：`bind_tools` 不执行工具、Checkpointer 不等于 Store、Subgraph 不等于 Subagent、interrupt resume 会重入节点、Runtime Journal 不等于 Trace/Evaluation。

第 06/11 章的 `asyncio.run` 是运行介质错误，会让实验失败，但其预期概念结论本身没有被相反输出“验证”；因此不把它升级为错误心智模型。

### 3. 练习反馈不足：1 项

1. **第 11 章实验 24 的级联 `IndexError` 掩盖前置失败。** 在 `--allow-errors` 继续运行时，前面的 demo 委派没有成功，`ledger_records[-1]` 只给出 `tuple index out of range`，没有指出“前置异步实验未完成/ledger 为空”。这会让初学者误查 Ledger，而不是定位首个事件循环错误。

依据：这不是新的独立实现缺陷，而是 B2 的次生反馈问题；归档数量按一个反馈链计算。其最小改进是让实验自建 fixture，或在读取最后一项前断言非空并给出明确前置提示。

### 4. 一般编辑建议：2 项

1. **文件名与正文主题有旧命名痕迹。** `05_Agent_Middleware.md` 的正文是 Context Engineering，`06_Observability_Persistence.md` 的正文是 Agent Middleware。README 和 H1 足以导航，所以不阻断，但搜索、书签和报错路径会增加一次认知切换。
2. **工程专题的异步示例应标注运行介质。** `SANDBOX_EXTENSIONS.md`、`CAPSTONE.md` 等正文含 `asyncio.run(...)` 的可运行代码。作为 `.py` 脚本正确，复制到 Jupyter 会复现同类错误。建议明确标注“保存为脚本运行”，或并列给出 Notebook 顶层 `await` 版本。

依据：这两项不迫使学习者猜核心架构，也不在所有正式路径上导致失败，因此保持为编辑建议，而不是 blocker。

## 外部环境问题：1 项

1. **B3，固定 DeerFlow commit 无法 fetch。** 两次固定 SHA 的浅 fetch 长时间无输出并被中止，导致四条外部源码路线不能完成固定版本证据复核。课程正确要求不要退回 `main`；因此这项只影响最终外部验收，不反证课程内 Mini DeerFlow 的概念链。

所需条件仍是首轮所列的最小项：可访问的 GitHub fetch 通道，或该固定 commit 的只读本地 checkout/archive。

## 补充实验对首轮结论的影响

11 个“动手修改”变体都得到与正文边界一致的输出，说明首轮对 01–11 概念链的理解可以由独立实验支持；特别是第 11 章 Semaphore 变体在普通 Python 脚本中成功，进一步把“异步概念/实现本身”与“正式 Jupyter 调用方式”区分开。

这不改变 **BLOCKED**：正式第 06/11 Notebook 仍未被修改，固定 DeerFlow commit 仍未取得。补充证据只补足书面验收，不把后续临时变体冒充正式课程已经可运行。
