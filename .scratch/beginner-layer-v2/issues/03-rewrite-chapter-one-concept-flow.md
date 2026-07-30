# 按概念依赖重写第 01 章工程深入

Status: resolved
Triage: ready-for-human
Type: task
Blocked by: 02

## Why

真实读者审核指出，第 01 章工程深入直接展示 Runnable、`tool_calls` 和 v2 stream 的现象，却没有先解释概念是什么、为什么需要以及 LangChain 如何实现。API 出现顺序早于概念依赖，读者能运行代码，却难以形成准确心智模型。

## Work

- 用最直白的话解释 Runnable，再说明 Prompt、Chat Model 和输出解析器如何通过 `|` 组成固定管道；
- 从“模型为什么需要外部能力”开始解释 Tool，依次介绍 `@tool`、`bind_tools`、`AIMessage.tool_calls`、应用执行责任和 `create_agent`；
- 先解释 streaming 的用途，再介绍 `stream_mode`、v2 事件信封及 `type`、`ns`、`data` 的读取顺序；
- 解释 Mini DeerFlow 为什么增加模型工厂和 Stream adapter，以及真实模型接入时变化与不变的边界；
- 同步 Markdown、Notebook 和文档站，由用户逐段审核。

## Acceptance

- 每个概念遵守“是什么 → 为什么需要 → LangChain 怎么做 → 示例发生什么 → 责任边界”的顺序；
- Fake Model 明确为不访问外部供应商、只按脚本返回预设消息的测试替身；
- 模型提出工具调用请求与应用执行工具的责任不再混淆；
- 用户确认第 01 章初学者主线和工程深入均可通过；
- `make check` 全部通过。

## Answer

- 第 01 章 Runnable、Tool、`bind_tools`、`tool_calls`、`create_agent`、streaming、Mini DeerFlow 接缝和真实模型部分已按概念依赖顺序重写。
- 用户先确认初学者主线无问题，再确认 Runnable/Tool 新叙述准确，最后确认第 01 章剩余内容可以通过。
- 第 01 章 Notebook 与文档站副本同步；离线示例执行成功。
- 发布候选完整门禁通过：186 passed、1 skipped；Tutorial validation 为 0；35 页构建成功；链接、发布和 SEO 契约均为 0。
