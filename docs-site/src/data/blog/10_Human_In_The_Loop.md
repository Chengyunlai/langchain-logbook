---
title: "第 10 章：从阻塞等待到可恢复人工审批"
description: "用 interrupt/resume 实现持久审批，并保护重放场景中的副作用。"
pubDatetime: 2026-03-24T00:00:00.000Z
featured: false
tags: ["tutorial"]
sourcePath: "tutorials/10_Human_In_The_Loop.md"
learningOrder: 10
learningStage: "langgraph"
learningStageTitle: "把业务流程写成可恢复的图"
learningGoal: "用 interrupt/resume 实现持久审批，并保护重放场景中的副作用。"
contentType: "main"
---



> **课程位置**：Graph 编排层第 4 章
> **锁定环境**：Python 3.12 / LangGraph 1.2.x / SQLite checkpointer 3.x
> **本章工件**：interrupt、Command(resume)、审批协议、重放边界与幂等 effect ledger

## 1. 上一刻系统：执行现场可以恢复，发布仍会直接发生

第 09 章让 Graph 跨 saver 与进程重建保留 StateSnapshot。现在研究报告生成后仍会直接发布；真实业务常要求负责人批准、编辑或拒绝。

人工可能数分钟或数天后响应。服务器不能让原 worker 一直停在 `input()`、Event.wait 或 HTTP 请求中。审批需要“保存现场、结束当前 Run、稍后以新请求恢复”。

```mermaid
sequenceDiagram
    participant C as Client / Gateway
    participant G as Approval Graph
    participant CP as Checkpointer
    participant H as Human Reviewer
    participant E as Effect Ledger

    C->>G: invoke(request, thread_id)
    G->>CP: checkpoint pending interrupt
    G-->>C: interrupt payload
    C->>H: 展示审批请求
    Note over G: 原 worker 已释放
    H->>C: approve / edit / reject
    C->>G: Command(resume=decision), same thread
    G->>E: record_once(operation_id)
    G-->>C: completed / rejected
```

**图的文本替代**：Graph 把 interrupt 写进 checkpoint 后返回控制权。人工决定通过新请求和同一 thread 恢复；审批通过后，副作用意图使用稳定 operation ID 记录。

## 2. 第一处失败：同步等待占住唯一 worker

`input()` 在 Notebook 中直观，在服务端却会占用线程、连接或协程。审批时间越长，资源泄漏越明显；部署或崩溃还会丢失原调用栈。


### 一个审批等待让后续任务无法开始

**运行前先预测**：线程池只有一个 worker，第一个任务等待 Event 时，第二个任务能否完成？

```python sync=ch10-blocking-wait-failure
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event


approval_arrived = Event()
waiting_started = Event()


def blocking_approval() -> str:
    waiting_started.set()
    approval_arrived.wait()
    return "approved"


with ThreadPoolExecutor(max_workers=1) as executor:
    waiting = executor.submit(blocking_approval)
    waiting_started.wait(timeout=1)
    unrelated = executor.submit(lambda: "unrelated-completed")
    try:
        unrelated.result(timeout=0.05)
    except TimeoutError:
        second_task_blocked = True
    else:
        second_task_blocked = False
    approval_arrived.set()
    approval_result = waiting.result(timeout=1)
    unrelated_result = unrelated.result(timeout=1)

print("second_task_blocked =", second_task_blocked)
print("approval_result =", approval_result)
print("unrelated_result =", unrelated_result)
print("worker_held_while_waiting =", True)
```

**观察结果**：

```text output=ch10-blocking-wait-failure
second_task_blocked = True
approval_result = approved
unrelated_result = unrelated-completed
worker_held_while_waiting = True
```

**发生了什么**：审批本身没有计算工作，却占住唯一 worker。增加线程只能推迟耗尽，不能让等待跨部署恢复。

**动手修改**：把线程数改为 2，再提交三个等待任务。说明容量扩张为什么没有改变资源与恢复模型。



### interrupt 保存暂停点并立即返回

**运行前先预测**：第一次 invoke 会返回 completed，还是携带 `__interrupt__`？snapshot.next 指向哪个节点？

```python sync=ch10-durable-interrupt-repair
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict, total=False):
    request_id: str
    status: str


def review(state: ApprovalState) -> dict[str, str]:
    decision = interrupt(
        {"request_id": state["request_id"], "question": "是否批准发布？"}
    )
    return {"status": "completed" if decision == "approve" else "rejected"}


builder = StateGraph(ApprovalState)
builder.add_node("review", review)
builder.add_edge(START, "review")
builder.add_edge("review", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "approval-001"}}
paused = graph.invoke({"request_id": "approval-001"}, config=config)
snapshot = graph.get_state(config)
resumed = graph.invoke(Command(resume="approve"), config=config)

print("interrupt_count =", len(paused["__interrupt__"]))
print("interrupt_value =", paused["__interrupt__"][0].value)
print("paused_next =", snapshot.next)
print("resumed_status =", resumed["status"])
```

**观察结果**：

```text output=ch10-durable-interrupt-repair
interrupt_count = 1
interrupt_value = {'request_id': 'approval-001', 'question': '是否批准发布？'}
paused_next = ('review',)
resumed_status = completed
```

**发生了什么**：`interrupt(value)` 让当前调用返回，pending review 写进 checkpoint。后续 `Command(resume=...)` 使用同一 thread，把值交回 interrupt 调用。

包含 interrupt 的节点恢复时从节点开头执行。不要用 broad `try/except` 吞掉 GraphInterrupt，也不要让 resume 使用另一个 thread ID。

**动手修改**：用新 thread ID 调用 resume。记录框架如何拒绝没有匹配 interrupt 的恢复请求。


## 3. Resume payload 是外部输入，仍要验证

人工决定不是可信 Python 对象。API 传入的 `approve`、`edit`、`reject` 必须有结构化协议；edit 还要限制允许修改的字段。


### 用 Pydantic 验证 approve、edit 与 reject

**运行前先预测**：decision 为 edit 却缺少 edited_payload 时，协议会在 Graph 路由前还是发布后失败？

```python sync=ch10-approval-decision-protocol
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    edited_payload: dict[str, str] | None = None
    reason: str = ""

    @model_validator(mode="after")
    def edit_requires_payload(self):
        if self.decision == "edit" and not self.edited_payload:
            raise ValueError("edit 必须包含 edited_payload")
        return self


approve = ApprovalDecision(decision="approve")
edit = ApprovalDecision(
    decision="edit",
    edited_payload={"path": "reports/reviewed.md"},
)
reject = ApprovalDecision(decision="reject", reason="证据不足")
try:
    ApprovalDecision(decision="edit")
except ValidationError as error:
    invalid_edit_error = error.errors()[0]["type"]
else:
    invalid_edit_error = "none"

print("decisions =", [approve.decision, edit.decision, reject.decision])
print("edited_path =", edit.edited_payload["path"])
print("reject_reason =", reject.reason)
print("invalid_edit_error =", invalid_edit_error)
```

**观察结果**：

```text output=ch10-approval-decision-protocol
decisions = ['approve', 'edit', 'reject']
edited_path = reports/reviewed.md
reject_reason = 证据不足
invalid_edit_error = value_error
```

**发生了什么**：决定在进入业务路由前完成结构和跨字段校验。Schema 合法仍不代表当前用户有审批权限，Gateway 还要校验 thread owner、stage role 与四眼原则。

**动手修改**：让 edit 只能改 path，不能改 request_id 或 action。明确允许字段，而不是接受任意 dict 后再删除危险 key。


## 4. 第二处失败：interrupt 前的副作用会在 resume 时重复

节点恢复从头执行，因此 interrupt 前的日志、邮件、扣款或文件写入会再次发生。Checkpoint 不会回滚外部世界。


### Resume 让外部 append 执行两次

**运行前先预测**：初次暂停前 append 一次，resume 重入节点后列表长度是多少？

```python sync=ch10-effect-before-interrupt-failure
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class UnsafeState(TypedDict):
    request_id: str


external_effects: list[str] = []


def unsafe_review(state: UnsafeState) -> dict[str, object]:
    external_effects.append(state["request_id"])
    interrupt({"request_id": state["request_id"]})
    return {}


builder = StateGraph(UnsafeState)
builder.add_node("review", unsafe_review)
builder.add_edge(START, "review")
builder.add_edge("review", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "unsafe-001"}}
graph.invoke({"request_id": "unsafe-001"}, config=config)
graph.invoke(Command(resume="approve"), config=config)

print("external_effects =", external_effects)
print("effect_count =", len(external_effects))
print("same_request_repeated =", len(set(external_effects)) == 1)
```

**观察结果**：

```text output=ch10-effect-before-interrupt-failure
external_effects = ['unsafe-001', 'unsafe-001']
effect_count = 2
same_request_repeated = True
```

**发生了什么**：Graph 正确恢复了 review，外部副作用却无法由 checkpoint 去重。问题不是 interrupt 重复，而是副作用顺序错误。

**动手修改**：在 append 前检查 State 中的布尔值。思考 crash 发生在 append 后、State checkpoint 前时，这个布尔值为什么仍不可靠。



### 把副作用移到审批后的独立节点

**运行前先预测**：review resume 会重入，但 publish 节点在批准后只执行几次？

```python sync=ch10-effect-after-interrupt-repair
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class SafeState(TypedDict, total=False):
    request_id: str
    status: str


external_effects: list[str] = []


def review(state: SafeState) -> Command[Literal["publish", "reject"]]:
    decision = interrupt({"request_id": state["request_id"]})
    return Command(goto="publish" if decision == "approve" else "reject")


def publish(state: SafeState) -> dict[str, str]:
    external_effects.append(state["request_id"])
    return {"status": "completed"}


builder = StateGraph(SafeState)
builder.add_node("review", review)
builder.add_node("publish", publish)
builder.add_node("reject", lambda state: {"status": "rejected"})
builder.add_edge(START, "review")
builder.add_edge("publish", END)
builder.add_edge("reject", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "safe-001"}}
graph.invoke({"request_id": "safe-001"}, config=config)
result = graph.invoke(Command(resume="approve"), config=config)

print("status =", result["status"])
print("external_effects =", external_effects)
print("effect_count =", len(external_effects))
```

**观察结果**：

```text output=ch10-effect-after-interrupt-repair
status = completed
external_effects = ['safe-001']
effect_count = 1
```

**发生了什么**：review 可以从头重入，publish 只在批准路径执行。这个顺序修复 resume 重入，但 publish 自身失败恢复或 time travel 仍可能重放，因此还需要幂等键。

**动手修改**：reject 后确认 external_effects 为空。再解释为什么 approve 请求重复提交需要 Gateway 冲突检查。


## 5. 第三处失败：Time travel 会再次执行发布节点

第 09 章已经证明 time travel 从历史 `next` 形成新 lineage。若目标 checkpoint 位于 publish 前，重放会再次触发外部调用。


### 从 publish 前 checkpoint 重放出第二条记录

**运行前先预测**：首次 approve 已 append 一次，再从 `next == ('publish',)` 重放，列表长度是多少？

```python sync=ch10-time-travel-duplicate-failure
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class EffectState(TypedDict, total=False):
    operation_id: str
    status: str


effects: list[str] = []


def review(state: EffectState) -> Command[Literal["publish"]]:
    interrupt({"operation_id": state["operation_id"]})
    return Command(goto="publish")


def publish(state: EffectState) -> dict[str, str]:
    effects.append(state["operation_id"])
    return {"status": "completed"}


builder = StateGraph(EffectState)
builder.add_node("review", review)
builder.add_node("publish", publish)
builder.add_edge(START, "review")
builder.add_edge("publish", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "replay-001"}}
graph.invoke({"operation_id": "publish-001"}, config=config)
graph.invoke(Command(resume="approve"), config=config)
before_publish = next(
    snapshot
    for snapshot in graph.get_state_history(config)
    if snapshot.next == ("publish",)
)
graph.invoke(None, config=before_publish.config)

print("effects =", effects)
print("effect_count =", len(effects))
print("unique_operation_ids =", len(set(effects)))
```

**观察结果**：

```text output=ch10-time-travel-duplicate-failure
effects = ['publish-001', 'publish-001']
effect_count = 2
unique_operation_ids = 1
```

**发生了什么**：Checkpoint 能准确重放节点，外部 list 却没有幂等语义。Exactly-once 不能由 Graph checkpoint 自动推导。

**动手修改**：每次重试生成新的随机 operation ID。说明这为何彻底破坏去重能力。



### 用稳定 operation ID 让重放返回 already_recorded

**运行前先预测**：记录函数第二次收到相同 ID 和 payload 时，应插入新记录还是返回已有结果？

```python sync=ch10-idempotent-effect-repair
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class EffectState(TypedDict, total=False):
    operation_id: str
    status: str
    effect_status: str


ledger: dict[str, str] = {}


def record_once(operation_id: str, payload: str) -> str:
    if operation_id in ledger:
        if ledger[operation_id] != payload:
            raise ValueError("operation ID 已用于不同 payload")
        return "already_recorded"
    ledger[operation_id] = payload
    return "recorded"


def review(state: EffectState) -> Command[Literal["publish"]]:
    interrupt({"operation_id": state["operation_id"]})
    return Command(goto="publish")


def publish(state: EffectState) -> dict[str, str]:
    effect_status = record_once(state["operation_id"], "reports/final.md")
    return {"status": "completed", "effect_status": effect_status}


builder = StateGraph(EffectState)
builder.add_node("review", review)
builder.add_node("publish", publish)
builder.add_edge(START, "review")
builder.add_edge("publish", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "idempotent-001"}}
graph.invoke({"operation_id": "publish-001"}, config=config)
graph.invoke(Command(resume="approve"), config=config)
before_publish = next(
    snapshot
    for snapshot in graph.get_state_history(config)
    if snapshot.next == ("publish",)
)
replayed = graph.invoke(None, config=before_publish.config)

print("replayed_effect_status =", replayed["effect_status"])
print("ledger_count =", len(ledger))
print("stored_payload =", ledger["publish-001"])
```

**观察结果**：

```text output=ch10-idempotent-effect-repair
replayed_effect_status = already_recorded
ledger_count = 1
stored_payload = reports/final.md
```

**发生了什么**：稳定 operation ID 把两次节点执行映射为同一个业务意图。相同 key、不同 payload 必须冲突，而不能伪装成功。

内存 dict 只解释语义，不能跨进程协调。工程迁移会使用 SQLite 事务；远端发布还需 provider idempotency key 或 outbox。

**动手修改**：第二次使用相同 ID 和不同 path。确认 fail closed，并记录冲突需要怎样审计。


## 6. 多个 interrupt 依赖稳定调用顺序

同一节点可以按顺序请求 risk、compliance 等审批。每次 resume 都从节点开头执行；已保存的 resume value 按 interrupt 调用顺序匹配。


### 两次 Resume 三次进入同一节点

**运行前先预测**：两个审批阶段需要初次运行加几次 resume？review 节点总共进入几次？

```python sync=ch10-multiple-interrupt-order
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class MultiState(TypedDict, total=False):
    stages: list[str]
    status: str


entries: list[str] = []


def review(state: MultiState) -> dict[str, str]:
    entries.append("review_node_entered")
    for stage in state["stages"]:
        interrupt({"stage": stage})
    return {"status": "completed"}


builder = StateGraph(MultiState)
builder.add_node("review", review)
builder.add_edge(START, "review")
builder.add_edge("review", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "multi-001"}}
graph.invoke({"stages": ["risk", "compliance"]}, config=config)
first_stage = graph.get_state(config).tasks[0].interrupts[0].value["stage"]
graph.invoke(Command(resume="approve"), config=config)
second_stage = graph.get_state(config).tasks[0].interrupts[0].value["stage"]
result = graph.invoke(Command(resume="approve"), config=config)

print("stages =", [first_stage, second_stage])
print("node_entry_count =", len(entries))
print("status =", result["status"])
```

**观察结果**：

```text output=ch10-multiple-interrupt-order
stages = ['risk', 'compliance']
node_entry_count = 3
status = completed
```

**发生了什么**：第一次 resume 让第一个 interrupt 取得保存值，然后在第二个暂停；第二次 resume 才完成。改变 interrupt 数量或顺序会让历史值错配。

**动手修改**：根据可变 State 交换 stages 顺序，观察为什么恢复协议必须冻结业务 request ID 与调用次序。


## 7. 工程迁移：Mini DeerFlow 的 durable approval

### 7.1 关闭 SQLite 后恢复审批


### 新 Graph 实例继续同一 interrupt

**运行前先预测**：暂停后关闭 saver，重开时 effect ledger 是否已有记录？批准后有几行？

```python sync=ch10-mini-deerflow-approve-restart
from pathlib import Path
import tempfile

from langgraph.types import Command

from mini_deerflow.graph import create_approval_workflow
from mini_deerflow.persistence import (
    SqliteEffectLedger,
    open_sqlite_checkpointer,
)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    checkpoint_path = root / "checkpoints.sqlite"
    effects = SqliteEffectLedger(root / "effects.sqlite")
    config = {"configurable": {"thread_id": "publish-001"}}
    request = {
        "request_id": "publish-001",
        "action": "publish_report",
        "payload": {"path": "reports/final.md"},
        "review_stages": ["risk"],
    }
    with open_sqlite_checkpointer(checkpoint_path) as saver:
        graph = create_approval_workflow(
            checkpointer=saver,
            effect_ledger=effects,
        )
        paused = graph.invoke(request, config=config)
        paused_next = graph.get_state(config).next
        count_while_paused = effects.count("publish-001")

    with open_sqlite_checkpointer(checkpoint_path) as saver:
        restarted = create_approval_workflow(
            checkpointer=saver,
            effect_ledger=effects,
        )
        result = restarted.invoke(
            Command(resume={"decision": "approve"}),
            config=config,
        )
        final_effect_count = effects.count("publish-001")

print("paused_stage =", paused["__interrupt__"][0].value["stage"])
print("paused_next =", paused_next)
print("count_while_paused =", count_while_paused)
print("final_status =", result["status"])
print("effect_count =", final_effect_count)
```

**观察结果**：

```text output=ch10-mini-deerflow-approve-restart
paused_stage = risk
paused_next = ('review',)
count_while_paused = 0
final_status = completed
effect_count = 1
```

**发生了什么**：审批暂停跨 saver 与 compiled Graph 重建存在，原 worker 已经结束。Effect intent 只在批准后记录。


### 7.2 Edit 与 reject 走不同业务终态


### 编辑 payload，拒绝不产生 intent

**运行前先预测**：edit 会保留原 path 还是替换为 reviewed path？reject 的 ledger count 是多少？

```python sync=ch10-mini-deerflow-edit-reject
from pathlib import Path
import tempfile

from langgraph.types import Command

from mini_deerflow.graph import create_approval_workflow
from mini_deerflow.persistence import SqliteEffectLedger, create_memory_checkpointer


with tempfile.TemporaryDirectory() as directory:
    effects = SqliteEffectLedger(Path(directory) / "effects.sqlite")
    graph = create_approval_workflow(
        checkpointer=create_memory_checkpointer(),
        effect_ledger=effects,
    )
    edit_config = {"configurable": {"thread_id": "edit-001"}}
    graph.invoke(
        {
            "request_id": "edit-001",
            "action": "publish_report",
            "payload": {"path": "reports/draft.md"},
        },
        config=edit_config,
    )
    edited = graph.invoke(
        Command(resume={
            "decision": "edit",
            "edited_payload": {"path": "reports/reviewed.md"},
        }),
        config=edit_config,
    )

    reject_config = {"configurable": {"thread_id": "reject-001"}}
    graph.invoke(
        {
            "request_id": "reject-001",
            "action": "publish_report",
            "payload": {"path": "reports/unsafe.md"},
        },
        config=reject_config,
    )
    rejected = graph.invoke(
        Command(resume={"decision": "reject", "reason": "证据不足"}),
        config=reject_config,
    )
    edit_effect_count = effects.count("edit-001")
    reject_effect_count = effects.count("reject-001")

print("edited_path =", edited["payload"]["path"])
print("edit_effect_count =", edit_effect_count)
print("rejected_status =", rejected["status"])
print("reject_effect_count =", reject_effect_count)
```

**观察结果**：

```text output=ch10-mini-deerflow-edit-reject
edited_path = reports/reviewed.md
edit_effect_count = 1
rejected_status = rejected
reject_effect_count = 0
```

**发生了什么**：edit 的结构化决定更新 payload 后才记录 intent；reject 形成终态但不触碰 ledger。生产 API 还要保留原提案和编辑审计。


### 7.3 多阶段审批保留稳定顺序


### 从 custom event 证明节点重入

**运行前先预测**：risk 与 compliance 两阶段完成后，review_node_entered 会出现几次？

```python sync=ch10-mini-deerflow-multiple-interrupts
from pathlib import Path
import tempfile

from langgraph.types import Command

from mini_deerflow.graph import create_approval_workflow
from mini_deerflow.persistence import SqliteEffectLedger, create_memory_checkpointer


with tempfile.TemporaryDirectory() as directory:
    effects = SqliteEffectLedger(Path(directory) / "effects.sqlite")
    graph = create_approval_workflow(
        checkpointer=create_memory_checkpointer(),
        effect_ledger=effects,
    )
    config = {"configurable": {"thread_id": "multi-001"}}
    request = {
        "request_id": "multi-001",
        "action": "publish_report",
        "payload": {"path": "reports/final.md"},
        "review_stages": ["risk", "compliance"],
    }
    first_events = list(graph.stream(request, config=config, stream_mode="custom"))
    first_stage = graph.get_state(config).tasks[0].interrupts[0].value["stage"]
    second_events = list(graph.stream(
        Command(resume={"decision": "approve"}),
        config=config,
        stream_mode="custom",
    ))
    second_stage = graph.get_state(config).tasks[0].interrupts[0].value["stage"]
    final_events = list(graph.stream(
        Command(resume={"decision": "approve"}),
        config=config,
        stream_mode="custom",
    ))

entry_events = [first_events[0], second_events[0], final_events[0]]
print("stages =", [first_stage, second_stage])
print("entry_events =", [event["event"] for event in entry_events])
print("final_status =", graph.get_state(config).values["status"])
```

**观察结果**：

```text output=ch10-mini-deerflow-multiple-interrupts
stages = ['risk', 'compliance']
entry_events = ['review_node_entered', 'review_node_entered', 'review_node_entered']
final_status = completed
```

**发生了什么**：项目事件把节点三次进入变成可测试事实。复杂并行审批可使用 interrupt ID 到 resume value 的映射，但业务 request ID 仍须稳定。


### 7.4 SQLite ledger 抵抗 time travel 重放


### 同一 effect intent 只保留一行

**运行前先预测**：从 `record_effect_intent` 前重放后，effect_status 与数据库行数分别是什么？

```python sync=ch10-mini-deerflow-time-travel-idempotency
from pathlib import Path
import tempfile

from langgraph.types import Command

from mini_deerflow.graph import create_approval_workflow
from mini_deerflow.persistence import SqliteEffectLedger, create_memory_checkpointer


with tempfile.TemporaryDirectory() as directory:
    effects = SqliteEffectLedger(Path(directory) / "effects.sqlite")
    graph = create_approval_workflow(
        checkpointer=create_memory_checkpointer(),
        effect_ledger=effects,
    )
    config = {"configurable": {"thread_id": "replay-001"}}
    graph.invoke(
        {
            "request_id": "replay-001",
            "action": "publish_report",
            "payload": {"path": "reports/final.md"},
        },
        config=config,
    )
    graph.invoke(Command(resume={"decision": "approve"}), config=config)
    before_effect = next(
        snapshot
        for snapshot in graph.get_state_history(config)
        if snapshot.next == ("record_effect_intent",)
    )
    replayed = graph.invoke(None, config=before_effect.config)
    replay_effect_count = effects.count("replay-001")

print("replayed_effect_status =", replayed["effect_status"])
print("effect_count =", replay_effect_count)
```

**观察结果**：

```text output=ch10-mini-deerflow-time-travel-idempotency
replayed_effect_status = already_recorded
effect_count = 1
```

**发生了什么**：SQLite ledger 把 operation ID、action 与规范化 payload 放进事务边界。它证明本地 intent 幂等，不宣称远端投递 exactly-once。


### 7.5 两个连接争抢同一 operation ID


### 本地事务串行化 check/insert

**运行前先预测**：两个 ledger 同时写同一 key，结果会是两次 recorded，还是 recorded + already_recorded？

```python sync=ch10-mini-deerflow-concurrent-intent
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading

from mini_deerflow.persistence import SqliteEffectLedger


with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "effects.sqlite"
    ledgers = [SqliteEffectLedger(path), SqliteEffectLedger(path)]
    barrier = threading.Barrier(2)

    def record(ledger: SqliteEffectLedger) -> str:
        barrier.wait()
        return ledger.record_once(
            "concurrent-001",
            "publish_report",
            {"path": "reports/final.md"},
        ).status

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(record, ledgers))
    concurrent_effect_count = ledgers[0].count("concurrent-001")

print("statuses =", sorted(statuses))
print("effect_count =", concurrent_effect_count)
```

**观察结果**：

```text output=ch10-mini-deerflow-concurrent-intent
statuses = ['already_recorded', 'recorded']
effect_count = 1
```

**发生了什么**：`BEGIN IMMEDIATE` 串行化本地 SQLite 临界区，主键是最终防线。跨数据库与远端 API 仍需它们自己的协调协议。


### 7.6 相同 key、不同副作用必须冲突


### 拒绝复用 operation ID

**运行前先预测**：同一个 operation ID 从 publish 改成 delete，ledger 会返回第一次结果还是抛冲突？

```python sync=ch10-mini-deerflow-idempotency-conflict
from pathlib import Path
import tempfile

from mini_deerflow.persistence import (
    IdempotencyConflictError,
    SqliteEffectLedger,
)


with tempfile.TemporaryDirectory() as directory:
    ledger = SqliteEffectLedger(Path(directory) / "effects.sqlite")
    ledger.record_once(
        "operation-001",
        "publish_report",
        {"path": "reports/final.md"},
    )
    try:
        ledger.record_once(
            "operation-001",
            "delete_report",
            {"path": "reports/final.md"},
        )
    except IdempotencyConflictError as error:
        conflict = True
        error_type = type(error).__name__
    else:
        conflict = False
        error_type = "none"
    conflict_effect_count = ledger.count("operation-001")

print("conflict =", conflict)
print("error_type =", error_type)
print("effect_count =", conflict_effect_count)
```

**观察结果**：

```text output=ch10-mini-deerflow-idempotency-conflict
conflict = True
error_type = IdempotencyConflictError
effect_count = 1
```

**发生了什么**：幂等不是“同 key 永远成功”。相同业务意图可重放，不同意图复用 key 必须 fail closed，并进入审计或人工处理。


| 最小概念 | Mini DeerFlow 增加的工程边界 |
| --- | --- |
| interrupt + resume | 版本化 ApprovalDecision 与项目 review stages |
| 同一 thread 恢复 | SQLite checkpointer 重建与产品 Run 接缝 |
| 副作用后移 | 独立 record_effect_intent 节点 |
| operation ID | SQLite 事务、冲突检测、并发测试 |
| 多 interrupt | custom event 与稳定阶段顺序 |

## 8. Graph 暂停不等于审批系统安全

Gateway 仍必须验证：thread ownership、审批角色、interrupt 是否仍待处理、edit 允许字段、四眼原则，以及原提案/决定/reason/身份/时间的不可抵赖审计。

不要把 auth token 放进 interrupt value 或 State；它们会进入 checkpoint、API 响应和可能的 trace。

动态 `interrupt(payload)` 适合业务审批。`interrupt_before=["tools"]` 是静态断点，适合调试或统一拦截，不能替代带业务载荷与决定 Schema 的审批协议。

## 9. 练习：把审批接入自己的副作用

### 练习 A：第三审批阶段

新增 legal 阶段，用事件证明节点初次运行加三次 resume 共进入四次。

### 练习 B：Edit allowlist

只允许修改 path 与 title。非法修改 request ID、action 或 owner 时拒绝 resume，并保留审计。

### 练习 C：事务 outbox

Graph 只写 outbox，独立 worker 发送。逐项分析 crash 发生在 insert、send、provider success、ack 前后的恢复策略。

### 练习 D：重复审批请求

同一 interrupt 被两个浏览器页面同时批准。定义 Gateway 冲突响应、Run ID 与最终审计事实。

### 延迟回忆

合上讲义回答：resume 从节点哪里开始？interrupt 前为何不能发送邮件？time travel 为何不会回滚数据库？相同幂等 key 何时应成功，何时应冲突？

## 10. 下一刻系统：流程可审批，Lead 上下文开始膨胀

本章结束后，Graph 能持久暂停、跨重建恢复、验证人工决定，并以稳定 operation ID 保护本地副作用意图。

第三部至此完成。随着研究轮次、工具结果和草稿增长，Lead Agent 的 Context 开始污染。第 11 章会先制造“把所有任务都塞给 Lead”的失败，再从零推出 Subagent 委派、隔离和稳定失败协议。

运行本章验收：

```bash
TMPDIR="$PWD/.tmp" uv run --locked --group dev python \
  scripts/sync_lesson_notebooks.py tutorials/10_Human_In_The_Loop.md --execute
TMPDIR="$PWD/.tmp" uv run --locked --group dev pytest -q \
  tests/test_mini_deerflow_persistence_hitl.py \
  tests/test_notebook_sync.py
TMPDIR="$PWD/.tmp" uv run --locked --group dev python scripts/validate_tutorials.py
```

资料访问日期：2026-07-21。

- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Time Travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)

继续阅读：[第 11 章：用 Subagent 隔离任务与上下文](/langchain-logbook/posts/11_multi_agent_patterns/)。