from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolMessage
from langchain.tools import tool

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.app import build_application, build_default_dependencies
from mini_deerflow.config import ApplicationSettings
from mini_deerflow.context import RuntimeContext
from mini_deerflow.middleware import ArtifactTrackingMiddleware
from mini_deerflow.mcp import (
    MCPAdapterUnavailableError,
    MCPToolAdapter,
)
from mini_deerflow.models import create_offline_model
from mini_deerflow.runtime import RunDescriptor
from mini_deerflow.sandbox import (
    LocalSandboxProvider,
    SandboxCommand,
    SandboxPathError,
)
from mini_deerflow.schemas import SubagentResult
from mini_deerflow.skills import (
    SkillCatalog,
    SkillFormatError,
    build_demo_skill_catalog,
    build_load_skill_tool,
)
from mini_deerflow.subagents import (
    DelegationLedger,
    SubagentExecutor,
    SubagentInvocation,
    SubagentOutput,
    SubagentRegistry,
    SubagentSpec,
    build_task_tool,
)
from mini_deerflow.tools import build_sandbox_workspace_tools


@tool("approved_echo")
def approved_echo(text: str) -> str:
    """离线 MCP fixture：回显输入。"""

    return f"approved:{text}"


@tool("unapproved_delete")
def unapproved_delete(path: str) -> str:
    """离线 MCP fixture：代表未获应用授权的工具。"""

    return f"deleted:{path}"


class LocalSandboxProviderTests(unittest.TestCase):
    def test_thread_workspaces_are_isolated_durable_and_path_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = LocalSandboxProvider(root / "sandboxes")
            thread_a = provider.acquire("thread-a", user_id="learner")
            same_thread = provider.acquire("thread-a", user_id="learner")
            thread_b = provider.acquire("thread-b", user_id="learner")
            other_user = provider.acquire("thread-a", user_id="other-learner")

            write = thread_a.write_text(
                "reports/result.md",
                "线程 A 的研究结果",
                media_type="text/markdown",
            )

            self.assertEqual(same_thread.sandbox_id, thread_a.sandbox_id)
            self.assertNotEqual(thread_b.sandbox_id, thread_a.sandbox_id)
            self.assertNotEqual(other_user.sandbox_id, thread_a.sandbox_id)
            self.assertEqual(thread_a.read_text("reports/result.md"), "线程 A 的研究结果")
            self.assertEqual(write.artifact.path, "reports/result.md")
            self.assertEqual(write.artifact.media_type, "text/markdown")
            with self.assertRaises(FileNotFoundError):
                thread_b.read_text("reports/result.md")
            with self.assertRaises(SandboxPathError):
                thread_a.write_text("../outside.md", "blocked")

            outside = root / "outside"
            outside.mkdir()
            (outside / "secret.txt").write_text("secret", encoding="utf-8")
            (thread_a.workspace_path / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(SandboxPathError):
                thread_a.read_text("escape/secret.txt")

            command_result = thread_a.execute(SandboxCommand(("python", "-V")))
            self.assertEqual(command_result.exit_code, 126)
            self.assertIn("disabled", command_result.stderr)

            provider.release(thread_a.sandbox_id)
            self.assertIsNone(provider.get(thread_a.sandbox_id))
            restored = provider.acquire("thread-a", user_id="learner")
            self.assertEqual(restored.audit_events(), ())
            self.assertEqual(restored.read_text("reports/result.md"), "线程 A 的研究结果")
            self.assertEqual([event.action for event in restored.audit_events()], ["read_text"])
            self.assertEqual(
                [(event.action, event.outcome) for event in thread_a.audit_events()],
                [
                    ("write_text", "completed"),
                    ("read_text", "completed"),
                    ("write_text", "rejected"),
                    ("read_text", "rejected"),
                    ("execute", "denied"),
                ],
            )

    def test_provider_rejects_a_symlink_replacing_the_workspace_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = LocalSandboxProvider(root / "sandboxes")
            session = provider.acquire("thread-a", user_id="learner")
            workspace = session.workspace_path
            provider.release(session.sandbox_id)
            shutil.rmtree(workspace)
            outside = root / "outside"
            outside.mkdir()
            workspace.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(SandboxPathError):
                provider.acquire("thread-a", user_id="learner")

    def test_provider_rejects_a_symlink_as_its_configured_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            linked_root = root / "linked-sandboxes"
            linked_root.symlink_to(outside, target_is_directory=True)
            provider = LocalSandboxProvider(linked_root)

            with self.assertRaises(SandboxPathError):
                provider.acquire("thread-a", user_id="learner")

    def test_workspace_write_tool_uses_runtime_identity_and_updates_artifact_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = LocalSandboxProvider(Path(directory) / "sandboxes")
            tools = build_sandbox_workspace_tools(provider)
            registry = {item.name: item for item in tools}
            agent = create_lead_agent(
                model=create_offline_model(
                    [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "write_workspace_file",
                                    "args": {
                                        "path": "reports/tool-result.md",
                                        "content": "由 Agent 工具写入",
                                        "media_type": "text/markdown",
                                    },
                                    "id": "write-workspace-1",
                                    "type": "tool_call",
                                }
                            ],
                        ),
                        AIMessage(content="已写入线程工作区。"),
                    ]
                ),
                tools=tools,
                middleware=[ArtifactTrackingMiddleware()],
            )

            state = agent.invoke(
                {"messages": [("user", "生成研究报告")]},
                config={"configurable": {"thread_id": "tool-thread"}},
                context=RuntimeContext(
                    user_id="learner",
                    workspace_root="/not/model-visible",
                ),
            )

            self.assertEqual(
                set(registry),
                {"read_workspace_file", "write_workspace_file"},
            )
            for tool in tools:
                self.assertNotIn("thread_id", tool.tool_call_schema.model_fields)
                self.assertNotIn("user_id", tool.tool_call_schema.model_fields)
                self.assertNotIn("workspace_root", tool.tool_call_schema.model_fields)
            self.assertEqual(state["artifacts"][0].path, "reports/tool-result.md")
            tool_message = next(
                message for message in state["messages"] if isinstance(message, ToolMessage)
            )
            self.assertIn("reports/tool-result.md", tool_message.content)
            session = provider.acquire("tool-thread", user_id="learner")
            self.assertEqual(
                session.read_text("reports/tool-result.md"),
                "由 Agent 工具写入",
            )

    def test_composition_root_registers_sandbox_tools_and_persists_their_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = ApplicationSettings.offline(workspace_root=directory)
            dependencies = build_default_dependencies(settings)
            application = build_application(
                settings,
                dependencies=replace(
                    dependencies,
                    model=create_offline_model(
                        [
                            AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "name": "write_workspace_file",
                                        "args": {
                                            "path": "reports/application.md",
                                            "content": "组合根写入",
                                            "media_type": "text/markdown",
                                        },
                                        "id": "application-write-1",
                                        "type": "tool_call",
                                    }
                                ],
                            ),
                            AIMessage(content="应用写入完成。"),
                        ]
                    ),
                ),
            )
            run = RunDescriptor(
                thread_id="application-thread",
                request_id="application-request",
                user_id="learner",
            )

            state = application.invoke(
                "写入应用报告",
                run=run,
                permissions={"workspace:write"},
            )

            self.assertIn("write_workspace_file", application.tool_names)
            self.assertEqual(state["artifacts"][0].path, "reports/application.md")
            self.assertEqual(
                dependencies.sandbox_provider.acquire(
                    run.thread_id,
                    user_id=run.user_id,
                ).read_text("reports/application.md"),
                "组合根写入",
            )


class SandboxSubagentIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_inherits_only_sandbox_handle_and_returns_artifact_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = LocalSandboxProvider(Path(directory) / "sandboxes")
            observed_contexts: list[dict[str, object]] = []

            async def report_writer(invocation: SubagentInvocation) -> SubagentOutput:
                observed_contexts.append(invocation.context)
                sandbox_id = str(invocation.context["sandbox_id"])
                session = provider.get(sandbox_id)
                if session is None:
                    raise RuntimeError("sandbox session missing")
                write = session.write_text(
                    "reports/subagent.md",
                    "Subagent 的有界结果",
                    media_type="text/markdown",
                )
                return SubagentOutput(
                    summary="已生成 Subagent 报告",
                    artifacts=[write.artifact],
                )

            ledger = DelegationLedger()
            executor = SubagentExecutor(
                SubagentRegistry(
                    [
                        SubagentSpec(
                            name="report-writer",
                            description="写入线程报告",
                            handler=report_writer,
                            allowed_context_fields=frozenset({"sandbox_id"}),
                        )
                    ]
                ),
                ledger=ledger,
            )
            task = build_task_tool(executor, sandbox_provider=provider)
            lead = create_lead_agent(
                model=create_offline_model(
                    [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "task",
                                    "args": {
                                        "task_id": "sandbox-task-1",
                                        "description": "生成线程报告",
                                        "prompt": "只写入有界结论",
                                        "subagent_type": "report-writer",
                                    },
                                    "id": "sandbox-task-call-1",
                                    "type": "tool_call",
                                }
                            ],
                        ),
                        AIMessage(content="已接收 Subagent 结果。"),
                    ]
                ),
                tools=[task],
            )

            state = await lead.ainvoke(
                {"messages": [("user", "委派报告")]},
                config={"configurable": {"thread_id": "shared-thread"}},
                context=RuntimeContext(
                    user_id="learner",
                    workspace_root="/must-not-be-delegated",
                    auth_token="must-not-leak",
                ),
            )

            raw = next(
                message.content
                for message in state["messages"]
                if isinstance(message, ToolMessage)
            )
            result = SubagentResult.model_validate(json.loads(str(raw)))
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.artifacts[0].path, "reports/subagent.md")
            self.assertEqual(set(observed_contexts[0]), {"sandbox_id"})
            self.assertNotIn("must-not-leak", json.dumps(observed_contexts[0]))
            self.assertEqual(
                provider.acquire("shared-thread", user_id="learner").read_text(
                    "reports/subagent.md"
                ),
                "Subagent 的有界结果",
            )
            self.assertEqual(ledger.list_records()[0].context_keys, ("sandbox_id",))


class OptionalExtensionTests(unittest.IsolatedAsyncioTestCase):
    async def test_packaged_demo_skill_is_discoverable_without_loading_its_body(self) -> None:
        catalog = build_demo_skill_catalog()

        self.assertEqual(
            [metadata.name for metadata in catalog.list_metadata()],
            ["research-report"],
        )
        self.assertNotIn("引用核验流程", catalog.render_index())
        self.assertIn("引用核验流程", catalog.load("research-report").instructions)

    async def test_mcp_adapter_is_lazy_optional_and_application_allowlisted(self) -> None:
        factory_calls = 0

        class FakeMCPClient:
            async def get_tools(self):
                return [approved_echo, unapproved_delete]

        def client_factory() -> FakeMCPClient:
            nonlocal factory_calls
            factory_calls += 1
            return FakeMCPClient()

        disabled = MCPToolAdapter(
            client_factory=client_factory,
            enabled=False,
            allowed_tool_names=frozenset({"approved_echo"}),
        )
        self.assertEqual(await disabled.load_tools(), ())
        self.assertEqual(factory_calls, 0)

        enabled = MCPToolAdapter(
            client_factory=client_factory,
            enabled=True,
            allowed_tool_names=frozenset({"approved_echo"}),
        )
        loaded = await enabled.load_tools()

        self.assertEqual([item.name for item in loaded], ["approved_echo"])
        self.assertEqual(loaded[0].metadata["source"], "mcp")
        self.assertTrue(loaded[0].metadata["optional_extension"])
        self.assertEqual(factory_calls, 1)

        with tempfile.TemporaryDirectory() as directory:
            settings = ApplicationSettings.offline(workspace_root=directory)
            dependencies = replace(
                build_default_dependencies(settings),
                model=create_offline_model(
                    [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "approved_echo",
                                    "args": {"text": "MCP 已接入"},
                                    "id": "mcp-tool-1",
                                    "type": "tool_call",
                                }
                            ],
                        ),
                        AIMessage(content="MCP 调用完成。"),
                    ]
                ),
                extension_tools=loaded,
            )
            application = build_application(settings, dependencies=dependencies)
            result = application.invoke("调用 MCP 工具")
            mcp_message = next(
                message
                for message in result["messages"]
                if isinstance(message, ToolMessage)
            )
            self.assertIn("approved_echo", application.tool_names)
            self.assertEqual(mcp_message.content, "approved:MCP 已接入")

        unavailable = MCPToolAdapter.from_langchain_servers(
            {"demo": {"transport": "stdio", "command": "demo-server"}},
            enabled=True,
            allowed_tool_names=frozenset({"approved_echo"}),
        )
        with patch.dict(
            sys.modules,
            {
                "langchain_mcp_adapters": None,
                "langchain_mcp_adapters.client": None,
            },
        ):
            with self.assertRaisesRegex(
                MCPAdapterUnavailableError,
                "langchain-mcp-adapters",
            ):
                await unavailable.load_tools()

    async def test_composition_root_rejects_duplicate_extension_tool_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = ApplicationSettings.offline(workspace_root=directory)
            dependencies = replace(
                build_default_dependencies(settings),
                extension_tools=(approved_echo, approved_echo),
            )

            with self.assertRaisesRegex(ValueError, "重复 tool name: approved_echo"):
                build_application(settings, dependencies=dependencies)

    async def test_skill_catalog_discloses_metadata_then_loads_body_on_demand(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skills"
            skill_dir = root / "research-report"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                """---
name: research-report
description: 生成带引用的研究报告
---

# Research Report

PRIVATE-INSTRUCTIONS：先验证来源，再写结论。
""",
                encoding="utf-8",
            )
            catalog = SkillCatalog.from_directory(root)

            metadata = catalog.list_metadata()
            loader = build_load_skill_tool(catalog)

            self.assertEqual(
                [(item.name, item.description) for item in metadata],
                [("research-report", "生成带引用的研究报告")],
            )
            self.assertNotIn("PRIVATE-INSTRUCTIONS", catalog.render_index())
            self.assertNotIn("PRIVATE-INSTRUCTIONS", loader.description)

            lead = create_lead_agent(
                model=create_offline_model(
                    [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "load_skill",
                                    "args": {"name": "research-report"},
                                    "id": "load-skill-1",
                                    "type": "tool_call",
                                }
                            ],
                        ),
                        AIMessage(content="已按技能生成报告。"),
                    ]
                ),
                tools=[loader],
            )
            state = await lead.ainvoke(
                {"messages": [("user", "生成研究报告")]}
            )

            tool_message = next(
                message
                for message in state["messages"]
                if isinstance(message, ToolMessage)
            )
            loaded_skill = json.loads(str(tool_message.content))
            self.assertEqual(loaded_skill["name"], "research-report")
            self.assertIn("PRIVATE-INSTRUCTIONS", loaded_skill["instructions"])

            outside = Path(directory) / "outside-skill"
            outside.mkdir()
            (outside / "SKILL.md").write_text(
                "---\nname: outside\ndescription: 不应加载\n---\n越界正文",
                encoding="utf-8",
            )
            (root / "outside-link").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(SkillFormatError):
                SkillCatalog.from_directory(root)

    async def test_skill_catalog_rechecks_the_file_budget_when_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skills"
            skill_dir = root / "bounded"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            frontmatter = "---\nname: bounded\ndescription: 有界技能\n---\n"
            skill_file.write_text(frontmatter + "初始正文", encoding="utf-8")
            catalog = SkillCatalog.from_directory(root)
            skill_file.write_text(frontmatter + ("大" * 256_000), encoding="utf-8")

            with self.assertRaisesRegex(SkillFormatError, "超过 256000 bytes"):
                catalog.load("bounded")


if __name__ == "__main__":
    unittest.main()
