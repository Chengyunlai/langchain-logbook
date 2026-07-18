# 重写第三部：把业务流程写成可恢复的图

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 22

## Why

第二部完成后，Lead Agent 已能使用工具并接受统一治理，但研究、并行撰写、持久恢复和人工审批仍需要显式业务拓扑。第 07–10 章应形成一条逐步增加控制能力的连续 Graph 路线。

## Work

- 用研究交付拓扑重写 StateGraph、Command/Send/Subgraph、Persistence 和 HITL 四章。
- 统一 Thread、Run、Checkpoint、Store、Graph State 和副作用术语。
- 让每次失败实验直接作用于上一章构建的研究 Graph。
- 清理提前引用不可见章节、编号断层和独立 Demo 跳转。

## Acceptance

- 第 07–10 章形成“显式图 → 并行控制流 → 跨重启恢复 → 审批与幂等”的因果链。
- 所有持久化与副作用结论保留边界、证据和测试。
- 第 10 章自然引出单 Agent 上下文膨胀与能力隔离问题。
- Notebook、测试、站点和链接验证通过。

## Answer

第 07–10 章已连接成同一研究 Graph 的四次升级：从 Middleware 治理的 Lead Agent 中抽出固定业务拓扑，用 Command/Send/Subgraph 表达并行研究，再以 SQLite Checkpointer 验证跨进程恢复，最后用 durable interrupt 和 effect-intent ledger 完成审批与幂等副作用边界。

四章开头均说明上一版系统与本章故障，结尾给出当前工件和下一项约束。第 10 章以 Lead Agent 上下文膨胀自然引出 Subagent。已重新生成并执行四个 Notebook；专项测试 `14 passed`，教程审计 `0 new / 0 known / 0 stale`。
