---
layout: ../layouts/AboutLayout.astro
title: "关于 LangChain Logbook"
description: "了解 LangChain Logbook 中文 Agent 工程课程的定位、学习产物、设计原则与本地运行入口。"
---

LangChain Logbook 是一套面向工程实践的 LangChain / LangGraph 中文课程，也是一套可以离线运行、测试和持续演进的 Mini DeerFlow 实验环境。

### 项目解决什么问题？

很多学习资料按 API 或独立 Demo 组织，读者很难理解模型调用、Agent 工具循环、Graph 编排和产品运行时之间的边界。本项目让同一个研究助手贯穿全部章节，每次只增加一组可以验证的新能力。

### 你会在这里完成什么？

- 用消息、结构化输出和检索建立可靠的模型输入输出边界。
- 用 Tools、Runtime Context 和 Middleware 构建受控 Agent。
- 用 StateGraph、Checkpoint 和 Interrupt 表达可恢复的业务流程。
- 用 Subagent、Sandbox、Gateway、SSE 和 Eval 装配完整的 Mini DeerFlow。
- 沿组合根与调用链阅读真实 DeerFlow，而不是按目录漫游。

### 项目原则

- **离线优先**：核心实验和测试默认不需要付费模型或外部服务。
- **连续演进**：章节共享同一业务情境和工程产物，不重复创建孤立 Demo。
- **契约验证**：Markdown、Notebook、Python 包、测试和文档站由自动化门禁保持一致。
- **独立维护**：课程路线、实现和发布流程以当前仓库为唯一事实源。

### 项目入口

- **GitHub**: [Chengyunlai/langchain-logbook](https://github.com/Chengyunlai/langchain-logbook)
- **在线课程**: [chengyunlai.github.io/langchain-logbook](https://chengyunlai.github.io/langchain-logbook/)
- **本地开始**: [PyCharm 快速上手](https://github.com/Chengyunlai/langchain-logbook/blob/main/docs/getting-started-pycharm.md)
