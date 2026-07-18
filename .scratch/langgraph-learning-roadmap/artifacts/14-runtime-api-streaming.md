# Mini DeerFlow 持久化 Runtime、FastAPI Gateway 与 SSE 实现记录

> 完成日期：2026-07-13  
> 对应任务：[实现持久化运行时、线程管理与 SSE/API](../issues/14-implement-runtime-api-streaming.md)  
> 学习入口：[`mini_deerflow/RUNTIME_GATEWAY.md`](../../../mini_deerflow/RUNTIME_GATEWAY.md)  
> 架构入口：[`mini_deerflow/ARCHITECTURE.md`](../../../mini_deerflow/ARCHITECTURE.md)

## 1. 结论

Mini DeerFlow 已完成从 Agent Harness 到产品运行时的纵切面：

```text
authenticated identity
→ product Thread ownership
→ pending Run + single-active policy
→ LocalRunManager background worker
→ LangGraph v2 messages/updates/values/custom
→ JSON-safe persistent RunEvent
→ id/event/data SSE + heartbeat + Last-Event-ID replay
→ success/interrupted/error/cancelled + atomic end
→ FastAPI Thread/Run/state/resume/cancel routes
```

该实现是单进程、本地 SQLite 教学运行时，不声称具备生产多 worker 的 queue/lease/pubsub。它保留了理解 DeerFlow Gateway/Runtime 所需的 ownership、Run 状态机、事件日志、StreamBridge 和 Harness 分层关系。

## 2. 持久化与领域边界

新增 `ThreadRecord`、`RunRecord`、`RunEvent`、`ThreadStateView` 和显式 `RunStatus`。`SqliteRuntimeRepository` 保存产品 Thread/Run/Event，并在所有公共查询中同时校验 authenticated `user_id`；无权访问与不存在统一投影为 not found，避免枚举其他用户资源。

四类事实保持分离：

- Runtime SQLite：产品 ownership、Run 状态、取消标志和 SSE journal；
- SQLite Checkpointer：Graph State、next tasks 和 interrupt；
- SQLite Store：跨线程用户偏好；
- Sandbox workspace：线程 Artifact 文件。

同一 Thread 的 pending/running Run 由 partial unique index 约束。事件 sequence 在 `BEGIN IMMEDIATE` 中分配；`finish_run()` 在同一个事务内写终态、可选 interrupt/error 和强制 end。普通 `transition_run()` 不允许写终态，防止绕开该不变量。

本地 worker 启动时把遗留 pending/running Run 恢复为 `worker_restarted/error/end`，既释放 active lock，也给重连客户端留下终态事实。文档明确该策略不能直接用于多 worker。

## 3. RunManager、取消与恢复

`LocalRunManager` 通过最小 `GraphRuntime.stream/get_state` 协议执行 compiled graph：

- message Run 转换为 Graph messages input；
- resume Run 使用相同 thread ID 和 `Command(resume=...)`；
- 每个 v2 StreamPart 复用严格 JSON normalizer 后持久化；
- snapshot 存在 interrupt 时，旧 Run 进入 interrupted；恢复创建新 Run；
- cancel 在开始和每个 stream part 间协作检查；
- Graph exception 只投影异常类型和稳定 code，不保存原始文本、路径或 Secret；
- close、等待超时、worker ownership 和 terminal status 均有明确行为。

`request_cancel()` 在一个写事务中检查 active status 并更新标志，关闭 complete/cancel 的 TOCTOU 竞态。断连 cleanup 若与刚完成的 Run 竞态，只保留既有终态。

## 4. Gateway、HTTP 与可重放 SSE

`MiniDeerFlowGateway` 是传输无关的应用服务；`create_fastapi_app()` 只负责身份依赖、路由、HTTP 状态和 `StreamingResponse`。请求 DTO 不接受 `user_id`、permissions 或 workspace/provider，让身份只能来自认证边界。

已实现：

- 创建 Thread；
- 启动/读取/等待/取消 Run；
- 读取 checkpoint state 投影；
- 以新 Run 恢复 interrupt；
- 全量或 `Last-Event-ID` 增量消费事件；
- `messages/updates/values/custom` 四种 Graph mode；
- product `metadata/interrupt/error/end` 事件；
- comment heartbeat 不推进 event ID；
- `continue/cancel` 两种 disconnect policy；
- FastAPI 首帧预取后仍把连接关闭传播给内层 iterator。

事件 ID 是 `<run_id>:<sequence>`。Graph producer 先写 SQLite，再由 SSE consumer 读取，因此网络断线不会制造“已发出但不可重放”的窗口。终态日志若缺少 end 会明确报 conflict，不静默伪装成完整流。

## 5. 官方基线与 DeerFlow 映射

当前实现以官方 LangGraph Streaming、Persistence、Interrupts、Agent Server、Join thread stream、Cancel runs，以及 WHATWG SSE/FastAPI StreamingResponse 为事实源。`RESOURCES.md` 已加入这些入口。

专题对照 DeerFlow `main` 固定提交 `3e7baba39a9597e480dd82bbc18aee806679a2bf`，阅读路径为：

```text
Gateway routers
→ gateway/services.py
→ runtime/runs/manager.py
→ runtime/runs/worker.py
→ run store + event store
→ runtime/stream_bridge/base.py
→ Agent Harness graph
```

文档明确对比两条部署路线：Agent Server 提供标准数据库/队列/Thread/Run/stream 基础设施；自建 FastAPI Gateway 只应在认证、现有业务数据库、协议或调度确有定制需求时承担对应成本。

## 6. 中文教学交付

`mini_deerflow/RUNTIME_GATEWAY.md` 不是 API 清单，而是完整章节闭环：

1. 从“Graph 能运行但不是服务”的失败模型开始；
2. 解释四类持久化事实和依赖方向；
3. 以 Repository、RunManager、interrupt、SSE 四个纵切面讲 TDD；
4. 提供 4 张 Mermaid 与逐图文本替代；
5. 给出 stream mode、API、Agent Server/Gateway 决策表；
6. 解释 replay、at-least-once、disconnect、cancel、backpressure 和生产边界；
7. 提供 DeerFlow 源码地图、失败诊断矩阵、5 个进阶练习和延迟回忆题。

专题已进入 Astro 单一来源同步流程；README、Mini DeerFlow README、ARCHITECTURE、Lead/Sandbox 专题、CONTEXT 和 RESOURCES 均已同步当前能力。

## 7. TDD 与双轴审查证据

定向测试共 11 项，覆盖：

- repository 重启、ownership、状态机、单调 sequence；
- startup orphan recovery；
- 四种 stream modes、state 与 terminal event；
- 真实 LangGraph interrupt/resume；
- 协作取消；
- Graph error 脱敏与 error/end；
- Checkpointer/Store/Runtime 三类 SQLite 服务重建；
- FastAPI create/start/wait/state/stream/resume/ownership；
- Last-Event-ID 重放与非法游标；
- StreamingResponse 首帧后断连的 cancel 传播。

双轴初审发现：终态/end 非原子、错误原文泄漏、取消 TOCTOU、Gateway repository feature envy、首帧预取关闭不传播。全部修复后 Standards 与 Spec 复核均为 0 个开放项。

## 8. 最终验证

- `make check`：通过；
- 离线测试：`118 passed, 1 skipped`；跳过项是显式外部 integration case；
- 唯一 pytest warning 来自 LangSmith 依赖使用 Python 3.14 将弃用的 `ast.Str`；
- 教程契约：`0 new / 0 known / 0 stale`；
- lock：216 packages，FastAPI `0.139.x` 与 lock 同步；
- Mini DeerFlow CLI smoke：offline graph/tool loop 正常；
- wheel：runtime、api、persistence、streaming 模块均已打包；
- 文档站：28 页，4 张 Runtime Mermaid 均转换，18 页进入搜索索引，`0 broken links`；
- Astro 保留 2 个既有 unused icon hints，Vite 保留 Mermaid 大 chunk 提示，均非本任务功能错误。

## 9. 有意延后的范围

- 多 worker queue、lease、heartbeat、retry、drain 和 hard cancellation；
- Redis/pubsub、event retention/compaction 和 replay window；
- 生产 IAM/JWT、rate limit、quota 和多租户数据库迁移；
- async database provider 与高并发压测；
- tracing、内部错误关联 ID、trajectory eval 和安全回归矩阵。

最后一组内容进入任务 15；任务 16 再把完整 Harness/Runtime/Evals 组合为最终长任务实战与 DeerFlow 导读。
