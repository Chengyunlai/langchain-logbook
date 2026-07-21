---
title: "第 08 章：从固定边到动态研究工作流"
description: "用 Command、Send、Subgraph 与 Reducer 表达条件、循环和动态并行。"
pubDatetime: 2026-03-26T00:00:00.000Z
featured: false
tags: ["tutorial"]
sourcePath: "tutorials/08_Engineering_Defense.md"
learningOrder: 8
learningStage: "langgraph"
learningStageTitle: "把业务流程写成可恢复的图"
learningGoal: "用 Command、Send、Subgraph 与 Reducer 表达条件、循环和动态并行。"
contentType: "main"
---



> **课程位置**：Graph 编排层第 2 章
> **锁定环境**：Python 3.12 / LangGraph 1.2.x
> **本章工件**：Command、Send、Subgraph、显式循环、Functional API 与 Mini DeerFlow 研究图

## 1. 上一刻系统：会画固定图，还表达不了动态任务

第 07 章已经从零实现 State、Node、Edge、条件边、Reducer 和显式 ReAct Graph。现在把研究计划真正放进图：拒绝空目标，按运行时 sections 动态研究，汇总草稿，质量不够时修订。

固定边能表达编译前已知的拓扑，却会遇到四个新问题：

1. 节点更新状态后，另一个 router 又重复判断一次；
2. section 数量运行时才知道，不能预先画固定数量的 worker；
3. review 只需草稿，却意外看到父图全部 State；
4. 循环有返回边，却没有可观察进度和终止条件。

```mermaid
flowchart TD
    S["START"] --> I["intake"]
    I -->|"Command: reject"| X["reject"]
    I -->|"Command: plan"| P["plan"]
    P -->|"Send(section A)"] R1["research_section"]
    P -->|"Send(section B)"] R2["research_section"]
    R1 --> Y["synthesize"]
    R2 --> Y
    Y --> SG["review subgraph"]
    SG --> Q{"quality_score"}
    Q -->|"不足"| V["revise"]
    V --> SG
    Q -->|"通过"| F["finalize"]
    X --> E["END"]
    F --> E
```

**图的文本替代**：intake 用 Command 同时写状态与选路；plan 用 Send 为每个 section 创建运行时任务；结果经 reducer 汇合；review 子图只读取局部 State，低分修订后重试，高分结束。

## 2. 第一处失败：节点与 router 各写一份判断规则

条件边适合“只读取现有 State 并决定下一站”。若一个节点已经判断并写入状态，随后 router 又重新读取原始输入判断，两个条件会逐渐漂移。


### 空白目标被 intake 拒绝，却被 router 送进 plan

**运行前先预测**：intake 使用 `strip()`，router 只判断字符串真假；输入三个空格时，最终 status 会是什么？

```python sync=ch08-duplicated-router-failure
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RouteState(TypedDict, total=False):
    objective: str
    status: str
    trace: list[str]


def intake(state: RouteState) -> dict[str, object]:
    accepted = bool(state.get("objective", "").strip())
    return {
        "status": "accepted" if accepted else "rejected",
        "trace": ["intake:accept" if accepted else "intake:reject"],
    }


def duplicated_router(state: RouteState) -> Literal["plan", "reject"]:
    return "plan" if state.get("objective") else "reject"


def plan(state: RouteState) -> dict[str, object]:
    return {"status": "planned", "trace": [*state["trace"], "plan"]}


builder = StateGraph(RouteState)
builder.add_node("intake", intake)
builder.add_node("plan", plan)
builder.add_node("reject", lambda state: {})
builder.add_edge(START, "intake")
builder.add_conditional_edges("intake", duplicated_router)
builder.add_edge("plan", END)
builder.add_edge("reject", END)
broken_graph = builder.compile()

result = broken_graph.invoke({"objective": "   "})
print("intake_decision =", result["trace"][0])
print("final_status =", result["status"])
print("trace =", result["trace"])
```

**观察结果**：

```text output=ch08-duplicated-router-failure
intake_decision = intake:reject
final_status = planned
trace = ['intake:reject', 'plan']
```

**发生了什么**：同一个业务决定出现两份实现。intake 认为空白目标无效，router 却把非空字符串送进 plan，最终状态自相矛盾。

不要为了使用 Command 而使用 Command。若节点只更新、router 只路由且规则不重复，条件边仍然清晰。这里需要 Command，是因为判断、更新和下一跳属于一个原子业务决定。

**动手修改**：只修 router 的 `strip()`，让测试变绿。然后再增加一个“目标最少 5 个字符”的规则，观察两处修改为何仍会反复漂移。



### 用 Command 同时返回 patch 与 goto

**运行前先预测**：intake 返回 `Command(update=..., goto=...)` 后，还需要额外 conditional edge 吗？

```python sync=ch08-command-route-repair
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class CommandState(TypedDict, total=False):
    objective: str
    status: str
    trace: list[str]


def intake_with_command(
    state: CommandState,
) -> Command[Literal["plan", "reject"]]:
    accepted = bool(state.get("objective", "").strip())
    if not accepted:
        return Command(
            update={"status": "rejected", "trace": ["intake:reject"]},
            goto="reject",
        )
    return Command(
        update={"status": "accepted", "trace": ["intake:accept"]},
        goto="plan",
    )


builder = StateGraph(CommandState)
builder.add_node("intake", intake_with_command)
builder.add_node("plan", lambda state: {"status": "planned"})
builder.add_node("reject", lambda state: {})
builder.add_edge(START, "intake")
builder.add_edge("plan", END)
builder.add_edge("reject", END)
command_graph = builder.compile()

rejected = command_graph.invoke({"objective": "   "})
accepted = command_graph.invoke({"objective": "解释 durable execution"})
print("rejected =", (rejected["status"], rejected["trace"]))
print("accepted =", (accepted["status"], accepted["trace"]))
print("separate_router =", False)
```

**观察结果**：

```text output=ch08-command-route-repair
rejected = ('rejected', ['intake:reject'])
accepted = ('planned', ['intake:accept'])
separate_router = False
```

**发生了什么**：一个节点拥有一次判断，并把 State patch 与下一跳一起返回。类型参数列出可能目的地，也帮助 Graph 可视化发现动态边。

`Command` 还支持 `graph` 与 `resume`。跨图导航和 interrupt 恢复分别在后续子图、HITL 章节出现；不要把四种能力一次塞进同一个例子。

**动手修改**：增加 `needs-info` 路径，并同步修改 `Literal`。故意漏掉类型中的目标，观察运行与静态可读性分别受到什么影响。


## 3. 第二处失败：固定 worker 数量吞掉第三个 section

静态 edge 在 compile 前确定。若为 `worker_0`、`worker_1` 各画一条边，输入恰好两个 section 时可用；第三个任务不会自动长出新节点。

第 07 章已经证明并行写同一字段必须有 reducer。本节复用这个前置知识，只增加动态任务数量这一项机制。


### 两个固定 worker 只处理前两个任务

**运行前先预测**：输入三个 section，而图里只有两个固定 worker，最终哪个 section 会消失？

```python sync=ch08-static-fanout-failure
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class FixedFanoutState(TypedDict):
    sections: list[str]
    findings: Annotated[list[str], operator.add]


def worker_at(position: int):
    def run(state: FixedFanoutState) -> dict[str, list[str]]:
        return {"findings": [state["sections"][position]]}

    return run


builder = StateGraph(FixedFanoutState)
builder.add_node("worker_0", worker_at(0))
builder.add_node("worker_1", worker_at(1))
builder.add_edge(START, "worker_0")
builder.add_edge(START, "worker_1")
builder.add_edge("worker_0", END)
builder.add_edge("worker_1", END)
fixed_graph = builder.compile()

requested = ["checkpoint", "side-effect", "thread_id"]
result = fixed_graph.invoke({"sections": requested, "findings": []})
print("requested =", requested)
print("researched =", sorted(result["findings"]))
print("missing =", sorted(set(requested) - set(result["findings"])))
```

**观察结果**：

```text output=ch08-static-fanout-failure
requested = ['checkpoint', 'side-effect', 'thread_id']
researched = ['checkpoint', 'side-effect']
missing = ['thread_id']
```

**发生了什么**：Reducer 正确合并了两个并行更新，却无法创造第三个任务。问题不在合并，而在任务数量被拓扑写死。

**动手修改**：手工增加 `worker_2`，再输入四个 section。记录每次需求变化需要修改多少节点和 edge。



### 用 Send 为每个 section 创建运行时任务

**运行前先预测**：三个 Send 会复制三个永久节点，还是复用同一个 `research_section` 定义？

```python sync=ch08-send-fanout-repair
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send


class ResearchState(TypedDict):
    sections: list[str]
    findings: Annotated[list[str], operator.add]


class ResearchTask(TypedDict):
    section: str


def fan_out(state: ResearchState) -> list[Send]:
    return [
        Send("research_section", {"section": section})
        for section in state["sections"]
    ]


def research_section(state: ResearchTask) -> dict[str, list[str]]:
    return {"findings": [f"evidence:{state['section']}"]}


builder = StateGraph(ResearchState)
builder.add_node("dispatch", lambda state: {})
builder.add_node("research_section", research_section)
builder.add_edge(START, "dispatch")
builder.add_conditional_edges("dispatch", fan_out, ["research_section"])
builder.add_edge("research_section", END)
send_graph = builder.compile()

sections = ["checkpoint", "side-effect", "thread_id"]
updates = list(
    send_graph.stream(
        {"sections": sections, "findings": []},
        stream_mode="updates",
    )
)
node_names = [next(iter(update)) for update in updates]
findings = [
    finding
    for update in updates
    for finding in update.get("research_section", {}).get("findings", [])
]
print("research_task_updates =", node_names.count("research_section"))
print("findings =", sorted(findings))
print("permanent_worker_nodes =", 1)
```

**观察结果**：

```text output=ch08-send-fanout-repair
research_task_updates = 3
findings = ['evidence:checkpoint', 'evidence:side-effect', 'evidence:thread_id']
permanent_worker_nodes = 1
```

**发生了什么**：`Send` 在运行时为同一个节点定义创建三个 task，每个 task 拿到不同输入。它们仍属于同一 Graph superstep，结果通过 findings reducer 合并。

`Send` 不是任意后台线程 API。外部服务并发上限、deadline、取消和部分失败仍需单独设计。

**动手修改**：输入空 sections。决定应直接结束、返回业务失败，还是调用默认研究任务，并把规则放在 fan-out 之前。


## 4. 第三处失败：普通 review 函数看到了整个父 State

把所有逻辑都写成父图节点最省代码，却会扩大耦合。质量审查只需 draft 与 revision count，不应读取 objective、用户身份或内部 secret。


### review 节点收到父图全部字段

**运行前先预测**：普通节点直接接收 ParentState 时，`secret` 会不会出现在可见 keys 中？

```python sync=ch08-review-state-leak-failure
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ParentState(TypedDict, total=False):
    objective: str
    draft: str
    secret: str
    review_seen_keys: list[str]
    quality_score: int


def unsafe_review(state: ParentState) -> dict[str, object]:
    return {
        "review_seen_keys": sorted(state),
        "quality_score": 1 if state.get("draft") else 0,
    }


builder = StateGraph(ParentState)
builder.add_node("review", unsafe_review)
builder.add_edge(START, "review")
builder.add_edge("review", END)
graph = builder.compile()
result = graph.invoke(
    {
        "objective": "解释 checkpoint",
        "draft": "初稿",
        "secret": "internal-token",
    }
)

print("review_seen_keys =", result["review_seen_keys"])
print("secret_visible =", "secret" in result["review_seen_keys"])
print("quality_score =", result["quality_score"])
```

**观察结果**：

```text output=ch08-review-state-leak-failure
review_seen_keys = ['draft', 'objective', 'secret']
secret_visible = True
quality_score = 1
```

**发生了什么**：函数虽然没有主动使用 secret，接口却允许未来改动读取它。测试也难以证明 review 的真实输入边界。

**动手修改**：在 review 中加入调试日志打印整个 state。解释为什么“当前没用 secret”不能替代最小输入 Schema。



### 用独立 ReviewState 编译子图

**运行前先预测**：子图声明的 State 只有 draft、score 和 seen keys 时，父图 secret 会不会进入子图？

```python sync=ch08-review-subgraph-repair
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ReviewState(TypedDict, total=False):
    draft: str
    quality_score: int
    review_seen_keys: list[str]


def inspect_review(state: ReviewState) -> dict[str, object]:
    return {
        "review_seen_keys": sorted(state),
        "quality_score": 1 if state.get("draft") else 0,
    }


review_builder = StateGraph(ReviewState)
review_builder.add_node("score", inspect_review)
review_builder.add_edge(START, "score")
review_builder.add_edge("score", END)
review_subgraph = review_builder.compile()


class SafeParentState(TypedDict, total=False):
    objective: str
    draft: str
    secret: str
    quality_score: int
    review_seen_keys: list[str]


parent_builder = StateGraph(SafeParentState)
parent_builder.add_node("review", review_subgraph)
parent_builder.add_edge(START, "review")
parent_builder.add_edge("review", END)
parent_graph = parent_builder.compile()
result = parent_graph.invoke(
    {
        "objective": "解释 checkpoint",
        "draft": "初稿",
        "secret": "internal-token",
    }
)

print("review_seen_keys =", result["review_seen_keys"])
print("secret_visible =", "secret" in result["review_seen_keys"])
print("quality_score =", result["quality_score"])
```

**观察结果**：

```text output=ch08-review-subgraph-repair
review_seen_keys = ['draft']
secret_visible = False
quality_score = 1
```

**发生了什么**：compiled subgraph 只建立自己声明的 channels。父子共享的 draft 与输出字段可以流动，objective 和 secret 不进入 ReviewState。

Subgraph 不等于 Subagent。Subgraph 是固定拓扑和 State 边界；Subagent 通常拥有独立 Prompt、模型、工具与上下文裁剪，并由 Lead 动态委派。第 11 章再引入后者。

**动手修改**：让 ReviewState 需要父图没有的 rubric。增加一个 adapter node 显式构造子图输入，避免靠同名 key 猜测转换。


## 5. 第四处失败：有返回边，却没有进度

画出循环不难，难的是证明它会结束。若 review 永远返回低分，revise 又不改变任何决定条件，Graph 只能等 recursion limit 强制中止。


### review 与 revise 永远回到同一状态

**运行前先预测**：review 永远给 0 分、revise 不更新计数时，Graph 能自行终止吗？

```python sync=ch08-no-progress-loop-failure
from typing import Literal, TypedDict

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph


class StuckState(TypedDict, total=False):
    quality_score: int


def route(state: StuckState) -> Literal["revise", "finish"]:
    return "finish" if state.get("quality_score", 0) >= 1 else "revise"


builder = StateGraph(StuckState)
builder.add_node("review", lambda state: {"quality_score": 0})
builder.add_node("revise", lambda state: {})
builder.add_node("finish", lambda state: {})
builder.add_edge(START, "review")
builder.add_conditional_edges("review", route)
builder.add_edge("revise", "review")
builder.add_edge("finish", END)
stuck_graph = builder.compile()

try:
    stuck_graph.invoke({}, config={"recursion_limit": 5})
except GraphRecursionError as error:
    stopped = True
    error_type = type(error).__name__
else:
    stopped = False
    error_type = "none"

print("stopped_by_guardrail =", stopped)
print("error_type =", error_type)
print("business_terminal_state =", False)
```

**观察结果**：

```text output=ch08-no-progress-loop-failure
stopped_by_guardrail = True
error_type = GraphRecursionError
business_terminal_state = False
```

**发生了什么**：recursion limit 保护了进程，却没有产出业务可解释的结果。它是最后护栏，不是循环设计。

**动手修改**：把 recursion limit 提高到 20。说明为什么“允许多跑几次”没有增加任何完成概率。



### 让修订次数推动可判定终止

**运行前先预测**：review 在 revision_count 达到 2 时通过，节点顺序会怎样重复？

```python sync=ch08-progress-loop-repair
import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RevisionState(TypedDict, total=False):
    revision_count: int
    quality_score: int
    trace: Annotated[list[str], operator.add]


def review(state: RevisionState) -> dict[str, object]:
    score = 1 if state.get("revision_count", 0) >= 2 else 0
    return {"quality_score": score, "trace": [f"review:{score}"]}


def revise(state: RevisionState) -> dict[str, object]:
    next_count = state.get("revision_count", 0) + 1
    return {"revision_count": next_count, "trace": [f"revise:{next_count}"]}


def route(state: RevisionState) -> Literal["revise", "finish"]:
    return "finish" if state.get("quality_score", 0) >= 1 else "revise"


builder = StateGraph(RevisionState)
builder.add_node("review", review)
builder.add_node("revise", revise)
builder.add_node("finish", lambda state: {"trace": ["finish"]})
builder.add_edge(START, "review")
builder.add_conditional_edges("review", route)
builder.add_edge("revise", "review")
builder.add_edge("finish", END)
revision_graph = builder.compile()
result = revision_graph.invoke(
    {"revision_count": 0, "quality_score": 0, "trace": []}
)

print("revision_count =", result["revision_count"])
print("quality_score =", result["quality_score"])
print("trace =", result["trace"])
```

**观察结果**：

```text output=ch08-progress-loop-repair
revision_count = 2
quality_score = 1
trace = ['review:0', 'revise:1', 'review:0', 'revise:2', 'review:1', 'finish']
```

**发生了什么**：循环拥有可观察进度、可判定终止和 Graph 级最后护栏。生产系统还应设置最大修订次数、deadline 与升级人工路径。

若质量完全由同一个模型自由自评，进度数字也可能失真。业务终止应结合确定性规则、独立 evaluator、预算或人工判断。

**动手修改**：加入 `max_revisions=1`，让未达标任务以 `needs_review` 结束，而不是继续循环或伪装 completed。


## 6. Functional API：为过程式函数增加 durable task 语义

Graph API 适合显式共享 State 与可视化拓扑。已有代码若本来就是“调用几个函数并收集 futures”，Functional API 可以用 `@entrypoint` 与 `@task` 增加持久执行语义。


### 用 task future 保持普通函数阅读方式

**运行前先预测**：调用 task 后立即得到字符串，还是先得到 future，再由 entrypoint 收集结果？

```python sync=ch08-functional-task-baseline
from langgraph.func import entrypoint, task


@task
def research_topic(topic: str) -> str:
    return f"evidence:{topic}"


@entrypoint()
def research_all(topics: list[str]) -> list[str]:
    futures = [research_topic(topic) for topic in topics]
    return [future.result() for future in futures]


result = research_all.invoke(["checkpoint", "thread_id"])
print("result =", result)
print("entrypoint_type =", type(research_all).__name__)
print("graph_builder_written =", False)
```

**观察结果**：

```text output=ch08-functional-task-baseline
result = ['evidence:checkpoint', 'evidence:thread_id']
entrypoint_type = Pregel
graph_builder_written = False
```

**发生了什么**：代码仍像普通函数编排，但 task 调用返回 future，entrypoint 负责 durable runtime。Graph API 与 Functional API 共享 LangGraph persistence，不是两个互斥框架。

**动手修改**：让一个 task 抛出异常。先观察默认 fail-fast，再决定在哪里聚合 partial result，而不是无条件吞掉异常。


## 7. 工程迁移：Mini DeerFlow 组合完整研究拓扑

概念实验已经分别证明 Command、Send、Subgraph、循环和 Functional task。现在再运行项目工作流，观察这些原语如何共享领域 State、类型与事件。

### 7.1 一次运行串起全部 Graph 形状


### 运行确定性研究交付

**运行前先预测**：初稿第一次 review 不通过时，最终会修订几次？两个 section 是否都进入 findings？

```python sync=ch08-mini-deerflow-research-workflow
from mini_deerflow.graph import create_research_workflow


graph = create_research_workflow()
result = graph.invoke(
    {
        "objective": "解释 LangGraph durable execution",
        "sections": ["checkpoint", "side-effect"],
    }
)
trace = [event.as_text() for event in result["trace"]]

print("status =", result["status"])
print("revision_count =", result["revision_count"])
print("quality_score =", result["quality_score"])
print("finding_sections =", sorted(finding.section for finding in result["findings"]))
print("review_count =", trace.count("review:score"))
print("terminal_event =", trace[-1])
```

**观察结果**：

```text output=ch08-mini-deerflow-research-workflow
status = completed
revision_count = 1
quality_score = 2
finding_sections = ['checkpoint', 'side-effect']
review_count = 2
terminal_event = finalize
```

**发生了什么**：一个项目图组合串行 intake/plan、Command 拒绝路径、Send fan-out、findings reducer、review 子图和修订循环。`ResearchFinding` 与 `WorkflowEvent` 让并行结果和轨迹保持结构化。


### 7.2 Command 在 fan-out 前拒绝无效请求


### 证明拒绝路径没有偷偷运行 worker

**运行前先预测**：空白 objective 被拒绝后，Reducer 字段 findings 会不存在，还是以空列表出现？

```python sync=ch08-mini-deerflow-command-reject
from mini_deerflow.graph import create_research_workflow


result = create_research_workflow().invoke(
    {"objective": "   ", "sections": ["must-not-run"]}
)
trace = [event.as_text() for event in result["trace"]]

print("status =", result["status"])
print("trace =", trace)
print("findings =", result["findings"])
print("research_ran =", any(event.startswith("research:") for event in trace))
```

**观察结果**：

```text output=ch08-mini-deerflow-command-reject
status = rejected
trace = ['intake:reject']
findings = []
research_ran = False
```

**发生了什么**：Reducer channel 即使没有任务更新，也可能以单位元空列表出现在终态。可靠断言是 findings 为空且 trace 无 research，而不是依赖 key 恰好不存在。


### 7.3 stream 显示 Send task 与质量循环


### 从 updates 计数动态节点执行

**运行前先预测**：三个 section 会产生几个同名 `research_section` update？review 为什么出现两次？

```python sync=ch08-mini-deerflow-send-stream
from mini_deerflow.graph import create_research_workflow


updates = list(
    create_research_workflow().stream(
        {
            "objective": "比较 State 与 Store",
            "sections": ["state", "store", "checkpoint"],
        },
        stream_mode="updates",
    )
)
node_names = [next(iter(update)) for update in updates]

print("research_section_updates =", node_names.count("research_section"))
print("review_updates =", node_names.count("review"))
print("synthesize_updates =", node_names.count("synthesize"))
print("finalize_updates =", node_names.count("finalize"))
```

**观察结果**：

```text output=ch08-mini-deerflow-send-stream
research_section_updates = 3
review_updates = 2
synthesize_updates = 1
finalize_updates = 1
```

**发生了什么**：同名 research node 被三个 Send task 复用；review 两次来自一次修订循环，不是两个永久 review 子图。


### 7.4 xray 展开子图而不改变运行协议


### 查看 review 内部 score 节点

**运行前先预测**：普通 graph view 会把 review 当一个节点，`xray=True` 是否能看到内部 score？

```python sync=ch08-mini-deerflow-subgraph-xray
from mini_deerflow.graph import create_research_workflow


collapsed = create_research_workflow().get_graph()
expanded = create_research_workflow().get_graph(xray=True)

print("collapsed_has_review =", "review" in collapsed.nodes)
print("collapsed_has_score =", "review:score" in collapsed.nodes)
print("expanded_has_score =", "review:score" in expanded.nodes)
print("expanded_has_research =", "research_section" in expanded.nodes)
```

**观察结果**：

```text output=ch08-mini-deerflow-subgraph-xray
collapsed_has_review = True
collapsed_has_score = False
expanded_has_score = True
expanded_has_research = True
```

**发生了什么**：子图对父图是一个可复用节点边界，调试时仍可展开内部拓扑。控制流封装与可观察性并不冲突。


### 7.5 Functional task 固化 retry、cache 与失败聚合


### 区分瞬时失败与永久失败

**运行前先预测**：flaky 第一次 Timeout 后会尝试几次？ValueError 是否会被同一 retry policy 重试？

```python sync=ch08-mini-deerflow-functional-policies
from mini_deerflow.graph import create_functional_research_flow


flow = create_functional_research_flow()
first = flow.invoke(["stable", "flaky", "failed"])
second = flow.invoke(["stable", "flaky"])

print("first_statuses =", [(item.topic, item.status) for item in first])
print("failed_error_type =", first[2].error_type)
print("attempts =", {
    topic: flow.attempts_for(topic)
    for topic in ["stable", "flaky", "failed"]
})
print("second_statuses =", [item.status for item in second])
```

**观察结果**：

```text output=ch08-mini-deerflow-functional-policies
first_statuses = [('stable', 'completed'), ('flaky', 'completed'), ('failed', 'failed')]
failed_error_type = ValueError
attempts = {'stable': 1, 'flaky': 2, 'failed': 1}
second_statuses = ['completed', 'completed']
```

**发生了什么**：只对 TimeoutError 有限重试；永久 ValueError 变成类型化失败；第二次 stable/flaky 复用 task cache。

Cache 适合 TTL 内输入决定输出的读取任务，不能替代副作用幂等。错误聚合保留 topic、status 和 error type，也不等于吞异常。


### 7.6 回收第 04 章延后的 Artifact Command


### 工具结果同时形成 ToolMessage 与 State patch

**运行前先预测**：`record_artifact` 只告诉模型“成功”，还是也把 ArtifactRef 写进 Agent State？

```python sync=ch08-mini-deerflow-artifact-command
from langchain_core.messages import AIMessage, ToolMessage

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.knowledge import LocalKnowledgeIndex
from mini_deerflow.models import create_offline_model


model = create_offline_model(
    [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "record_artifact",
                    "args": {
                        "path": "reports/answer.md",
                        "media_type": "text/markdown",
                    },
                    "id": "artifact-1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(content="产物已经登记。"),
    ]
)
agent = create_lead_agent(
    model=model,
    knowledge_index=LocalKnowledgeIndex(),
)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "登记报告"}]}
)
tool_message = next(
    message for message in result["messages"] if isinstance(message, ToolMessage)
)

print("artifact =", result["artifacts"][0].model_dump())
print("tool_call_id =", tool_message.tool_call_id)
print("tool_message_name =", tool_message.name)
print("final_answer =", result["messages"][-1].content)
```

**观察结果**：

```text output=ch08-mini-deerflow-artifact-command
artifact = {'path': 'reports/answer.md', 'media_type': 'text/markdown'}
tool_call_id = artifact-1
tool_message_name = record_artifact
final_answer = 产物已经登记。
```

**发生了什么**：工具返回 `Command(update=...)`，既补上与 call ID 配对的 ToolMessage，也更新 artifacts State。第 04 章先学习消息循环；现在已有 StateGraph 基础，才解释这个双重效果。

真正写文件、校验路径、审计和隔离仍属于 Sandbox。登记引用不等于文件已安全落盘。


| 最小概念 | Mini DeerFlow 增加的工程边界 |
| --- | --- |
| Command update + goto | 类型化 WorkflowEvent、拒绝状态、真实业务路径 |
| Send task | ResearchFinding 领域类型、并行 reducer、确定性汇总 |
| ReviewState | 可展开 review subgraph 与父图组合 |
| Revision progress | 质量分数、修订次数、终态事件 |
| Functional task | 有限 retry、TTL cache、类型化 partial failure |
| Artifact Command | ToolMessage 配对、ArtifactRef reducer、后续 Sandbox 接缝 |

## 8. 如何选择 conditional edge、Command、Send 与 Subgraph

| 需求 | 优先机制 | 原因 |
| --- | --- | --- |
| 只读 State 后选择下一站 | conditional edge | router 保持纯函数 |
| 一个业务决定同时写 patch 并选路 | Command | 判断只有一个所有者 |
| 任务数量或输入运行时才知道 | Send | 动态 map task |
| 局部拓扑需要独立 State Schema | Subgraph | 缩小状态与复用边界 |
| 已有过程式函数需要 durable task | Functional API | 保留普通代码阅读方式 |

机制可以组合，但每次组合都要说明所有权。一个节点同时返回 Command、创建 Send、写多个 reducer 字段并调用外部副作用，通常说明模块边界过深或难以测试。

## 9. 并行、循环与副作用的工程约束

并行完成顺序不应决定业务语义。Mini DeerFlow 测试比较 section 集合，synthesize 再显式排序。如果必须保留计划顺序，应保存 sequence number，而不是依赖 scheduler 恰好按提交顺序结束。

循环至少需要：可观察进度、可判定终止、强制预算。若循环内包含发消息、写文件或扣费，重放与重试还要求幂等键；recursion limit 无法解决重复副作用。

Reducer 也是领域规则。`operator.add` 只适合“保留全部”的 append-only 语义；按 ID 去重、最大版本、last-write-wins 或冲突即失败都需要显式实现。

## 10. 练习：扩展同一个研究图

### 练习 A：部分失败

让一个 research task 返回类型化失败。选择 fail-fast、partial result 或 retry，并让 synthesize 明确知道缺少哪个 section。

### 练习 B：顺序语义

给 section 增加 sequence，随机延迟三个 worker。证明最终草稿按计划顺序汇总，而不是完成顺序。

### 练习 C：Command 路由

增加 `needs_info` 路径。比较 conditional edge 与 Command 两种写法，指出判断规则的唯一所有者。

### 练习 D：子图 adapter

让 review 使用与父图不同的字段名。编写显式输入/输出 adapter，并测试 secret 不进入子图。

### 延迟回忆

合上讲义回答：Command 何时优于条件边？Send 为什么仍需要 Reducer？Subgraph 与 Subagent 有什么不同？recursion limit 为什么不是业务终止策略？

## 11. 下一刻系统：研究拓扑完整，进程退出仍会清空现场

本章结束后，研究请求可以动态 fan-out，结果按领域规则汇合，局部 review 拥有独立 State，修订循环也有可观察进度。

但这些状态仍只活在当前进程。下一章会给同一 Graph 注入 Checkpointer，用真实 SQLite 关闭与重开实验区分 checkpoint、thread、snapshot 和 time travel。

运行本章验收：

```bash
TMPDIR="$PWD/.tmp" uv run --locked --group dev python \
  scripts/sync_lesson_notebooks.py tutorials/08_Engineering_Defense.md --execute
TMPDIR="$PWD/.tmp" uv run --locked --group dev pytest -q \
  tests/test_mini_deerflow_graph_workflows.py \
  tests/test_mini_deerflow_tool_contracts.py \
  tests/test_notebook_sync.py
TMPDIR="$PWD/.tmp" uv run --locked --group dev python scripts/validate_tutorials.py
```

资料访问日期：2026-07-21。

- [LangGraph Graph API: Command and Send](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph Use Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- [LangGraph Functional API](https://docs.langchain.com/oss/python/langgraph/use-functional-api)

继续阅读：[第 09 章：让研究 Graph 跨进程恢复](/langchain-logbook/posts/09_multi_agent_eval/)。