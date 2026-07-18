# 整合课程、综合实战与 DeerFlow 源码导读

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 07, 08, 09, 10, 13, 14, 15

## Why

各模块完成后仍需把它们组织成学习体验。最终章节要让学习者先独立完成 Mini DeerFlow，再带着相同概念进入真实 DeerFlow，而不是直接面对大型仓库。

## Work

- 为每章增加“本章改造 Mini DeerFlow 的哪一部分”。
- 设计最终业务需求、迭代步骤、故障注入和验收清单。
- 制作 Mini DeerFlow → DeerFlow 的模块映射表、调用链和源码阅读路线。
- 提供分层阅读问题：先看接口，再看状态，再看 middleware，最后看运行时和网关。

## Acceptance

- 学习者能从空目录逐步得到可运行综合项目。
- 最终实战不是翻译或天气 Demo，而是包含研究、文件、审批、委派和恢复的长任务场景。
- DeerFlow 导读引用当前官方源码，并明确版本日期。
- 课程目标、章节练习、项目测试和最终验收相互对应。

## Answer

已交付 [`CAPSTONE.md`](../../../mini_deerflow/CAPSTONE.md)、可运行的 `capstone.py` 与 6 个综合测试。最终业务真实包含检索、文件草稿、两个隔离 specialist、durable interrupt、approve/edit/reject、Checkpointer 重开、幂等 effect intent、发布前质量门和结果/轨迹/预算评测；空目录参考工程及 M1–M10 测试驱动重建路线均已给出并实测。

已按 DeerFlow 官方 `4af617835805dd7cd78162ebed02fd6b782ea8bf`（2026-07-14）交付 [`DEERFLOW_GUIDE.md`](../../../mini_deerflow/DEERFLOW_GUIDE.md)，提供 manifest/Lead、State/Middleware、task/Subagent、Gateway/Runtime 四条调用链，明确 Trace、Runtime Event Journal 与 Checkpoint 的边界。第 01–11 章均增加 Mini DeerFlow 增量入口。

最终 `make check` 通过：`135 passed, 1 skipped`，教程漂移 `0/0/0`，33 页文档站、0 断链；10 张新增 Mermaid 均含文本替代和读图顺序；Standards/Spec 双轴复审均 PASS。完整证据见[任务 16 实现记录](../artifacts/16-capstone-deerflow-guide.md)。
