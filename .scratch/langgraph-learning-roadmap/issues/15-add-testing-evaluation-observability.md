# 补齐测试、评测、可观测性与安全验收

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 12, 13, 14

## Why

能运行不等于可交付。核心 Agent 业务需要同时验证确定性代码、图路径、工具轨迹、最终质量、成本和安全边界。

## Work

- 建立节点、reducer、middleware、工具和 API 单元测试。
- 建立图路径、interrupt/resume、subagent 和 sandbox 集成测试。
- 使用当前 LangSmith API 演示 dataset、offline eval、trajectory eval 和回归比较。
- 接入 LangSmith/Langfuse 之一作为主观测示例，并解释回调根节点与重复 span 问题。
- 加入 prompt injection、越权工具、路径穿越、重复副作用和 token budget 测试。

## Acceptance

- 不再使用已移除的 `langchain.smith` API。
- 测试可以在无外部 API 时运行，在线评测可显式启用。
- 评测同时覆盖结果与执行轨迹。
- CI 能阻止关键安全和恢复行为退化。

## Answer

已完成 provider-neutral `EvaluationDataset → AgentObservation → outcome/trajectory/budget → regression comparison`，并用真实 Mini DeerFlow model/tool loop 验证轨迹。当前 LangSmith adapter 同时提供内存 Example + `upload_results=False` 的真正离线路径、显式远程 Dataset sync，以及要求远程名称/Client/`--confirm-upload` 的在线 `evaluate()` 入口；不再使用已移除的 `langchain.smith`。

`LangSmithObservability` 明确 Graph/Gateway root 所有权，组合根可注入并实际包住 `graph.invoke()`；`correlation_id` 与产品 Run/request 保持类型语义。`quality/critical-regressions.json` 把 prompt injection、工具授权、路径穿越、重复副作用、预算和持久恢复映射到真实测试。

中文 [`EVALUATION_OBSERVABILITY.md`](../../../mini_deerflow/EVALUATION_OBSERVABILITY.md) 含 5 张 Mermaid、失败实验、在线/离线边界、安全矩阵和 DeerFlow 固定提交 tracing/RunJournal/guardrail 映射。最终 `make check` 通过：`128 passed, 1 skipped`，教程漂移 `0/0/0`，29 页文档站、0 断链；Standards/Spec 双轴复核均 pass。完整证据见[任务 15 实现记录](../artifacts/15-testing-evaluation-observability.md)。
