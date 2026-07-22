# 改写第 04–06 章

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 02

## Why

工具、Context 与 Middleware 容易写成 API 分类。需要让三章继续沿同一个 Agent 的失败自然升级。

## Acceptance

- 手动工具循环先于 `create_agent` 封装解释。
- Context 和 Middleware 都从已观察的错误推导。
- 术语密度下降，但安全和所有权边界不弱化。

## Answer

第 04 章先让学习者手写 ToolMessage 闭环，再由 `create_agent` 接管通用循环。第 05–06 章从万能 State、权限泄漏、错误归一化与生命周期顺序等可见故障推导 Context 和 Middleware。

三章继续使用同一个研究助手；所有 lesson lab、代码、稳定输出和安全边界均保留。
