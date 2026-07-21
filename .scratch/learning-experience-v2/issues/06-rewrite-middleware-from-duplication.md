# 从重复治理逻辑重写第 06 章 Middleware

Status: open
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
