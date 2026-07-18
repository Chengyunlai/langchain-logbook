from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.config import LeadAgentContext
from mini_deerflow.knowledge import LocalKnowledgeIndex
from mini_deerflow.models import create_offline_model
from mini_deerflow.tools import build_tool_registry


def _tool_call(name: str, args: dict[str, object], call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


class ToolContractTests(unittest.TestCase):
    def test_registry_exposes_calculator_and_search_with_validated_schemas(self) -> None:
        registry = {tool.name: tool for tool in build_tool_registry(LocalKnowledgeIndex())}

        result = registry["calculator"].invoke({"operation": "multiply", "left": 6, "right": 7})

        self.assertEqual(result, "42.0")
        self.assertIn("search_knowledge", registry)
        self.assertEqual(
            registry["search_knowledge"].metadata,
            {"required_permission": "knowledge:read"},
        )
        self.assertEqual(
            registry["read_workspace_file"].metadata,
            {"required_permission": "workspace:read"},
        )

    def test_read_only_workspace_tool_uses_runtime_context_not_model_args(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "notes.txt").write_text("只读工作区证据", encoding="utf-8")
            model = create_offline_model(
                [
                    _tool_call("read_workspace_file", {"path": "notes.txt"}, "read-1"),
                    AIMessage(content="已读取文件。"),
                ]
            )
            agent = create_lead_agent(model=model, knowledge_index=LocalKnowledgeIndex())

            result = agent.invoke(
                {"messages": [{"role": "user", "content": "读取 notes.txt"}]},
                context=LeadAgentContext(user_id="learner", workspace_root=directory),
            )

        tool_message = next(
            message for message in result["messages"] if isinstance(message, ToolMessage)
        )
        self.assertIn("只读工作区证据", tool_message.content)

    def test_artifact_tool_returns_command_that_updates_agent_state(self) -> None:
        model = create_offline_model(
            [
                _tool_call(
                    "record_artifact",
                    {"path": "reports/answer.md", "media_type": "text/markdown"},
                    "artifact-1",
                ),
                AIMessage(content="产物已经登记。"),
            ]
        )
        agent = create_lead_agent(model=model, knowledge_index=LocalKnowledgeIndex())

        result = agent.invoke({"messages": [{"role": "user", "content": "登记报告"}]})

        self.assertEqual(result["artifacts"][0].path, "reports/answer.md")

    def test_unbounded_tool_loop_hits_the_graph_recursion_limit(self) -> None:
        looping_model = create_offline_model(
            [_tool_call("calculator", {"operation": "add", "left": 1, "right": 1}, f"c-{i}") for i in range(10)]
        )
        agent = create_lead_agent(model=looping_model, knowledge_index=LocalKnowledgeIndex())

        with self.assertRaises(GraphRecursionError):
            agent.invoke(
                {"messages": [{"role": "user", "content": "不停计算"}]},
                config={"recursion_limit": 3},
            )


if __name__ == "__main__":
    unittest.main()
