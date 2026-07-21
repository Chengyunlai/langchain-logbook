# 把双层案例扩展到其余章节

Status: claimed
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

## Progress

- 第 01 章已完成 7 个 lesson lab：单次模型、Runnable、tool intent 失败/修复、v2 envelope 失败/修复和 Mini DeerFlow 模型/事件入口。
- 完整 `create_agent` 工具循环的解释代码保留在正文，首次可执行工具循环后移第 04 章，避免提前解决后章核心问题。
- 第 01 章 Web、已执行 Notebook、稳定 stdout、站点发布副本与全量质量门禁均已验证。
- 第 02 章已完成 11 个 lesson lab：固定标签解析失败、最小 Pydantic 请求、真实 `with_structured_output`、危险默认值失败/修复、Artifact path 失败/修复、结果协议失败/修复、Schema 生命周期对照与 Mini DeerFlow Schema 迁移。
- `SubagentResult` 已从第 02 章后移第 11 章；第 02 章不再借子代理封装首次解释结构化输出。概念实验仅使用 Pydantic 与 LangChain 公共 fake chat model，Mini DeerFlow 只在最后一个迁移实验导入。
- 第 02 章 Web、已执行 Notebook、11 组稳定 stdout、段落长度、发布副本与全量质量门禁均已验证；同步前用户修改的 Notebook 保存在 `../backups/02_Structured_Output.ipynb`。
- 下一步处理第 03 章透明 RAG；任务保持 claimed，直到其余教程、工程专题、Capstone 与 DeerFlow 导读全部完成。
