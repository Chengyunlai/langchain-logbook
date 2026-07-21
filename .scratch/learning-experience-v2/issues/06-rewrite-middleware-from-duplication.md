# 从重复治理逻辑重写第 06 章 Middleware

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 04

## Why

当前章节先展示生命周期 hook 和完整治理链，读者尚未体验权限、计数、日志和异常转换散落在模型与工具调用点的重复和遗漏。

## Work

- 先构建没有 Middleware 的最小 Agent，在多个工具中重复权限、计数、日志和异常处理。
- 制造至少一个因遗漏检查或顺序错误产生的可观察失败。
- 从重复职责推导横切关注点，再逐步引入 before/after hook、`wrap_model_call` 和 `wrap_tool_call`。
- 最后迁移到 Mini DeerFlow 的治理链、摘要、HITL 和 listener 边界。

## Acceptance

- 生命周期图和 hook 名称出现在需求形成之后。
- 每个 Middleware 实验只抽取一种横切能力，并展示抽取前后的执行记录。
- 读者能解释 Middleware 与显式业务 Graph 的边界。
- 现有异步对称、短路、副作用和错误分类内容全部保留。

## Answer

第 06 章已重写为 14 个连续 lesson lab。第一个 Agent 没有 Middleware，发布工具因遗漏权限检查真实执行副作用；紧邻实验再用原生 `wrap_tool_call` 短路工具并返回配对的拒绝 ToolMessage。

生命周期图移动到需求形成之后。before/after 顺序通过两个原生 Middleware 的真实事件验证；`wrap_model_call` 分别实验安全 Context 投影、应用控制的模型路由与模型调用预算短路。

工具错误部分先让原始 `TimeoutError` 中断 Agent，再从零实现同步/异步 `wrap_tool_call`，把异常分类成稳定 payload。异步取消继续上抛为 `NodeCancelledError`，没有被普通错误消息吞掉。

Summarization 与 HITL 使用 LangChain 内置 Middleware 独立运行，分别展示来源标记和副作用为零。Runnable listener 的错误签名与修复相邻出现，明确它不等于 Agent Middleware。

最后一个 migration lab 才导入 Mini DeerFlow，运行默认治理链并展示注册顺序、PII 脱敏、生命周期 trace 与最终回答。原有摘要、HITL、异步、短路、错误分类和 listener 深度均保留。

验证证据：14 个实验已离线执行并同步 Notebook；`make check` 通过 169 项测试（1 项外部集成跳过），教程 validator、Astro 构建、站内链接、发布契约与 SEO 检查全部通过。
