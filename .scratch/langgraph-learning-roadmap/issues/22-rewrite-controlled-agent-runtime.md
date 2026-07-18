# 重写第二部：让 Agent 成为受控运行时

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 21

## Why

第一部已经交付可观察的模型、业务 Schema 和带来源的检索工具。第 04–06 章需要继续使用同一个研究交付任务，说明系统为何从固定检索链进入 Lead Agent，又为何必须拆分运行时事实并引入 Middleware 治理。

## Work

- 重写第 04 章，使 `search_knowledge` 自然进入首个 `model → tool → model` 循环。
- 重写第 05 章，用研究任务中的身份、线程计划、长期偏好、Secret 与连接对象解释 Context、State、Store 边界。
- 重写第 06 章，用同一 Lead Agent 的权限、PII、限额、摘要和失败处理引出 Middleware chain。
- 保留全部 sync 实验、失败实验、练习、自动验收与 DeerFlow 映射。

## Acceptance

- 第 04–06 章共享同一研究请求、Artifact 和 Lead Agent，不重置业务场景。
- 每章开头说明上一版系统，结尾交付可运行工件和下一项约束。
- 第 06 章自然引出“通用工具循环无法表达固定业务拓扑”，为 StateGraph 做准备。
- Notebook、测试、站点和链接验证通过。

## Answer

第 04–06 章已经接入同一个研究交付任务。第 04 章直接把第一部的 `search_knowledge` 装入 Lead Agent；第 05 章在同一个 factory 上划分 Runtime Context、Graph State、Store 与业务数据库；第 06 章让 Middleware 统一消费这些边界并治理 Prompt、模型、工具、权限、PII、预算与失败。

三章均以系统快照开篇，并以可运行工件和下一项约束结束。第 06 章明确留下“固定业务规则仍隐藏在通用工具循环中”，自然引出 StateGraph。已重新生成并执行三个 Notebook；专项测试 `36 passed`，教程审计 `0 new / 0 known / 0 stale`。
