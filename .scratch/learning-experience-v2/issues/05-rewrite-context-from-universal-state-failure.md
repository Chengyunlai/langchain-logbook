# 从“万能 State”失败重写第 05 章 Context Engineering

Status: resolved
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

## Answer

第 05 章已重写为 9 个连续 lesson lab。章节先让 `UniversalState` 同时暴露 Token 和不可序列化连接，再使用原生 `context_schema` 与 `Runtime` 拆开运行依赖和 Graph State。

第二组实验先证明偏好放在 Thread State 后无法跨 Thread，再用原生 `InMemoryStore` 按认证用户 namespace 保存，并独立验证不同用户隔离。

第三组实验用 SQLite 业务账户制造 Store 陈旧余额，随后通过 `AccountRepository` 恢复业务数据库的权威地位。独立 checkpoint 实验证明两个 `thread_id` 的状态互不污染。

判断表已移动到全部失败与修复之后。Reducer 的首次解释继续归第 07 章；本章只说明 State 是可 checkpoint 的线程事实，不提前教授并行合并。

最后一个 migration lab 才导入 Mini DeerFlow，对照 `RuntimeContext`、安全视图、类型化 Artifact、checkpoint guard 与 `UserPreferenceRepository`，保留原有安全和持久化深度。

验证证据：9 个实验已离线执行并同步 Notebook；`make check` 通过 169 项测试（1 项外部集成跳过），教程 validator、Astro 构建、站内链接、发布契约与 SEO 检查全部通过。
