# 实现持久化运行时、线程管理与 SSE/API

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 06, 12

## Why

Agent 从 Notebook 进入业务系统后，需要线程、运行、取消、恢复和流式事件边界。只用 LangServe 包装 Runnable 无法解释 DeerFlow Gateway 或 LangGraph 兼容运行时。

## Work

- 选择并实现本地持久化 checkpointer/store。
- 设计 thread/run API、SSE 事件 envelope、错误与取消语义。
- 对比 `langgraph.json`/Agent Server 与自建 FastAPI Gateway 的职责。
- 演示前端或命令行如何消费 messages、updates、values 和自定义事件。

## Acceptance

- 服务重启后可恢复线程状态。
- API 支持创建线程、启动运行、消费流、读取状态和恢复 interrupt。
- 流式协议与教程前文一致，有契约测试。
- 文档明确哪些能力来自 LangGraph，哪些是应用运行时自建能力。

## Answer

已完成产品 Thread/Run/Event SQLite repository、后台 `LocalRunManager`、原子状态机与取消、服务启动孤儿 Run 恢复、SQLite Checkpointer/Store 重建、真实 interrupt/new-Run resume、四种 LangGraph v2 stream mode、可重放 SSE 和 FastAPI adapter。请求体不能选择身份，ownership 在查询层执行；终态、terminal event 与 end 同事务提交；Graph 错误原文不会进入数据库或 SSE。

中文 [`RUNTIME_GATEWAY.md`](../../../mini_deerflow/RUNTIME_GATEWAY.md) 详细解释四类存储、状态机、SSE/Last-Event-ID、disconnect/cancel/backpressure、Agent Server 与自建 Gateway 选择，并以 DeerFlow `3e7baba39a9597e480dd82bbc18aee806679a2bf` 映射 Gateway/RunManager/EventStore/StreamBridge。

最终 `make check` 通过：`118 passed, 1 skipped`，教程漂移 `0/0/0`，28 页文档站构建、4 张专题 Mermaid 转换、0 断链。Standards/Spec 双轴复核均为 0 开放项。完整实现与遗留边界见[任务 14 实现记录](../artifacts/14-runtime-api-streaming.md)。
