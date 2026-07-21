from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from mini_deerflow.graph import (
    create_explicit_react_graph,
    create_functional_research_flow,
    create_research_workflow,
)
from mini_deerflow.persistence import create_memory_checkpointer
from mini_deerflow.models import create_offline_model
from mini_deerflow.tools import calculator


class ExplicitReactGraphTests(unittest.TestCase):
    def test_explicit_graph_completes_model_tool_model_loop(self) -> None:
        model = create_offline_model(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "calculator",
                            "args": {"operation": "multiply", "left": 6, "right": 7},
                            "id": "calc-42",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="结果是 42。"),
            ]
        )
        graph = create_explicit_react_graph(model=model, tools=[calculator])

        result = graph.invoke({"messages": [("user", "计算 6 × 7")]})

        self.assertEqual(
            [event.as_text() for event in result["node_trace"]],
            ["model", "tools", "model"],
        )
        self.assertEqual(result["messages"][-1].content, "结果是 42。")
        self.assertEqual(
            next(
                message.content
                for message in result["messages"]
                if isinstance(message, ToolMessage)
            ),
            "42.0",
        )


class DeterministicResearchWorkflowTests(unittest.TestCase):
    def test_workflow_runs_serial_conditional_parallel_loop_and_subgraph_paths(self) -> None:
        graph = create_research_workflow()

        result = graph.invoke(
            {
                "objective": "解释 LangGraph durable execution",
                "sections": ["checkpoint", "side-effect"],
            }
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["revision_count"], 1)
        self.assertEqual(result["quality_score"], 2)
        self.assertEqual(
            {finding.section for finding in result["findings"]},
            {"checkpoint", "side-effect"},
        )
        rendered_trace = [event.as_text() for event in result["trace"]]
        self.assertEqual(rendered_trace.count("review:score"), 2)
        self.assertIn("revise", rendered_trace)
        self.assertEqual(rendered_trace[-1], "finalize")

    def test_command_rejects_an_empty_objective_before_fan_out(self) -> None:
        result = create_research_workflow().invoke(
            {"objective": "   ", "sections": ["must-not-run"]}
        )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(
            [event.as_text() for event in result["trace"]],
            ["intake:reject"],
        )
        self.assertEqual(result["findings"], [])

    def test_compiled_workflow_exposes_checkpointed_state_by_thread(self) -> None:
        graph = create_research_workflow(checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "research-001"}}

        graph.invoke(
            {"objective": "解释 checkpoint", "sections": ["persistence"]},
            config=config,
        )

        snapshot = graph.get_state(config)
        self.assertEqual(snapshot.values["status"], "completed")
        self.assertEqual(snapshot.values["objective"], "解释 checkpoint")

    def test_project_memory_checkpointer_deserializes_allowlisted_domain_types(self) -> None:
        graph = create_research_workflow(checkpointer=create_memory_checkpointer())
        config = {"configurable": {"thread_id": "allowlist-001"}}
        graph.invoke(
            {"objective": "验证类型 allowlist", "sections": ["checkpoint"]},
            config=config,
        )

        history = list(graph.get_state_history(config))

        self.assertTrue(history)
        self.assertTrue(
            any(snapshot.values.get("findings") for snapshot in history)
        )


class FunctionalResearchFlowTests(unittest.TestCase):
    def test_tasks_retry_cache_and_aggregate_failures_without_failing_entrypoint(self) -> None:
        flow = create_functional_research_flow()

        first = flow.invoke(["stable", "flaky", "failed"])
        second = flow.invoke(["stable", "flaky"])

        self.assertEqual(
            [(result.topic, result.status) for result in first],
            [("stable", "completed"), ("flaky", "completed"), ("failed", "failed")],
        )
        self.assertEqual(first[2].error_type, "ValueError")
        self.assertEqual(flow.attempts_for("stable"), 1)
        self.assertEqual(flow.attempts_for("flaky"), 2)
        self.assertEqual(flow.attempts_for("failed"), 1)
        self.assertEqual([result.status for result in second], ["completed", "completed"])


if __name__ == "__main__":
    unittest.main()
