# 把双层案例扩展到其余章节

Status: claimed
Triage: ready-for-agent
Type: task
Blocked by: 05, 06

## Why

三章试点只能校准结构，不能代替全书改造。第 01–04、08–11 章、工程专题和综合实战都必须按概念依赖重排，不能继续使用工程封装首次解释概念。

## Work

- 审计每章概念首次出现、失败体验、最小代码、观察输出和 Mini DeerFlow 迁移位置。
- 优先处理 Checkpoint、Interrupt、Command、Send、Subagent 和 Sandbox 等抽象跨度较大的机制。
- 保持同一个研究交付业务情境，但让概念实验拥有独立、透明的代码。
- 检查每章进入 Mini DeerFlow 前是否已完成概念预测、运行观察和最小修改。
- 重生成所有 Notebook 和站点文章。

## Acceptance

- 每个核心概念首次出现时都能回答“为什么现在需要它”。
- Mini DeerFlow 不再遮挡概念的第一次实现。
- Web、Notebook 和测试三端保留一致事实源与可读输出。
- 全书概念依赖、章节过渡和工程迁移保持连续。

## Progress

- 第 01 章已完成 7 个 lesson lab：单次模型、Runnable、tool intent 失败/修复、v2 envelope 失败/修复和 Mini DeerFlow 模型/事件入口。
- 完整 `create_agent` 工具循环的解释代码保留在正文，首次可执行工具循环后移第 04 章，避免提前解决后章核心问题。
- 第 01 章 Web、已执行 Notebook、稳定 stdout、站点发布副本与全量质量门禁均已验证。
- 第 02 章已完成 11 个 lesson lab：固定标签解析失败、最小 Pydantic 请求、真实 `with_structured_output`、危险默认值失败/修复、Artifact path 失败/修复、结果协议失败/修复、Schema 生命周期对照与 Mini DeerFlow Schema 迁移。
- `SubagentResult` 已从第 02 章后移第 11 章；第 02 章不再借子代理封装首次解释结构化输出。概念实验仅使用 Pydantic 与 LangChain 公共 fake chat model，Mini DeerFlow 只在最后一个迁移实验导入。
- 第 02 章 Web、已执行 Notebook、11 组稳定 stdout、段落长度、发布副本与全量质量门禁均已验证；同步前用户修改的 Notebook 保存在 `../backups/02_Structured_Output.ipynb`。
- 第 03 章已完成 13 个 lesson lab：Context 预算失败/透明 top-k、字符串切分丢 source/Document Splitter 修复、BM25 Retriever、Context 引用丢失/修复、固定 Runnable RAG、强制最近邻失败/显式空召回、recall@k 与两种 Mini DeerFlow 索引迁移。
- `build_search_knowledge_tool` 的首次执行已从第 03 章后移第 04 章；第 03 章明确停在 `query -> list[Document]` 与固定 `retrieve -> model` 数据流，不把 Retriever、RAG 与 Agent 自主工具循环混为一谈。
- 第 03 章 Web、已执行 Notebook、13 组稳定 stdout、当前 BM25 import、段落长度、发布副本与全量质量门禁均已验证；README 的章节交付也已同步。
- 第 04 章已完成 16 个 lesson lab：工具参数越界失败/Schema 修复、`bind_tools` 意图、孤立工具结果失败/手动 ToolMessage、原生 `create_agent` 循环与 v2 stream、身份冒充失败/ToolRuntime 修复、错误 input/messages 修复，以及五个 Mini DeerFlow 迁移实验。
- `Command(update=...)` 的首次教学已从第 04 章后移第 08 章；学习者先掌握 Message 协议和 Agent 循环，再在已有 StateGraph 心智模型上理解 Command 更新与路由，项目的 `record_artifact` 能力仍完整保留。
- validator 现在仅对 v2 `kind=failure` 实验允许 `agent-input-key` 反例；普通正文、Notebook 和其他 lab 仍会失败。新增两项测试分别锁住允许与拒绝路径。
- 第 04 章 Web、已执行 Notebook、16 组稳定 stdout、段落长度、发布副本与全量质量门禁均已验证；全量测试增至 171 passed、1 external integration skipped。
- 第 08 章已完成 15 个 lesson lab：重复 router 漂移/Command 修复、固定 worker 丢任务/Send 修复、父 State 泄漏/Subgraph 修复、无进度循环/显式进度修复、Functional task，以及六个 Mini DeerFlow 工作流迁移实验。
- 第 04 章后移的 `Command(update=...)` 已在本章回收：`record_artifact` 同时产生配对 ToolMessage 与 Artifact State patch；课程先建立消息循环和 StateGraph，再解释工具 Command 的双重效果。
- 第 08 章 Web、已执行 Notebook、15 组稳定 stdout、段落长度、发布副本与全量质量门禁均已验证；README 章节交付已同步。
- 第 09 章已完成 14 个 lesson lab：无 Checkpointer 失败/InMemory 修复、缺 thread ID/线程隔离、内存重建失败/SQLite reopen、StateSnapshot、history、time travel、旧 State 类型失败/显式 migration，以及三个 Mini DeerFlow 持久化迁移实验。
- Mini DeerFlow 持久化 provider 现在让 InMemory 与 SQLite 共用显式 msgpack 类型 allowlist，并补充 `ResearchFinding`、`WorkflowEvent`、`DraftDocument` 等领域类型；新增测试真实反序列化研究图 history，避免未来严格模式从警告升级为运行失败。
- 第 09 章 Web、已执行 Notebook、14 组稳定 stdout、段落长度、发布副本与全量质量门禁均已验证；全量测试增至 172 passed、1 external integration skipped。
- 第 10 章已完成 14 个 lesson lab：阻塞 worker/durable interrupt、审批决定协议、interrupt 前副作用失败/后移修复、time travel 重复/幂等 operation ID、多个 interrupt 顺序，以及六个 Mini DeerFlow/SQLite 审批迁移实验。
- Notebook 执行发现并修复五处临时 SQLite 生命周期错误：所有 ledger 统计都在 `TemporaryDirectory` 退出前读取，课程不再依赖已删除数据库文件。
- 第 10 章 Web、已执行 Notebook、14 组稳定 stdout、段落长度、发布副本与全量质量门禁均已验证。
- 第 11 章已完成 24 个 lesson lab：Lead 原始结果污染/有界委派、父 Context 深拷贝泄漏/allowlist 投影、Command/Send Router、Handoff、Subgraph 边界、临时 specialist、无界并发/Semaphore、裸 gather/稳定部分失败、无界输出/preview+digest，以及 Delegation Record。
- 第 11 章的八个 Mini DeerFlow 迁移实验覆盖 built-in specialist、task tool、真实 Lead model→tool→model 循环、context policy、并发、异常/timeout、输出预算和 DelegationLedger。`tool_call_schema` 与内部 `args_schema` 的 runtime 注入差异也由执行结果校准。
- 第 11 章 Web、已执行 Notebook、24 组稳定 stdout、concept/migration 边界、发布 HTML 与全量质量门禁均已验证；全量基线保持 172 passed、1 external integration skipped。
- 工程架构总览已补上真实 CLI 输出、装配探针、前 11 章到代码入口映射、四文件首读路线、固定 thread 调用实验、数据归类四问法和依赖方向诊断表，不再让初学者从 package 目录漫游。
- 架构探针发现组合根仍使用裸 `InMemorySaver`。已通过红→绿回归改为复用 `create_memory_checkpointer()`，让内存与 SQLite provider 共用显式领域类型 allowlist；新增 critical regression 防止宽松反序列化回归。全量基线增至 173 passed、1 external integration skipped。
- Lead Agent Core 已补上与架构总览的连续入口，并把原来无法证明 Artifact 更新的伪最小片段替换为完整可运行实验：两个独立 application、两个 SQLite 连接、两组确定性 tool call，打印两轮消息恢复、同路径 reducer 覆盖和 snapshot 对齐。
- Lead Agent Core 的 Streaming 部分新增真实 v2 updates 执行记录：17 个事件、2 次 model update、1 次 tools update、严格 JSON 投影与真实 Mermaid 节点，用动态轨迹解释 model→tool→model，而不是只展示 API 名称。
- Sandbox/Extensions 已按单一能力链重排：Artifact 文件落点 → user/thread workspace → ToolRuntime 写工具 → Subagent capability handle → MCP discovery/allowlist → Skill metadata/body 渐进披露，不再把四个扩展名词并列倾倒。
- Sandbox 专题新增四组完整运行记录：workspace 生命周期与拒绝审计；Lead 写文件同时形成文件、ArtifactRef 与 ToolMessage；Subagent 只继承 sandbox_id 且 Secret 不泄漏；fake MCP server 暴露两个工具但应用只授权一个。Skill 也打印正文加载前后差异。
- 下一步处理 Runtime Gateway、Evaluation/Observability、Capstone 与 DeerFlow Guide；任务保持 claimed，直到初学者盲读和换新 Agent 复验完成。
