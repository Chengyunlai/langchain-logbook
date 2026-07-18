# 重构 StateGraph、持久化与 HITL 课程

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 04, 05, 06

## Why

现有 07–08 只有概念和脚手架，无法形成核心业务编排能力。需要从完整图开始，逐步进入 reducer、并行、恢复和副作用安全。

## Work

- 完整实现 ReAct 图和一个确定性业务工作流。
- 详细覆盖 State、Reducer、Node、Edge、Command、Send、Subgraph 与 Runtime。
- 区分 InMemory、SQLite、Postgres 等 checkpointer 与 Store。
- 实现动态 `interrupt()`、`Command(resume=...)`、approve/edit/reject、多 interrupt 和 time travel。
- 通过高风险工具演示幂等、重放和副作用边界。

## Acceptance

- Notebook 不再把核心实现留作空白作业。
- 至少包含串行、条件、循环、并行和子图五种完整路径。
- 重启进程后的持久化实验使用真实持久化后端，不再依赖 MemorySaver。
- HITL 示例能证明暂停不阻塞、恢复可能重放节点、外部副作用必须幂等。

## Answer

- 07–10 已重构为显式 ReAct、Command/Send/Subgraph/Functional API、Persistence/State migration、HITL/副作用安全四个连续章节。
- Mini DeerFlow 新增显式 ReAct 图、含串行/条件/循环/并行/子图的确定性研究图、Functional task policy、SQLite v1→v2 migration graph、动态审批图和本地 effect-intent ledger。
- 真实 SQLite 实验会关闭 saver 后重新打开；HITL 覆盖 approve/edit/reject、多 interrupt、节点重入、time travel、interrupt 前副作用重复和双连接幂等记录竞态。
- 课程明确 SQLite intent 记录不等于任意远端 exactly-once；远端必须使用 provider idempotency key、事务 outbox 或领域协议。
- 07–10 Notebook 已确定性生成并离线执行；教程债务从 13 项降为 0。
- 最终双轴审查均 CLOSED。验收为 `71 passed, 1 skipped`、教程 `0 new / 0 known / 0 stale`、Astro 23 页、Pagefind 13 页、断链 0。
- 详细设计、流程图、DeerFlow 映射与审查记录见[实施记录](../artifacts/09-graph-persistence-hitl.md)。
