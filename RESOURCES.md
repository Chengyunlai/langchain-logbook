# LangChain / LangGraph Agent 工程学习资源

> 校准与访问日期：2026-07-13。易变 API 以链接中的官方文档和锁定环境实测为准。

## Knowledge

- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)  
  当前 `create_agent`、工具循环、结构化响应和 Agent 扩展入口。用于第 01、04–06 章及 Lead Agent factory。
- [LangChain Models](https://docs.langchain.com/oss/python/langchain/models)  
  消息、统一模型初始化、调用和模型能力边界。用于模型 adapter 与真实供应商 integration profile。
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)  
  ProviderStrategy、ToolStrategy 与 Agent 最终响应契约。用于第 02 章。
- [LangChain Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)  
  loader、splitter、embedding、vector store 和 retriever 的当前抽象。用于第 03 章。
- [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)  
  Tool Schema、`ToolRuntime`、Context/State/Store 注入与错误边界。用于第 04–06 章。
- [LangGraph Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)  
  v1/v2 stream shape、mode、namespace 和 custom event。用于事件 adapter 和后续 SSE Gateway。
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)  
  State、Reducer、Node、Edge、Command 和 Send 的官方事实源。用于第 07–10 章。
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)  
  Checkpoint、Thread、Store、恢复与时间线语义。用于持久化和 durable execution 章节。
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)  
  持久暂停、interrupt payload 与 `Command(resume=...)`。用于区分 checkpoint 恢复和产品 Run 生命周期。
- [LangChain Middleware](https://docs.langchain.com/oss/python/langchain/middleware/overview)  
  Agent 生命周期 hooks 与横切治理。用于 Context/Middleware 重构和 DeerFlow Harness 阅读。
- [LangChain Prebuilt Middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in)  
  `SummarizationMiddleware` 的 trigger/keep、上下文压缩边界与其他内置治理能力。用于 Lead Agent 核心纵切面。
- [LangChain Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent)  
  Subagents、Handoffs、Router、Skills 与 Custom Workflow 的模式入口。第 11 章据此校准控制权、上下文隔离和 DeerFlow task tool。
- [LangChain MCP](https://docs.langchain.com/oss/python/langchain/mcp)  
  `MultiServerMCPClient`、tool conversion、stateless/session 语义与 interceptor。用于区分 MCP 能力发现、LangGraph runtime 注入和应用最终授权。
- [LangChain Deep Agents Backends](https://docs.langchain.com/oss/python/deepagents/backends)  
  State/Filesystem/Store/Sandbox backend 的选择和安全边界。用于解释为什么路径护栏、本地工作区与生产 Sandbox 不是同一能力。
- [LangChain Deep Agents Skills](https://docs.langchain.com/oss/python/deepagents/skills)  
  `SKILL.md` frontmatter、metadata discovery 与 progressive disclosure。用于 Mini DeerFlow Skill catalog 的组织与按需加载。
- [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro)  
  MCP client/server 角色、transport 和 server 能力的协议事实源。
- [LangGraph Test](https://docs.langchain.com/oss/python/langgraph/test)  
  节点、图路径、interrupt 和持久化测试方式。用于每章自动验收。
- [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation)  
  Dataset、Target、Evaluator 以及 offline/online evaluation 的当前概念边界。用于 Mini DeerFlow 评测领域层。
- [LangSmith Local Evaluation](https://docs.langchain.com/langsmith/local)  
  内存 Example 与 `upload_results=False` 的本地执行方式；课程还显式关闭被评 Graph 的自动 tracing，保证默认门禁不上传。
- [LangSmith Dataset Management](https://docs.langchain.com/langsmith/manage-datasets-programmatically)  
  `Client.create_dataset` 与批量 `create_examples(examples=[...])`。远程同步仅在用户显式调用 adapter 时发生。
- [LangSmith Agent Trajectory Evaluation](https://docs.langchain.com/langsmith/trajectory-evals)  
  确定性路径匹配与 LLM judge 的适用边界。课程默认实现无 judge 的顺序/禁止步骤 matcher。
- [LangSmith Trace LangChain Applications](https://docs.langchain.com/langsmith/trace-with-langchain)  
  `tracing_context`、Runnable 自动层级和请求级开关。用于唯一 root span 与 metadata 继承。
- [LangSmith Sensitive Data Masking](https://docs.langchain.com/langsmith/mask-inputs-outputs)  
  trace 输入输出处理与脱敏边界。用于区分关联 metadata 和禁止记录的 Secret/PII。
- [AgentEvals](https://github.com/langchain-ai/agentevals/tree/4b68015eeb444a5fc6fb986932d92a999446890c)  
  官方 trajectory match 与 graph trajectory 实现；作为可选扩展阅读，不是 `langsmith` 的传递依赖。
- [OpenEvals](https://github.com/langchain-ai/openevals/tree/d4a096b76c216feca6252cbdc277cf75c2b29a11)  
  Prompt injection、PII leakage、code injection 等在线语义 evaluator；不能替代确定性授权和沙箱门禁。
- [官方 New LangGraph Project](https://github.com/langchain-ai/new-langgraph-project)  
  可导入 package、测试和 `langgraph.json` 的最小工程结构。用于 Mini DeerFlow 骨架。
- [LangSmith Application structure](https://docs.langchain.com/langsmith/application-structure)  
  当前 `langgraph.json` 的 dependencies、graphs 与 env 结构，以及 compiled graph / factory 的注册边界。用于 Mini DeerFlow 标准入口。
- [LangSmith Local development & testing](https://docs.langchain.com/langsmith/local-dev-testing)  
  区分 `langgraph dev` 与 `langgraph up` 的本地开发和生产式验证职责。用于后续 Agent Server/Gateway 对比。
- [LangSmith Agent Server](https://docs.langchain.com/langsmith/agent-server)  
  graph、数据库、任务队列、worker 与服务端注入 Checkpointer/Store 的责任。用于对比标准运行平台和自建 Gateway。
- [LangSmith Join thread stream](https://docs.langchain.com/langsmith/agent-server-api/threads/join-thread-stream)  
  线程事件重连和 `Last-Event-ID`。用于校准 Mini DeerFlow 的可重放 SSE 契约。
- [LangSmith Cancel runs](https://docs.langchain.com/langsmith/cancel-run)  
  官方 Run 取消入口与行为。用于区分取消订阅、协作取消和 worker 强制终止。
- [WHATWG Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)  
  `id/event/data`、comment heartbeat 与重连游标的网络协议事实源。
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/stream-data/)  
  自建 Gateway 的流式 HTTP adapter；不作为 Run、事件日志或 durable execution 的事实源。
- [官方 Retrieval Agent Template](https://github.com/langchain-ai/retrieval-agent-template)  
  检索能力进入 Agent/Graph 的工程示例。用于第 03–04 章，不直接复制其依赖或业务文本。
- [DeerFlow 官方源码（课程固定提交）](https://github.com/bytedance/deer-flow/tree/4af617835805dd7cd78162ebed02fd6b782ea8bf)  
  2026-07-14 校准的 Lead Agent、ThreadState、Middleware、Subagent、Sandbox、Runtime/Gateway 与 tracing 阅读锚点；用于最终综合实战后的四条调用链导读。

## Wisdom (Communities)

- [LangChain Forum](https://forum.langchain.com/)  
  官方社区的迁移、部署与运行时问题讨论。用于验证真实项目中的边缘案例，不替代官方 API 文档。
- [LangChain GitHub Discussions](https://github.com/langchain-ai/langchain/discussions)  
  维护者与使用者讨论设计选择和兼容问题。用于调查文档未覆盖的行为。
- [LangGraph GitHub Issues](https://github.com/langchain-ai/langgraph/issues)  
  已知缺陷、回归和运行时边界。升级依赖或遇到恢复/streaming 异常时优先检索。

## Gaps

- Mini DeerFlow 的最终综合实战与系统化 DeerFlow 导读已按 2026-07-14 官方源码校准；剩余工作是文档站视觉检查、全量发布 QA 与发布记录。
- 中文检索和混合召回没有一个可直接照搬的通用最佳配置；课程通过固定 fixture、指标和 adapter contract 教选择方法，而不是给万能参数。
