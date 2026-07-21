# 让全新初学者 Agent 端到端盲读课程

Status: open
Triage: ready-for-human
Type: task
Blocked by: 07

## Why

作者、实现 Agent 和评审 Agent 已熟悉架构，容易用既有知识补全文档缺口。必须让未参与改写的全新子 Agent 只依赖公开课程，验证 Web 阅读与 Jupyter 实践能否真正建立基础概念并过渡到 Mini DeerFlow。

## Work

- 启动不继承当前对话和改造历史的全新子 Agent，只告知它具备基础 Python，不预先解释 LangChain、LangGraph 或 Mini DeerFlow。
- 让它从 Web 首页按正式顺序阅读全部章节，并在干净环境中逐个运行 Jupyter Notebook。
- 课程明确要求前，不允许读取 Mini DeerFlow 源码、测试文件、任务地图或改造说明来补全文档缺口。
- 每章记录：当前系统是什么、概念的自述定义、运行前预测、实际输出、完成的修改、仍然不懂的问题和被迫猜测的前置知识。
- 进入工程迁移后，再检查它能否把概念实验映射到 Mini DeerFlow 的模块、状态、控制流和安全边界。
- 输出逐章盲读日志、阻塞等级和最终能力矩阵。

## Acceptance

- 盲读 Agent 不向主 Agent 索取解释；遇到阻塞只记录课程缺口。
- 每章至少验证“能解释、能预测、能运行、能修改”四项，不以测试通过代替理解。
- 最终能够从入口追踪 Mini DeerFlow 的核心 Agent 调用链，并用自己的语言解释为何使用对应 LangGraph 机制。
- 报告明确区分课程缺口、环境故障和初学者合理遗忘。
- 报告保存为本地图下的中文 Markdown 工件。

## Answer

第一位不继承改写上下文的初学者 Agent 已按 README、01–11、Notebook、工程专题与 DeerFlow Guide 完成严格盲读，报告保存为 [`beginner-audit-1.md`](../artifacts/beginner-audit-1.md)。它能解释完整概念递进和 Mini DeerFlow 架构，但真实 Jupyter 暴露第 06/11 章 `asyncio.run(...)` 阻塞，完整 Git fetch 也无法完成，因此如实判定 `BLOCKED`。报告给出了精确实验、错误证据和最小修复范围，没有向主 Agent 索取答案。

Markdown、Notebook 和逐章修改证据已经完成；尚未满足的是“初学者 Agent 从真实 Web 首页亲自导航”。两个初学者子 Agent 的隔离会话均没有 Browser backend，不能用 curl 或根任务截图冒充它们亲自阅读。根任务的真实桌面/窄屏 QA 见 [`web-ui-qa.md`](../artifacts/web-ui-qa.md)；本项保持 `ready-for-human`，等待真实读者从线上首页完成独立体验反馈。
