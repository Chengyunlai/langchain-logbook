# Mission: 用 LangGraph 构建核心 Agent 业务并读懂 DeerFlow

## Why

把零散的 LangChain/LangGraph 示例重建成一条可执行的中文工程学习路线。学习者最终不仅能运行 Notebook，还能独立设计、测试和交付自己的核心 Agent 业务，并能沿模块边界阅读 DeerFlow 这样的真实 Agent Harness。

## Success looks like

- 能解释增强模型、Agent 工具循环、Graph 编排和 Agent 工程层的责任边界。
- 能从零实现带 State、Middleware、Tools、Subagents、Sandbox、Persistence 和 SSE 的 Mini DeerFlow。
- 能通过失败实验、离线测试和评测证明恢复、安全与结果质量，而不只展示成功回答。
- 能把 Mini DeerFlow 的模块逐一映射到 DeerFlow 的 Lead Agent、Harness 和 Gateway 架构。

## Constraints

- 教学正文使用详细中文和本地 Markdown，不通过删减原理缩短内容。
- 核心实验默认离线可运行；真实模型和外部服务必须显式 opt-in。
- Markdown、Notebook 与 Python package 必须有自动同步和验证边界。
- 优先使用可版本化 Mermaid；只有精确图无法表达时才使用生成位图。

## Out of scope

- 完整复刻 DeerFlow 的所有产品、渠道、租户和运维功能。
- 为所有模型供应商维护等量示例。
- 构建生产级多租户 SaaS 或完整 Web 前端。
