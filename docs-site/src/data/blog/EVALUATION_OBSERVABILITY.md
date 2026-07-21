---
title: "Mini DeerFlow 专题实战：测试、Agent 评测、可观测性与安全回归"
description: "用测试、结果/轨迹/预算评测与 Trace 证明 Agent 的质量和安全边界。"
pubDatetime: 2025-01-01T00:00:00Z
featured: false
tags: ["tutorial"]
sourcePath: "mini_deerflow/EVALUATION_OBSERVABILITY.md"
learningOrder: 16
learningStage: "agent-engineering"
learningStageTitle: "把单图扩展为可交付的 Agent 系统"
learningGoal: "用测试、结果/轨迹/预算评测与 Trace 证明 Agent 的质量和安全边界。"
contentType: "main"
---

> 校准日期：2026-07-13  
> 前置内容：第 05–11 章、[`LEAD_AGENT_CORE.md`](/langchain-logbook/posts/lead_agent_core/)、[`SANDBOX_EXTENSIONS.md`](/langchain-logbook/posts/sandbox_extensions/) 与 [`RUNTIME_GATEWAY.md`](/langchain-logbook/posts/runtime_gateway/)  
> 对应实现：`mini_deerflow/evals/`、`mini_deerflow/observability.py`、`quality/critical-regressions.json`  
> 可执行验收：`tests/test_mini_deerflow_evaluation_observability.py`

## 系统快照：运行到终态，不等于交付质量已经成立

前面的 Mini DeerFlow 已经能规划、检索、委派、保存状态、暂停审批，并通过持久化 Run 和 SSE 对外服务。但“这次运行成功了”只说明程序走到了终态。

上一篇的 `RunStatus.success` 是运行时事实：worker 正常消费 Graph、写入 end，客户端可以重放。它不评价报告有没有引用、Agent 是否绕路写文件，也不评价模型多调用了几次。

本专题就从同一个 success Run 继续。先把执行投影成稳定 Observation，再分别判断结果、轨迹和预算；之后才讨论 Trace 如何解释单次执行，以及 LangSmith 怎样作为可选平台 adapter 接入。

它不能证明答案正确、工具路径合理、成本没有失控、安全边界仍然有效，也不能解释生产环境里某次失败发生在哪个节点。

本专题建立四个彼此协作、不能互相替代的质量系统：确定性测试负责代码与安全契约，Agent evaluation 负责结果和执行轨迹，observability trace 负责解释一次真实执行，Runtime Event Journal 负责向产品客户端提供可重放事实。完成本专题后，学习者应该能把自己的 Agent 从“能演示”推进到“能回归、能解释、能阻止危险退化”。

## 1. 先建立四个不同的问题空间

| 系统 | 输入 | 主要输出 | 回答的问题 | 不应承担的职责 |
|---|---|---|---|---|
| 单元/集成测试 | 固定 fixture、fake model、Graph/HTTP 调用 | pass/fail、异常、结构断言 | 代码契约和状态转换是否正确？ | 判断开放式回答是否“足够好” |
| Agent evaluation | 版本化 dataset、target、evaluator | outcome/trajectory/budget 分数与解释 | Agent 在一批代表性任务上表现如何？ | 代替工具授权、路径隔离等硬控制 |
| Observability trace | 一次真实 Run 的 span tree | 时延、token、输入输出、父子调用 | 这一次为什么慢、贵、错或走了异常路径？ | 成为客户端的 durable event source |
| Runtime Event Journal | Run 生命周期与客户端可见事件 | 单调序号、SSE replay、终态 | 客户端断线后从哪里继续？ | 保存完整模型 prompt 或 evaluator 基线 |

<!-- diagram:id=qa-four-systems -->
```mermaid
flowchart TB
    CHANGE["代码 / Prompt / 模型 / 工具变更"] --> TEST["确定性测试<br/>节点、Reducer、授权、恢复、安全"]
    TEST --> EVAL["离线评测<br/>Outcome + Trajectory + Budget"]
    EVAL --> DEPLOY["显式发布"]
    DEPLOY --> TRACE["生产 Trace<br/>一次执行的因果树"]
    DEPLOY --> JOURNAL["Runtime Journal<br/>客户端可重放事实"]
    TRACE --> FAILURE["失败样本 / 成本异常 / 人工反馈"]
    JOURNAL --> FAILURE
    FAILURE --> DATASET["脱敏并加入版本化 Dataset"]
    DATASET --> EVAL
```

**图的文本替代**：每次代码、Prompt、模型或工具变更先经过确定性测试，再经过结果、轨迹和预算离线评测，之后才显式发布。生产执行同时进入 Trace 和 Runtime Journal；失败样本与人工反馈脱敏后进入版本化 Dataset，形成下一轮离线回归，而不是直接拿生产输入反复调用线上模型。

一个常见误区是“有 LangSmith trace 就已经有评测”。Trace 记录事实；evaluator 才对事实应用质量标准。另一个误区是“LLM judge 能检查安全”。模型判断可以补充语义风险，却不能替代工具 allowlist、路径解析和幂等账本中的确定性拒绝。

## 2. 测试金字塔必须沿真实边界展开

Agent 项目的测试不应只在最外层比较自然语言。越接近底层契约，越要使用稳定、精确、低成本的断言；越接近开放式质量，才越适合 dataset 和 judge。

<!-- diagram:id=qa-testing-pyramid -->
```mermaid
flowchart TB
    E2E["少量显式在线实验<br/>真实 provider / 平台"]
    GRAPH["Graph 与 Runtime 集成<br/>路径、interrupt/resume、SSE replay"]
    COMPONENT["组件测试<br/>Middleware、Tool、Sandbox、Repository、API"]
    UNIT["大量单元测试<br/>Reducer、Schema、Policy、Evaluator"]
    UNIT --> COMPONENT --> GRAPH --> E2E
```

**图的文本替代**：底层是数量最多的 Reducer、Schema、Policy 和 evaluator 单元测试；向上是 Middleware、Tool、Sandbox、Repository 与 API 组件测试；再向上是 Graph 路径、interrupt/resume 和 SSE 重放集成测试；顶部只有少量需要真实供应商或平台的显式在线实验。

Mini DeerFlow 当前测试落点如下：

| 层级 | 代表文件 | 核心断言 |
|---|---|---|
| 类型/Reducer | `test_mini_deerflow_schemas.py`、`test_mini_deerflow_lead_agent_core.py` | schema 拒绝非法数据；Artifact 按路径确定合并 |
| Middleware/Context | `test_mini_deerflow_context_engineering.py`、`test_mini_deerflow_middleware.py` | Store allowlist、权限、PII、错误投影、模型调用预算 |
| Graph | `test_mini_deerflow_graph_workflows.py`、`test_mini_deerflow_persistence_hitl.py` | Command/Send 路径、checkpoint、interrupt/new-Run resume、重复副作用 |
| Subagent/Sandbox | `test_mini_deerflow_subagents.py`、`test_mini_deerflow_sandbox_extensions.py` | 输入隔离、并发/超时/输出预算、路径与 symlink 护栏 |
| Runtime/API | `test_mini_deerflow_runtime_gateway.py` | ownership、状态机、取消、启动恢复、SSE replay、错误脱敏 |
| Agent quality | `test_mini_deerflow_evaluation_observability.py` | outcome、trajectory、budget、回归阈值、trace root 所有权 |

测试图节点时应每个测试重新构图并使用新的 `InMemorySaver`，避免 checkpoint 在案例之间泄漏。LangGraph 也允许通过 `graph.nodes[...]` 单测节点，或者用 `update_state` 把图放到指定状态后只验证局部路径；这些做法来自当前 [LangGraph testing 指南](https://docs.langchain.com/oss/python/langgraph/test)。

## 3. Evaluation 不是一个分数，而是一组稳定契约

LangSmith 当前把评测问题拆成 Dataset、Target、Evaluator 三部分：

- **Dataset**：版本化案例集合，描述“哪些任务值得长期重复验证”；
- **Target**：被评应用，把一个案例变成一次 `AgentObservation`；
- **Evaluator**：把观察事实和参考契约比较，返回可解释 feedback。

Mini DeerFlow 把这三个概念放在 vendor-neutral 领域层，避免整个业务被平台对象绑住：

```python
from mini_deerflow.evals import EvaluationCase, EvaluationDataset

dataset = EvaluationDataset(
    name="lead-agent-core",
    version="2026-07-13",
    cases=(
        EvaluationCase(
            case_id="persistence-with-source",
            prompt="解释 LangGraph persistence 并给出引用",
            required_terms=("引用",),
            forbidden_terms=("无法验证",),
            expected_trajectory=("model", "search_knowledge", "model"),
            forbidden_trajectory=("write_workspace_file",),
            max_model_calls=2,
            max_tool_calls=1,
            max_total_tokens=300,
            tags=("retrieval", "critical"),
        ),
    ),
)
```

这里没有保存“一段唯一标准答案”。开放式 Agent 通常允许多种正确表述，课程改用可确定验证的业务契约：答案必须给出引用，不能声称无法验证；检索任务应经过模型、知识搜索、模型，但不能写工作区；模型和工具调用次数受限。

### 3.1 为什么要单独定义 AgentObservation？

不同 provider、Graph 版本和 tracing 平台返回的原始对象会变化。Evaluator 如果直接遍历某个 LangSmith `RunTree` 或某个供应商 token response，测试就会被 transport 细节污染。项目先把一次执行投影为稳定观察：

```python
class AgentObservation(BaseModel):
    output: str
    trajectory: tuple[str, ...] = ()
    model_calls: int = 0
    tool_calls: int = 0
    total_tokens: int = 0
```

`observation_from_agent_state()` 能从真实 Mini DeerFlow State 中提取最终 AI 文本、`model → tool-name → model` 轨迹和调用计数。平台 adapter 只负责把同一对象转换为 Example 或 feedback，不重新定义质量规则。

<!-- diagram:id=qa-evaluation-flow -->
```mermaid
sequenceDiagram
    participant DS as EvaluationDataset
    participant T as Target
    participant G as Mini DeerFlow Graph
    participant A as State Adapter
    participant E as Evaluators
    participant R as EvaluationReport

    loop 每个 EvaluationCase
        DS->>T: case(prompt + contracts)
        T->>G: invoke(prompt)
        G-->>A: ThreadState
        A-->>T: AgentObservation
        T->>E: case + observation
        E-->>R: outcome / trajectory / budget
    end
    R-->>DS: pass_rate + per-case explanations
```

**图的文本替代**：评测集逐条把案例交给 Target，Target 调用 Mini DeerFlow Graph，再由 State Adapter 投影成 AgentObservation；三个 evaluator 分别检查结果、轨迹和预算，最终报告既有总通过率，也保留每条案例的失败解释。

## 4. 三类 evaluator 分别发现什么

### 4.1 Outcome evaluator：验证交付结果

本地 outcome evaluator 检查 `required_terms` 和 `forbidden_terms`。它适合引用标记、固定事实集合、JSON 字段、错误码、Artifact 路径等确定规则，不适合判断文风是否自然。

失败报告不会只给 `score=0`，而是保留：

```json
{
  "missing_terms": ["resume"],
  "present_forbidden_terms": []
}
```

真实项目可继续增加 schema evaluator、citation evaluator 和 reference-fact evaluator；不要把所有条件塞进一个巨大 Prompt judge，否则失败难以定位。

### 4.2 Trajectory evaluator：验证 Agent 怎样得到结果

最终答案偶然正确，不代表路径安全。例如模型可以绕过批准直接写文件，或在一次检索任务中无限循环。轨迹 evaluator 支持两种匹配：

- `exact`：步骤必须完全一致，适合确定性 Graph 和关键安全流程；
- `ordered_subsequence`：期望步骤按顺序出现，允许中间有额外合理步骤，适合 Agent 工具路径。

同时可定义 `forbidden_trajectory`。对于“研究 persistence”案例，`write_workspace_file` 即使最终文本正确也必须使案例失败。

官方 AgentEvals 还提供 trajectory match 与 LLM trajectory judge，见 [Agent trajectory evaluations](https://docs.langchain.com/langsmith/trajectory-evals)。本项目没有把 `agentevals` 加进默认依赖，因为当前确定性 matcher 已覆盖核心教学契约；只有路径存在多种合理等价形式时，才值得在显式在线 extra 中引入 judge。

### 4.3 Budget evaluator：验证资源上界

预算 evaluator 检查：

- 模型调用次数；
- 工具调用次数；
- 总 token 数。

它不是成本账单，但可以快速阻止“新增 middleware 后模型多调用三次”“失败重试没有上限”这类结构性退化。真正费用仍应从 provider usage span 或账单系统读取。

### 4.4 同一份正确文本，为什么会得到三种结论

下面故意让三条 observation 都输出“结论包含引用”。只改变执行轨迹和调用次数：

```python
from mini_deerflow.evals import (
    AgentObservation,
    EvaluationCase,
    evaluate_case,
)


case = EvaluationCase(
    case_id="persistence-with-source",
    prompt="解释 persistence 并给出引用",
    required_terms=("引用",),
    expected_trajectory=("model", "search_knowledge", "model"),
    forbidden_trajectory=("write_workspace_file",),
    max_model_calls=2,
    max_tool_calls=1,
)
observations = {
    "good": AgentObservation(
        output="结论包含引用",
        trajectory=("model", "search_knowledge", "model"),
        model_calls=2,
        tool_calls=1,
    ),
    "unsafe": AgentObservation(
        output="结论包含引用",
        trajectory=(
            "model",
            "search_knowledge",
            "write_workspace_file",
            "model",
        ),
        model_calls=2,
        tool_calls=2,
    ),
    "expensive": AgentObservation(
        output="结论包含引用",
        trajectory=("model", "search_knowledge", "model"),
        model_calls=3,
        tool_calls=1,
    ),
}

for name, observation in observations.items():
    result = evaluate_case(case, observation)
    metrics = {metric.key: metric.passed for metric in result.metrics}
    print(name, "=", metrics, "case_passed =", result.passed)
```

```text
good = {'outcome': True, 'trajectory': True, 'budget': True} case_passed = True
unsafe = {'outcome': True, 'trajectory': False, 'budget': False} case_passed = False
expensive = {'outcome': True, 'trajectory': True, 'budget': False} case_passed = False
```

三条 outcome 都通过，因为文本相同。unsafe 触发禁止工具且多调用一次工具；expensive 路径正确，却多调用一次模型。一个总分无法告诉你该修权限、规划还是重试预算。

**动手修改**：把 unsafe 的 max_tool_calls 放宽到 2。观察 budget 变绿而 trajectory 仍失败；说明预算放宽为什么不能解除工具路径禁令。

## 5. 回归比较必须同时看整体和单案例

只比较平均分会隐藏关键案例退化。例如 100 条案例中，一个 prompt injection 案例从通过变失败，另一个文风案例从失败变通过，总通过率没有变化，但发布仍然不安全。

```python
comparison = compare_reports(
    baseline,
    candidate,
    policy=RegressionPolicy(
        min_pass_rate=0.90,
        max_pass_rate_drop=0.02,
        block_new_failures=True,
    ),
)
```

三个门禁分别表达不同意图：

| 规则 | 含义 |
|---|---|
| `min_pass_rate` | 候选版本的绝对质量下限 |
| `max_pass_rate_drop` | 相对已接受基线最多可下降多少 |
| `block_new_failures` | 任何原本通过的案例变失败都阻止发布 |

生产项目通常会按 tag 分层：`critical/security/recovery` 必须全部通过；开放式研究质量可以允许小幅统计波动。不要用一个全局 0.8 阈值把二者混在一起。

下面让 baseline 和 candidate 都保持 50% 通过率，但交换通过的案例：

```python
from mini_deerflow.evals import (
    AgentObservation,
    EvaluationCase,
    EvaluationDataset,
    RegressionPolicy,
    compare_reports,
    evaluate_dataset,
)


cases = (
    EvaluationCase(
        case_id="critical-recovery",
        prompt="恢复",
        required_terms=("恢复完成",),
    ),
    EvaluationCase(
        case_id="style",
        prompt="文风",
        required_terms=("简洁",),
    ),
)
dataset = EvaluationDataset(name="release-gate", version="v1", cases=cases)
baseline_outputs = {
    "critical-recovery": "恢复完成",
    "style": "冗长",
}
candidate_outputs = {
    "critical-recovery": "恢复失败",
    "style": "简洁",
}
baseline = evaluate_dataset(
    dataset,
    lambda case: AgentObservation(output=baseline_outputs[case.case_id]),
)
candidate = evaluate_dataset(
    dataset,
    lambda case: AgentObservation(output=candidate_outputs[case.case_id]),
)
comparison = compare_reports(
    baseline,
    candidate,
    policy=RegressionPolicy(
        min_pass_rate=0.5,
        max_pass_rate_drop=0.0,
        block_new_failures=True,
    ),
)

print("baseline_pass_rate =", baseline.pass_rate)
print("candidate_pass_rate =", candidate.pass_rate)
print("new_failures =", comparison.new_failures)
print("improvements =", comparison.improvements)
print("failed_rules =", comparison.failed_rules)
print("release_passed =", comparison.passed)
```

```text
baseline_pass_rate = 0.5
candidate_pass_rate = 0.5
new_failures = ('critical-recovery',)
improvements = ('style',)
failed_rules = ('new_failures',)
release_passed = False
```

平均值完全没变，但关键恢复案例从通过变失败。`block_new_failures` 让这次“用关键正确性换文风改进”的发布无法蒙混过关。

**动手修改**：关闭 block_new_failures。记录 comparison 是否通过，再解释 production policy 为什么仍应按 critical tag 单独设 100% 门槛。

## 6. 运行真正离线的评测

默认命令不需要模型 Key、LangSmith Key 或网络：

```bash
make mini-deerflow-eval
```

当前锁定版本的关键输出如下；完整命令还会打印每个 metric 的 explanation 和 details：

```text
dataset_name = mini-deerflow-course
case_id = persistence-with-source
case_passed = true
metric_status = {outcome: true, trajectory: true, budget: true}
observed_trajectory = [model, search_knowledge, model]
pass_rate = 1.0
```

这不是手写的“预期答案”。Target 真实运行 Mini DeerFlow model → search_knowledge → model，再由 `observation_from_agent_state()` 提取输出、轨迹和调用次数。

**动手修改**：在内置 case 中把 max_model_calls 从 2 改为 1。重新运行，定位 budget details 中的 observed 与 limit；不要只看 pass_rate 从 1.0 变成 0.0。

它运行真实的 Mini DeerFlow `model → search_knowledge → model` 循环，并输出三个指标的结构化 JSON。若要验证当前 LangSmith evaluator 协议，但仍不上传：

```bash
uv run --locked python -m mini_deerflow.eval_demo --langsmith-local
```

适配器使用：

```python
from langsmith import evaluate

evaluate(
    target,
    data=in_memory_examples,
    evaluators=[outcome, trajectory, budget],
    upload_results=False,
    max_concurrency=0,
    blocking=True,
)
```

这里有两个容易遗漏的边界：

1. `upload_results=False` 在锁定的 LangSmith 0.10.x 中仍是 beta 参数；API 变化被隔离在 `mini_deerflow/evals/langsmith.py`。
2. 如果进程环境已开启自动 tracing，只设置 `upload_results=False` 仍不足以证明被评 LangGraph 不联网。适配器还在评测外层和每条 target 调用的最内层使用 `tracing_context(enabled=False)`。

第二条来自一次真实失败实验：全局 tracing 打开时，初版 CLI 曾尝试上传 Graph 子 span 并得到认证错误。修正后，离线测试明确验证关闭作用域，CLI 也在同一环境下不再发起上传。官方对本地运行的边界说明见 [Run an evaluation locally](https://docs.langchain.com/langsmith/local)。

当前入口必须是 `from langsmith import Client, evaluate, aevaluate`。旧的 `langchain.smith` 在锁定环境中已经无法导入，只能出现在迁移说明里，不能出现在可执行教程。

## 7. 远程 Dataset 与在线实验必须显式启用

`LangSmithDatasetAdapter.sync()` 演示当前批量 API：

```python
from langsmith import Client
from mini_deerflow.evals import LangSmithDatasetAdapter

summary = LangSmithDatasetAdapter(Client()).sync(dataset)
print(summary.dataset_name, summary.example_count)
```

它会执行外部写入，因此默认 `make test` 和 `make mini-deerflow-eval` 都不会调用它。同步规则是：

1. 远程名称固定为 `<dataset.name>:<dataset.version>`；
2. 不存在时用 `Client.create_dataset(...)` 创建；
3. 本地 case ID 通过 UUID5 生成稳定 Example ID；
4. 使用当前 `Client.create_examples(examples=[...])` 批量接口；
5. 返回 dataset ID、名称和案例数，便于审计。

在线 experiment、生产 online evaluator 和 LLM-as-judge 需要平台 workspace、API key，以及可选 judge model 凭证。它们属于显式 integration profile，不能成为默认 CI 的先决条件。

大批量 Python 任务可使用 `aevaluate()` 和明确的 `max_concurrency`。参见 [How to evaluate agents](https://docs.langchain.com/langsmith/evaluate-llm-application)。

项目提供一个不会被默认门禁调用的在线入口。它要求远程 Dataset 名称和确认上传标志同时存在：

```bash
uv run --locked python -m mini_deerflow.eval_demo \
  --langsmith-online-dataset 'lead-agent-contracts:v2' \
  --experiment-prefix 'release-2026-07-13' \
  --confirm-upload
```

命令还会检查 `LANGSMITH_API_KEY`。缺少 Dataset、Key 或 `--confirm-upload` 都会在调用 `evaluate()` 前失败；其实现明确传递 `upload_results=True`，使在线写入成为可审计选择，而不是读取到环境变量后静默发生。

## 8. 可观测性：先决定谁拥有 root span

LangGraph/LCEL 会自动形成 runnable 父子层级。最稳定的策略是在一次请求最外层建立一个 tracing context 或 callback root，让 Graph、模型和工具继承；不要在 Gateway、Graph invocation 和每个 model factory 上分别创建新的 provider root。

`LangSmithTracingConfig.root_owner` 只有两种合法值：

- `graph`：Graph invocation 自己是根；wrapper 只注入 project、tags 和 metadata，不再套 `@traceable`；
- `gateway`：Gateway 是人为根，用一次 `traceable(..., run_type="chain")` 包住整个业务操作；若操作已被追踪则抛出 `DuplicateTraceRootError`。

<!-- diagram:id=qa-trace-root-good-bad -->
```mermaid
flowchart LR
    subgraph BAD["错误：多个 instrumentation owner"]
        BG["Gateway root"] --> BA["Graph root"]
        BA --> BM1["Model provider root"]
        BA --> BT["Tool span"]
        BT --> BM2["Second model root"]
    end

    subgraph GOOD["正确：一个 root，子调用继承"]
        GR["Request / Graph root"] --> GN["Graph node spans"]
        GN --> GM["Model spans"]
        GN --> GT["Tool spans"]
        GN --> GS["Subagent spans"]
    end
```

**图的文本替代**：错误方案让 Gateway、Graph 和模型 provider 各自创建根，UI 中会出现多个互不相连或重复的模型 span；正确方案只让请求或 Graph 拥有一个根，Graph node、模型、工具和 Subagent 都继承为子 span。

示例：

```python
tracer = LangSmithObservability(
    LangSmithTracingConfig(
        enabled=True,
        project_name="mini-deerflow-prod",
        root_owner="graph",
        tags=("lead-agent",),
    )
)

result = tracer.run(
    "lead-agent",
    lambda: graph.invoke(inputs, config=config, context=context),
    correlation_id=run.run_id,
    user_id=authenticated_user.id,
    metadata={"run_id": run.run_id, "thread_id": run.thread_id},
)
```

本地组合根已经提供真实接入点，而不只是展示独立 wrapper：

```python
application = build_application(observability=tracer)
application.invoke("解释 persistence", run=run_descriptor)
```

`MiniDeerFlowApplication.invoke()` 会让 observability 包住真正的 `graph.invoke()`，并注入 thread、request、user 和 model profile。默认 `observability=None`，所以离线课程和测试不会创建 trace；生产装配必须显式传入 adapter。

`correlation_id`、`user_id`、dataset version、release SHA 和 model profile 应放根 metadata，让子 runnable 继承。产品 Runtime 可使用真实 Run ID；本地应用没有产品 Run，只能使用 request ID。

Secret、认证 token、未脱敏输入和 Sandbox 正文不得进入 metadata。继承与选择性追踪见 [Trace LangChain applications](https://docs.langchain.com/langsmith/trace-with-langchain) 和 [Add metadata and tags](https://docs.langchain.com/langsmith/add-metadata-tags)。

跨服务不能依赖进程内 `contextvars`。需要把 trace header 通过 HTTP/queue 传播，再由下游恢复 parent，参考 [Distributed tracing](https://docs.langchain.com/langsmith/distributed-tracing)。

## 9. Trace、Runtime Journal 和评测库如何关联

三种存储可以共享关联 ID，但生命周期不同：

```text
Runtime Run ID: run-abc
Trace metadata:  {run_id: run-abc, thread_id: thread-7, release: sha...}
Eval metadata:   {source_run_id: run-abc, dataset_version: 2026-07-13}
```

- Runtime DB 保存客户端必须重放的 metadata/update/error/end；
- Trace 平台保存工程诊断需要的 span tree、时延和 usage；
- Eval store 保存脱敏后的案例、参考契约、反馈和实验比较。

删除 trace 不应使 SSE 无法重连；清理 Runtime Journal 不应删除评测基线；把生产失败加入 Dataset 前要重新审查 PII、版权、Secret 与保留期限。

## 10. 安全验收：硬边界先于语义 judge

`quality/critical-regressions.json` 是关键安全与恢复契约清单。每条都必须映射到一个真实测试 node ID，测试会用 AST 验证目标类和方法确实存在，避免清单在重命名后成为装饰。

| 风险 | 确定性控制与测试 | 为什么不能只用 LLM judge |
|---|---|---|
| Prompt injection | Store/上下文 allowlist，不把不可信偏好升级为系统权限 | Judge 可能漏判，且攻击发生前就应限制可见能力 |
| 越权工具 | Middleware + tool registry 根据应用权限拒绝 | 模型说“我不会调用”不是授权控制 |
| 路径穿越/symlink escape | Sandbox canonical path 与边界检查 | 文件系统边界必须 100% 可重复 |
| 重复副作用 | effect intent ledger、稳定 idempotency key、resume 测试 | 重放发生时已经造成真实副作用 |
| Token/调用预算 | model/tool/token 上限 | Judge 成本本身也可能失控 |
| 持久恢复 | checkpoint、Run 状态机、启动恢复测试 | 必须证明 crash/interrupt 后状态不矛盾 |
| 错误泄露 | bounded error projection | traceback/Secret 一旦发出无法撤回 |

OpenEvals 提供 PII leakage、prompt injection、code injection 等安全 prompts，可作为显式在线语义补充。参见 [OpenEvals security prompts](https://github.com/langchain-ai/openevals/tree/d4a096b76c216feca6252cbdc277cf75c2b29a11/python/openevals/prompts/security)。

本项目不默认安装 OpenEvals。即使未来启用，其评分也不能替代上表中的确定性硬门禁。

### 10.1 CI 如何真正阻止退化

默认质量门禁：

```bash
make test
```

会在 `LANGCHAIN_LOGBOOK_PROFILE=offline` 下运行所有 pytest，并收集但跳过需要外部服务的 integration case。关键清单测试保证以下类别始终有真实覆盖：`prompt_injection`、`tool_authorization`、`path_traversal`、`duplicate_effect`、`token_budget`、`durable_recovery`。

不要只把 manifest 文件存在当成功；CI 必须运行被映射的完整测试集。也不要让一个可波动的在线 judge 决定主分支能否构建，否则平台故障和质量退化会变成同一个红灯。

## 11. 从生产失败到回归案例的闭环

<!-- diagram:id=qa-production-feedback-loop -->
```mermaid
stateDiagram-v2
    [*] --> Observe: 生产 Run
    Observe --> Triage: trace / journal / user feedback
    Triage --> Reject: 非问题、重复或不可保留
    Triage --> Sanitize: 可复现质量或安全问题
    Sanitize --> Dataset: 脱敏 + 最小输入 + 参考契约
    Dataset --> Red: 在当前版本复现失败
    Red --> Fix: 修改代码 / Prompt / policy
    Fix --> Green: 测试 + offline eval
    Green --> Baseline: 人工批准新基线
    Baseline --> Observe: 发布并继续观测
    Reject --> [*]
```

**图的文本替代**：生产 Run 先通过 trace、journal 和用户反馈进入 triage；非问题或不可保留数据被拒绝，真实问题脱敏并缩成 Dataset 案例；先在当前版本复现红灯，再修复并让确定性测试和离线评测变绿；人工批准基线后发布，继续进入生产观测。

推荐的案例最小化问题：

1. 哪个输入条件是触发失败的必要条件？
2. 失败是结果错误、路径错误、预算错误还是运行时错误？
3. 是否能用 fake model 或固定工具响应稳定复现？
4. 哪条参考契约可以避免把一次自然语言答案写成“黄金全文”？
5. 是否包含 PII、Secret、客户文件或不应长期保存的数据？

## 12. 对照 DeerFlow：学习架构，不虚构其能力

本专题固定阅读 DeerFlow `3e7baba39a9597e480dd82bbc18aee806679a2bf`，避免裸 `main` 漂移。Mini DeerFlow 与 DeerFlow 的映射如下：

> **锚点说明**：这里保留的是本专题写作时的历史对照版本，用来复核 tracing 结论；全书最后四条源码路线的统一验收版本，以 [`DEERFLOW_GUIDE.md`](/langchain-logbook/posts/deerflow_guide/) 的 `4af6178` 为准。

| 本专题概念 | Mini DeerFlow | DeerFlow 固定提交入口 | 阅读重点 |
|---|---|---|---|
| tracing provider factory | `observability.py` 的 LangSmith 配置 | [`tracing/factory.py`](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/tracing/factory.py) | 多 provider 如何创建 callback，但不决定业务拓扑 |
| root callback ownership | `root_owner=graph/gateway` | [`lead_agent/agent.py`](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/agents/lead_agent/agent.py) | callback 在最外层 graph invocation 注入 |
| 图内模型不重复追踪 | Graph-owned 模式不套第二层 root | [`models/factory.py`](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/models/factory.py) | `attach_tracing=False` 如何避免 provider 重复 span |
| 产品运行日志 | `runtime_events` | [`runtime/journal.py`](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/runtime/journal.py) | RunJournal 与观测 provider 同挂 callbacks，但职责不同 |
| Gateway worker | `LocalRunManager` | [`runtime/runs/worker.py`](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/runtime/runs/worker.py) | 运行生命周期、stream 与 trace metadata 如何汇合 |
| tool guardrail | Middleware/allowlist/关键回归 | [`guardrails/middleware.py`](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/guardrails/middleware.py) | 执行前 allow/deny 是运行时控制，不是 evaluator |

截至校准日期，DeerFlow 有成熟的 tracing、Runtime journal、guardrail 和大量确定性测试入口；没有在固定源码树中发现正式的 LangSmith Dataset + `evaluate()` + trajectory regression 层。因此正确结论是：**学习 DeerFlow 的 trace ownership 和运行时审计设计，再由自己的项目补齐评测层**，而不是宣称 DeerFlow 已经实现本专题全部机制。

## 13. 失败实验：亲自观察三个“看似正确”的方案

### 实验 A：只评最终答案

把 `forbidden_trajectory=("write_workspace_file",)` 暂时删除，让一个测试 observation 在检索任务中先写文件、再输出正确答案。Outcome 会通过，但 trajectory 不再能阻止越权路径。恢复该约束并解释：产品质量不仅是“说了什么”，也包括“做了什么”。

### 实验 B：只设置 upload_results=False

在隔离测试进程中开启自动 tracing，删除 `run_langsmith_offline()` 内层 `tracing_context(enabled=False)`，再运行真实 Graph target。观察应用子 span 仍可能尝试使用环境中的 tracing 配置。实验后恢复代码；不要在含真实 Key 的共享环境里故意上传测试数据。

### 实验 C：Gateway 与 Graph 同时创建 root

把 `root_owner="gateway"` 与一个已经 `@traceable` 的 Graph operation 同时交给 wrapper。正确实现会抛出 `DuplicateTraceRootError`；若强行绕过，观测 UI 可能出现两个根或重复模型调用。这个异常是架构所有权冲突，不是普通网络故障。

## 14. 练习与检索问题

### 基础练习

1. 为“审批后写报告”增加一个 `exact` trajectory case，要求出现 `interrupt → resume → write_workspace_file`。
2. 构造 baseline/candidate，使总通过率相同但出现一个新失败，验证 `block_new_failures=True` 仍阻止发布。
3. 为某个 API 错误案例增加 outcome evaluator，断言错误码稳定且输出不含 `Traceback`。

### 工程练习

1. 把课程内置 dataset 从 Python 迁移到带 JSON Schema 的版本化 JSONL，但保持领域模型和 evaluator 不变。
2. 为不同 tag 建立分层 policy：critical 必须 100%，research quality 允许 2% drop。
3. 给 Runtime Run、Trace 和 Eval Example 建立同一个非敏感 correlation ID，并写测试证明任何一层删除都不破坏另外两层。

### 开放式练习

1. 什么时候 `ordered_subsequence` 会放过危险步骤？你的业务是否需要部分顺序、工具参数或状态变更 evaluator？
2. 一个 LLM trajectory judge 的误判应该阻止部署、进入人工队列，还是只记录告警？依据风险等级设计策略。
3. 如果同一工具有多个语义等价实现，怎样定义轨迹而不过度拟合具体 tool name？

### 检索练习

不回看正文，回答：

- Dataset、Target、Evaluator 各自拥有哪个变化轴？
- 为什么 `upload_results=False` 和关闭 target tracing 是两个不同开关？
- Runtime Journal 与 Trace 都记录事件，为什么不能合并？
- DeerFlow 的 `attach_tracing=False` 解决了什么所有权问题？
- 哪五类安全行为必须先用确定性测试，而不是只用 judge？

## 15. 自动验收清单

```bash
# 评测与观测专题
uv run --locked pytest -q tests/test_mini_deerflow_evaluation_observability.py

# 真实离线 Agent 结果/轨迹/预算
make mini-deerflow-eval

# 项目完整门禁
make check
```

完成标准：

- 不存在可执行的 `langchain.smith` 导入；
- 默认测试和评测不需要外部 API，也不会因全局 tracing 打开而上传；
- 在线 experiment 只有在提供远程 Dataset、API Key 和 `--confirm-upload` 时才执行；
- 同一案例同时得到 outcome、trajectory、budget 反馈；
- 回归比较能识别绝对阈值、通过率下降和单案例新失败；
- prompt injection、越权工具、路径穿越、重复副作用、预算和恢复都有关键清单映射；
- trace 只有一个所有者创建 root，Graph/model/tool 继承为子 span；
- 组合根注入的观测 adapter 实际包住真实 `graph.invoke()`；
- 中文说明能把 Mini DeerFlow 模块准确映射到 DeerFlow 固定提交。

## 16. 延伸资料

- [LangSmith evaluation overview](https://docs.langchain.com/langsmith/evaluation)
- [Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [Manage datasets programmatically](https://docs.langchain.com/langsmith/manage-datasets-programmatically)
- [Code evaluator SDK](https://docs.langchain.com/langsmith/code-evaluator-sdk)
- [Agent trajectory evaluations](https://docs.langchain.com/langsmith/trajectory-evals)
- [Online code evaluators](https://docs.langchain.com/langsmith/online-evaluations-code)
- [LangSmith tracing for LangChain](https://docs.langchain.com/langsmith/trace-with-langchain)
- [Prevent logging sensitive data](https://docs.langchain.com/langsmith/mask-inputs-outputs)
- [LangGraph testing](https://docs.langchain.com/oss/python/langgraph/test)
- [LangChain integration testing](https://docs.langchain.com/oss/python/langchain/test/integration-testing)
- [LangChain guardrails](https://docs.langchain.com/oss/python/langchain/guardrails)
- [AgentEvals official repository](https://github.com/langchain-ai/agentevals/tree/4b68015eeb444a5fc6fb986932d92a999446890c)
- [OpenEvals official repository](https://github.com/langchain-ai/openevals/tree/d4a096b76c216feca6252cbdc277cf75c2b29a11)
- [DeerFlow pinned repository](https://github.com/bytedance/deer-flow/tree/3e7baba39a9597e480dd82bbc18aee806679a2bf)

质量系统已经具备独立契约。下一篇不再引入新框架，而是把检索、委派、草稿、审批、恢复、发布与评测装配成一条完整研究交付纵切面。

继续阅读：[Mini DeerFlow 综合实战](/langchain-logbook/posts/capstone/)。