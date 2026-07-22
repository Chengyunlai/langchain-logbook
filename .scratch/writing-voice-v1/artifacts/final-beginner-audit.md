# LangChain Logbook 最终初学者盲读验收

验收日期：2026-07-22（Asia/Shanghai）

## 盲读边界

我以“只会基础 Python、第一次系统学习 LangChain/LangGraph”的读者身份，从线上首页 `https://chengyunlai.github.io/langchain-logbook/` 开始，按站点给出的正式阅读顺序验收。浏览器会话在当前环境不可用，因此我通过 HTTPS 直接读取已发布页面 HTML；这使我能验收正式文字、代码、链接目标和页面顺序，但不能评价真实浏览器中的点击、样式和交互体验。

除正式 Web 页面外，我只读取并运行了 `tutorials/01_*.ipynb` 到 `tutorials/11_*.ipynb`。11 个 Notebook 均在项目虚拟环境中无 API Key 执行通过。验收前及验收过程中，我没有读取仓库 Markdown 源文件、Mini DeerFlow Python 源码、tests、scripts、`CONTEXT.md`、`.scratch` 计划、git diff/历史或作者说明，也没有用这些材料替课程补洞。真实 DeerFlow 的调用关系只依据正式 Web 的《沿四个故障读懂 DeerFlow》复述，没有另开 DeerFlow 源码验证。

## A. 我理解的阅读顺序，以及研究助手怎样成长

首页给出的顺序是明确而且可执行的：序章 → 第 01–03 章 → 第 04–06 章 → 第 07–10 章 → 第 11 章 → Mini DeerFlow 工程架构、Lead、Sandbox、Runtime、Evaluation、Capstone → DeerFlow 四故障导读。`/posts/` 页面还明确说附录、版本策略、发布手册等是按需参考，不属于线性前置。

我对第 01–11 章的理解不是“学了 11 组 API”，而是同一个研究助手连续摆脱 11 个实际限制：

1. 第 01 章先解决“看起来都像调用模型”的混乱。助手只会一次回答时，程序必须先分清输入/输出是 Message，固定管道是 Runnable，工具意图在 `tool_calls`，v2 stream 外层是 `{type, ns, data}`。否则后面连“模型做了什么”都看不见。
2. 第 02 章解决自然语言结果无法被程序稳定消费的问题。“目标”换个说法，字符串解析就坏；于是计划、Artifact 和失败结果被收紧成 Pydantic 业务对象，非法路径和缺失依赖在边界处失败。
3. 第 03 章解决“结构正确但事实过时、没有来源”的问题。助手有了检索、排序、引用映射、空召回协议和可替换索引；资料正文与 source 不再在切分和格式化时分家。
4. 第 04 章解决固定 RAG 对所有输入都执行同一动作的问题。模型第一次能从已批准工具中选择动作；手写 `AIMessage(tool_calls) → ToolMessage → AIMessage` 后，再由 `create_agent` 接管标准循环。身份等应用事实则通过 ToolRuntime/Runtime Context 注入，模型不能自行填写。
5. 第 05 章解决“所有东西都叫上下文并塞进一个 State”的问题。当前线程的计划和消息进 Graph State；一次调用的身份、权限和连接进 Runtime Context；跨 Thread 偏好进 Store；余额、订单等权威事实留在业务数据库。
6. 第 06 章解决权限、脱敏、预算、错误处理散落在每个模型/工具调用点的问题。Middleware 在统一生命周期 seam 上拦截调用、短路预算、规范化 ToolMessage 错误，并用顺序测试固定治理语义。
7. 第 07 章解决 Prompt 无法证明“先规划、并行搜索、再汇总”的问题。固定业务顺序进入 StateGraph；节点交 patch，边表达可达关系，Reducer 明确并行或重复更新如何合并。
8. 第 08 章解决静态图只能容纳固定任务数、规则重复、子流程看见过多 State、循环不收敛的问题。Command 合并“更新+选路”，Send 按运行时计划展开任务，Subgraph 缩小 State 边界，显式进度让循环能够业务终止。
9. 第 09 章解决进程退出后只剩返回值、没有执行现场的问题。Checkpointer 按 thread 保存 StateSnapshot、`next`、tasks 和历史；SQLite 重开证明跨实例恢复，旧 State 还必须通过版本迁移进入新代码。
10. 第 10 章解决人工审批不能占着 worker、恢复又会重放副作用的问题。`interrupt` 保存暂停点并返回，`Command(resume=...)` 在同一 thread 恢复；副作用移到审批后，并用稳定 operation ID/ledger 抵抗 resume 和 time travel 重放。
11. 第 11 章解决 Lead 被原始资料、工具轨迹和 Secret 淹没的问题。任务被投影到临时 Subagent 的最小上下文，长内容留在 Artifact，Lead 只收有界结构化结果；Executor 统一守住并发、超时、部分失败、输出预算和审计终态。

这条成长链成立。每章开头都能指出上一章的“顺利结果为什么还不够”，每章结尾又把下一章的问题暴露出来。11 个 Notebook 的实验顺序与 Web 页面一致，并且全部离线执行成功。

## B. 13 个核心概念的初学者解释

| 概念 | 我的解释 | 标记 | 形成理解的页面/实验 |
|---|---|---|---|
| model | 一个接收消息并返回 `AIMessage` 的模型接口。一次 `invoke` 只做一次模型调用；它不会自动执行工具、保存 Thread 或决定完整业务流程。 | 能独立解释 | 第 01 章“模型返回的是 Message”；Notebook 实验 1“调用一次模型并检查返回消息类型” |
| Message | Agent 协议中的有类型记录，不只是字符串。`HumanMessage` 表示用户输入，`AIMessage` 可含正文或 `tool_calls`，`ToolMessage` 用 call ID 把执行结果配回工具请求。 | 能独立解释 | 第 01 章“content 为空，模型也可能已经做出决定”；第 04 章实验 4–6 |
| Runnable | 由程序固定顺序的数据流，例如 Prompt → model → parser。模型只能完成其中一步，不能跳过前后步骤，也不负责开放式规划。 | 能独立解释 | 第 01 章“步骤固定时，用 Runnable”；Notebook 实验 2 |
| create_agent | LangChain 的高层 Agent 工厂，把标准的 model → tools → model 循环装成一个由 LangGraph runtime 执行的 compiled graph，自动完成工具查找、参数校验、ToolMessage 配对和继续/终止。 | 能独立解释 | 第 04 章“让 create_agent 接管重复循环”；Notebook 实验 6、7 |
| Runtime Context | 应用在一次 invocation 中注入的受信事实和活依赖，如 user、permissions、request、workspace 句柄、数据库连接。模型不能填写，节点通常只读；它不会自动进入 Prompt，也不应被 checkpoint。 | 能独立解释 | 第 04 章实验 9；第 05 章“用原生 Runtime 拆开运行依赖与线程事实” |
| Graph State | 当前 checkpoint thread 中由节点共同读写、随步骤演进的可持久化事实。节点读取快照、返回局部 patch，框架通过字段规则合并。 | 能独立解释 | 第 05 章 Thread 隔离实验；第 07 章实验 1“节点只交回自己改动的字段” |
| Store | 应用按 namespace/key 显式读写的跨 Thread 数据空间，适合用户明确保存的偏好。它不自动复制 State，也不是订单、余额等权威业务数据库。 | 能独立解释 | 第 05 章实验 4–7，“Checkpointer 不是 Store”“Store 不是业务数据库” |
| Middleware | 围绕 Agent 模型/工具生命周期的可组合治理层。它可以在 handler 前授权或短路，在请求/结果两侧脱敏、记账和归一化错误；注册顺序会改变进入和退出语义。 | 能独立解释 | 第 06 章实验 2、3、6、8；“什么该放 Middleware，什么该进 Graph” |
| StateGraph | 用 State、Node、Edge 和条件路由显式表达业务拓扑的构建器。它适合必须由程序证明的顺序、分支、fan-out/fan-in、循环、暂停和恢复。 | 能独立解释 | 第 07 章“先让研究提纲穿过节点和边”“哪些流程值得显式画出来” |
| Reducer | 某个 State 字段收到旧值和一个或多个更新时的领域合并规则。列表追加、按 ID 替换、冲突即失败是不同语义，不能都用 `operator.add`。 | 能独立解释 | 第 07 章实验 4–7；Notebook“同一个 reducer 会把任务表合并错” |
| Checkpointer | 在 Graph superstep 边界按 thread 保存执行快照的组件。快照不只含最终 values，还含下一节点、tasks、interrupt、checkpoint lineage，因此能恢复、查看历史和 time travel。 | 能独立解释 | 第 09 章实验 1–9；SQLite 重开实验 6 |
| interrupt | 节点内的持久暂停点。它把待处理 payload 与当前位置写进 checkpoint，让当前调用和 worker 释放；之后用同一 thread 的 `Command(resume=...)` 继续，节点会从头重入。 | 能独立解释 | 第 10 章实验 2、4、8；“interrupt 保存暂停点并立即返回” |
| Subagent | Lead 为一笔委派临时创建的隔离 Agent/invocation。它有自己的 Prompt、工具、允许的 Context 和运行预算，返回有界 `SubagentResult`；在 subagent-as-tool 模式中控制权回到 Lead，而不是永久接管用户会话。 | 能独立解释 | 第 11 章实验 2、4、9、17–24；“Subagent-as-tool：Lead 委派一次，再收回控制权” |

我的结论是：这 13 项在不看源码的情况下都能建立可操作解释。最有误解风险的仍是三组相邻概念：Runtime Context/Graph State/Store、Checkpointer/产品 Run/Event、Subgraph/Subagent；但课程已经提供直接制造错误的对照实验，而不是只给定义。

## C. 何时用 create_agent，何时需要 StateGraph

当“下一步由模型在一组批准的工具中自由选择”时，用 `create_agent`。典型例子是搜索、计算、读文件之间的开放式选择，以及标准的 model → tool → model 循环。它已经处理消息配对、工具执行、继续循环和基础 streaming，不值得手写一遍 ReAct。

当“下一步本身是产品必须证明的规则”时，需要显式 StateGraph。例如：规划一定先于检索；三个 section 动态并行并按 Reducer 汇合；发布一定经过审批；修订最多两次；暂停后可恢复；质量门失败不得到达副作用节点。这些规则若只写在 Prompt 中，就无法通过拓扑、State 和轨迹测试证明。

两者不是互斥替代关系，原因有两层：

- `create_agent` 本身就运行在 LangGraph runtime 上，它不是另一套竞争框架。
- 外层 StateGraph 可以拥有确定性的业务阶段，其中某个“智能节点”再调用 `create_agent` 完成开放式工具循环。第 06 章“什么该放 Middleware，什么该进 Graph”、第 07 章“哪些流程值得显式画出来”和练习 C 都明确展示了这个组合。

我会把判断压缩成一句话：标准 Agent 循环交给 `create_agent`，必须由业务拥有的控制流交给 StateGraph；实际系统经常是 Graph 外层包住 Agent 节点。

## D. 从基础章到 Mini DeerFlow 系统

完成基础章节后，我能把 Mini DeerFlow 复述为下面这套组合，而不是若干目录名：

1. **组合根**：`build_application/_assemble_graph` 是唯一装配决策点。非敏感 settings 与活 dependencies 分开进入；它创建工具表、Middleware 顺序、SubagentExecutor/task、Store、Checkpointer，再把它们交给 Lead Agent。CLI、Notebook、API 不应各装一套。
2. **Lead Agent**：Lead 使用 `create_agent` 保留标准工具循环；ThreadState 保存 messages、Artifact 和治理轨迹；Runtime Context 每次重建身份/权限；Middleware 治理模型与工具；Checkpointer 在模型调用前恢复同一 thread；stream adapter 把上游 v2 event 变成 JSON-safe 应用事件。
3. **Sandbox 与扩展**：SandboxProvider 按 user/thread 取得工作区 session，模型只见相对路径。Subagent 只继承 opaque `sandbox_id`，不拿宿主绝对路径或完整父 Context。MCP 是候选能力来源，必须再过应用 allowlist；Skill 启动时只披露 metadata，正文按需加载。发现不等于授权。
4. **Runtime/Gateway**：Gateway 先认证并拥有产品 Thread、Run、Event；RunManager/worker 驱动 Graph；Runtime repository 保存状态机和单调事件序号；SSE 只重放已持久化事件。Graph Checkpointer、跨线程 Store、Workspace 和产品 Run/Event 各自保存不同事实。
5. **Evaluation/Observability**：确定性测试守住 Reducer、授权、路径、幂等、恢复等硬边界；Dataset/Target/Evaluator 把一次执行投影为 Observation，再分别评 outcome、trajectory、budget；Trace 解释单次因果树，RunJournal/Event Journal 服务客户端重放，二者只通过 correlation ID 关联。
6. **Capstone**：同一请求先经 Lead 检索，再并行委派 research/coding；长草稿落入线程 Workspace；Approval Graph 在 SQLite checkpoint 中 interrupt；新实例 resume 后先通过质量门和幂等 ledger，再写正式 Artifact；最后用 outcome/trajectory/budget 验收。拒绝保留草稿但没有正式 Artifact/effect，重复 request 只得到 `already_recorded`。

“概念实验 → 工程迁移”的过渡有两层。第 01–11 章每章后半已经有明确的“Mini DeerFlow 在这里增加了什么/把同一机制装回 Mini DeerFlow”，因此不是第 11 章后突然换项目；真正的工程阶段切换发生在《Mini DeerFlow 是怎样装成一套应用的》，它第一次把组合根、依赖方向、四类数据所有者和一条完整消息链放在同一张图里。随后 Lead/Sandbox/Runtime/Evaluation 是对既有接缝逐层加压，Capstone 只负责业务顺序，不再发明平行框架。

## E. DeerFlow Guide 的四条故障路线

### 1. 身份边界：伪造管理员为什么不能进 State

起点是请求 body 伪造 `user_role=admin`，并要求 Lead 调用发布工具。阅读链是：`backend/langgraph.json` 注册 `deerflow.agents:make_lead_agent` → Lead factory 解析 config → 分别装入 model、tools、Middleware、prompt、ThreadState → 汇入 `create_agent`。

关键判断不是“State 里有没有 role 字段”，而是谁拥有它。认证 user/role 应由 Gateway/worker 从可信认证上下文放进 Runtime Context；ThreadState 只保存可 checkpoint 的 Agent 执行事实；产品 Thread/Run 的 owner 又由 Gateway repository 单独保存。Middleware 按真实装配顺序做输入/身份治理、能力过滤和工具执行防线，模型只能选择已注册且允许的工具。

最终责任边界：Gateway 负责认证与资源 owner，worker 负责构造可信 Runtime Context，Harness/Middleware 根据它过滤能力，provider 执行并审计副作用。用户正文无权改写这条链；把 role 合入 State 会让伪造身份进入 checkpoint、resume、trace 和 Subagent 继承路径。

### 2. Workspace/Sandbox：任务为什么写进别人的工作区

起点是 Lead 正常调用 `task`，Subagent 内容正确，却写进另一用户 workspace。调用链是：Lead → task tool（解析 subagent type/config/tool groups/skills）→ 从父 runtime 投影受信的 thread/run/sandbox handle → SubagentExecutor → 创建禁用继续 `task` 的临时 Agent → Sandbox/provider 执行 → structured terminal result/ToolMessage/Command 回到 Lead；旁路产生 task progress 事件。

Sandbox、MCP、Skills 共用一条能力生命周期：discover → describe/load → authorize → register → bind 可信身份/句柄 → provider execute → 结果清洗、预算与审计。MCP server 的 schema、Skill 正文或一个 workspace 字符串都不是授权。

最终责任边界：受信 sandbox handle 的创建和父→子投影负责租户绑定，Executor 负责上下文/递归/终态边界，provider 负责路径和实际执行隔离，Gateway/Harness policy 负责权限。若 task 接受客户端 workspace path，或 Subagent 自建未绑定认证主体的 provider，错误早在写文件前已经发生，不能靠 Prompt 的“不要越权”修复。

### 3. SSE 断线恢复：为什么不应重跑 Subagent

起点是后台研究仍在运行，浏览器 SSE 短暂断开。调用链从 HTTP 反向追：thread_runs router 权限检查 → Gateway services 转换输入/`Command(resume)` → RunManager 创建、领取和调度产品 Run → worker 调用 Lead Graph → Graph 产生 messages/updates/custom → worker 先把事件追加到 RunJournal/EventStore，再发布到 StreamBridge → router 输出 `id/event/data` SSE。

断线只让 subscriber 消失，不等于 cancel worker；Cancel Run、Graph interrupt、Resume 是另外三种状态变化。重连应按 run_id 加入现有流，并从 Last-Event-ID/sequence 之后重放。已经完成的 Subagent 不应再执行。

最终责任边界：RunManager/worker 拥有后台执行，RunJournal/EventStore 拥有客户端可重放事件，StreamBridge/SSE 拥有 live delivery 与游标，Checkpointer 只拥有 Graph State/interrupt 恢复。Checkpoint 不能回答客户端已经看过哪些事件。

### 4. Trace/RunJournal：Trace 后端坏了，Run 是否还能成功

起点有两个分支：tracing backend 断开但 Agent 已生成答案；或 EventStore 写失败但 trace 平台留下绿色执行。当前导读说明 Graph invocation root 只挂一次 tracing callback，内部 model 以 `attach_tracing=False` 避免重复 root；Agent、model、tool、Subagent 都作为 child span 进入 trace backend。

同一次执行还并行进入 RunJournal callback：它产生 run lifecycle/message/usage 等产品事件，写入 EventStore，再供 SSE/query。Trace 保存诊断因果树、时延、token 和错误；Journal 保存客户端必须查询、重放的交付事实。关联 ID 只连接查询，不把两套存储合并。

最终责任边界：trace backend 失效通常不应把业务 Run 自动判失败，但故障必须可见；EventStore 失效则意味着产品无法可靠交付/重放，不能仅凭绿色 trace 宣称 Run 已可靠成功。安全证据也分散在 Gateway 身份、Middleware policy、Sandbox audit、ToolMessage、Journal 和 trace 中，各自负责一段事实。

## F. 阻塞、回退、跳跃、模板感与密度记录

### 阻断理解

- **课程内容本身：未发现阻断。** 01–11 的全部 Notebook 无 API Key 执行通过；没有任何一章必须通过源码、测试或作者说明才能理解本章核心概念。
- **验收工具边界：不构成课程阻断。** 当前环境没有可用浏览器会话，因此无法评价真实点击/视觉交互；正式 HTML 仍可顺序读取。
- **真实 DeerFlow 证据的独立复核：属于本次盲读边界。** 《沿四个故障读懂 DeerFlow》1.1 明确要求固定 commit 或下载“证据切片”，2.1 又要求 `rg` 后打开定义上下文。本次禁止读源码，所以我能理解和复述导读给出的调用链，但不能独立证明这些 symbol 在固定 commit 中确实如此。这不是正文断裂，却意味着“看懂 Guide”与“完成源码验收”仍是两级完成标准。

### 明显摩擦

1. **第 06 章提前使用尚未系统学习的恢复协议。** “摘要与审批为什么需要完整协议”直接出现 `HumanInTheLoopMiddleware`、`InMemorySaver`、`Command(resume=...)`、同一 thread 恢复；但 StateGraph、Checkpointer、interrupt 分别要到第 07、09、10 章才从零建立。代码能跑，初学者却需要暂时相信 `interrupt` 的重入/持久化语义，之后倒回补课。建议把该实验明确标成“只观察 Middleware 接缝，暂不要求解释恢复”，或移到第 10 章回接。
2. **下载 Notebook 的文件名与可见章节主题错位。** Web 第 05 章《为运行事实划清所有权》下载的是 `05_Agent_Middleware.ipynb`；第 06 章《用 Agent Middleware 收回散落的调用治理》下载的是 `06_Observability_Persistence.ipynb`；第 09 章《关掉进程，研究任务还能回来吗》下载的是 `09_Multi_Agent_Eval.ipynb`。Notebook 内部标题正确，但下载后仅看文件名很容易打开错材料，尤其第 09 章文件名会让人误以为已进入评测。
3. **第 11 章负荷过大。** Web/Notebook 从请求协议、Context 投影一路覆盖 Router、Send、Handoff、Subgraph、Subagent-as-tool、Semaphore、部分失败、timeout、大输出、Ledger，再迁移到 Mini DeerFlow；Notebook 有 121 个 cell、24 个实验。核心判断“谁拥有下一步控制权”很好，但容易被执行器细节淹没。建议拆成“模式与控制权”及“Subagent 运行边界”两条必修单元，或给出必做/选做实验标记。
4. **第 06 章也偏密。** 70 个 cell、14 个实验同时处理 tool/model wrapper、hook 顺序、动态模型、预算、同步/异步错误、取消、摘要、HITL、Runnable listener 和工程治理链。尤其 listener 与 HITL 两段会把“Agent Middleware 的最小模型”拉散。
5. **工程阶段编号不统一。** `/posts/` 把架构总览到 DeerFlow Guide 编为 12–18；《Mini DeerFlow 是怎样装成一套应用的》“后续专题从哪些接缝继续”却用 12 Lead、13 Sandbox、14 Runtime、15 Evaluation、16 Capstone/Guide，没有把当前架构总览计入，也把 Capstone 与 Guide 合并。读者很难判断页面里的“第 12/16 项”指站点章节还是工程任务号。
6. **工程页面的展示日期与校准日期冲突。** 架构、Lead、Sandbox、Runtime、Evaluation 页面顶部显示 `1 Jan, 2025`，正文却分别写 2026-07-13/14 校准；Capstone 和 DeerFlow Guide 又显示 2026-07-14。对一个反复强调 fixed commit 和版本事实源的课程，这会削弱读者对“当前/历史”的判断。
7. **Capstone 3.1/3.2 的动作目标容易混。** “先证明参考工程没有隐藏依赖”要求复制整个 package/tests/README/Makefile 到临时目录；紧接着“再按全书顺序重建公共接缝”又要求另建空目录、不要复制整个 package。两者目的不同，但对初学者容易都理解为“开始做 Capstone”。建议在 3.1 标成可选的“发布物完整性检查”，把 3.2 标成真正学习任务。
8. **第 08 章 Functional API 是一段孤立支线。** “已有的过程式函数也要能恢复”用 `@entrypoint/@task` 引入第二种编排表面，后续主线又回到 Graph/Agent/Capstone。实验本身清楚，但第一次读者会猜它与 StateGraph 的选择优先级。建议标明它是按需替代入口，不是完成后续章节的必要前置。

### 可选润色

1. **实验模板重复感在长章里很强。** “运行前先预测 → 观察结果 → 发生了什么 → 动手修改”对前几章非常有效；到第 11 章连续 24 次后，会像自动生成的固定模板。可保留结构，但把相邻小实验合并为一个故障故事，减少机械重复。
2. **“先不要……现在才……不要从目录开始……”的命令句过密。** 架构、Lead、Sandbox、DeerFlow Guide 都用这种话建立阅读纪律，方向正确；连续出现时略像模板化训令。可在每篇开头给一次“本篇阅读协议”，正文减少重复提醒。
3. **页面标题、发布日期、校准日期、固定 commit 的层级可统一。** 目前历史专题 commit 与最终统一 commit 需要在正文多次解释。可以用固定的页面元信息框显示“本文发布日期/最后校准/局部锚点/全书统一锚点”。
4. **工程专题可以提供一条“只读主线”。** Runtime 和 Evaluation 页面很完整，但单页极长。为初学者标出“必须读的调用链/可选生产扩展/练习”会减少第一次阅读压力，而不删掉工程深度。

## G. 最终裁决

### 1. 基础概念能否在不看源码情况下建立

**能。** 13 个必查概念都有“先制造可观察错误，再用最小机制修复”的直接证据；01–11 Notebook 全部离线执行通过。尤其 Message/tool call、Context/State/Store、Reducer、Checkpointer、interrupt、Subagent 不是靠比喻，而是靠返回类型、StateSnapshot、轨迹、重放计数和边界失败建立。

### 2. 能否自然上升到 Mini DeerFlow

**能，且过渡总体自然。** 每章先做框架原生实验，再说明 Mini DeerFlow 增加的类型、组合根、安全、持久化或协议边界；架构总览把零件装成同一应用，Lead/Sandbox/Runtime/Evaluation 分别沿接缝加压，Capstone 最终只做业务纵切面装配。主要问题不是概念缺口，而是第 06/11 章和工程专题的单页密度。

### 3. 能否据此读懂 DeerFlow Guide 的四条路线

**能读懂责任链，也能从故障定位所有者。** 我可以不看源码复述身份、Workspace、SSE、Trace/Journal 四条路线的起点、关键调用关系和最终责任边界。要达到 Guide 自己定义的“每个箭头都能用固定 commit 调用点证明”，仍必须进入它提供的固定源码/证据切片；这是源码验收阶段，不是基础概念阶段。

### 4. 宣称“全书完成”前必须修复什么

我没有发现需要重写核心教学内容的阻断缺陷，但以下三项应在公开宣称“面向初学者的全书完成版”前修复：

1. **统一导航身份**：修正 05/06/09 Notebook 文件名、工程章节 12–18 编号和工程页面日期/校准信息。它们是发布物层面的客观不一致，不只是文风偏好。
2. **补清前置边界**：在第 06 章 HITL 实验明确标注“预览，不要求掌握持久恢复”，或将完整实验移到第 10 章，避免初学者在尚未学 StateGraph/Checkpointer 时被迫猜测。
3. **给超长章节分层**：至少为第 11 章提供两段式结构或必做/选做路线；否则“控制权选择”这个真正主线会被 24 个实验稀释。第 06 章也应标出最小 Middleware 主线与扩展实验。

在这三项修复前，我的裁决是：**内容闭环已经完成，初学者可以从零建立概念并读到 DeerFlow；但发布导航和学习负荷尚未达到可以毫无保留称为“最终完成版”的程度。**
