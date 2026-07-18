from __future__ import annotations

import asyncio
import json
import unittest

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.config import LeadAgentContext
from mini_deerflow.models import create_offline_model
from mini_deerflow.schemas import ArtifactRef, SubagentResult
from mini_deerflow.subagents import (
    DelegationLedger,
    SubagentExecutor,
    SubagentInvocation,
    SubagentOutput,
    SubagentRegistry,
    SubagentRequest,
    SubagentSpec,
    build_handoff_graph,
    build_demo_subagent_registry,
    build_parallel_router_graph,
    build_shared_subgraph_graph,
    build_single_router_graph,
    build_task_tool,
)


class SubagentExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_demo_registry_exposes_two_isolated_specialists(self) -> None:
        registry = build_demo_subagent_registry()
        executor = SubagentExecutor(registry, max_concurrency=2)

        results = await executor.dispatch_many(
            [
                SubagentRequest(
                    task_id="demo-research",
                    agent_name="research",
                    description="研究 reducer",
                    prompt="解释 reducer 的并行合并边界",
                ),
                SubagentRequest(
                    task_id="demo-coding",
                    agent_name="coding",
                    description="设计 reducer 测试",
                    prompt="给出一个防重复合并的测试建议",
                ),
            ],
            parent_context={"locale": "zh-CN", "messages": ["不应转发"]},
        )

        self.assertEqual(
            registry.describe(),
            (
                ("research", "检索、比较并压缩证据"),
                ("coding", "分析 Python 接口并提出可测试实现"),
            ),
        )
        self.assertEqual([result.status for result in results], ["completed", "completed"])
        self.assertTrue(results[0].summary.startswith("研究摘要"))
        self.assertTrue(results[1].summary.startswith("代码建议"))
        self.assertEqual(
            registry.resolve("research").handler.tool_names,
            ("lookup_evidence",),
        )
        self.assertIs(registry.resolve("research").handler.checkpointer, False)

    async def test_dispatch_passes_only_allowlisted_context_to_a_fresh_subagent(self) -> None:
        observed: list[SubagentInvocation] = []

        async def research(invocation: SubagentInvocation) -> SubagentOutput:
            observed.append(invocation)
            return SubagentOutput(summary=f"已研究：{invocation.prompt}")

        registry = SubagentRegistry(
            [
                SubagentSpec(
                    name="research",
                    description="检索并压缩证据",
                    handler=research,
                    allowed_context_fields=frozenset({"user_id", "locale"}),
                )
            ]
        )
        executor = SubagentExecutor(registry)

        result = await executor.dispatch(
            SubagentRequest(
                task_id="task-isolation",
                agent_name="research",
                description="调查持久化边界",
                prompt="只返回三条证据",
            ),
            parent_context={
                "user_id": "learner-1",
                "locale": "zh-CN",
                "messages": ["主会话的全部历史"],
                "auth_token": "must-not-leak",
                "internal_notes": "Lead Agent 私有推理",
            },
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(observed[0].context, {"user_id": "learner-1", "locale": "zh-CN"})
        self.assertNotIn("messages", observed[0].model_dump_json())
        self.assertNotIn("must-not-leak", observed[0].model_dump_json())

    async def test_dispatch_many_limits_concurrency_and_preserves_partial_failures(self) -> None:
        active = 0
        peak = 0

        async def worker(invocation: SubagentInvocation) -> SubagentOutput:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            if invocation.prompt == "fail":
                raise RuntimeError("source unavailable")
            return SubagentOutput(summary=f"done:{invocation.prompt}")

        registry = SubagentRegistry(
            [SubagentSpec(name="worker", description="并行 worker", handler=worker)]
        )
        executor = SubagentExecutor(registry, max_concurrency=2)
        requests = [
            SubagentRequest(
                task_id=f"parallel-{index}",
                agent_name="worker",
                description="并行任务",
                prompt=prompt,
            )
            for index, prompt in enumerate(["a", "fail", "b", "c"])
        ]

        results = await executor.dispatch_many(requests)

        self.assertEqual(peak, 2)
        self.assertEqual(
            [result.status for result in results],
            ["completed", "failed", "completed", "completed"],
        )
        self.assertEqual(results[1].error, "RuntimeError: subagent handler failed")

    async def test_timeout_and_oversized_output_become_bounded_results(self) -> None:
        async def slow(_: SubagentInvocation) -> SubagentOutput:
            await asyncio.sleep(0.05)
            return SubagentOutput(summary="late")

        async def verbose(_: SubagentInvocation) -> SubagentOutput:
            return SubagentOutput(
                summary="x" * 80,
                artifacts=[
                    ArtifactRef(path=f"reports/{index}.md", media_type="text/markdown")
                    for index in range(5)
                ],
            )

        registry = SubagentRegistry(
            [
                SubagentSpec(name="slow", description="慢任务", handler=slow),
                SubagentSpec(
                    name="verbose",
                    description="大输出任务",
                    handler=verbose,
                    max_output_chars=24,
                    max_artifacts=2,
                ),
            ]
        )
        executor = SubagentExecutor(registry, timeout_seconds=0.01)

        timed_out, oversized = await executor.dispatch_many(
            [
                SubagentRequest(
                    task_id="timeout-1",
                    agent_name="slow",
                    description="触发超时",
                    prompt="slow",
                ),
                SubagentRequest(
                    task_id="large-1",
                    agent_name="verbose",
                    description="触发输出限制",
                    prompt="verbose",
                ),
            ]
        )

        self.assertEqual(timed_out.status, "timed_out")
        self.assertEqual(oversized.status, "output_too_large")
        self.assertEqual(len(oversized.summary), 24)
        self.assertEqual(oversized.output_chars, 80)
        self.assertEqual(len(oversized.output_sha256 or ""), 64)
        self.assertEqual(len(oversized.artifacts), 2)

    async def test_task_tool_returns_structured_result_and_records_bounded_ledger(self) -> None:
        seen_users: list[str] = []

        async def coding(invocation: SubagentInvocation) -> SubagentOutput:
            seen_users.append(str(invocation.context["user_id"]))
            return SubagentOutput(summary=f"接口建议：{invocation.prompt}")

        ledger = DelegationLedger()
        executor = SubagentExecutor(
            SubagentRegistry(
                [SubagentSpec(name="coding", description="代码设计", handler=coding)]
            ),
            ledger=ledger,
        )
        task = build_task_tool(executor)
        model = create_offline_model(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "task",
                            "args": {
                                "task_id": "tool-1",
                                "description": "设计 registry",
                                "prompt": "给出公共接口",
                                "subagent_type": "coding",
                            },
                            "id": "tool-call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="done"),
            ]
        )
        lead = create_lead_agent(model=model, tools=[task])

        state = await lead.ainvoke(
            {"messages": [{"role": "user", "content": "设计 registry"}]},
            context=LeadAgentContext(
                user_id="learner",
                workspace_root="/tmp/lesson",
                auth_token="hidden",
            ),
        )
        raw = next(
            message.content for message in state["messages"] if isinstance(message, ToolMessage)
        )
        result = SubagentResult.model_validate(json.loads(raw))
        records = ledger.list_records()

        self.assertEqual(result.status, "completed")
        self.assertEqual(records[0].task_id, "tool-1")
        self.assertEqual(records[0].context_keys, ("locale", "request_id", "user_id"))
        self.assertNotIn("hidden", records[0].model_dump_json())

        second_model = create_offline_model(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "task",
                            "args": {
                                "task_id": "tool-2",
                                "description": "复核 registry",
                                "prompt": "检查公共接口",
                                "subagent_type": "coding",
                            },
                            "id": "tool-call-2",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="done again"),
            ]
        )
        second_lead = create_lead_agent(model=second_model, tools=[task])
        await second_lead.ainvoke(
            {"messages": [{"role": "user", "content": "复核 registry"}]},
            context=LeadAgentContext(user_id="other-user", workspace_root="/tmp/other"),
        )

        self.assertEqual(seen_users, ["learner", "other-user"])

    async def test_lead_agent_can_use_task_as_a_subagent_tool(self) -> None:
        executor = SubagentExecutor(build_demo_subagent_registry())
        task = build_task_tool(executor)
        model = create_offline_model(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "task",
                            "args": {
                                "task_id": "lead-task-1",
                                "description": "研究 checkpoint",
                                "prompt": "压缩成三条恢复原则",
                                "subagent_type": "research",
                            },
                            "id": "lead-call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="我已汇总 Subagent 结果。"),
            ]
        )
        lead = create_lead_agent(model=model, tools=[task])

        state = await lead.ainvoke(
            {"messages": [{"role": "user", "content": "解释 checkpoint"}]},
            context=LeadAgentContext(user_id="learner", workspace_root="/tmp/lesson"),
        )

        tool_message = next(
            message for message in state["messages"] if isinstance(message, ToolMessage)
        )
        delegated = SubagentResult.model_validate(json.loads(tool_message.content))
        self.assertEqual(delegated.agent_name, "research")
        self.assertEqual(delegated.status, "completed")
        self.assertEqual(state["messages"][-1].content, "我已汇总 Subagent 结果。")

    async def test_secret_aliases_and_exception_text_are_bounded(self) -> None:
        async def explodes(_: SubagentInvocation) -> SubagentOutput:
            raise RuntimeError("sensitive-provider-error:" + "x" * 2_000)

        for index, unsafe_field in enumerate(
            ("client_secret", "openai_api_key", "access_token", "refresh_token")
        ):
            with self.assertRaisesRegex(ValueError, "secret 字段"):
                SubagentSpec(
                    name=f"unsafe-{index}",
                    description="错误 policy",
                    handler=explodes,
                    allowed_context_fields=frozenset({unsafe_field}),
                )

        ledger = DelegationLedger()
        executor = SubagentExecutor(
            SubagentRegistry(
                [SubagentSpec(name="failure", description="失败边界", handler=explodes)]
            ),
            ledger=ledger,
        )
        result = await executor.dispatch(
            SubagentRequest(
                task_id="bounded-error",
                agent_name="failure",
                description="限制异常文本",
                prompt="fail",
            )
        )

        self.assertEqual(result.status, "failed")
        self.assertLessEqual(len(result.error or ""), 500)
        self.assertEqual(ledger.list_records()[0].error_code, "failed")
        self.assertNotIn("sensitive-provider-error", ledger.list_records()[0].model_dump_json())


class MultiAgentPatternTests(unittest.TestCase):
    def test_command_single_router_runs_one_specialist(self) -> None:
        result = build_single_router_graph().invoke({"query": "研究 LangGraph checkpoint"})

        self.assertEqual(result["route"], "research")
        self.assertEqual(result["trace"], ["router:research", "research"])

    def test_send_parallel_router_runs_selected_specialists_and_fans_in(self) -> None:
        result = build_parallel_router_graph().invoke(
            {"query": "比较研究结论与 Python 实现", "routes": ["research", "coding"]}
        )

        self.assertEqual(
            sorted(item.agent_name for item in result["results"]),
            ["coding", "research"],
        )
        self.assertIn("research", result["answer"])
        self.assertIn("coding", result["answer"])

    def test_handoff_changes_who_owns_the_next_turn(self) -> None:
        graph = build_handoff_graph(checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "handoff-1"}}
        first = graph.invoke({"request": "请修复 Python 类型错误"}, config=config)
        result = graph.invoke({"request": "继续解释这个修复"}, config=config)

        self.assertEqual(first["active_agent"], "coding")
        self.assertEqual(result["active_agent"], "coding")
        self.assertEqual(
            result["trace"],
            ["triage->coding", "coding:answered", "coding:answered"],
        )

    def test_subgraph_shares_only_its_declared_parent_state(self) -> None:
        result = build_shared_subgraph_graph().invoke(
            {"query": "解释 reducer", "notes": ["parent"]}
        )

        self.assertEqual(result["notes"], ["parent", "subgraph:解释 reducer"])


if __name__ == "__main__":
    unittest.main()
