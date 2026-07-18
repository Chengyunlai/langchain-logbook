from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from langchain_core.messages import AIMessage, HumanMessage
from langchain.tools import tool
from langgraph.types import Command

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.app import build_application, build_default_dependencies
from mini_deerflow.config import ApplicationSettings
from mini_deerflow.models import create_offline_model
from mini_deerflow.middleware import (
    ArtifactTrackingMiddleware,
    StructuredToolErrorMiddleware,
    build_lead_middleware,
)
from mini_deerflow.persistence import open_sqlite_checkpointer
from mini_deerflow.runtime import RunDescriptor
from mini_deerflow.streaming import StreamEvent


def _record_artifact_call(*, media_type: str, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "record_artifact",
                "args": {"path": "reports/core-agent.md", "media_type": media_type},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


@tool("unsafe_artifact")
def unsafe_artifact() -> Command:
    """返回越界 Artifact，用于证明 middleware 会拒绝不安全 State update。"""

    return Command(
        update={
            "artifacts": [
                {"path": "../outside.md", "media_type": "text/markdown"}
            ]
        }
    )


class LeadAgentCoreTests(unittest.TestCase):
    def test_thread_resumes_after_application_rebuild_and_merges_artifact_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint_path = Path(directory) / "lead-agent.sqlite"
            settings = ApplicationSettings.offline(workspace_root=directory)
            first_run = RunDescriptor(
                thread_id="core-thread",
                request_id="core-request-1",
                user_id="learner",
            )
            second_run = replace(first_run, request_id="core-request-2")

            with open_sqlite_checkpointer(checkpoint_path) as saver:
                dependencies = replace(
                    build_default_dependencies(settings),
                    checkpointer=saver,
                    model=create_offline_model(
                        [
                            _record_artifact_call(
                                media_type="text/markdown", call_id="artifact-1"
                            ),
                            AIMessage(content="第一轮已登记 Markdown 产物。"),
                        ]
                    ),
                )
                first_application = build_application(
                    settings, dependencies=dependencies
                )
                first_state = first_application.invoke(
                    "登记研究报告",
                    run=first_run,
                    permissions={"artifact:write"},
                )

            with open_sqlite_checkpointer(checkpoint_path) as saver:
                dependencies = replace(
                    build_default_dependencies(settings),
                    checkpointer=saver,
                    model=create_offline_model(
                        [
                            _record_artifact_call(
                                media_type="application/json", call_id="artifact-2"
                            ),
                            AIMessage(content="第二轮已更新同一路径的产物类型。"),
                        ]
                    ),
                )
                restored_application = build_application(
                    settings, dependencies=dependencies
                )
                second_state = restored_application.invoke(
                    "继续线程并更新产物",
                    run=second_run,
                    permissions={"artifact:write"},
                )
                snapshot = restored_application.state_for(second_run)

            self.assertEqual(
                [
                    message.content
                    for message in second_state["messages"]
                    if isinstance(message, HumanMessage)
                ],
                ["登记研究报告", "继续线程并更新产物"],
            )
            self.assertEqual(len(second_state["artifacts"]), 1)
            self.assertEqual(
                second_state["artifacts"][0].media_type,
                "application/json",
            )
            self.assertEqual(snapshot["artifacts"], second_state["artifacts"])
            self.assertEqual(snapshot["messages"][-1].content, "第二轮已更新同一路径的产物类型。")
            self.assertEqual(
                [event.as_text() for event in second_state["middleware_trace"][-6:]],
                [
                    "lead:before_model",
                    "lead:wrap_model_exit",
                    "lead:after_model",
                    "lead:before_model",
                    "lead:wrap_model_exit",
                    "lead:after_model",
                ],
            )

    def test_application_stream_normalizes_v2_updates_and_exports_graph_mermaid(self) -> None:
        application = build_application(ApplicationSettings.offline(workspace_root="."))
        run = RunDescriptor(
            thread_id="stream-thread",
            request_id="stream-request",
            user_id="learner",
        )

        events = list(application.stream("流式解释 Agent", run=run))
        diagram = application.draw_mermaid()

        self.assertTrue(events)
        self.assertTrue(all(isinstance(event, StreamEvent) for event in events))
        serialized_events = [
            json.dumps(event.as_dict(), ensure_ascii=False, allow_nan=False)
            for event in events
        ]
        self.assertTrue(all(serialized_events))
        self.assertEqual({event.type for event in events}, {"updates"})
        updated_nodes = {
            node_name
            for event in events
            for node_name in event.data
        }
        self.assertIn("model", updated_nodes)
        self.assertIn("tools", updated_nodes)
        self.assertIn("graph TD", diagram)
        self.assertIn("model(model)", diagram)
        self.assertIn("tools(tools)", diagram)
        self.assertEqual(
            application.state_for(run)["messages"][-1].content,
            "离线工具循环已完成；请查看 ToolMessage 中的引用。",
        )

    def test_default_middleware_chain_order_is_an_explicit_contract(self) -> None:
        middleware = build_lead_middleware(
            summary_model=build_default_dependencies(
                ApplicationSettings.offline(workspace_root=".")
            ).summary_model,
        )

        self.assertEqual(
            [type(item).__name__ for item in middleware],
            [
                "LifecycleTraceMiddleware",
                "SummarizationMiddleware",
                "ContextPromptMiddleware",
                "PIIMiddleware",
                "ToolPermissionMiddleware",
                "StructuredToolErrorMiddleware",
                "ArtifactTrackingMiddleware",
                "ModelCallLimitMiddleware",
            ],
        )

    def test_default_application_summarizes_old_messages_before_context_overflows(self) -> None:
        settings = replace(
            ApplicationSettings.offline(workspace_root="."),
            summary_trigger_messages=5,
            summary_keep_messages=2,
        )
        application = build_application(settings)
        first_run = RunDescriptor(
            thread_id="summary-thread",
            request_id="summary-request-1",
            user_id="learner",
        )
        second_run = replace(first_run, request_id="summary-request-2")

        application.invoke("第一轮：解释 Context", run=first_run)
        state = application.invoke("第二轮：解释 Middleware", run=second_run)

        summary_messages = [
            message
            for message in state["messages"]
            if message.additional_kwargs.get("lc_source") == "summarization"
        ]
        self.assertEqual(len(summary_messages), 1)
        self.assertIn("Context、State、Tools 与 Middleware", summary_messages[0].content)
        self.assertEqual(state["messages"][-1].content, "离线工具循环已完成；请查看 ToolMessage 中的引用。")

    def test_artifact_tracking_middleware_rejects_unsafe_tool_state_update(self) -> None:
        agent = create_lead_agent(
            model=create_offline_model(
                [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "unsafe_artifact",
                                "args": {},
                                "id": "unsafe-artifact-1",
                                "type": "tool_call",
                            }
                        ],
                    ),
                    AIMessage(content="已拒绝不安全产物。"),
                ]
            ),
            tools=[unsafe_artifact],
            middleware=[
                StructuredToolErrorMiddleware(),
                ArtifactTrackingMiddleware(),
            ],
        )

        state = agent.invoke({"messages": [("user", "登记越界产物")]})

        tool_message = next(
            message for message in state["messages"] if message.type == "tool"
        )
        self.assertEqual(tool_message.status, "error")
        self.assertIn("invalid_tool_input", tool_message.content)
        self.assertEqual(state.get("artifacts", []), [])


if __name__ == "__main__":
    unittest.main()
