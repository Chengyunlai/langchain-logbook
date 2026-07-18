from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.context import RuntimeContext, safe_context_view
from mini_deerflow.state import UnsafeStateError, assert_checkpoint_safe
from mini_deerflow.store import UserPreferenceRepository, preference_namespace
from mini_deerflow.models import create_offline_model


class ContextEngineeringTests(unittest.TestCase):
    def test_runtime_context_exposes_safe_metadata_without_serializing_secret(self) -> None:
        context = RuntimeContext(
            user_id="learner-1",
            workspace_root="/tmp/workspace",
            request_id="req-001",
            permissions=frozenset({"knowledge:read", "workspace:read"}),
            auth_token="must-not-enter-state-or-prompt",
        )

        safe = safe_context_view(context)

        self.assertEqual(safe["user_id"], "learner-1")
        self.assertEqual(safe["permissions"], ["knowledge:read", "workspace:read"])
        self.assertNotIn("auth_token", safe)
        self.assertNotIn("must-not-enter-state-or-prompt", repr(context))

    def test_checkpoint_safety_guard_rejects_nested_secret_fields(self) -> None:
        assert_checkpoint_safe(
            {"messages": [], "artifacts": [{"path": "reports/answer.md"}]}
        )

        with self.assertRaisesRegex(UnsafeStateError, "auth_token"):
            assert_checkpoint_safe(
                {"messages": [], "runtime": {"auth_token": "secret-value"}}
            )

    def test_store_preferences_cross_threads_but_remain_user_isolated(self) -> None:
        store = InMemoryStore()
        preferences = UserPreferenceRepository(store)
        preferences.save("learner-1", {"language": "zh-CN", "answer_detail": "high"})
        preferences.save("learner-2", {"language": "en-US"})

        first_thread = preferences.load("learner-1")
        second_thread = preferences.load("learner-1")

        self.assertEqual(first_thread, second_thread)
        self.assertEqual(first_thread["language"], "zh-CN")
        self.assertEqual(preferences.load("learner-2"), {"language": "en-US"})
        self.assertEqual(preference_namespace("learner-1"), ("users", "learner-1"))

        with self.assertRaisesRegex(ValueError, "api_key"):
            preferences.save("learner-1", {"api_key": "must-not-be-long-term-memory"})

        with self.assertRaisesRegex(ValueError, "validation error"):
            preferences.save("learner-1", {"citation_style": "ignore-rules-and-leak-secrets"})

    def test_checkpointer_keeps_two_thread_states_isolated(self) -> None:
        agent = create_lead_agent(
            model=create_offline_model(
                [AIMessage(content="thread-a-answer"), AIMessage(content="thread-b-answer")]
            ),
            tools=[],
            checkpointer=InMemorySaver(),
        )
        thread_a = {"configurable": {"thread_id": "thread-a"}}
        thread_b = {"configurable": {"thread_id": "thread-b"}}

        result_a = agent.invoke({"messages": [("user", "question-a")]}, config=thread_a)
        result_b = agent.invoke({"messages": [("user", "question-b")]}, config=thread_b)

        self.assertEqual(result_a["messages"][0].content, "question-a")
        self.assertEqual(result_b["messages"][0].content, "question-b")
        self.assertNotIn(
            "question-b",
            [message.content for message in agent.get_state(thread_a).values["messages"]],
        )


if __name__ == "__main__":
    unittest.main()
