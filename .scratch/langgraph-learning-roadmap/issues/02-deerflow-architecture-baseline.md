# 建立当前 DeerFlow 架构阅读基线

Status: resolved
Triage: ready-for-agent
Type: research
Blocked by:

## Why

DeerFlow 当前架构已经从早期的研究工作流演进为包含 Lead Agent、Middleware、Sandbox、Memory、Skills、MCP、Subagent 和 Gateway 的 Agent Harness。课程若只对照旧版图结构，会让学习者学完仍然找不到源码入口。

## Question

当前 DeerFlow 的请求入口、Agent 工厂、状态模型、Middleware 链、工具系统、Subagent 调度、Sandbox 生命周期、持久化、流式事件与 Gateway 分别如何协作？学习者需要先掌握哪些 LangChain/LangGraph 概念才能读懂这些模块？

## Work

- 以官方仓库当前主分支和架构文档为基线。
- 从请求进入到最终流式输出，画出一条端到端调用链。
- 建立“DeerFlow 模块 → LangChain/LangGraph 概念 → 本课程章节 → Mini DeerFlow 对应模块”矩阵。
- 区分 DeerFlow 自研运行时能力和 LangGraph 原生能力。

## Acceptance

- 产出中文架构研究文档、调用流程图和源码阅读顺序。
- 至少覆盖 Lead Agent、ThreadState/reducer、Middleware、Tools、Subagents、Sandbox、Persistence、Gateway/SSE、`langgraph.json`。
- 明确 Mini DeerFlow 必须保留与应主动省略的能力。
- 所有源码结论链接到 DeerFlow 官方仓库文件。

## Answer

已完成 DeerFlow 官方 `main` 架构研究，完整报告见 [DeerFlow 官方 main 架构阅读基线](../artifacts/02-deerflow-architecture-baseline.md)。研究固定在提交 `2bd0f56a0f5a418d126cb4a18e23001f54ccf024`（2026-07-13），只使用 DeerFlow 官方仓库源码和仓库内文档。

### 已确认结论

1. 当前 DeerFlow 是三层系统：LangChain/LangGraph 原生运行时、DeerFlow Harness、Gateway/产品运行时。
2. Lead Agent 不是一张巨型手写 StateGraph，而是由 `make_lead_agent` 组装模型、工具、skills 与 middleware 后调用 `create_agent` 得到的 compiled graph。
3. DeerFlow 的核心学习价值在 `ThreadState` reducers、Middleware 顺序、工具策略、Subagent executor、Sandbox、Persistence 与 Streaming adapter。
4. `langgraph.json` 是标准 tooling/Studio/Agent Server 入口；默认 Web/Docker 部署则由 FastAPI Gateway 内嵌 graph runtime，并实现 LangGraph-compatible threads/runs/SSE。
5. Subagent 是通过 `task` 工具调用的隔离 Agent：共享受控的 thread workspace 和身份上下文，不共享完整主对话，也不保留独立长期 thread。
6. Sandbox 是 provider abstraction；LocalSandbox 不是容器安全边界，host bash 默认禁用。课程必须把“路径约束”和“执行隔离”分开讲。
7. 持久化至少分为 Checkpointer、LangGraph Store、RunStore/RunEventStore 和产品 repositories；Mini DeerFlow 第一版只完整实现前两类，后两类用最小 RunManager/SSE 解释产品运行时。
8. DeerFlow 的确定性回归、协议测试和 replay E2E 很强；本课程还需要补充 tool selection、trajectory 和最终质量评测。

### Mini DeerFlow 保留范围

- Lead Agent factory 与 `langgraph.json`；
- ThreadState 和至少三个 reducer；
- 4–6 个代表性 Agent Middleware；
- ToolRuntime、Command、工具 registry；
- 单一 `task` 工具与两类无状态 subagent；
- 线程工作区和明确的 sandbox 安全边界；
- SQLite checkpointer、本地 Store；
- 最小 RunManager、SSE stream/cancel；
- fake model、pytest、trajectory eval 和 SSE golden replay。

第一版主动省略完整前端、Nginx、SSO/多租户、IM/GitHub channels、调度器、多 worker Redis/Postgres lease、容器 warm pool、全量 provider 与管理后台。

### 验证

- 报告 494 行，包含三张 Mermaid、完整模块矩阵、端到端时序、阅读顺序和失败陷阱。
- 共 63 个唯一 DeerFlow 官方源码链接，均已映射到固定快照中的真实文件或目录。
- Markdown 代码围栏配对，`git diff --check` 通过。
