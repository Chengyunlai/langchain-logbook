from __future__ import annotations

from dataclasses import replace
import unittest

from langchain_core.messages import AIMessage, HumanMessage

from mini_deerflow.app import (
    MiniDeerFlowApplication,
    build_application,
    build_default_dependencies,
)
from mini_deerflow.config import ApplicationSettings
from mini_deerflow.models import create_offline_model


class MiniDeerFlowApplicationTests(unittest.TestCase):
    def test_default_offline_application_builds_and_completes_a_minimal_run(self) -> None:
        settings = ApplicationSettings.offline(workspace_root=".")
        application = build_application(settings)

        result = application.invoke("create_agent 和 LangGraph 是什么关系？")

        self.assertIsInstance(application, MiniDeerFlowApplication)
        self.assertEqual(application.settings.model.profile, "offline")
        self.assertIsInstance(result["messages"][0], HumanMessage)
        self.assertEqual(
            result["messages"][-1].content,
            "离线工具循环已完成；请查看 ToolMessage 中的引用。",
        )
        self.assertGreaterEqual(len(result["middleware_trace"]), 3)
        self.assertIn("task", application.tool_names)

        second_result = application.invoke("同一应用再运行一个独立线程")
        self.assertEqual(
            second_result["messages"][-1].content,
            "离线工具循环已完成；请查看 ToolMessage 中的引用。",
        )

    def test_dependencies_can_be_replaced_without_changing_the_composition_root(self) -> None:
        settings = ApplicationSettings.offline(workspace_root=".")
        dependencies = build_default_dependencies(settings)
        injected_model = create_offline_model([AIMessage(content="injected-model")])
        application = build_application(
            settings,
            dependencies=replace(dependencies, model=injected_model),
        )

        result = application.invoke("只回答，不调用工具")

        self.assertEqual(result["messages"][-1].content, "injected-model")

    def test_each_invocation_builds_application_controlled_runtime_context(self) -> None:
        settings = ApplicationSettings.offline(
            workspace_root=".",
            default_user_id="learner-42",
        )
        application = build_application(settings)

        context = application.context_for(
            request_id="request-42",
            permissions={"knowledge:read", "workspace:read"},
        )

        self.assertEqual(context.user_id, "learner-42")
        self.assertEqual(context.request_id, "request-42")
        self.assertEqual(context.model_profile, "offline")
        self.assertTrue(context.workspace_root.startswith("/"))
        self.assertEqual(
            context.permissions,
            frozenset({"knowledge:read", "workspace:read"}),
        )


if __name__ == "__main__":
    unittest.main()
