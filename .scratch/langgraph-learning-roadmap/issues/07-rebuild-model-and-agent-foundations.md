# 重构增强模型层与 Agent 封装层课程

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 04, 05, 06

## Why

现有 01–04 是项目最成熟的部分，应在保留详细内容的基础上消除层级混淆，并把所有示例接入贯穿项目。

## Work

- 校准消息、Runnable、结构化输出、RAG、工具 Schema、`bind_tools` 与 `create_agent` 的边界。
- 修正 streaming v1/v2 示例并解释事件 envelope。
- 把 RAG 从孤立链路升级为可被 Agent 使用的检索能力，同时保留索引工程细节。
- 为 Mini DeerFlow 建立模型工厂、基础工具和第一个 Lead Agent。

## Acceptance

- 每章 Markdown 与 Notebook 内容同步且能通过自动验证。
- 学习者能解释“增强模型”和“运行 Agent”的区别。
- 章节保留详细原理、失败实验和工程说明。
- 课程产物可以直接被后续 State/Middleware 章节导入。

## Answer

已完成 01–04 章增强模型层与 Agent 封装层重构，详细实施证据见 [01–04 章模型层与 Agent 封装层重构实施记录](../artifacts/07-model-agent-foundations.md)。

本轮保留原有详细内容，并补齐模型/Runnable/Agent 分层、结构化输出三态、可替换知识索引与 recall@k、工具 Runtime/Command、Lead Agent 完整工具循环、v2 streaming adapter、失败实验、分层练习和 DeerFlow 映射。`mini_deerflow` 已提供后续章节可直接导入的模型、Schema、知识、工具和 Agent 公共边界。

Markdown 的必备实验会确定性生成并离线执行同名 Notebook；`quality/lesson-contracts.json` 防止两侧同时删除实验造成假绿，package region 测试保证源码是唯一事实源。最终结果为 42 passed、1 skipped，tutorial validation 0 new / 16 known / 0 stale，文档站 22 pages、0 broken links。课程已知债务由 23 项降至 16 项，01–04 本轮债务已清零。
