# 重构多 Agent 模式与上下文隔离课程

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 02, 04, 05, 06

## Why

“把两个翻译子图挂到主图”不足以解释真实 Agent 系统。课程需要教会学习者根据控制权、上下文和并发需求选择 Router、Handoff、Subgraph 或 Subagent-as-tool。

## Work

- 对比 Router、Handoff、Supervisor、Subgraph、Subagent-as-tool。
- 演示 `Command` 单路由与 `Send` 并行 fan-out。
- 设计主 Agent 如何裁剪输入上下文、限制子代理并发、汇总结果和记录 delegation ledger。
- 实现类似 DeerFlow `task` 工具的最小调度模型。

## Acceptance

- 每种模式都有适用条件、反例和可运行示例。
- 学习者能解释 DeerFlow 为什么使用 Lead Agent + task/subagent，而不只是静态路由图。
- Mini DeerFlow 支持至少两个隔离子代理和受控并行执行。
- 对子代理失败、超时、输出过大和上下文污染有明确处理策略。

## Answer

- 新增第 11 章详细中文 Markdown 与确定性离线 Notebook，完整对比 Router、Handoff、Supervisor、Subgraph 和 Subagent-as-tool；每种模式都有适用条件、反例和可运行实验。
- Mini DeerFlow 新增 registry、两个真实 `create_agent(..., checkpointer=False)` specialist、从每次 ToolRuntime 读取 Context 的 task tool、受控并发 executor 和有界 delegation ledger。
- `Command` 单路由、`Send` fan-out/fan-in、跨 checkpoint turn 的 Handoff 和 Subgraph reducer adapter 均有公共行为测试。
- 失败实验覆盖 Context/Secret 污染、并发峰值、部分失败、timeout、异常去敏、summary/artifact 过大；明确 event-loop timeout、digest 与本地 ledger 的适用边界。
- 课程映射到 DeerFlow 固定提交 `216309426fc6f954689ebee138af117029e43f8b` 的 Lead Agent → task → SubagentExecutor → ToolMessage 路径。
- 双轴审查均 CLOSED；最终验收为 `82 passed, 1 skipped`、教程 `0 new / 0 known / 0 stale`、Astro 24 页、Pagefind 14 页、断链 0。
- 详细架构、流程图、失败策略和验证记录见[实施记录](../artifacts/10-multi-agent-patterns.md)。
