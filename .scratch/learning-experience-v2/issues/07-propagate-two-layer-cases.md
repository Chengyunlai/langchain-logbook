# 把双层案例扩展到其余章节

Status: open
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
