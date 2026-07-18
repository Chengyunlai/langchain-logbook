"""A transparent ReAct graph for learning control flow beneath ``create_agent``."""

from __future__ import annotations

from collections.abc import Sequence
import operator
from typing import Annotated, Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from mini_deerflow.graph.events import WorkflowEvent


# region tutorial:07-explicit-react-graph
class ReactGraphState(MessagesState):
    """Messages plus an append-only trace that exposes the ReAct loop."""

    node_trace: Annotated[list[WorkflowEvent], operator.add]


def create_explicit_react_graph(
    *,
    model: BaseChatModel,
    tools: Sequence[BaseTool],
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Compile a model → tools → model loop without a prebuilt Agent factory."""

    resolved_tools = list(tools)
    bound_model = model.bind_tools(resolved_tools)
    tool_node = ToolNode(resolved_tools)

    def call_model(state: ReactGraphState) -> dict[str, object]:
        response = bound_model.invoke(state["messages"])
        return {"messages": [response], "node_trace": [WorkflowEvent(name="model")]}

    def call_tools(state: ReactGraphState) -> dict[str, object]:
        update = tool_node.invoke(state)
        return {
            "messages": update["messages"],
            "node_trace": [WorkflowEvent(name="tools")],
        }

    def route_after_model(state: ReactGraphState) -> Literal["tools", "__end__"]:
        last_message = state["messages"][-1]
        return "tools" if getattr(last_message, "tool_calls", None) else END

    builder = StateGraph(ReactGraphState)
    builder.add_node("model", call_model)
    builder.add_node("tools", call_tools)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route_after_model)
    builder.add_edge("tools", "model")
    return builder.compile(checkpointer=checkpointer)
# endregion tutorial:07-explicit-react-graph


__all__ = ["ReactGraphState", "create_explicit_react_graph"]
