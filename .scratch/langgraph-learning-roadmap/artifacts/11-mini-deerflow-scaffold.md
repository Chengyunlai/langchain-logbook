# Mini DeerFlow 工程骨架实现记录

> 完成日期：2026-07-13  
> 对应任务：[设计并搭建 Mini DeerFlow 工程骨架](../issues/11-scaffold-mini-deerflow.md)  
> 核心文档：[`mini_deerflow/ARCHITECTURE.md`](../../../mini_deerflow/ARCHITECTURE.md)

## 1. 结论

原先分散在第 01–11 章中的 Model、Schema、Knowledge、Tools、Context、State、Store、Middleware、Graph、Persistence/HITL 和 Subagent 工件，已经通过 `mini_deerflow.app` 组合成一个真实 Python 应用。学习者现在可以在无 API Key 环境中完成下面的工程闭环：

```text
安装 wheel
→ import package
→ 从显式 settings/dependencies 构建应用
→ 构造 application-controlled Runtime Context
→ 运行真实 create_agent / LangGraph model-tool-model 循环
→ 观察 Middleware trace 与 checkpointed state
→ 从 langgraph.json 加载独立 graph factory
```

骨架没有提前伪造 Sandbox 或 Gateway。`sandbox/`、`runtime/`、`api/` 和 `evals/` 已提供带约束的 Protocol/DTO/领域结果，为后续 Wayfinder 任务提供落点；未实现的隔离、服务和在线评测仍被明确标记为后续能力。

## 2. 关键架构决策

### 2.1 组合根集中在 `app.py`

- `ApplicationSettings` 保存非敏感 profile、默认权限和模型/Subagent 预算。
- `ApplicationDependencies` 保存 Model、KnowledgeIndex、Store、Checkpointer、SubagentRegistry 和 DelegationLedger 活对象。
- `build_application()` 为 CLI/单元测试装配独享的 `InMemoryStore` 与 `InMemorySaver`。
- 测试可以用 `dataclasses.replace()` 只替换一个依赖，无需复制 Agent factory。

### 2.2 本地应用入口与 Agent Server 入口分开

`langgraph.json` 指向 `mini_deerflow.app:make_graph`。factory 每次创建新的离线模型和 compiled graph，且明确不绑定 Checkpointer/Store；这是因为官方 Agent Server 会在运行时注入它管理的持久化后端。CLI 则需要独立、进程内的本地持久化，因此走 `build_application()`。

双轴审查曾发现初稿把 `InMemorySaver/InMemoryStore` 绑定到 manifest graph，这是部署语义错误；最终实现已用测试锁定 `make_graph()` 返回 graph 的 `checkpointer is None` 与 `store is None`。

### 2.3 离线模型可重复运行但仍驱动真实 Agent loop

章节级 `create_demo_lead_model()` 保持有界脚本，让单元测试能发现意外多调用；应用级 `create_repeating_demo_lead_model()` 循环提供“tool call → final answer”响应，使同一个应用实例能运行多个独立线程。两者都只替换模型决策，不绕开真实工具、Middleware、State reducer、Checkpointer 或 LangGraph runtime。

### 2.4 依赖方向由测试保护

`api → runtime → Agent Harness` 是允许方向。结构测试扫描所有非 API Python 文件，禁止 `mini_deerflow.api` 被 Harness 反向 import。API 请求 DTO 也不接受 `user_id` 或 permissions，避免把模型/客户端提交的身份误当认证结果。

## 3. 新增与调整的工程边界

| 边界 | 当前公共接口 | 后续用途 |
|---|---|---|
| 应用组合 | `build_application()`、`ApplicationDependencies`、`make_graph()` | Lead Agent 核心和部署入口继续复用 |
| 配置 | `ApplicationSettings.offline()` | provider、预算与本地运行默认值 |
| 运行身份 | `RunDescriptor` | thread/run manager、取消与恢复 |
| API DTO | `ConversationRequest/Response` | Gateway 与 SSE adapter，不泄漏完整 State |
| Sandbox port | `SandboxProvider`、`SandboxCommand/Result` | 第 12 章实现安全 provider/lifecycle |
| Eval contract | `EvaluationCase/Result`、`evaluate_required_terms()` | 第 13 章扩展 dataset、trajectory 和 judge |
| CLI smoke | `python -m mini_deerflow`、`make mini-deerflow` | 从 Notebook 进入正式 package 的最短验证路径 |

## 4. 官方资料与 DeerFlow 校准

- [LangSmith Application structure](https://docs.langchain.com/langsmith/application-structure)：确认 `langgraph.json` 的 dependencies/graphs/env 和 compiled graph/factory 入口。
- [LangSmith Agent Server](https://docs.langchain.com/langsmith/agent-server)：确认服务端自动注入 Checkpointer/Store，graph 代码不应绑定本地后端。
- [LangSmith Local development & testing](https://docs.langchain.com/langsmith/local-dev-testing)：确认 `langgraph dev` 与 `langgraph up` 的职责边界。
- DeerFlow `main` 阅读锚点 [`62f905342c14f76263a7c55e496af45c9a260853`](https://github.com/bytedance/deer-flow/tree/62f905342c14f76263a7c55e496af45c9a260853)：确认标准 manifest factory、Harness/App 依赖方向，以及 Gateway 可以与 `langgraph.json` 工具入口并存。

详细的三层边界、三张 Mermaid 图、四类数据表、失败模式与 Mini DeerFlow → DeerFlow 映射已经进入本地架构文档，并同步为文档站第 15 篇可搜索正文。

## 5. 验证证据

- TDD 红灯：新增测试最初因 `mini_deerflow.app` 缺失而 collection error，随后由组合根实现转绿。
- 工程骨架目标测试：`8 passed`；加入既有 Lead Agent 测试后 `10 passed`。
- 同一默认应用可连续完成两个独立线程的离线最小对话。
- `make mini-deerflow` 输出 offline profile、5 个工具、最终文本和 6 个 Middleware events。
- wheel 构建成功，并确认包含 `app.py` 及 `api/runtime/sandbox/evals` 子包。
- 全量门禁：`90 passed, 1 skipped`；唯一 warning 来自 LangSmith 依赖使用 Python 3.14 将弃用的 `ast.Str`。
- 教程验证：`0 new / 0 known / 0 stale`。
- 文档站：25 页构建成功，Pagefind 索引 15 页/3749 词，链接检查 `0 broken`；Astro 仅保留 2 个既有未使用 import hints。
- Standards 审查：`CLOSED`。
- Spec 审查：`CLOSED`。

## 6. 有意延后的范围

- 尚未安装 `langgraph-cli[inmem]` 或启动 Agent Server；本任务验证 manifest 结构、factory 可导入/构图和服务端持久化边界，真实 thread/run/SSE 服务属于 Wayfinder 任务 14。
- Sandbox 当前只有 provider contract，没有本地命令执行；路径隔离、生命周期和副作用审计属于 Wayfinder 任务 13。
- `EvaluationCase` 当前只提供确定性术语 smoke evaluator；dataset、trajectory、tracing 与回归比较属于 Wayfinder 任务 15。

这些延后点都有明确模块落点和任务验收标准，不是未登记的实现缺口。
