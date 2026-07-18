# Mini DeerFlow 测试、评测、可观测性与安全验收实现记录

> 完成日期：2026-07-13  
> 对应任务：[补齐测试、评测、可观测性与安全验收](../issues/15-add-testing-evaluation-observability.md)  
> 学习入口：[`mini_deerflow/EVALUATION_OBSERVABILITY.md`](../../../mini_deerflow/EVALUATION_OBSERVABILITY.md)  
> 研究基线：[`15-current-evaluation-observability-baseline.md`](../research/15-current-evaluation-observability-baseline.md)

## 1. 结论

Mini DeerFlow 已形成四个职责独立的质量系统：

```text
deterministic tests
→ versioned EvaluationDataset
→ real Graph target → AgentObservation
→ outcome + trajectory + budget feedback
→ baseline/candidate regression policy
→ optional LangSmith local/online adapters
→ one trace root + inherited child spans
→ production failure → sanitized regression case
```

默认路径无外部模型、无凭证、无上传；在线 Dataset/experiment 只有在显式提供 Client、远程 Dataset、API Key 和 `--confirm-upload` 时才执行。测试、评测、Trace 与 Runtime Event Journal 在代码和中文术语中保持分离。

## 2. Vendor-neutral 评测领域层

`mini_deerflow/evals/` 新增并扩展：

- `EvaluationCase`：结果必需/禁止文本、期望/禁止轨迹、exact/ordered-subsequence、模型/工具/token 预算和 tags；
- `EvaluationDataset`：名称、版本、唯一 case ID；
- `AgentObservation`：最终输出、轨迹、模型/工具调用数与 token；
- `MetricEvaluation`、`CaseEvaluation`、`EvaluationReport`：逐指标解释与聚合通过率；
- `RegressionPolicy/Comparison`：绝对通过率、最大下降和新案例失败门禁；
- `observation_from_agent_state()`：从真实 Mini DeerFlow messages 提取 `model → tool → model` 和 usage；
- `evaluate_case/dataset()`：确定性 outcome、trajectory、budget evaluator。

早期工程骨架的 `EvaluationResult/evaluate_required_terms()` 被保留为窄兼容投影，但与完整 outcome evaluator 复用 `match_text_constraints()`，不再维护两套文本规则。

## 3. 当前 LangSmith API 与离线/在线边界

官方和锁定环境实测确认当前入口为 `from langsmith import Client, evaluate, aevaluate`；`langchain.smith` 已无法导入。

离线 adapter：

- 用 UUID5 生成稳定的内存 `Example` ID；
- 实际调用 `evaluate(..., upload_results=False, max_concurrency=0)`；
- 将三个 vendor feedback 投影回稳定 `LangSmithFeedback`；
- 外层和每条 target 最内层均使用 `tracing_context(enabled=False)`；
- 在本机全局 tracing 已开启的环境里复测，不再尝试上传 Graph 子 span。

远程 adapter：

- `LangSmithDatasetAdapter.sync()` 使用版本化远程名称、`create_dataset` 和当前批量 `create_examples(examples=[...])`；
- `run_langsmith_online()` 必须显式接收远程 Dataset、Client 和 experiment prefix，并明确 `upload_results=True`；
- CLI 只有同时给出 `--langsmith-online-dataset`、Key 和 `--confirm-upload` 才会进入在线路径；
- 默认 `make test`、`make mini-deerflow-eval` 与 `--langsmith-local` 均不执行外部写入。

AgentEvals/OpenEvals 没有被假定为 LangSmith 传递依赖。课程默认实现确定性 trajectory matcher；LLM trajectory/security judge 仅作为可选在线扩展说明。

## 4. 真实观测接入与 root span 所有权

`LangSmithObservability` 使用 `tracing_context` 注入 project/tags/metadata，并要求 `root_owner` 明确为：

- `graph`：不再套 `traceable` wrapper，让 LangGraph/LCEL 自己形成 root 与子层级；
- `gateway`：只包一层 `traceable` root，已被追踪的 operation 会抛出 `DuplicateTraceRootError`。

`build_application(observability=...)` 已把最小观测端口注入组合根，`MiniDeerFlowApplication.invoke()` 实际包住真实 `graph.invoke()`，不是孤立示例。端口使用诚实的 `correlation_id`：本地 Application 可传 request ID，产品 Runtime 才能另存真实 `run_id`，不把 Request 冒充 Run。

## 5. 安全与恢复门禁

`quality/critical-regressions.json` 将以下关键类别映射到真实 pytest node ID：

- prompt injection / Store allowlist；
- tool authorization；
- path traversal 与 symlink escape；
- duplicate effect / replay；
- token/model-call budget；
- durable recovery；
- runtime ownership 与错误脱敏。

清单测试通过 AST 验证目标测试类和方法仍存在。默认 CI 执行完整 pytest，因此清单不是静态勾选表。文档明确 LLM judge 不能替代这些执行前硬边界。

## 6. 中文教学交付

`mini_deerflow/EVALUATION_OBSERVABILITY.md` 完成章节闭环：

1. 区分 test、evaluation、trace、Runtime Journal；
2. 用测试金字塔映射现有测试文件；
3. 解释 Dataset/Target/Evaluator 与 AgentObservation；
4. 分别讲 outcome、trajectory、budget 和 regression；
5. 记录全局 tracing 下“只设 upload_results=False 仍可能联网”的真实失败实验；
6. 给出在线三重显式选择与敏感信息边界；
7. 解释唯一 trace root、跨服务传播和三类存储关联；
8. 映射 DeerFlow 固定提交的 tracing factory、root callback、`attach_tracing=False`、RunJournal、worker 和 guardrail；
9. 提供失败实验、基础/工程/开放练习和延迟回忆问题。

专题包含 5 张 Mermaid，全部有文本替代；已进入 Astro 单一来源同步。README、Mini DeerFlow README、ARCHITECTURE、CONTEXT 和 RESOURCES 已同步。

## 7. DeerFlow 对照结论

本轮固定 DeerFlow `3e7baba39a9597e480dd82bbc18aee806679a2bf`。当前源码展示了成熟的 tracing provider factory、Graph root callback 注入、图内模型 `attach_tracing=False`、RunJournal、Gateway worker、guardrail 和大量确定性测试。

没有在固定源码树中发现正式的 LangSmith Dataset + `evaluate()` + trajectory regression 层。因此课程学习其 trace ownership 和运行时审计设计，再由 Mini DeerFlow 补齐可教学 eval layer，不虚构 DeerFlow 已提供的能力。

## 8. 双轴审查

Standards 初审发现两项判断/术语问题：早期 smoke 与完整 outcome 重复文本匹配；本地 request ID 被误称为 trace `run_id`。修复为共享 matcher 和 `correlation_id` 后，最终 Standards pass。

Spec 初审发现两项部分实现：观测 wrapper 尚未进入真实 Graph；只有 Dataset sync、没有显式在线 `evaluate()`。修复组合根注入、在线函数和 `--confirm-upload` CLI 后，最终 Spec pass。

## 9. 最终验证

- `make check`：通过；
- 离线测试：`128 passed, 1 skipped`；跳过项是显式外部 integration case；
- 专题定向测试：10 项，覆盖真实 Graph observation、三指标、回归、Dataset sync、online evaluate 参数、离线禁追踪、组合根观测和 duplicate root；
- 教程契约：`0 new / 0 known / 0 stale`；
- lock：216 packages，与 `pyproject.toml` 同步；
- Mini DeerFlow CLI：真实离线 model/tool/middleware loop 正常；
- 本地 LangSmith adapter：`pass_rate=1.0`、1 row、3 feedback，已开启的全局 tracing 环境下无上传错误；
- wheel：evals、observability、eval_demo 均已打包；
- 文档站：29 页，专题 5 张 Mermaid 全部转换，0 broken links；
- 双轴最终复核：Standards pass，Spec pass。

## 10. 有意延后的范围

- 大规模 Dataset 文件存储、split/tag 策略与人工 annotation queue；
- AgentEvals/OpenEvals 的可选 dependency extra 和真实 judge model 实验；
- 生产 online evaluator sampling/backfill/retention 与费用治理；
- 多服务 trace header 传播和 LangSmith/Langfuse 双 provider 对照；
- 真实业务 golden set 的人工批准流程。

这些不是任务 15 默认离线质量闭环的缺口。任务 16 将把现有 Harness、Runtime、Evals 和安全故障注入整合为最终长任务实战与 DeerFlow 源码阅读路线。
