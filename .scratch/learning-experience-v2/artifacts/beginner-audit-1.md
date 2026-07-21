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
