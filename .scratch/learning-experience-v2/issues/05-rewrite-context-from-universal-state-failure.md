# 从“万能 State”失败重写第 05 章 Context Engineering

Status: open
Triage: ready-for-agent
Type: task
Blocked by: 04

## Why

Context、State、Store 和业务数据库的判断表目前先于失败体验，学习者只能记结论，无法根据所有权、生命周期、恢复和序列化要求自行推导边界。

## Work

- 从身份、Token、连接、偏好和消息都放入 State 的错误实现开始。
- 展示 Secret 进入 checkpoint、连接不可序列化、跨 thread 偏好丢失和业务事实被误当记忆等失败。
- 从失败推导所有权与生命周期问题，再分别引入 Runtime Context、Graph State、Store 和业务数据库。
- 使用原生 API 从零构建最小 Agent，最后迁移到 Mini DeerFlow 的安全视图、ThreadState 和 Repository。
- 把 Reducer 的首次教学移交第 07 章，只保留本章理解所需的 State 写入规则。

## Acceptance

- 判断表位于推导之后，而不是章节开场。
- 概念实验不通过 `mini_deerflow.context` 等封装首次解释机制。
- 同用户不同 Thread、跨 Thread Store 和不同用户隔离都有可观察输出。
- 工程迁移保留现有安全与持久化边界。
