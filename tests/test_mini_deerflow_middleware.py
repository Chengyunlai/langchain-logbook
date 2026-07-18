from __future__ import annotations

import asyncio
import json
import unittest

from langchain.agents.middleware import HumanInTheLoopMiddleware, SummarizationMiddleware
from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import NodeCancelledError
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.context import RuntimeContext
from mini_deerflow.middleware import (
    ContextPromptMiddleware,
    LifecycleTraceMiddleware,
    ModelRouterMiddleware,
    StructuredToolErrorMiddleware,
    ToolPermissionMiddleware,
    build_lead_middleware,
)
from mini_deerflow.models import ToolCallingFakeModel, create_offline_model
from mini_deerflow.store import UserPreferenceRepository
from mini_deerflow.knowledge import LocalKnowledgeIndex
from mini_deerflow.tools import build_tool_registry


class RecordingFakeModel(ToolCallingFakeModel):
    captured_messages: list[list[BaseMessage]] = []

    def _generate(self, messages: list[BaseMessage], *args: object, **kwargs: object) -> ChatResult:
        self.captured_messages.append(list(messages))
        return super()._generate(messages, *args, **kwargs)


@tool
def always_fails(reason: str) -> str:
    """用于验证工具异常边界的确定性失败工具。"""

    raise RuntimeError(reason)


def _tool_call(name: str, args: dict[str, object], call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


class MiddlewareIntegrationTests(unittest.TestCase):
    def test_before_hooks_run_in_order_and_after_hooks_unwind_in_reverse(self) -> None:
        agent = create_lead_agent(
            model=create_offline_model([AIMessage(content="完成")]),
            tools=[],
            middleware=[LifecycleTraceMiddleware("outer"), LifecycleTraceMiddleware("inner")],
        )

        result = agent.invoke({"messages": [("user", "测试顺序")]})

        self.assertEqual(
            [event.as_text() for event in result["middleware_trace"]],
            [
                "outer:before_model",
                "inner:before_model",
                "inner:wrap_model_exit",
                "outer:wrap_model_exit",
                "inner:after_model",
                "outer:after_model",
            ],
        )

    def test_context_prompt_adds_safe_run_metadata_but_never_auth_token(self) -> None:
        store = InMemoryStore()
        UserPreferenceRepository(store).save(
            "learner-1", {"answer_detail": "high", "citation_style": "source-first"}
        )
        model = RecordingFakeModel(
            messages=iter([AIMessage(content="完成")]), captured_messages=[]
        )
        agent = create_lead_agent(
            model=model,
            tools=[],
            middleware=[ContextPromptMiddleware()],
            store=store,
        )
        context = RuntimeContext(
            user_id="learner-1",
            workspace_root="/tmp/workspace",
            permissions=frozenset({"knowledge:read"}),
            locale="zh-CN",
            auth_token="never-copy-this-secret",
        )

        agent.invoke({"messages": [("user", "你好")]}, context=context)

        rendered = "\n".join(message.text for message in model.captured_messages[0])
        self.assertIn("learner-1", rendered)
        self.assertIn("knowledge:read", rendered)
        self.assertIn("answer_detail=high", rendered)
        self.assertIn("citation_style=source-first", rendered)
        self.assertNotIn("never-copy-this-secret", rendered)

    def test_tool_exception_becomes_structured_error_message(self) -> None:
        model = create_offline_model(
            [
                _tool_call("always_fails", {"reason": "temporary outage"}, "fail-1"),
                AIMessage(content="我已看到结构化工具错误。"),
            ]
        )
        agent = create_lead_agent(
            model=model,
            tools=[always_fails],
            middleware=[StructuredToolErrorMiddleware()],
        )

        result = agent.invoke({"messages": [("user", "执行失败工具")]})

        tool_message = next(
            message for message in result["messages"] if isinstance(message, ToolMessage)
        )
        payload = json.loads(tool_message.content)
        self.assertEqual(tool_message.status, "error")
        self.assertEqual(payload["error"], "tool_execution_failed")
        self.assertEqual(payload["tool"], "always_fails")

    def test_timeout_is_classified_as_retryable_without_leaking_details(self) -> None:
        @tool
        def timeout_tool() -> str:
            """模拟可重试的外部超时。"""

            raise TimeoutError("internal endpoint and credential must stay private")

        agent = create_lead_agent(
            model=create_offline_model(
                [
                    _tool_call("timeout_tool", {}, "timeout-1"),
                    AIMessage(content="已识别超时"),
                ]
            ),
            tools=[timeout_tool],
            middleware=[StructuredToolErrorMiddleware()],
        )

        result = agent.invoke({"messages": [("user", "调用超时工具")]})
        payload = json.loads(next(
            message.content for message in result["messages"] if isinstance(message, ToolMessage)
        ))

        self.assertEqual(payload["error"], "tool_timeout")
        self.assertTrue(payload["retryable"])
        self.assertNotIn("credential", json.dumps(payload))

    def test_tool_permission_denial_short_circuits_execution(self) -> None:
        execution_count = 0

        @tool
        def publish_report(path: str) -> str:
            """发布报告；测试中不应在权限不足时执行。"""

            nonlocal execution_count
            execution_count += 1
            return f"published:{path}"

        model = create_offline_model(
            [
                _tool_call("publish_report", {"path": "reports/a.md"}, "publish-1"),
                AIMessage(content="发布被权限边界拒绝。"),
            ]
        )
        agent = create_lead_agent(
            model=model,
            tools=[publish_report],
            middleware=[ToolPermissionMiddleware({"publish_report": "report:publish"})],
        )

        result = agent.invoke(
            {"messages": [("user", "发布报告")]},
            context=RuntimeContext(
                user_id="reader", workspace_root="/tmp", permissions=frozenset()
            ),
        )

        tool_message = next(
            message for message in result["messages"] if isinstance(message, ToolMessage)
        )
        self.assertEqual(execution_count, 0)
        self.assertEqual(json.loads(tool_message.content)["error"], "permission_denied")

    def test_permission_policy_is_read_from_tool_metadata(self) -> None:
        workspace_tool = next(
            tool
            for tool in build_tool_registry(LocalKnowledgeIndex())
            if tool.name == "read_workspace_file"
        )
        agent = create_lead_agent(
            model=create_offline_model(
                [
                    _tool_call("read_workspace_file", {"path": "secret.txt"}, "read-1"),
                    AIMessage(content="读取被拒绝"),
                ]
            ),
            tools=[workspace_tool],
            middleware=[ToolPermissionMiddleware({})],
        )

        result = agent.invoke(
            {"messages": [("user", "读取文件")]},
            context=RuntimeContext(user_id="reader", workspace_root="/tmp"),
        )

        payload = json.loads(next(
            message.content for message in result["messages"] if isinstance(message, ToolMessage)
        ))
        self.assertEqual(payload["error"], "permission_denied")
        self.assertEqual(payload["required_permission"], "workspace:read")

    def test_model_router_uses_application_controlled_context_profile(self) -> None:
        base_model = create_offline_model([AIMessage(content="base-model")])
        premium_model = create_offline_model([AIMessage(content="premium-model")])
        agent = create_lead_agent(
            model=base_model,
            tools=[],
            middleware=[ModelRouterMiddleware({"premium": premium_model})],
        )

        result = agent.invoke(
            {"messages": [("user", "选择模型")]},
            context=RuntimeContext(
                user_id="learner", workspace_root="/tmp", model_profile="premium"
            ),
        )

        self.assertEqual(result["messages"][-1].content, "premium-model")

    def test_default_governance_chain_redacts_email_and_records_lifecycle(self) -> None:
        agent = create_lead_agent(
            model=create_offline_model([AIMessage(content="done")]),
            tools=[],
            middleware=build_lead_middleware(model_call_limit=3),
        )

        result = agent.invoke(
            {"messages": [("user", "邮箱 alice@example.com")]},
            context=RuntimeContext(user_id="learner", workspace_root="/tmp"),
        )

        self.assertEqual(result["messages"][0].content, "邮箱 [REDACTED_EMAIL]")
        self.assertEqual(
            [event.as_text() for event in result["middleware_trace"]],
            ["lead:before_model", "lead:wrap_model_exit", "lead:after_model"],
        )

    def test_model_call_limit_stops_before_the_model_handler(self) -> None:
        agent = create_lead_agent(
            model=create_offline_model([AIMessage(content="must-not-run")]),
            tools=[],
            middleware=build_lead_middleware(model_call_limit=0),
        )

        with self.assertRaises(ModelCallLimitExceededError):
            agent.invoke(
                {"messages": [("user", "超出预算")]},
                context=RuntimeContext(user_id="learner", workspace_root="/tmp"),
            )

    def test_summarization_replaces_old_messages_with_tagged_summary(self) -> None:
        summary_model = create_offline_model(
            [AIMessage(content="摘要：用户正在学习 Context 与 Middleware。")]
        )
        agent = create_lead_agent(
            model=create_offline_model([AIMessage(content="基于摘要继续回答")]),
            tools=[],
            middleware=[
                SummarizationMiddleware(
                    model=summary_model,
                    trigger=("messages", 3),
                    keep=("messages", 1),
                )
            ],
        )

        result = agent.invoke(
            {
                "messages": [
                    ("user", "第一问"),
                    ("assistant", "第一答"),
                    ("user", "第二问"),
                    ("assistant", "第二答"),
                    ("user", "第三问"),
                ]
            }
        )

        self.assertEqual(result["messages"][0].additional_kwargs["lc_source"], "summarization")
        self.assertIn("Context 与 Middleware", result["messages"][0].content)
        self.assertEqual(result["messages"][-1].content, "基于摘要继续回答")

    def test_hitl_interrupt_rejection_prevents_tool_side_effect(self) -> None:
        published: list[str] = []

        @tool
        def publish_report(path: str) -> str:
            """发布报告；只有审批通过后才允许执行。"""

            published.append(path)
            return "published"

        model = create_offline_model(
            [
                _tool_call("publish_report", {"path": "reports/a.md"}, "approval-1"),
                AIMessage(content="审批结果已处理"),
            ]
        )
        agent = create_lead_agent(
            model=model,
            tools=[publish_report],
            middleware=[HumanInTheLoopMiddleware(interrupt_on={"publish_report": True})],
            checkpointer=InMemorySaver(),
        )
        config = {"configurable": {"thread_id": "hitl-thread"}}

        interrupted = agent.invoke({"messages": [("user", "发布报告")]}, config=config)
        resumed = agent.invoke(
            Command(
                resume={
                    "decisions": [
                        {"type": "reject", "message": "证据不足，暂不发布"}
                    ]
                }
            ),
            config=config,
        )

        self.assertTrue(interrupted["__interrupt__"])
        self.assertEqual(published, [])
        self.assertIn("证据不足", next(
            message.content for message in resumed["messages"] if isinstance(message, ToolMessage)
        ))

    def test_trace_reducer_appends_updates_across_a_tool_loop(self) -> None:
        model = create_offline_model(
            [
                _tool_call("always_fails", {"reason": "x"}, "trace-tool-1"),
                AIMessage(content="完成"),
            ]
        )
        agent = create_lead_agent(
            model=model,
            tools=[always_fails],
            middleware=[LifecycleTraceMiddleware(), StructuredToolErrorMiddleware()],
        )

        result = agent.invoke({"messages": [("user", "运行两轮模型") ]})

        self.assertEqual(
            [event.as_text() for event in result["middleware_trace"]],
            [
                "lead:before_model",
                "lead:wrap_model_exit",
                "lead:after_model",
                "lead:before_model",
                "lead:wrap_model_exit",
                "lead:after_model",
            ],
        )

    def test_async_cancellation_is_not_converted_to_tool_error(self) -> None:
        @tool
        async def cancelled_tool(task: str) -> str:
            """模拟调用方取消异步工具。"""

            del task
            raise asyncio.CancelledError

        async def run() -> None:
            agent = create_lead_agent(
                model=create_offline_model(
                    [_tool_call("cancelled_tool", {"task": "x"}, "cancel-1")]
                ),
                tools=[cancelled_tool],
                middleware=[StructuredToolErrorMiddleware()],
            )
            await agent.ainvoke({"messages": [("user", "取消任务")]})

        with self.assertRaises(NodeCancelledError):
            asyncio.run(run())

    def test_context_prompt_supports_async_agent_invocation(self) -> None:
        async def run() -> str:
            agent = create_lead_agent(
                model=create_offline_model([AIMessage(content="异步完成")]),
                tools=[],
                middleware=[ContextPromptMiddleware()],
            )
            result = await agent.ainvoke(
                {"messages": [("user", "异步调用")]},
                context=RuntimeContext(user_id="async-user", workspace_root="/tmp"),
            )
            return str(result["messages"][-1].content)

        self.assertEqual(asyncio.run(run()), "异步完成")


if __name__ == "__main__":
    unittest.main()
