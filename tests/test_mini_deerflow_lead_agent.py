from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.knowledge import KnowledgeDocument, LocalKnowledgeIndex
from mini_deerflow.models import create_offline_model


class LeadAgentTests(unittest.TestCase):
    def test_explicit_empty_index_is_not_replaced_by_demo_knowledge(self) -> None:
        agent = create_lead_agent(knowledge_index=LocalKnowledgeIndex())

        result = agent.invoke({"messages": [{"role": "user", "content": "检索未知内容"}]})

        tool_message = next(
            message for message in result["messages"] if isinstance(message, ToolMessage)
        )
        self.assertEqual(tool_message.content, "[]")

    def test_user_message_can_complete_an_offline_knowledge_tool_loop(self) -> None:
        index = LocalKnowledgeIndex()
        index.upsert(
            [
                KnowledgeDocument(
                    id="agent-runtime",
                    text="create_agent 构建在 LangGraph runtime 之上。",
                    source="official/agents.md",
                )
            ]
        )
        model = create_offline_model(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_knowledge",
                            "args": {"query": "create_agent LangGraph", "limit": 1},
                            "id": "search-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="create_agent 使用 LangGraph runtime，并保留高层工具循环。"),
            ]
        )
        agent = create_lead_agent(model=model, knowledge_index=index)

        result = agent.invoke({"messages": [{"role": "user", "content": "两者是什么关系？"}]})

        self.assertIsInstance(result["messages"][0], HumanMessage)
        tool_message = next(
            message for message in result["messages"] if isinstance(message, ToolMessage)
        )
        self.assertIn("official/agents.md", tool_message.content)
        self.assertEqual(
            result["messages"][-1].content,
            "create_agent 使用 LangGraph runtime，并保留高层工具循环。",
        )


if __name__ == "__main__":
    unittest.main()
