# Mini DeerFlow 综合实战与 DeerFlow 源码导读实现记录

> 完成日期：2026-07-14  
> 对应任务：[整合课程、综合实战与 DeerFlow 源码导读](../issues/16-integrate-course-capstone-deerflow-guide.md)  
> 综合实战：[`mini_deerflow/CAPSTONE.md`](../../../mini_deerflow/CAPSTONE.md)  
> 源码导读：[`mini_deerflow/DEERFLOW_GUIDE.md`](../../../mini_deerflow/DEERFLOW_GUIDE.md)  
> 研究基线：[`16-current-deerflow-capstone-reading-map.md`](../research/16-current-deerflow-capstone-reading-map.md)

## 1. 结论

课程现已形成一条从第 01 章到真实 DeerFlow 源码的连续交付路径：

```text
01–04 model/schema/retrieval/tool
→ 05–06 Context/State/Store/Middleware
→ 07–10 Graph/Persistence/Interrupt/Effect
→ 11 Subagent patterns
→ Mini DeerFlow Lead/Sandbox/Runtime/Evaluation
→ Capstone 长任务纵切面
→ DeerFlow 四条源码调用链
```

最终项目不是天气、翻译或单轮对话。它实际执行检索、两个临时 specialist、线程工作区草稿、持久审批、Checkpointer 重开、edit/reject、幂等 effect intent、正式 Artifact 和 outcome/trajectory/budget 评测。综合代码只装配已有公共接口，没有创建第二套平行 Agent 框架。

## 2. 综合实战代码

`mini_deerflow/capstone.py` 新增：

- `CapstoneRequest`：稳定请求、Thread、用户和正式报告路径；路径在任何 workspace 副作用前拒绝绝对路径和 `..`；
- `PublishIntent`：审批与 effect ledger 之间的领域类型；edit 后的 path/digest 在 resume 记账前重新验证；
- `CapstoneResult`：返回状态、草稿/正式 Artifact、Subagent 状态、effect count、重建证据和评测报告；
- `run_capstone_scenario()`：复用真实 `MiniDeerFlowApplication`、`SubagentExecutor`、Sandbox provider、Approval Graph、SQLite Checkpointer、Effect Ledger 和 evaluator；
- CLI：`python -m mini_deerflow.capstone`，由 `make mini-deerflow-capstone` 提供确定性入口。

默认成功轨迹为：

```text
model
→ search_knowledge
→ model
→ subagent:research
→ subagent:coding
→ interrupt:risk
→ resume:approve
→ write_workspace_file
```

## 3. 质量门与副作用边界

初审发现“正式 Artifact 写完才评测”无法实现发布门禁，现已改为三段：

1. **Draft gate**：草稿完成后、审批前检查两个 specialist 的终态、必需/禁止内容、轨迹和预算；
2. **Prepublish gate**：恢复审批后、正式写入前检查截至 resume 的精确轨迹；
3. **Final evaluation**：真实写入后再检查包含 `write_workspace_file` 的完整轨迹。

research timeout 会保留草稿和结构化 `timed_out` 状态，但状态转为 `quality_rejected`，不创建审批 effect，也不发布正式报告。审批 edit 若把路径改成 `../escaped.md`，`PublishIntent` 会在 ledger 前拒绝，`effect_count` 保持 0。

本地 ledger 只证明同一 request/payload 的本地发布意图只记一次。远端 Git、邮件、支付或对象存储仍需要 provider idempotency key 或 transactional outbox；课程没有把本地 SQLite 证据夸大为远端 exactly-once。

## 4. 从空目录重建

`CAPSTONE.md` 提供两条互补路线：

- **参考工程复现**：从真正空目录复制明确列出的 package、锁文件、manifest、测试和质量清单，执行 `uv sync`、6 个 capstone tests 和最终命令；已在 `/tmp/capstone-scaffold-check` 实测成功；
- **学习者重建**：从 M1 到 M10 建立目录，每关复制对应外部测试契约，先红后绿，并在进入下一关前运行全部旧测试。

这修复了早期“`uv init` 后直接调用空目录中不存在的 Makefile”问题。里程碑现在有文件落点和精确测试命令，而不是只有概念表。

## 5. 故障注入与 Runtime 对齐

综合实战直接覆盖：

- approve/reject/edit；
- Checkpointer 关闭并重新打开；
- 同 request replay 的 effect count 为 1；
- 初始与 edit 后路径穿越；
- 一个 specialist timeout、另一个正常完成；
- 失败报告在正式发布前被质量门拒绝。

产品 Runtime 的 SSE replay 和 worker recovery 不被 capstone 的内存返回值冒充；文档给出真实 Runtime 测试节点：

- `SqliteRuntimeRepositoryTests::test_sse_frames_are_replayable_after_last_event_id`；
- `SqliteRuntimeRepositoryTests::test_local_worker_restart_marks_orphaned_active_runs_error_and_replayable`。

学习者扩展任务要求把 Harness capstone 与 RunManager/Gateway 真正组合，证明 interrupt 结束旧 Run、resume 创建新 Run、断线重连不重复应用事件。

## 6. DeerFlow 当前源码导读

2026-07-14 复核官方 `bytedance/deer-flow` HEAD：

```text
4af617835805dd7cd78162ebed02fd6b782ea8bf
2026-07-14T08:58:06+08:00
feat(trace): add agent observability with Monocle (#4024)
```

`DEERFLOW_GUIDE.md` 不按目录漫游，而提供四条路线：

1. `backend/langgraph.json → make_lead_agent → create_agent`：注册入口和 Lead 组合根；
2. `ThreadState → Runtime Context → Middleware/tools`：数据与治理边界；
3. `task_tool → SubagentExecutor → ephemeral create_agent`：委派、策略继承、递归与终态边界；
4. `Gateway router → services → RunManager → worker → RunJournal/EventStore/StreamBridge → SSE`：产品交付链。

本次 commit 的重点是 graph root 统一挂 tracing callbacks，内部 model/subagent model 使用 `attach_tracing=False`。导读把诊断链与产品事件链明确分开：

```text
graph root callback → model/tool/subagent child spans → trace backend
RunManager/worker → RunJournal → EventStore → StreamBridge → SSE
```

两条链可以用 thread/run/trace ID 关联，但 Trace 不能替代可重放产品 Journal，Journal 也不是完整父子调用树。

## 7. 中文教学与图示交付

- `CAPSTONE.md`：3 张 Mermaid；
- `DEERFLOW_GUIDE.md`：7 张 Mermaid；
- 每张图都有文本替代和明确的读图顺序；
- 导读包含三层架构、Lead 组合、trace root、Middleware 生命周期、Subagent 时序、Gateway Run 时序、Trace/Journal 分离；
- 包含五个错误阅读实验、固定源码映射、故障问题、ADR 练习和最终验收清单；
- 第 01–11 章各增加“本章如何推进 Mini DeerFlow”，把章节产物连接到综合实战；
- README、Mini README、ARCHITECTURE、CONTEXT、RESOURCES 和 Astro 单一来源同步入口已更新。

本任务不使用 imagegen：所有新增关系都是精确调用链、状态和所有权关系，Mermaid 更可维护、可审查且适合版本控制。

## 8. 双轴审查

Standards 初审发现：

- edit payload 在 ledger 后才由 Sandbox 拒绝；
- 10 张新增图缺“读图顺序”。

修复 `PublishIntent` 前置验证、effect count 测试和所有读图顺序后，Standards 复审 PASS。

Spec 初审发现：

- 空目录只有里程碑，没有可执行脚手架；
- timeout/SSE/edit/restart 的练习与测试映射不完整；
- 正式 Artifact 先写后评，无法阻止 critical failure 发布。

补齐两条空目录路线、精确 fault test 节点和 draft/prepublish gate 后，Spec 复审 PASS。

## 9. 最终验证

- `make check`：通过；
- 全部离线测试：`135 passed, 1 skipped`；跳过项为显式外部 integration case；
- 教程契约：`0 new / 0 known / 0 stale`；
- lock：216 packages，与 `pyproject.toml` 同步；
- `make mini-deerflow-capstone`：`completed`、两个 Subagent 完成、`effect_count=1`、Checkpointer 确认重开、评测 `pass_rate=1.0`；
- 空目录复现：6 个 capstone tests 通过，最终命令通过；
- 故障证据：timeout/edit traversal/SSE replay/worker restart 4 个精确节点通过；
- 文档站：33 pages，21 pages 进入中文搜索索引，0 broken links；
- 新增 Mermaid：10/10 被转换，10/10 含文本替代和读图顺序；
- 双轴最终复核：Standards PASS，Spec PASS。

## 10. 有意留给任务 17 的范围

- 用真实浏览器检查桌面与窄屏的 Mermaid、表格和长代码块；
- 核对站点导航、章节排序、下载入口和搜索体验；
- 执行 API smoke、Notebook 与发布命令的最终组合记录；
- 区分自动通过项、在线依赖项和必须人工观察的发布项。

这些属于发布视觉 QA，不是任务 16 核心业务、源码路线或自动验收的缺口。
