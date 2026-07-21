# LangGraph 学习路线与 Mini DeerFlow 改造 Todo

本文件是项目改造的公开入口。完整的目的地、流程图、依赖关系和决策记录位于 [Wayfinder 总地图](./.scratch/langgraph-learning-roadmap/map.md)，每项任务的详细中文解释与验收标准位于 [任务目录](./.scratch/langgraph-learning-roadmap/issues/)。

## 当前阶段

- 新一轮学习体验迭代已经进入[双层案例课程地图](./.scratch/learning-experience-v2/map.md)：全部 Web 章节和 Jupyter 练习都要先用概念实验室回答“为什么需要”，再用 Mini DeerFlow 工程迁移回答“在完整项目中放在哪里”。改写完成后，由两个互不共享历史的全新初学者 Agent 依次盲读、修复和复验。

- 已完成：现状扫描、主要缺口识别、本地任务跟踪约定、统一领域术语、[官方生态能力基线](./.scratch/langgraph-learning-roadmap/artifacts/01-official-ecosystem-baseline.md)、[DeerFlow 架构阅读基线](./.scratch/langgraph-learning-roadmap/artifacts/02-deerflow-architecture-baseline.md)、[现有内容可执行性审计](./.scratch/langgraph-learning-roadmap/artifacts/03-current-content-execution-audit.md)、[课程信息架构与章节契约](./.scratch/langgraph-learning-roadmap/artifacts/04-curriculum-information-architecture.md)、[中文教学与视觉表达标准](./.scratch/langgraph-learning-roadmap/artifacts/05-content-and-visual-standard.md)、[版本、依赖与自动验证基线](./.scratch/langgraph-learning-roadmap/artifacts/06-version-dependency-ci-baseline.md)、[01–04 模型层与 Agent 封装层重构](./.scratch/langgraph-learning-roadmap/artifacts/07-model-agent-foundations.md)、[05–06 Context Engineering 与 Agent Middleware 重构](./.scratch/langgraph-learning-roadmap/artifacts/08-context-middleware.md)、[07–10 StateGraph、Persistence 与 HITL 重构](./.scratch/langgraph-learning-roadmap/artifacts/09-graph-persistence-hitl.md)、[第 11 章多 Agent 模式与上下文隔离重构](./.scratch/langgraph-learning-roadmap/artifacts/10-multi-agent-patterns.md)、[Mini DeerFlow 工程骨架](./.scratch/langgraph-learning-roadmap/artifacts/11-mini-deerflow-scaffold.md)、[Mini DeerFlow Lead Agent 核心](./.scratch/langgraph-learning-roadmap/artifacts/12-lead-agent-core.md)、[Subagent、Sandbox、MCP 与 Skills 扩展](./.scratch/langgraph-learning-roadmap/artifacts/13-subagents-sandbox-extensions.md)、[持久化 Runtime、FastAPI Gateway 与 SSE](./.scratch/langgraph-learning-roadmap/artifacts/14-runtime-api-streaming.md)、[测试、评测、可观测性与安全验收](./.scratch/langgraph-learning-roadmap/artifacts/15-testing-evaluation-observability.md)、[综合实战与 DeerFlow 源码导读](./.scratch/langgraph-learning-roadmap/artifacts/16-capstone-deerflow-guide.md)、[文档站、视觉质量与发布验证](./.scratch/langgraph-learning-roadmap/artifacts/17-docs-visual-release-qa.md)、[发布契约自动化门禁](./.scratch/langgraph-learning-roadmap/artifacts/18-site-release-contracts.md)、[CI、Pages 与发布手册对齐](./.scratch/langgraph-learning-roadmap/artifacts/19-ci-pages-release.md)。
- 上一轮结果：任务 01–25 已全部完成。课程已从日期倒序文章集改造成“序章 + 四部 + 维护资料”的连续工程书，第 01–11 章与 Mini DeerFlow 专题沿同一个研究交付 Agent 演进，并已完成 Notebook、测试、站点、链接、发布契约和桌面/窄屏视觉验收。
- 最终产物：完整中文课程、可运行的 Mini DeerFlow、测试与评测、部署示例、DeerFlow 源码导读。

## 总体阶段

1. **建立可信基线**：以当前官方文档、优质示例和真实源码校准概念与 API。
2. **重建学习主线**：把零散知识组织成增强模型层、Agent 封装层、Graph 编排层和 Agent 工程层。
3. **构建贯穿项目**：每个章节都向 Mini DeerFlow 增加一个可运行能力。
4. **补齐工程闭环**：加入持久化、沙箱、子代理、流式 API、测试、评测和观测。
5. **完成迁移阅读**：把课程中的模块逐一映射到 DeerFlow 当前源码。

详细执行状态以 Wayfinder 子任务中的 `Status` 为准。
