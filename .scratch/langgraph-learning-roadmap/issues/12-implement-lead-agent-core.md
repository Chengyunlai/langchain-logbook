# 实现 Mini DeerFlow 的 Lead Agent 核心

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 08, 09, 11

## Why

这是“核心 Agent 业务”的第一条完整闭环：状态、模型、工具、Middleware、持久化配置和流式事件必须作为一个系统工作，而不是分散示例。

## Work

- 实现 Lead Agent 工厂和自定义 ThreadState/reducers。
- 实现基础工具、ToolRuntime 注入和工具错误边界。
- 组合动态上下文、摘要、调用限制、安全和产物跟踪 middleware。
- 输出稳定的流式事件，并提供图可视化。

## Acceptance

- 一个端到端场景能跨多轮调用工具、更新状态并恢复执行。
- reducer 冲突和 middleware 顺序均有测试。
- 课程逐步展示代码演进，而不是直接粘贴最终实现。
- 架构能够与 DeerFlow `make_lead_agent`、`ThreadState` 和 middleware chain 对照阅读。

## Answer

已完成可恢复 Lead Agent 核心纵切面，详细实现与验证证据见 [Lead Agent 核心实现记录](../artifacts/12-lead-agent-core.md)，学习者入口见 [`mini_deerflow/LEAD_AGENT_CORE.md`](../../../mini_deerflow/LEAD_AGENT_CORE.md)。

核心结果：

- 两个独立 application/SQLite 连接可用同一 `thread_id` 恢复多轮消息、工具结果、Artifact 和 Middleware trace；
- `merge_artifacts()` 按工作区相对路径解决 reducer 冲突，第二轮同路径事实替换旧值；
- 默认链组合摘要、动态 Context、PII、权限、结构化工具错误、Artifact 校验和模型调用上限，并用精确测试锁定 8 项声明顺序与实际 hook 方向；
- `StreamEvent` 固定应用 envelope，并把 Graph update 严格投影为 JSON-safe 数据；未知对象显式失败；
- `draw_mermaid()` 从真实 compiled graph 导出 model/tools 拓扑；
- 中文专题按四次 Red → Green → Refactor 展示恢复、治理、事件与拓扑演进，并映射当前 DeerFlow 固定提交的 Lead Agent/ThreadState/Middleware/runtime 路径。

验证：`96 passed, 1 skipped`；教程契约 `0 new / 0 known / 0 stale`；lock 与 wheel 通过；文档站 26 页、Pagefind 16 页/3872 词、`0 broken links`；Standards/Spec 双轴审查全部关闭。

有意延后：Sandbox/MCP/Skills 属于任务 13；thread/run API、完整 SSE、取消和 interrupt 恢复属于任务 14。两项均复用本任务建立的 State、Middleware、Artifact 与 JSON-safe 事件接缝。
