# 重构 Context Engineering 与 Agent Middleware 课程

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 04, 05, 06

## Why

Runtime Context、Graph State、Store 和 Agent Middleware 是当前课程到 DeerFlow 之间最大的知识断层，也是 DeerFlow Lead Agent 的主要扩展方式。

## Work

- 用统一场景解释 transient context、persistent state、long-term store。
- 实现 `AgentMiddleware` 的 before/after/wrap hooks 和 state schema。
- 讲清 middleware 顺序、组合、错误传播和同步/异步对称性。
- 覆盖动态 Prompt、动态模型、工具错误、PII、调用限制、摘要和 HITL middleware。
- 为 Mini DeerFlow 增加用户上下文、动态上下文和工具防护 middleware。

## Acceptance

- 不再把 Runnable 包装器冒充 Agent Middleware。
- 至少有一个从定义、组合、执行到测试完整可运行的自定义 middleware。
- 学习者能判断数据应该进入 Context、State 还是 Store。
- 对应模块能直接映射到 DeerFlow middleware chain。

## Answer

- 第 05 章已重构为 Runtime Context、Graph State、Store、Checkpointer 与业务数据库的数据边界课程，并用 secret 拒绝、Store 跨线程/跨用户和 Checkpointer 双线程隔离实验验收。
- 第 06 章已重构为真正的 `AgentMiddleware` 生命周期课程，覆盖 before/after/wrap、顺序、动态 Prompt/模型、PII、权限、结构化错误、调用限制、摘要、HITL 与 sync/async 取消传播。
- Mini DeerFlow 已新增类型化 `RuntimeContext`、`ThreadState`、`ArtifactRef`、`MiddlewareTraceEvent`、Store allowlist repository 和可组合治理链；Lead Agent 工厂可注入 Store、Checkpointer 与 middleware。
- Markdown 的必备实验已确定性生成并离线执行 05–06 Notebook；04 因 artifact State 契约类型化同步再生成。
- 两路最终审查均为 CLOSED。完整验收为 `60 passed, 1 skipped`、教程 `0 new / 13 known / 0 stale`、Astro 22 页、Pagefind 12 页、断链 0。
- 详细设计、流程图、DeerFlow 映射、审查修正与剩余边界见 [实施记录](../artifacts/08-context-middleware.md)。
