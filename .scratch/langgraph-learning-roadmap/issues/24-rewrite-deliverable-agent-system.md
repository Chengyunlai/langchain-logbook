# 重写第四部：扩展为可交付的 Agent 系统

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 23

## Why

第三部交付可恢复、可审批的 Graph 后，课程还要把单体图扩展成带 Subagent、Sandbox、Runtime、Gateway、评测和观测的业务系统，并使 Capstone 与 DeerFlow 导读成为同一项目的完成和迁移阶段。

## Work

- 重写第 11 章及 Mini DeerFlow 六个工程专题的章节开合和跨文档衔接。
- 让 Capstone 只装配已学能力，不再像突然出现的新项目。
- 用完成后的 Mini DeerFlow 作为认知参照，重写 DeerFlow 源码导读入口。
- 调整篇幅节奏，拆分过密章节中的主线与参考材料。

## Acceptance

- 第四部从上下文膨胀连续推进到 Subagent、Sandbox、Runtime、评测、综合实战和 DeerFlow 阅读。
- 学习者在进入源码导读前已经实际使用对应架构边界。
- 不削减安全、恢复、事件日志、评测和源码证据。
- 测试、站点、搜索与发布契约通过。

## Answer

第四部已连接为“Subagent 上下文隔离 → 应用组合根 → Lead 核心纵切面 → Sandbox/MCP/Skills 能力边界 → Runtime/Gateway 产品交付 → 评测与观测 → Capstone 装配 → DeerFlow 调用链迁移”。

第 11 章明确从第 10 章的上下文膨胀出发；每篇工程专题新增系统快照和下一篇接口；Capstone 明确只装配已有公共接缝；DeerFlow 导读以学习者已经亲手使用的边界作为阅读坐标，并新增全书收束。第 11 章 Notebook 已重新生成执行，工程专项测试 `66 passed`，教程审计无新增问题。
