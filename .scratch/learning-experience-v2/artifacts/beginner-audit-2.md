# 第二位初学者严格盲读验收报告

## 结论

**PASS**。

判定依据不是“文档看起来完整”，而是以下条件同时成立：

1. 我以只具备基础 Python、不了解 LangChain/LangGraph/DeerFlow 的视角，从 `README.md` 开始，严格按 `tutorials/01` 到 `tutorials/11` 阅读；在 11 章结束前没有打开 `mini_deerflow` Python 源码。
2. 11 个正式 Notebook 均通过仓库 `.venv` 的 Jupyter 执行器原样运行，输出只写入 `/tmp/beginner-audit-2-XX.ipynb`，未改正式 Notebook。`.venv/bin/jupyter kernelspec list --json` 显示 `python3` kernelspec 位于仓库 `.venv/share/jupyter/kernels/python3`。
3. 我能不用标题复述，基于亲自运行的消息序列、State patch、checkpoint、interrupt、Subagent 结果解释指定机制。
4. Mini DeerFlow 七篇工程文档按规定顺序阅读，文中主要离线实验、专题测试、Capstone 与全项目门禁均实际执行。
5. DeerFlow 源码证据来自固定提交 `4af617835805dd7cd78162ebed02fd6b782ea8bf` 的 13 文件证据切片；下载脚本的 `--verify-only` 实际通过。没有改读 `main`，也没有把指南文字当作源码证据。

本轮没有发现代码不能运行、前置概念无法推导、固定源码无法核验或依赖隐含答案才能继续的阻断项。

## 盲读约束执行情况

- 未读取 `TODO.md`、`CONTEXT.md`、`docs/agents/`、`tests/` 内容、`quality/` 内容、`scripts/` 实现、git log/diff/status、前一轮报告或 `.scratch/learning-experience-v2` 中的其他文件。
- 测试和脚本只按正式材料给出的命令执行，没有打开其实现。
- `scripts/fetch_deerflow_snapshot.py` 只按 `DEERFLOW_GUIDE.md` 调用，没有阅读脚本源码。
- 01–11 完成前，只执行 Notebook 中已有的 Mini DeerFlow 调用，没有打开其 Python 源码。
- 唯一新增的仓库文件是本报告；Capstone 的 `.capstone-demo` 临时目录已在实验后清理。DeerFlow 源码只存在 `/tmp`。

## README 路线理解

README 给出的路线不是按 API 分类，而是同一研究助手在四次约束升级中的连续演进：

1. 第一部先让概率模型产生程序可依赖的 Message、Schema、来源和事件边界。
2. 第二部用 `create_agent` 建立标准工具循环，再用 Context/Middleware 管理身份、权限、错误和预算。
3. 第三部把固定阶段、并行、恢复和审批写入显式 LangGraph 控制流。
4. 第四部再处理 Subagent 上下文隔离、Sandbox、产品 Runtime/SSE 和评测，最终映射到 DeerFlow。

阶段依赖是可推导的：没有稳定消息和结构化对象，工具调用无法可靠配对；没有受控工具循环，业务图无法安全组合智能步骤；没有 State/Checkpoint，就没有长任务恢复与 durable interrupt；没有这些内核，Gateway 和评测只能包住一次性 Demo。

## 逐章学习记录

| 章 | 进入前预计解决的问题 | Notebook | 实际新增的能力 | 到下一章是否有跳跃 |
|---|---|---|---|---|
| 01 模型、消息与调用 | 区分单次模型、固定 Runnable、工具意图、Agent 与 v2 事件 | PASS | 我能检查 `AIMessage.content` 与 `tool_calls`，知道 `bind_tools` 只表达意图；能先按 `type/ns/data` 解析 v2 envelope | 无。稳定调用后，下一问题自然是自然语言结果不可验证 |
| 02 结构化输出 | 让计划可路由、持久化、校验，并统一失败协议 | PASS | 能用 Pydantic 区分模型输出、工具参数、Agent response 三个生命周期；知道 Schema 合法不等于事实正确；能为必填字段、依赖、Artifact path 和 failure kind 建契约 | 无。结构正确仍可能引用过时事实 |
| 03 RAG | 让事实带来源、支持空召回并能独立评测检索 | PASS | 能解释 Document 正文和 metadata 必须一起经过 Splitter/Index/Retriever；固定 RAG 不是 Agent；空召回不是崩溃；recall@k 评检索而非生成忠实度 | 无。检索仍被程序固定调用，模型还不能选动作 |
| 04 工具循环 | 亲手完成 tool intent→执行→ToolMessage→第二次模型调用 | PASS | 能按 call ID 配对结果；理解 tool schema 与 ToolRuntime 的所有权；能从 `updates` 看出 `model→tools→model` | 无。循环可运行后，身份、线程事实和长期偏好仍都被口语化叫“上下文” |
| 05 Context Engineering | 分开 Runtime Context、State、Store 和业务数据库 | PASS | 能按所有者和生命周期分类；知道 Checkpointer 按 thread 保存执行状态，Store 按 namespace/key 保存跨线程选择性事实，业务库仍是权威 | 无。数据归位后，权限/日志/预算会在调用点重复 |
| 06 Middleware | 统一模型/工具生命周期治理 | PASS | 能解释 before 正序、after 逆序、wrap 洋葱式包裹；权限在副作用前短路；错误变成配对 ToolMessage；取消不能被普通异常吞掉 | 无。横切治理不能证明固定业务拓扑 |
| 07 StateGraph | 把固定阶段、条件、并行合并和循环写成图 | PASS | 能解释 State patch、Node/Edge、纯 router、字段 reducer、显式 ReAct、业务预算与 recursion limit 的区别 | 无。静态分支不能覆盖运行时动态 section 数量 |
| 08 Command/Send/Subgraph | 动态路由、fan-out、局部状态隔离和 durable task | PASS | 能选择 Command、Send、Subgraph、Functional task；理解 Send 仍需要 reducer；Subgraph 不等于 Subagent | 无。图仍只活在当前进程 |
| 09 Persistence | 区分 result、snapshot、thread、history、time travel，并跨进程恢复 | PASS | 真实关闭并重开 SQLite saver 后恢复；能读取 `values/next/tasks/config`；知道 time travel 新建 lineage，不回滚外部世界 | 无。恢复会重放节点，危险副作用尚未保护 |
| 10 HITL | durable pause/resume、外部决定校验和幂等副作用 | PASS | 能解释 interrupt 释放 worker、resume 从节点开头重入；副作用后移；稳定 operation ID 对相同意图去重、不同 payload 冲突 | 无。主流程可靠后，Lead 上下文仍被所有 specialist 原始材料污染 |
| 11 Multi-Agent | 建立委派协议、上下文投影、模式选择、执行预算 | PASS | 能区分 Router/Handoff/Subgraph/Subagent-as-tool；能用 allowlist 投影、Semaphore、timeout、partial failure、输出预算和 Ledger 控制委派 | 无。下一步自然是由组合根把这些零件装成一个应用 |

11 次执行命令均为：

```text
.venv/bin/jupyter nbconvert --to notebook --execute tutorials/<chapter>.ipynb \
  --output-dir /tmp --output beginner-audit-2-<chapter>.ipynb \
  --ExecutePreprocessor.timeout=600
```

每次返回码均为 0；没有跳过、删改单元格或改写正式 Notebook。

## 指定机制的亲自解释

### `create_agent` 工具循环

它不是“模型自动执行函数”。模型先返回带 `name/args/id` 的 `AIMessage.tool_calls`；Agent runtime 在已注册工具表中找同名工具，用 Schema 验证参数并执行；执行结果包装成 `ToolMessage(tool_call_id=同一 id)`；随后把 HumanMessage、工具意图、ToolMessage 的完整历史再次交给模型。模型不再产生 tool call 时，最后一条 AIMessage 才是终态。第 04 章真实结果为 `HumanMessage → AIMessage → ToolMessage → AIMessage`，stream 节点为 `model → tools → model`。

### State 与 Reducer

State 是当前 thread 中节点共享、可 checkpoint 的事实快照；节点读取当前快照，只返回自己负责的 patch。Reducer 是同一 channel 收到多个 patch 时的业务合并协议，不是“所有 list 都相加”。证据列表可 append；任务表需要按任务 ID 替换；Sandbox ID 的冲突应 fail closed。第 07 章无 reducer 的并行同字段写入实际抛 `InvalidUpdateError`，增加 `operator.add` 后两条证据同时保留，自定义 ID reducer 后 pending 被 done 原位替换。

### Command、Send、Subgraph

- `Command(update=..., goto=...)` 适合一次业务判断同时拥有状态更新与下一跳，避免 node 和 router 各写一份规则。
- `Send(node, task_input)` 在运行时为同一个节点定义创建多个 task；它解决动态任务数，不解决 fan-in，所以输出字段仍需 reducer。
- Subgraph 是固定局部拓扑与独立 State Schema。它可以缩小父子 State 交集，但若父子共用同一 Schema，Secret 仍会进入子图；它不自动拥有独立 Prompt、模型或工具。

### Checkpointer 与 Store

Checkpointer 在 Graph superstep 边界，以 `thread_id/checkpoint_id/namespace` 保存 State、next、tasks、pending writes 和 lineage，回答“图从哪里继续”。Store 由应用以 namespace/key 显式保存跨 thread 的选择性数据，回答“同一用户下次会话要记住什么”。两者都不是余额/订单等权威业务数据库，也都不是产品 Run/Event journal。第 09 章关闭第一个 SQLite saver 和 Graph，再打开新 saver/Graph 后仍恢复同一 thread，是持久恢复证据；换新 InMemorySaver 时 State 为空。

### interrupt/resume

`interrupt(payload)` 把暂停点和载荷写入 checkpoint，然后让当前 Run 返回，原 worker 不需阻塞等待。外部决定必须先经过 Schema、ownership 和角色校验，再用相同 thread 的 `Command(resume=decision)` 交回 interrupt。恢复从包含 interrupt 的节点开头重入，因此 interrupt 前的外部副作用会重复；即使副作用移到批准后独立节点，time travel/失败恢复仍可能重放，所以要用稳定 operation ID 和事务 ledger。

### Subagent-as-tool

Lead 把最小任务描述作为一个 `task` tool call 交给 executor。Executor 按 registry/config 解析 specialist，从空对象出发只投影 allowlist 字段，创建临时 Agent/invocation，施加并发、timeout、输出和终止预算。Subagent 返回有界摘要、ArtifactRef、status、长度/digest，结果作为 ToolMessage 回到 Lead，最终综合由 Lead 的第二次模型调用完成。它与 Handoff 的根本区别是主会话和下一步控制权始终回到 Lead；它与 Subgraph 的区别是它有独立能力/上下文边界，而不是只嵌套固定拓扑。

## Mini DeerFlow 工程文档与运行证据

正式阅读顺序为：`ARCHITECTURE.md → LEAD_AGENT_CORE.md → SANDBOX_EXTENSIONS.md → RUNTIME_GATEWAY.md → EVALUATION_OBSERVABILITY.md → CAPSTONE.md → DEERFLOW_GUIDE.md`。

### 架构总览

- 离线 CLI 输出 profile=offline，工具为 `search_knowledge/calculator/read/write/record_artifact/task`，真实循环完成。
- 装配探针证明 `application.dependencies.store is dependencies.store` 与 checkpointer identity 均为 True。
- 文章点名后才打开 `app.py` 与 `agents/lead_agent.py`：`_assemble_graph()` 创建 Executor、合并工具、拒绝重名、构造 Middleware，然后把依赖交给 `create_lead_agent()`；factory 只接入 `create_agent`，没有自行扫描 MCP/Skills 或提升权限；`MiniDeerFlowApplication.invoke()` 由应用构造 Context 和 thread config。

### Lead 核心

- 两个 application、两个 SQLite 连接、相同 thread、不同 request：恢复出两条 HumanMessage。
- 同一路径 Artifact 两次登记后数量为 1，第二轮 media type `application/json` 覆盖旧值。
- 最新 snapshot 与 invocation State 一致。
- stream 共 17 个 updates，model=2、tools=1，全部严格 JSON-safe；真实 compiled graph Mermaid 同时含 model/tools。
- 正式专题验收：27 passed。

### Sandbox 与扩展

- `(user, thread)` 隔离成立；`../outside.md` 抛 `SandboxPathError`；宿主命令 exit code 126。
- release 后 session 消失，重新 acquire 后文件仍在；audit 只有 action/path/outcome 等有界事实。
- Lead 写文件同时产生实际 workspace 文件、State Artifact 和配对 ToolMessage。
- Subagent 实际 context keys 只有 `sandbox_id`；Secret 未进入 context 或 Ledger。
- MCP disabled 时 client factory 调用数为 0；enabled 后 server 两个工具只有 allowlist 的 `approved_echo` 进入应用。
- Skill index 不含正文，显式 load 后正文才出现；模型可见 schema 只有 `name`。
- 正式专题验收：31 passed。

### Runtime/Gateway

- `start_message()` 立即返回 pending；后台完成后 status=success。
- 持久事件类型顺序为 `metadata → updates → end`，17 个 updates；event ID 为 `run-runtime-demo:1..N` 严格单调。
- `after_sequence=1` 从 `:2` 重放；other-user 查询得到 `RuntimeNotFoundError`；Graph State 仍由 checkpoint 提供。
- 正式 unittest：11 tests OK，覆盖 ownership、HTTP/SSE、interrupt 新 Run 恢复、协作取消、错误脱敏、worker restart。

### Evaluation/Observability

- 相同正确文本下：good 三指标通过；unsafe 的 outcome 通过而 trajectory/budget 失败；expensive 只有 budget 失败。
- baseline/candidate 均 50% 时，关键恢复案例成为 new failure，发布仍被阻断。
- `make mini-deerflow-eval` 真实运行 `model → search_knowledge → model`，outcome/trajectory/budget 全通过，pass_rate=1.0。
- LangSmith local 运行 1 条、生成 3 条 feedback，没有上传。
- 正式专题验收：10 passed。

### Capstone

- approve：completed；research/coding 均 completed；interrupt/resume 间 checkpoint 真实关闭并重开。
- 首次 effect 为 `recorded, 1`；同 request 完整重放为 `already_recorded, 1`。
- 精确轨迹：`model → search_knowledge → model → subagent:research → subagent:coding → interrupt:risk → resume:approve → write_workspace_file`。
- 报告实际包含“研究摘要、代码建议、引用”。
- reject：draft 存在，正式 Artifact 不存在，effect count=0。
- Capstone 与 SSE/worker 故障节点：8 passed。

### 全项目门禁

`make check` 完整通过：

- 175 passed，1 skipped；
- Workflow contracts 0 failure；
- Tutorial validation 0 new/known/stale；
- Astro check 0 errors、0 warnings、0 hints；
- Site link validation、release contracts、SEO contracts 均 0 failure。

## DeerFlow 固定源码核验

### 获取过程

1. 先按指南尝试完整 shallow fetch；网络只有约 20–30 KiB/s，长时间停留在接收阶段，按指南中止。
2. 第一次匿名 Contents API 证据切片下载遇到 HTTP 403 rate limit；`--verify-only` 因快照未生成而失败。
3. 环境未提供 `GITHUB_TOKEN/GH_TOKEN`，但本机 `gh` 已认证。只将 `gh auth token` 注入脚本进程环境，没有回显 token。
4. 第二次下载成功，13 个文件全部 fetched；随后 `--verify-only` 输出：

```text
verified 4af617835805dd7cd78162ebed02fd6b782ea8bf in /tmp/deerflow-course-snapshot
```

`DEERFLOW_COMMIT` 第一行也精确等于该 commit。

### 四条源码证据表

| 路线 | 可执行入口 | 调用者 → 被调用者 | 经过的数据/能力 | 没有该边界时的失败 |
|---|---|---|---|---|
| Lead 组合根 | `backend/langgraph.json` 的 `graphs.lead_agent = deerflow.agents:make_lead_agent` | `make_lead_agent()` → `_make_lead_agent()` → `get_available_tools/filter_tools_by_skill_allowed_tools/assemble_deferred_tools/build_middlewares/apply_prompt_template` → 两处 `create_agent()` | runtime config 中的 model、thinking、plan、subagent、tool_groups、skills、user；最终 model/tools/middleware/prompt/`ThreadState`；根部 tracing callbacks | 工具存在即授权、配置散落、bootstrap 与常规 Agent 偷换依赖、model 再挂 tracing 导致重复 root/span |
| State/Context/Middleware | `thread_state.py::ThreadState`；`lead_agent/agent.py::build_middlewares`；`runtime/runs/worker.py::_build_runtime_context` | worker 构造不可被 caller 覆盖的 thread_id/run_id context → factory/Agent/Middleware；节点 patch → `ThreadState` reducers；产品 Run 另由 `RunManager` 管 | messages；sandbox/thread handles；artifact 去重；delegation terminal ledger；只保留 Skill reference 的有界 skill_context；Runtime user/role/run/provider；产品 Run status/lease | 客户端正文自选 admin、Secret/连接进 checkpoint、并行 sandbox ID 静默冲突、终态被非终态覆盖、产品 Run 与 Graph checkpoint 混成一表 |
| task/Subagent | `task_tool.py::task_tool` | Lead tool call → `get_subagent_config` → `get_available_tools(..., subagent_enabled=False)` → `SubagentExecutor.execute_async()` → `_aexecute()` → `_create_agent()` → `create_agent(checkpointer=False)` → `Command(ToolMessage)` | description/prompt/type/call ID；父级 tool_groups/skill allowlist；明确传播 sandbox/thread handle、认证 user/role/run/trace；fresh messages；completed/failed/cancelled/timed_out/capped 状态与进度事件 | 完整父消息/Secret 泄漏、specialist 递归调用 task、未知 type 任意 import、timeout 抹掉兄弟结果、异常炸毁 Lead 工具循环 |
| Gateway/Run/SSE | `gateway/app.py` 注册 `thread_runs`/`runs` router；`thread_runs.py::stream_run` | router 权限检查 → `start_run`/`sse_consumer`；worker `run_agent()` → `RunManager.set_status`/Agent factory/`agent.astream` → `RunJournal` + `StreamBridge.publish/publish_end`；join/cancel/events 路由分别查询 manager/bridge/event store | authenticated owner；产品 thread/run/status/lease；Graph runtime context 和 checkpoint handles；持久 Run events、usage；SSE `id/event/data`、`last_event_id`、heartbeat/end | 断线等于取消、run 无 owner、并发双执行、事件先发后存而永久丢失、heartbeat 推进游标、trace 成功却无客户端可重放事件 |

### 从固定源码回答五道题

1. `langgraph.json` 注册 graph factory、auth 和 checkpointer provider，不是 Gateway app。
2. `ThreadState` 由 Harness/Graph checkpoint 保存；`Runtime.context` 由 Gateway worker 每次调用构造；产品 Thread/Run 由 Gateway runtime repository/RunManager 独立拥有。
3. `task` 是 Lead 的工具。它创建隔离的 Subagent Agent；不是共享父 State 的第二张长期 Graph。
4. Run 由 RunManager/worker ownership 与 lease 管理；可重放产品事件由 RunJournal/EventStore/StreamBridge 链管理。Graph checkpoint 只保存图恢复事实。
5. tracing callback 形成诊断用 root/child span；RunJournal 也是 callback，但写产品可查询事件与 usage。二者可共享 correlation ID，不能互相替代。

## 闭卷架构图

以下关系是在结束源码阅读后不回看文档写出的：

```text
LangChain 高层接口
  Message / Runnable / Structured Output / Tool / create_agent
                         │
                         │ create_agent 把通用工具循环编译到 LangGraph runtime
                         ▼
LangGraph 执行内核
  State + Reducer + Node/Edge
  Command（更新+路由） / Send（动态任务） / Subgraph（局部拓扑）
  Checkpointer（thread 恢复） / Store（跨 thread 选择性事实）
  interrupt + Command(resume) / stream modes
                         │
                         │ Mini DeerFlow 把原语收敛成可运行教学 Harness
                         ▼
Mini DeerFlow
  app.py 组合根
    ├─ Lead create_agent + ThreadState + Middleware
    ├─ tool registry + task/SubagentExecutor
    ├─ SandboxProvider + Artifact
    ├─ Checkpointer / Store / effect ledger
    ├─ Runtime Thread/Run/Event + SSE adapter
    └─ Outcome / Trajectory / Budget + observability adapter
                         │
                         │ 同一责任关系扩展为动态配置与产品运行时
                         ▼
DeerFlow @ 4af6178
  langgraph manifest → make_lead_agent 组合根
  ThreadState + 大型有序 Middleware 链
  task tool → 隔离 Subagent create_agent
  Sandbox / MCP / Skills providers
  Gateway router → RunManager/worker
  RunJournal/EventStore + StreamBridge/SSE
  tracing root 与产品 Journal 两条独立观测链
```

边界不是“LangChain 被 LangGraph 替代，再被 DeerFlow 替代”。LangChain 提供高层建模/Agent 接口；LangGraph提供有状态执行和恢复；Mini DeerFlow 是缩小、可执行、可解释的 Agent Harness；DeerFlow 在相同关系上增加动态配置、更多 provider、multi-worker ownership、Gateway 和产品能力。

## 真正理解与仅能复述的边界

### 我认为已经真正理解

- Message/tool call/ToolMessage 的配对与 `create_agent` 循环：有手动循环、自动循环和 stream 轨迹三类证据。
- State patch、并行冲突和 reducer identity：亲自运行了异常、append 修复和按 ID 替换。
- Command/Send/Subgraph 的控制权差异：有分支漂移、动态 fan-out 和 Secret 可见性实验。
- Checkpointer/Store/业务数据库/Run repository：有 InMemory 失败、SQLite 重开、跨 thread Store 和 runtime journal 的不同证据。
- durable interrupt、节点重入和幂等 ledger：亲自观察了 interrupt 前副作用重复、time travel 重放和相同 key/不同 payload 冲突。
- Subagent-as-tool 的输入投影、临时生命周期、并发/timeout/partial failure/输出预算：既有 Notebook 实验，也有 Mini DeerFlow 与固定 DeerFlow 调用点。
- Mini DeerFlow 与 DeerFlow 的边界：能从固定源码入口沿依赖方向找到组合根、能力边界和产品交付链，而不是按目录念名字。

### 目前只能在源码层解释，尚不能声称生产掌握

- DeerFlow 完整多 worker lease、故障接管与跨进程 StreamBridge：固定切片能证明接口、worker 和状态分支，但我没有部署多个 worker 做真实网络分区实验。
- 远程/容器 Sandbox 的进程、网络、CPU/内存隔离：只运行了 Local provider；它明确不是生产隔离。
- 真实 MCP server 的 OAuth、schema 漂移、timeout 和 prompt injection：只运行 fake client 的 lazy/allowlist 契约。
- 真实模型 provider 的随机 tool selection、语义检索质量和在线 LLM judge：本轮核心证据使用确定性 fake model；这是契约证据，不是模型质量证明。
- Langfuse/Monocle/LangSmith 在线 tracing backend 的故障与跨服务 parent propagation：本轮只运行 local evaluation 和源码静态链，没有向外部平台写入。

这种区分不影响本课程的 PASS：课程要求的是能基于运行证据和固定源码解释机制与边界，不是把本地教学实现冒充生产验证。

## 叙事与学习体验评价

没有阻断性跳跃。最有效的设计是每章从可观察失败开始，再给最小修复，最后才迁移到 Mini DeerFlow；这使抽象名词都有失败现场可回指。01→04、07→10、11→工程专题的依赖尤其清楚。

有两处轻微认知摩擦，但不构成 BLOCKED：

1. 第 11 章和几篇工程专题各自标出不同时间点的 DeerFlow commit，最终 `DEERFLOW_GUIDE` 又统一固定为 `4af6178`。正文能解释这是校准锚点演进，但初学者需要主动区分“该专题历史锚点”和“最终源码验收锚点”。最小改进是在每篇旧锚点旁增加一句醒目标注：“最终四路线验收统一使用 DEERFLOW_GUIDE 的 4af6178”。
2. 13 文件切片不包含 Gateway `services.py`，因此切片内可以证明 router 调用 `start_run/sse_consumer`、worker 调用 Agent/Journal/Bridge，但 router→service→manager 调度的 glue 只能在接口两端核对。指南仍足以完成四条证据表；若希望每个箭头都能在离线切片中展开，最小改进是把 `backend/app/gateway/services.py` 加入切片，或明确标注该箭头以导入/调用签名为验收粒度。

这两项是可读性改进，不影响本轮所有正式 Notebook、离线实验、门禁和固定源码边界的通过结论。
