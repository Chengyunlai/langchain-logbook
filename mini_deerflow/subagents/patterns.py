"""Router、Handoff 与 Subgraph 的确定性离线对照实验。"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from mini_deerflow.schemas import SubagentResult


# region tutorial:11-control-patterns
class SingleRouterState(TypedDict, total=False):
    query: str
    route: Literal["research", "coding"]
    answer: str
    trace: Annotated[list[str], operator.add]


def build_single_router_graph():
    """用 ``Command`` 进行一次分类，只运行一个 specialist。"""

    def route(state: SingleRouterState) -> Command[Literal["research", "coding"]]:
        selected: Literal["research", "coding"] = (
            "coding" if any(word in state["query"] for word in ("代码", "Python", "修复")) else "research"
        )
        return Command(
            goto=selected,
            update={"route": selected, "trace": [f"router:{selected}"]},
        )

    def research(_: SingleRouterState) -> dict[str, object]:
        return {"answer": "research specialist result", "trace": ["research"]}

    def coding(_: SingleRouterState) -> dict[str, object]:
        return {"answer": "coding specialist result", "trace": ["coding"]}

    graph = StateGraph(SingleRouterState)
    graph.add_node("router", route)
    graph.add_node("research", research)
    graph.add_node("coding", coding)
    graph.add_edge(START, "router")
    graph.add_edge("research", END)
    graph.add_edge("coding", END)
    return graph.compile()


class ParallelRouterState(TypedDict, total=False):
    query: str
    routes: list[Literal["research", "coding"]]
    agent_name: Literal["research", "coding"]
    results: Annotated[list[SubagentResult], operator.add]
    answer: str


def build_parallel_router_graph():
    """用 ``Send`` fan-out 到同一个 worker，再以 reducer fan-in。"""

    def fan_out(state: ParallelRouterState) -> list[Send]:
        return [
            Send("specialist", {"query": state["query"], "agent_name": route})
            for route in state["routes"]
        ]

    def specialist(state: ParallelRouterState) -> dict[str, object]:
        agent_name = state["agent_name"]
        return {
            "results": [
                SubagentResult(
                    task_id=f"router-{agent_name}",
                    agent_name=agent_name,
                    status="completed",
                    summary=f"{agent_name}:{state['query']}",
                )
            ]
        }

    def synthesize(state: ParallelRouterState) -> dict[str, str]:
        names = sorted(result.agent_name for result in state["results"])
        return {"answer": "+".join(names)}

    graph = StateGraph(ParallelRouterState)
    graph.add_node("specialist", specialist)
    graph.add_node("synthesize", synthesize)
    graph.add_conditional_edges(START, fan_out, ["specialist"])
    graph.add_edge("specialist", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


class HandoffState(TypedDict, total=False):
    request: str
    active_agent: Literal["triage", "research", "coding"]
    answer: str
    trace: Annotated[list[str], operator.add]


def build_handoff_graph(*, checkpointer=None):
    """Handoff 把 active owner 保存在 state；后续 turn 直接回到该 Agent。"""

    def enter(
        state: HandoffState,
    ) -> Command[Literal["triage", "research", "coding"]]:
        active = state.get("active_agent")
        if active in {"research", "coding"}:
            return Command(goto=active)
        return Command(goto="triage")

    def triage(state: HandoffState) -> Command[Literal["research", "coding"]]:
        selected: Literal["research", "coding"] = (
            "coding" if any(word in state["request"] for word in ("代码", "Python", "修复")) else "research"
        )
        return Command(
            goto=selected,
            update={"active_agent": selected, "trace": [f"triage->{selected}"]},
        )

    def answer(state: HandoffState) -> dict[str, object]:
        owner = state["active_agent"]
        return {"answer": f"{owner} owns this turn", "trace": [f"{owner}:answered"]}

    graph = StateGraph(HandoffState)
    graph.add_node("enter", enter)
    graph.add_node("triage", triage)
    graph.add_node("research", answer)
    graph.add_node("coding", answer)
    graph.add_edge(START, "enter")
    graph.add_edge("research", END)
    graph.add_edge("coding", END)
    return graph.compile(checkpointer=checkpointer)


class SharedSubgraphState(TypedDict):
    query: str
    notes: Annotated[list[str], operator.add]


def build_shared_subgraph_graph():
    """父图与子图共享 schema，但 wrapper 只把 child 的增量写回父 reducer。"""

    def collect(state: SharedSubgraphState) -> dict[str, list[str]]:
        return {"notes": [f"subgraph:{state['query']}"]}

    child = StateGraph(SharedSubgraphState)
    child.add_node("collect", collect)
    child.add_edge(START, "collect")
    child.add_edge("collect", END)
    compiled_child = child.compile()

    def call_child(state: SharedSubgraphState) -> dict[str, list[str]]:
        child_result = compiled_child.invoke(state)
        # child 的最终 state 包含输入 notes；若整份返回给父 reducer，会重复追加。
        new_notes = child_result["notes"][len(state["notes"]) :]
        return {"notes": new_notes}

    parent = StateGraph(SharedSubgraphState)
    parent.add_node("specialist_subgraph", call_child)
    parent.add_edge(START, "specialist_subgraph")
    parent.add_edge("specialist_subgraph", END)
    return parent.compile()
# endregion tutorial:11-control-patterns


__all__ = [
    "build_handoff_graph",
    "build_parallel_router_graph",
    "build_shared_subgraph_graph",
    "build_single_router_graph",
]
