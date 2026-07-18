from __future__ import annotations

import unittest
import warnings

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain.tools import ToolRuntime, tool
from langchain_classic.indexes import SQLRecordManager, index
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"langsmith\.evaluation\._key_extraction",
    )
    from langsmith import Client, evaluate
from typing_extensions import TypedDict


class CounterState(TypedDict):
    value: int


class LangGraphPublicContractTests(unittest.TestCase):
    def test_current_course_imports_are_publicly_available(self) -> None:
        public_symbols = [
            AgentMiddleware,
            ToolRuntime,
            tool,
            SQLRecordManager,
            index,
            Command,
            Send,
            interrupt,
            Client,
            evaluate,
        ]

        self.assertTrue(all(symbol is not None for symbol in public_symbols))

    def test_v2_stream_uses_a_named_event_envelope(self) -> None:
        builder = StateGraph(CounterState)
        builder.add_node("increment", lambda state: {"value": state["value"] + 1})
        builder.add_edge(START, "increment")
        builder.add_edge("increment", END)
        graph = builder.compile()

        parts = list(graph.stream({"value": 0}, stream_mode=["updates"], version="v2"))

        self.assertEqual(len(parts), 1)
        self.assertIsInstance(parts[0], dict)
        self.assertEqual(parts[0]["type"], "updates")
        self.assertEqual(parts[0]["ns"], ())
        self.assertEqual(parts[0]["data"], {"increment": {"value": 1}})

    def test_agent_messages_input_preserves_the_human_message(self) -> None:
        model = GenericFakeChatModel(messages=iter([AIMessage(content="离线回答")]))
        agent = create_agent(model, tools=[])

        result = agent.invoke({"messages": [{"role": "user", "content": "离线问题"}]})

        self.assertEqual(len(result["messages"]), 2)
        self.assertIsInstance(result["messages"][0], HumanMessage)
        self.assertEqual(result["messages"][0].content, "离线问题")
        self.assertEqual(result["messages"][1].content, "离线回答")


if __name__ == "__main__":
    unittest.main()
