# 任务 15：当前评测、可观测性与安全验收基线

> 校准日期：2026-07-13  
> 研究范围：LangSmith、LangGraph、LangChain 官方文档与第一方源码；DeerFlow 官方仓库当前 `main` 固定提交；本仓库锁定环境。  
> 目的：为课程任务 15 提供可直接实现的 API 基线，避免继续使用已经移除的 `langchain.smith`，并明确哪些能力默认离线、哪些需要显式联网和凭证。

## 1. 结论先行

1. **课程默认门禁必须是无凭证、无网络、确定性的 `pytest`**。节点、reducer、middleware、工具授权、路径边界、幂等副作用、interrupt/resume 与 token budget 都应首先在这一层阻止回归。LangGraph 官方测试指南推荐每个测试重新构图、使用新的 `InMemorySaver`，并允许通过 `graph.nodes[...]` 单测节点或通过 `update_state` 做部分路径测试。[LangGraph Test](https://docs.langchain.com/oss/python/langgraph/test)
2. **“offline evaluation”不等于“完全离线运行”**。LangSmith 的 offline evaluation 指上线前、面向数据集的实验；它仍可能访问 LangSmith 和模型供应商。只有在使用本地 examples、纯本地 target/evaluator，并显式传入 `upload_results=False` 时，才真正做到结果、应用 trace 和 evaluator trace 都不上传。[Evaluation overview](https://docs.langchain.com/langsmith/evaluation) · [Run an evaluation locally](https://docs.langchain.com/langsmith/local)
3. **本仓库当前正确入口是 `from langsmith import Client, evaluate, aevaluate`**。锁定版本是 `langsmith==0.10.2`；`langchain.smith` 在当前环境中实际导入失败，不能出现在新代码或教程中。[LangSmith Python reference](https://reference.langchain.com/python/langsmith) · [PyPI: langsmith 0.10.2](https://pypi.org/project/langsmith/0.10.2/)
4. **结果评测与轨迹评测必须分开**。最终答案可用代码 evaluator、LLM-as-judge 或 reference comparison；Agent 工具轨迹优先用 AgentEvals 的确定性 match，只有路径存在多种合理解时再用 LLM judge。[Agent Evals](https://docs.langchain.com/oss/python/langchain/test/evals) · [AgentEvals official repository](https://github.com/langchain-ai/agentevals)
5. **LangSmith tracing 的首选是一次性建立根 trace，让 LangGraph/LCEL 子调用继承上下文**。全局使用 `LANGSMITH_TRACING=true`，请求级使用 `tracing_context`，或显式把一个 `LangChainTracer` 放在最外层 graph invocation 的 `RunnableConfig.callbacks`。不要同时在图根和图内 model 实例上重复绑定新的 provider handler。官方文档确认 metadata/tags 会由父 runnable 继承；DeerFlow 当前源码也专门以 `attach_tracing=False` 避免图内 model 产生重复 span。[Trace LangChain applications](https://docs.langchain.com/langsmith/trace-with-langchain) · [DeerFlow model factory at pinned commit](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/models/factory.py)
6. **online evaluation 是生产 trace 上的 LangSmith 平台规则，不应成为默认 CI 前提**。它通过项目/数据集绑定 evaluator，支持 run 或 thread、filter、sampling、backfill；需要 LangSmith workspace/API key，LLM judge 还需要模型凭证。[Online code evaluators](https://docs.langchain.com/langsmith/online-evaluations-code) · [Multi-turn online evaluators](https://docs.langchain.com/langsmith/online-evaluations-multi-turn)
7. **安全评测不能只靠 LLM judge**。越权工具、路径穿越、重复副作用、预算上限必须由确定性测试给出硬失败；OpenEvals 的安全 prompt 适合做显式启用的语义补充。目前 OpenEvals `main` 的 Python 公共安全 prompt 是 `PII_LEAKAGE_PROMPT`、`PROMPT_INJECTION_PROMPT`、`CODE_INJECTION_PROMPT`。[OpenEvals pinned source](https://github.com/langchain-ai/openevals/tree/d4a096b76c216feca6252cbdc277cf75c2b29a11/python/openevals/prompts/security)
8. **DeerFlow 当前有成熟 tracing/运行日志/guardrail 入口，但没有发现 LangSmith dataset + `evaluate()` 的正式回归框架**。课程不能把 DeerFlow 的 tracing 当成 eval；应学习它的 trace ownership，再自行补齐 dataset、offline experiment、trajectory regression 和安全质量门禁。[DeerFlow pinned tree](https://github.com/bytedance/deer-flow/tree/3e7baba39a9597e480dd82bbc18aee806679a2bf)

---

## 2. 名词边界：四件事不要混在一起

| 能力 | 回答的问题 | 默认是否可完全离线 | 主要接口 |
| --- | --- | --- | --- |
| 确定性测试 | 状态、路径、权限、幂等和恢复是否满足硬约束 | 是 | `pytest`、fake model/tool、`InMemorySaver` |
| Offline evaluation | 新版本在固定数据集上的质量是否退化 | 可以，但不一定 | `langsmith.evaluate()` / `aevaluate()` |
| Online evaluation | 生产真实交互是否持续满足质量/安全要求 | 否 | LangSmith evaluator + project rule/filter/sampling |
| Observability / tracing | 一次请求具体经过哪些 graph/node/model/tool，耗时和 token 如何 | 否（若上传） | `LANGSMITH_TRACING`、`tracing_context`、callbacks |

LangSmith 官方把评测流程定义为 Dataset、Target、Evaluator 三部分；offline eval 面向 curated dataset，online eval 面向没有 reference output 的生产 runs/threads。[Evaluation quickstart](https://docs.langchain.com/langsmith/evaluation-quickstart) · [Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)

一个容易误解的边界是：

- `offline` 是**生命周期位置**，即上线前实验；
- `upload_results=False` 是**数据传输策略**；
- evaluator 是否调用 LLM，则是**模型网络与成本策略**。

因此，一个 offline experiment 仍可能同时调用 LangSmith SaaS 和外部 judge model；反过来，一个使用本地 examples、纯代码 target/evaluator、`upload_results=False` 的 offline experiment 才是课程默认 CI 可接受的真正离线评测。

---

## 3. 本仓库锁定环境的实测结果

### 3.1 锁定版本

本地 `uv` 环境实际解析为：

| 包 | 版本 |
| --- | --- |
| `langsmith` | `0.10.2` |
| `langchain` | `1.3.13` |
| `langchain-core` | `1.4.9` |
| `langgraph` | `1.2.9` |
| `pytest` | `8.4.2` |

`pyproject.toml` 当前约束是 `langsmith>=0.10.2,<0.11`。本研究在该环境中实际验证了以下 imports：

```python
from langsmith import Client, aevaluate, evaluate, expect, traceable, tracing_context
from langsmith import testing as t
```

并实际验证：

```python
import langchain.smith
```

结果为：

```text
ModuleNotFoundError: No module named 'langchain.smith'
```

所以课程只能把 `langchain.smith` 放在迁移说明中，不能将其当成可运行 API。

### 3.2 当前核心签名

锁定的 `langsmith==0.10.2` 中，课程真正需要的顶层入口是：

```python
evaluate(
    target,
    /,
    data=None,
    evaluators=None,
    summary_evaluators=None,
    metadata=None,
    experiment_prefix=None,
    description=None,
    max_concurrency=0,
    num_repetitions=1,
    client=None,
    blocking=True,
    experiment=None,
    upload_results=True,
    error_handling="log",
)

aevaluate(
    target,
    /,
    data=None,
    evaluators=None,
    summary_evaluators=None,
    metadata=None,
    experiment_prefix=None,
    description=None,
    max_concurrency=0,
    num_repetitions=1,
    client=None,
    blocking=True,
    experiment=None,
    upload_results=True,
    error_handling="log",
)
```

官方对较大 Python evaluation job 推荐 `aevaluate()`，并要求显式考虑 `max_concurrency`。[How to evaluate agents](https://docs.langchain.com/langsmith/evaluate-llm-application)

Dataset 的当前 SDK 主路径是：

```python
client = Client()
dataset = client.create_dataset(
    dataset_name="mini-deerflow-regression",
    description="核心 Agent 回归集",
)
client.create_examples(
    dataset_id=dataset.id,
    examples=[
        {
            "inputs": {...},
            "outputs": {...},       # reference outputs
            "metadata": {...},
        }
    ],
)
examples = client.list_examples(dataset_id=dataset.id)
```

当前 reference 明确建议批量使用 `create_examples(examples=[...])`，不要继续教授把 `inputs`、`outputs` 拆成并行数组的旧式批量参数。[Client.create_examples](https://reference.langchain.com/python/langsmith/client/Client/create_examples) · [Programmatic dataset management](https://docs.langchain.com/langsmith/manage-datasets-programmatically)

### 3.3 真正无凭证的 `evaluate()` 已实测

使用本地 `langsmith.schemas.Example`、纯 Python target/evaluator 和 `upload_results=False`，在清空 `LANGSMITH_API_KEY`、关闭 tracing 的情况下可以得到本地结果：

```python
from uuid import UUID

from langsmith import evaluate, schemas

examples = [
    schemas.Example(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        dataset_id=UUID("00000000-0000-0000-0000-000000000002"),
        inputs={"x": 1},
        outputs={"y": 2},
    )
]

results = evaluate(
    lambda inputs: {"y": inputs["x"] + 1},
    data=examples,
    evaluators=[
        lambda outputs, reference_outputs: outputs == reference_outputs
    ],
    upload_results=False,
)
```

官方保证该参数不会记录 experiment results、application traces 或 evaluator traces。[Run an evaluation locally](https://docs.langchain.com/langsmith/local)

但锁定 SDK 在运行时会发出 `LangSmithBetaWarning: 'upload_results' parameter is in beta`。因此课程应将它描述为“**官方文档支持、当前 SDK 仍标记 beta 的本地运行能力**”，并用契约测试锁定，而不是误称为永不变化的稳定参数。

### 3.4 可选包现状

当前仓库环境：

- `agentevals`：未安装；
- `openevals`：未安装；
- `langsmith.pytest_plugin`：随当前 `langsmith` 可导入；
- `langsmith[pytest]` extra：若要 rich output 和 HTTP cache，官方仍建议显式安装。

所以任务 15 若引入 AgentEvals/OpenEvals，应把它们写成明确的新依赖或在线 extra，不能假设 `langsmith` 会传递安装它们。

---

## 4. Dataset：当前推荐组织方式

### 4.1 Example 的语义

LangSmith Dataset 是一组 examples。每个 example 至少包含：

- `inputs`：传给 target 的输入；
- `outputs`：可选 reference outputs，不是本次实际运行输出；
- `metadata`：用例来源、风险类别、难度、版本等；
- 可选 split、attachments 和 schema。

官方说明 Dataset 用于在时间上重复运行一致的评测，并支持版本、tag、split、metadata filter 与 JSON Schema。[Manage datasets](https://docs.langchain.com/langsmith/manage-datasets) · [Dataset UI and schemas](https://docs.langchain.com/langsmith/manage-datasets-in-application)

对 Mini DeerFlow，建议 reference output 不只存最终文本，还存可确定验证的业务契约：

```json
{
  "inputs": {
    "messages": [{"role": "user", "content": "..."}],
    "tenant_id": "tenant-a"
  },
  "outputs": {
    "required_tools": ["search"],
    "forbidden_tools": ["shell"],
    "terminal_status": "success",
    "answer_facts": ["..."],
    "max_tool_calls": 3
  },
  "metadata": {
    "risk": "prompt-injection",
    "split": "security-regression",
    "source": "hand-curated"
  }
}
```

这样一条 example 能同时驱动结果 evaluator、trajectory evaluator 和安全断言，而不是把“正确答案”简化成一个精确字符串。

### 4.2 在线 Dataset 与本地 fixture 的边界

| 方式 | 是否需要 LangSmith 凭证 | 适用场景 |
| --- | --- | --- |
| 仓库 JSON/JSONL fixture | 否 | 默认 CI、安全回归、PR 门禁 |
| `langsmith.schemas.Example` 内存列表 | 否 | 本地 `evaluate(upload_results=False)` |
| `Client.create_dataset/create_examples` | 是 | 团队共享 benchmark、实验对比 |
| 从 production trace 加入 dataset | 是 | 失败案例闭环、人工标注 |

推荐保留一个版本控制内的 canonical fixture，再用显式命令同步到 LangSmith。不要让默认测试为了读取测试数据而依赖 SaaS 可用性。

---

## 5. Offline evaluation：当前接口和 evaluator 契约

### 5.1 Target

`evaluate()` 的 target 可以是：

- 接收 `inputs: dict`、返回 `outputs: dict` 的函数；
- LangChain `Runnable`；
- 已存在 experiment；
- 两个 experiment 的 tuple，用于 comparative evaluation。

`data` 可以是 dataset 名称、UUID、examples 列表或 generator。[Client.evaluate reference](https://reference.langchain.com/python/langsmith/client/Client/evaluate)

课程应给 graph 包一层稳定 target adapter，让输入输出契约清楚，而不是把整个 `StateSnapshot` 或不可序列化对象直接上传：

```python
def target(inputs: dict) -> dict:
    state = graph.invoke(
        {"messages": inputs["messages"]},
        config={"configurable": {"thread_id": inputs["case_id"]}},
    )
    return {
        "messages": state["messages"],
        "terminal_status": "success",
    }
```

### 5.2 Code evaluator

当前官方 code evaluator 可以直接声明它需要的命名参数，常用的是：

```python
def evaluator(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict,
) -> bool | dict | list[dict]:
    ...
```

返回值可为布尔值、数值或带 `key`、`score`、`comment` 的 feedback 字典；多指标时返回列表。代码 evaluator 适合 JSON schema、工具白名单、预算、状态、事实集合等确定规则。[Code evaluator SDK](https://docs.langchain.com/langsmith/code-evaluator-sdk)

### 5.3 Summary 和 comparative evaluator

- `summary_evaluators` 在整个 experiment 完成后接收结果集合，适合成功率、P95、总成本、路径覆盖率；
- pairwise/comparative evaluator 用于比较两个已有 experiment；
- `num_repetitions` 用于观察非确定性；
- `metadata` 应记录 model、prompt、tools、git SHA 或课程版本。

官方明确区分单 example evaluator、summary evaluator、pairwise evaluator。[Evaluation types](https://docs.langchain.com/langsmith/evaluation-types)

### 5.4 推荐的双层门禁

```text
第一层：纯代码 evaluator
  ├─ 权限、路径、幂等、预算、终态、结构
  └─ 失败直接阻断 CI

第二层：可选 LLM judge
  ├─ 正确性、相关性、完整性、语气
  └─ 显式在线运行，阈值和波动策略单独配置
```

不要让 LLM judge 决定“是否调用了越权工具”或“副作用是否执行两次”；这些信息已经能从 trajectory/run event 得到确定答案。

---

## 6. Online evaluation：生产 trace 评测，不是另一个 `evaluate()`

LangSmith 当前 online evaluation 的主要配置面是 workspace evaluator 与 tracing project rule：

1. 生产交互首先产生 trace；
2. evaluator 绑定到 project 或 dataset；
3. filter 选择 run/thread；
4. sampling 控制比例和成本；
5. 可选 backfill 对历史 runs 执行；
6. feedback 写回 run/thread，进入监控和数据集闭环。

官方在线 code evaluator 的函数形状是接收一个 `Run`，返回 feedback dict：

```python
def perform_eval(run):
    outputs = run["outputs"]
    return {
        "formatted": "facts" in outputs,
        "safe": True,
    }
```

平台内联 code evaluator 当前没有网络访问，并限制可导入的第三方库；官方建议先本地测试 evaluator。[Online code evaluators](https://docs.langchain.com/langsmith/online-evaluations-code)

Thread evaluator 会等待一个 idle time 后再评估多轮对话，并支持 filter/sampling。它适合检查跨轮任务完成度、知识保持和用户满意度，但要注意长 thread 的上下文和 judge 成本。[Multi-turn online evaluators](https://docs.langchain.com/langsmith/online-evaluations-multi-turn)

### 凭证与成本边界

| Online 能力 | LangSmith key | 模型 key | 备注 |
| --- | --- | --- | --- |
| 上传/查看 traces | 需要 | target 视情况 | `LANGSMITH_TRACING=true` |
| 代码 online evaluator | 需要 | 不需要 | 平台受限运行环境 |
| LLM-as-judge online evaluator | 需要 | 需要 workspace secret | 有采样与调用成本 |
| thread evaluator | 需要 | 通常需要 | 等待 idle window |
| automation add-to-dataset | 需要 | 不需要 | 可把失败 trace 回流 dataset |

LangSmith automation rules 还支持 filter、sampling、annotation queue、add to dataset、webhook 与 retention；多个 rule 独立调度，不能假设执行顺序，若依赖前一个 feedback，需在下游 rule filter 中显式表达。[Automation rules](https://docs.langchain.com/langsmith/rules)

当前 `langsmith==0.10.2` 的 `Client.evaluators` 暴露了 generated async online-evaluator resource（`create/list/retrieve/update/delete` 等），但官方主教程仍以 UI/project rule 配置为主。课程基础章节不应先依赖这组较新的生成式管理 API；可以在进阶附录说明并用版本契约测试保护。

---

## 7. Agent trajectory evaluation

### 7.1 为什么最终答案分数不够

同样的最终答案可能来自：

- 正确的只读检索；
- 未授权的 shell/database 工具；
- 重复执行副作用后侥幸返回；
- 过度循环消耗大量 token；
- 忽略 interrupt 审批。

因此 Agent eval 至少要同时保存最终结果与 messages/tool calls/graph steps。LangSmith 官方将 Agent 评测分为 final response、single step、trajectory 三类。[Application-specific evaluation approaches](https://docs.langchain.com/langsmith/evaluation-approaches)

### 7.2 AgentEvals：确定性优先

当前官方 AgentEvals 第一方仓库 pinned commit 为 `4b68015eeb444a5fc6fb986932d92a999446890c`。消息/工具轨迹入口为：

```python
from agentevals.trajectory.match import create_trajectory_match_evaluator

evaluator = create_trajectory_match_evaluator(
    trajectory_match_mode="strict",
)
result = evaluator(
    outputs=actual_messages,
    reference_outputs=reference_messages,
)
```

四种模式：

| 模式 | 语义 | 推荐用途 |
| --- | --- | --- |
| `strict` | 消息/工具顺序严格一致 | 审批前置、固定 workflow |
| `unordered` | 工具集合一致，顺序可变 | 并行检索 |
| `subset` | 实际只使用 reference 允许的工具 | 防止越权/多余工具 |
| `superset` | 实际至少包含 reference 必需工具 | 验证最低必要行为 |

这些检查不调用 judge model，适合默认 CI。[Trajectory evaluations guide](https://docs.langchain.com/langsmith/trajectory-evals) · [Pinned match source](https://github.com/langchain-ai/agentevals/blob/4b68015eeb444a5fc6fb986932d92a999446890c/python/agentevals/trajectory/match.py)

### 7.3 LLM trajectory judge

存在多条合理路径、需要判断效率或逻辑合理性时，使用：

```python
from agentevals.trajectory.llm import create_trajectory_llm_as_judge
```

它可带或不带 reference trajectory，但需要 judge model，因此属于显式在线层。不要用它替代工具白名单、参数 schema、预算和副作用次数断言。[Pinned LLM trajectory source](https://github.com/langchain-ai/agentevals/blob/4b68015eeb444a5fc6fb986932d92a999446890c/python/agentevals/trajectory/llm.py)

### 7.4 LangGraph graph trajectory

AgentEvals 还提供 graph 级接口：

```python
from agentevals.graph_trajectory.strict import graph_trajectory_strict_match
from agentevals.graph_trajectory.llm import create_graph_trajectory_llm_as_judge
```

`GraphTrajectory` 包含每轮 `inputs`、`results`、`steps`。它更适合验证 LangGraph node 路径、`__interrupt__` 和 resume，而普通 trajectory match 更适合验证对外 messages/tool calls。[Pinned graph strict source](https://github.com/langchain-ai/agentevals/blob/4b68015eeb444a5fc6fb986932d92a999446890c/python/agentevals/graph_trajectory/strict.py) · [Pinned graph judge source](https://github.com/langchain-ai/agentevals/blob/4b68015eeb444a5fc6fb986932d92a999446890c/python/agentevals/graph_trajectory/llm.py)

课程应明确：AgentEvals 是额外包，不是 `langsmith` 内建模块。

---

## 8. Pytest 与 LangSmith testing 集成

### 8.1 默认 pytest

LangChain 官方建议把真实模型 integration tests 与 unit tests 分开，用 marker 显式运行；非确定模型应断言消息类型、tool name、argument shape 和结构，不要精确比较自然语言。[Integration testing](https://docs.langchain.com/oss/python/langchain/test/integration-testing)

本项目已有 `integration` marker，任务 15 应延续为：

```bash
# 默认：无外部 API
uv run pytest

# 显式在线
uv run pytest -m integration
```

### 8.2 `pytest.mark.langsmith`

当前官方集成用法：

```python
import pytest
from langsmith import testing as t

@pytest.mark.langsmith
def test_case() -> None:
    t.log_inputs({...})
    t.log_reference_outputs({...})
    t.log_outputs({...})
    t.log_feedback(key="authorized", score=True)
    assert ...
```

每个 decorated test 会同步为 dataset example，并为每次 test suite 运行建立 experiment；默认 pass/fail 写入 `pass` feedback。[LangSmith pytest integration](https://docs.langchain.com/langsmith/pytest)

当前可用 testing helpers 已实测：

```python
t.log_inputs(inputs)
t.log_outputs(outputs)
t.log_reference_outputs(reference_outputs)
t.log_feedback(key=..., score=...)
with t.trace_feedback():
    ...
```

`trace_feedback()` 用于把 judge/evaluator 的 trace 与主应用 trace 分离，避免 evaluator 的模型调用被误认成应用业务路径。

完全不上传可设置：

```bash
LANGSMITH_TEST_TRACKING=false pytest
```

若启用模型 HTTP cache：

```bash
LANGSMITH_TEST_CACHE=tests/cassettes pytest
```

官方说明 rich output/cache 需要 `langsmith[pytest]`；缓存 cassette 必须过滤 authorization/API key。默认 CI 仍应优先使用 fake/replay，而不是静默发起真实模型请求。

`@test` / `@unit` decorator 已被官方放在 Legacy 小节，当前主路线是 `pytest.mark.langsmith`。[LangSmith pytest legacy section](https://docs.langchain.com/langsmith/pytest#test--unit-decorator)

---

## 9. Tracing：根节点、上下文传播与重复 span

### 9.1 三种当前入口

**应用级自动 tracing：**

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=mini-deerflow
```

LangChain/LangGraph 会自动记录 runnable 层级。[Tracing quickstart](https://docs.langchain.com/langsmith/observability-quickstart)

**请求级动态 tracing：**

```python
import langsmith as ls

with ls.tracing_context(
    enabled=True,
    project_name="mini-deerflow",
    metadata={"thread_id": thread_id},
    tags=["env:test"],
):
    graph.invoke(inputs, config=config)
```

`tracing_context(enabled=False)` 也能在全局 tracing 打开时按请求关闭。[Trace selectively](https://docs.langchain.com/langsmith/trace-with-langchain)

**显式 callback：**

```python
from langchain_core.tracers.langchain import LangChainTracer

config = {
    "callbacks": [LangChainTracer(project_name="mini-deerflow")],
    "metadata": {"thread_id": thread_id, "run_id": run_id},
    "tags": ["gateway"],
}
graph.invoke(inputs, config=config)
```

这适合需要同时挂载业务 `RunJournal`、token recorder、LangSmith、Langfuse 等多个 callback 的自建 runtime。

### 9.2 推荐 ownership

```text
HTTP / CLI / Worker 请求
        │
        └── graph.invoke / graph.stream  ← 唯一 provider callback 根
                ├── graph nodes
                ├── model calls
                ├── tools
                └── subgraphs
```

规则：

1. provider callback 在最外层业务 graph invocation 配置一次；
2. 业务 journal/token recorder 可与 provider callback 并列，但不要覆盖已有 callbacks；
3. graph 内模型复用继承的 `RunnableConfig`；
4. standalone model 若不在任何 graph root 下，才自行绑定 provider handler；
5. evaluator/judge trace 与 application trace 分开；
6. metadata/tags 放根 config，子 runnable 自动继承。[Metadata and tags](https://docs.langchain.com/langsmith/add-metadata-tags)

### 9.3 重复 span 的典型成因

- graph root 已含 tracing callback，model constructor 又绑定一个新的同类 callback；
- 全局 instrumentor 与手工 provider wrapper 重复包裹同一次模型调用；
- resume/重试时错误地新建两个业务 root，而不是以 run attempt metadata 区分；
- evaluator LLM call 没有放入 feedback trace，混入被评应用路径；
- callbacks 被 append 多次，且未做 handler identity/type 去重。

这部分“同一次调用只选一个 provider instrumentation owner”是基于官方 trace inheritance 和 DeerFlow 第一方实现得出的工程规则。官方还说明 LangSmith/LangChain 使用 `contextvars` 自动传播父 trace；Python 3.11+ 的 async propagation 最可靠。[Troubleshoot trace nesting](https://docs.langchain.com/langsmith/nest-traces)

跨进程/服务边界不能依赖进程内 contextvar。官方使用 `langsmith-trace` 与可选 `baggage` headers，FastAPI/Starlette 可使用 `TracingMiddleware`，或在服务端 `tracing_context(parent=request.headers)` 继续父 trace。[Distributed tracing](https://docs.langchain.com/langsmith/distributed-tracing)

### 9.4 测试“没有重复 span”

不要在线查询 LangSmith UI 才判断。默认测试可挂一个本地 recording callback，断言：

- 每次 HTTP Run 只有一个 root chain/graph start；
- 一个模型调用只有一个 `on_llm_start` / `on_chat_model_start` 与一个 end/error；
- tool call id 唯一；
- resume 是新的业务 run 或明确 attempt，但旧副作用不重复；
- callbacks 列表保留业务 recorder，provider handler 数量不超过预期。

在线 smoke test 再用 `Client.list_runs(project_name=..., is_root=True)` 验证 trace tree，不能替代离线契约测试。当前 `Client.list_runs` 实际支持 `trace_id`、`is_root`、`parent_run_id`、metadata filter 等筛选。[Query traces using the SDK](https://docs.langchain.com/langsmith/export-traces)

---

## 10. 隐私与 trace 安全

评测系统本身也是数据出口。官方提供：

```bash
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=true
```

以及：

```python
Client(
    hide_inputs=...,
    hide_outputs=...,
    hide_metadata=...,
    anonymizer=...,
)
```

还可在单个 `@traceable` 上用 `process_inputs` / `process_outputs`。处理函数应返回新对象，不应原地修改业务输入。[Prevent logging sensitive data](https://docs.langchain.com/langsmith/mask-inputs-outputs)

课程必须强调：

- trace redaction 是上传前控制，不是 UI 隐藏；
- dataset 比普通 trace 保存更久，不能把密钥、完整租户 token 或原始敏感文件放入 reference data；
- zero-retention 客户请求应条件性关闭 tracing，而不是只依赖 mask；
- metadata 同样可能包含 user id、路径、prompt/tool arguments，需要审计；
- online evaluator 命中的 trace 可能提升 retention，并影响费用。[Online code evaluator retention note](https://docs.langchain.com/langsmith/online-evaluations-code)

---

## 11. 安全评测接口与优先级

### 11.1 硬安全属性：确定性测试

以下项目不应交给 LLM judge 决定：

| 风险 | 必测断言 |
| --- | --- |
| Prompt injection | 不改变 system policy；不调用 forbidden tool；检索文档中的指令仅作为数据 |
| 越权工具 | tenant/user/role 不满足时，tool executor 在执行前拒绝 |
| 路径穿越 | `..`、绝对路径、symlink escape 均不能越过 workspace root |
| 重复副作用 | 同一个 effect id 最多提交一次；retry/resume 读取 ledger |
| Token/tool budget | 超限走明确终态或中断，不无限循环 |
| interrupt/resume | 未批准前无副作用；拒绝后不能继续执行 |
| trace leakage | inputs/outputs/metadata 脱敏函数覆盖敏感字段 |

这些测试使用 fake model、fake tool、临时目录和本地 checkpointer，默认无凭证。

### 11.2 LangChain guardrail 运行接口

LangChain 官方当前提供 `PIIMiddleware`、`HumanInTheLoopMiddleware` 和自定义 middleware hooks。PII 支持 `redact`、`mask`、`hash`、`block`；自定义 guardrail 可在 agent 前后或 model/tool 周围执行。[Guardrails](https://docs.langchain.com/oss/python/langchain/guardrails)

这属于**运行时防护**，不是评测本身。任务 15 应同时测试：

1. guardrail 判定器的纯函数；
2. middleware 是否阻止实际 tool executor；
3. 被拒绝路径是否留下可审计 event；
4. guardrail 异常采用 fail-open 还是 fail-closed。

### 11.3 OpenEvals 安全 judge

OpenEvals 官方当前 `main` pinned commit `d4a096b76c216feca6252cbdc277cf75c2b29a11` 的 Python security prompts 是：

```python
from openevals.llm import create_llm_as_judge
from openevals.prompts import (
    CODE_INJECTION_PROMPT,
    PII_LEAKAGE_PROMPT,
    PROMPT_INJECTION_PROMPT,
)
```

用法：

```python
pii_evaluator = create_llm_as_judge(
    prompt=PII_LEAKAGE_PROMPT,
    feedback_key="pii_leakage",
    model="provider:model",
)
result = pii_evaluator(inputs=inputs, outputs=outputs)
```

它需要 `openevals` 和 judge model 凭证，分数是模型判断，适合显式在线评测，不能作为唯一路径。[OpenEvals official repository](https://github.com/langchain-ai/openevals) · [Pinned security exports](https://github.com/langchain-ai/openevals/blob/d4a096b76c216feca6252cbdc277cf75c2b29a11/python/openevals/prompts/security/__init__.py)

截至本研究 pinned commit，Python security export **没有** `JAILBREAK_PROMPT`；搜索结果或旧示例中若出现该名称，不应在未做 import contract test 前写进课程。

LangSmith UI 另有 Security、Safety、Trajectory 等 evaluator template 分类，但它们是 workspace 平台资源，应描述为“可选在线模板”，不是本地 Python 常量。[Manage evaluators](https://docs.langchain.com/langsmith/evaluators)

---

## 12. DeerFlow 当前 main 的架构入口

### 12.1 固定版本

2026-07-13 检查到 DeerFlow 官方 `main`：

```text
3e7baba39a9597e480dd82bbc18aee806679a2bf
```

后续课程源码导读应固定该 commit，不使用会漂移的裸 `main` 链接。[DeerFlow pinned repository](https://github.com/bytedance/deer-flow/tree/3e7baba39a9597e480dd82bbc18aee806679a2bf)

### 12.2 Tracing factory

`deerflow/tracing/factory.py` 根据显式启用的 providers 构造 callbacks：

- LangSmith：`langchain_core.tracers.langchain.LangChainTracer(project_name=...)`；
- Langfuse：初始化 `Langfuse` client 后建立 LangChain `CallbackHandler`；
- 缺凭证或 handler 初始化失败时 fail fast；
- 支持同时返回两个 providers 的 callbacks。

[DeerFlow tracing factory](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/tracing/factory.py)

### 12.3 Graph root ownership

`make_lead_agent` 把 tracing callbacks append 到传入的 `config["callbacks"]`，保留已有 callbacks；源码注释明确说明：根级 callback 让一次 LangGraph run 形成一个 trace，node/LLM/tool 成为 children，并使根 metadata 被 provider 读取。

[Lead agent root callback injection](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/agents/lead_agent/agent.py)

Gateway worker `run_agent` 还会：

- 建立 runtime context；
- append `RunJournal` callback 记录 token/lifecycle；
- 注入 thread/user/assistant/model/environment/request trace metadata；
- 设置 root `run_name`；
- 再构造 `RunnableConfig` 驱动 graph。

[Gateway run worker](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/runtime/runs/worker.py) · [Run journal](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/runtime/journal.py)

Embedded `DeerFlowClient.stream` 采用同一原则：在 graph invocation root append callbacks 和 metadata，再流式运行 graph。[Embedded client tracing](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/client.py)

### 12.4 DeerFlow 如何避免重复 span

`create_chat_model(..., attach_tracing=True)` 的注释给出非常直接的 ownership：

- standalone model 默认 `True`，它自己需要 provider callback；
- 已在 graph root 配置 tracing 的调用者必须传 `attach_tracing=False`；
- 否则同一 LLM call 会同时由 graph root 和 model handler 记录，产生重复 spans，且根 trace metadata 可能无法正确提升。

Title middleware 正是以 `attach_tracing=False` 创建图内模型，并把继承的 config 传给 `ainvoke()`。[Model tracing ownership](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/models/factory.py) · [Title middleware](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/agents/middlewares/title_middleware.py)

DeerFlow 还为这些行为建立了明确测试入口：

- tracing config/provider factory；
- lead-agent root callback；
- gateway worker metadata；
- embedded client metadata；
- subagent callback 保留与 metadata；
- trace context 和 HTTP trace middleware。

[DeerFlow tracing tests](https://github.com/bytedance/deer-flow/tree/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/tests)

### 12.5 运行日志与 vendor trace 是两套职责

DeerFlow 的 `RunJournal` 是 LangChain callback，用于把 lifecycle、LLM usage 等运行事件写入自身 runtime event store；LangSmith/Langfuse callback 则上传可观测性 trace。两者同时挂在 root callbacks，但落点和职责不同。

这正是课程应保留的分层：

```text
Runtime event store：恢复、SSE replay、审计、产品状态
Provider tracing：调试、性能、token、跨步骤可视化
Evaluation results：数据集实验分数、回归阈值
```

不能用 LangSmith trace 代替产品运行状态，也不能把 runtime event 数量当作质量分数。

### 12.6 Guardrail 入口

DeerFlow 当前有 `GuardrailProvider.evaluate/aevaluate` 和 `GuardrailMiddleware`，在 tool execution 前判断 allow/deny；provider error 支持配置 fail-open/fail-closed，并有单元测试。[Guardrail provider](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/guardrails/provider.py) · [Guardrail middleware](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/guardrails/middleware.py) · [Guardrail tests](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/tests/test_guardrail_middleware.py)

这是运行时授权/安全控制，不是 LangSmith evaluator。课程应把它映射到“执行前硬边界 + 离线安全回归”，再用 OpenEvals/LangSmith online evaluator 做语义监控。

### 12.7 DeerFlow 当前 eval 缺口

在 pinned checkout 的 `backend/` 中检索 `langsmith.evaluate`、`create_dataset`、`create_examples`、`agentevals`、`openevals`，没有发现正式 dataset/experiment/trajectory regression 实现。名称含 `eval` 的 `skills/review/eval_schema.py` 与 goal/guardrail evaluator 属于产品内部判定，不等同于 LangSmith evaluation harness。

因此对课程最准确的描述是：

- DeerFlow 是 tracing、runtime audit、guardrail 与大量 deterministic tests 的优秀架构参考；
- 任务 15 需要在 Mini DeerFlow 中额外建立可教学的 eval layer；
- 不能宣称 DeerFlow 当前已经提供完整 LangSmith dataset/offline eval 实现。

---

## 13. 建议任务 15 采用的稳定/可选矩阵

| 能力/API | 课程定位 | 默认测试 | 凭证 | 稳定性判断 |
| --- | --- | --- | --- | --- |
| `pytest` + fake model/tool | 核心硬门禁 | 开启 | 无 | 稳定 |
| 新 graph + `InMemorySaver` | LangGraph 单元/路径测试 | 开启 | 无 | 官方推荐 |
| `from langsmith import evaluate, aevaluate` | offline eval runner | 开启纯本地 smoke | 无/可选 | 当前公共 API |
| `upload_results=False` | 不上传本地 eval | 开启 | 无 | 官方文档支持，SDK 标记 beta |
| `Client.create_dataset/create_examples` | 团队共享 dataset | 关闭 | LangSmith | 当前公共 API |
| `pytest.mark.langsmith` | 测试同步/experiment | 关闭 | LangSmith | 当前主路线 |
| AgentEvals deterministic match | trajectory CI | 可开启 | 无 | 可选第一方包 |
| AgentEvals LLM judge | trajectory 质量 | 关闭 | judge model，可选 LangSmith | 可选在线 |
| OpenEvals security prompts | 语义安全评测 | 关闭 | judge model | 可选第一方包 |
| `LANGSMITH_TRACING` | 应用 trace | 关闭 | LangSmith | 当前推荐 |
| `tracing_context` | 请求级开关/parent | 本地契约可测 | 上传时需 LangSmith | 当前公共 API |
| root `LangChainTracer` callback | 多 provider/runtime 自建组合 | 本地 recording handler | 上传时需 LangSmith | 当前 LangChain Core API |
| LangSmith online evaluator/rule | 生产监控 | 关闭 | LangSmith + 可选 judge | 平台能力 |
| `langchain.smith` | 仅迁移反例 | 禁止 | — | 已移除 |

---

## 14. 对任务 15 实现的最小正确切片

本研究不修改实现，但建议主任务按以下顺序落地：

1. **先建离线安全/恢复门禁**：节点、reducer、middleware、tool、API、interrupt/resume、subagent、sandbox、权限、路径、幂等、预算。
2. **建立统一 trajectory capture**：从 messages/tool calls/run events 提取稳定 DTO；不要让 evaluator 直接依赖 vendor trace schema。
3. **建立本地 dataset fixture**：inputs + structured reference outputs + metadata risk/split。
4. **接入 `evaluate(upload_results=False)`**：纯代码 target/evaluators，默认 CI 可跑。
5. **接入 AgentEvals deterministic match**：结果分与路径分同时存在。
6. **建立 tracing ownership**：root config 一次挂 provider handler，图内模型继承；本地测试无重复 span。
7. **增加显式 online command/marker**：LangSmith dataset sync、experiment upload、OpenEvals/AgentEvals judge；缺凭证时 skip，而不是失败或静默降级。
8. **最后给 online evaluator 配置说明**：project filter、sampling、thread idle、failure-to-dataset 闭环。

推荐最终报告至少输出这些指标：

```text
hard_pass_rate
final_answer_score
trajectory_match_score
unauthorized_tool_calls
duplicate_effect_attempts
interrupt_resume_pass
token_budget_pass
root_trace_count
duplicate_span_count
```

其中所有 `*_pass`、越权、重复副作用和重复 span 都必须有确定性断言；LLM judge 只能补充主观质量。

---

## 15. 直接来源索引

### LangSmith / LangGraph / LangChain

- [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation)
- [Evaluation quickstart](https://docs.langchain.com/langsmith/evaluation-quickstart)
- [Run an evaluation locally](https://docs.langchain.com/langsmith/local)
- [How to evaluate agents](https://docs.langchain.com/langsmith/evaluate-llm-application)
- [Code evaluator SDK](https://docs.langchain.com/langsmith/code-evaluator-sdk)
- [Manage datasets programmatically](https://docs.langchain.com/langsmith/manage-datasets-programmatically)
- [Manage datasets](https://docs.langchain.com/langsmith/manage-datasets)
- [LangSmith pytest integration](https://docs.langchain.com/langsmith/pytest)
- [Trajectory evaluations](https://docs.langchain.com/langsmith/trajectory-evals)
- [Agent Evals](https://docs.langchain.com/oss/python/langchain/test/evals)
- [Online code evaluators](https://docs.langchain.com/langsmith/online-evaluations-code)
- [Multi-turn online evaluators](https://docs.langchain.com/langsmith/online-evaluations-multi-turn)
- [Trace LangChain applications](https://docs.langchain.com/langsmith/trace-with-langchain)
- [Custom instrumentation](https://docs.langchain.com/langsmith/annotate-code)
- [Distributed tracing](https://docs.langchain.com/langsmith/distributed-tracing)
- [Troubleshoot trace nesting](https://docs.langchain.com/langsmith/nest-traces)
- [Mask inputs/outputs/metadata](https://docs.langchain.com/langsmith/mask-inputs-outputs)
- [LangGraph testing](https://docs.langchain.com/oss/python/langgraph/test)
- [LangChain integration testing](https://docs.langchain.com/oss/python/langchain/test/integration-testing)
- [LangChain guardrails](https://docs.langchain.com/oss/python/langchain/guardrails)
- [LangSmith Python reference](https://reference.langchain.com/python/langsmith)
- [LangSmith Client reference](https://reference.langchain.com/python/langsmith/client/Client)

### 第一方 evaluator 源码

- [AgentEvals pinned repository](https://github.com/langchain-ai/agentevals/tree/4b68015eeb444a5fc6fb986932d92a999446890c)
- [OpenEvals pinned repository](https://github.com/langchain-ai/openevals/tree/d4a096b76c216feca6252cbdc277cf75c2b29a11)

### DeerFlow

- [DeerFlow pinned repository](https://github.com/bytedance/deer-flow/tree/3e7baba39a9597e480dd82bbc18aee806679a2bf)
- [Tracing factory](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/tracing/factory.py)
- [Tracing metadata](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/tracing/metadata.py)
- [Lead agent root callback](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- [Gateway worker](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/runtime/runs/worker.py)
- [Embedded client](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/client.py)
- [Model tracing ownership](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/models/factory.py)
- [Run journal](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/runtime/journal.py)
- [Guardrail middleware](https://github.com/bytedance/deer-flow/blob/3e7baba39a9597e480dd82bbc18aee806679a2bf/backend/packages/harness/deerflow/guardrails/middleware.py)

