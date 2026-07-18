"""通过 SandboxProvider 暴露的线程工作区工具。"""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

from mini_deerflow.context import RuntimeContext
from mini_deerflow.sandbox import SandboxProvider, SandboxSession


def _session_for_runtime(
    provider: SandboxProvider,
    runtime: ToolRuntime[RuntimeContext, dict[str, object]],
) -> SandboxSession:
    context = runtime.context
    if not isinstance(context, RuntimeContext):
        raise ValueError("workspace 工具需要应用注入 RuntimeContext")
    configurable = runtime.config.get("configurable", {})
    thread_id = configurable.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("workspace 工具需要 configurable.thread_id")
    return provider.acquire(thread_id, user_id=context.user_id)


def build_sandbox_workspace_tools(provider: SandboxProvider) -> tuple[BaseTool, BaseTool]:
    """构建不向模型暴露用户、线程或宿主路径的读写工具。"""

    @tool("read_workspace_file")
    def sandbox_read_workspace_file(
        path: str,
        runtime: ToolRuntime[RuntimeContext, dict[str, object]],
    ) -> str:
        """读取当前线程工作区内的 UTF-8 文本文件。"""

        content = _session_for_runtime(provider, runtime).read_text(path)
        return json.dumps(
            {"ok": True, "path": path, "content": content},
            ensure_ascii=False,
        )

    @tool("write_workspace_file")
    def sandbox_write_workspace_file(
        path: str,
        content: str,
        media_type: str,
        runtime: ToolRuntime[RuntimeContext, dict[str, object]],
    ) -> Command:
        """原子写入当前线程工作区，并登记一个 Artifact State update。"""

        result = _session_for_runtime(provider, runtime).write_text(
            path,
            content,
            media_type=media_type,
        )
        payload = {
            "ok": True,
            "artifact": result.artifact.model_dump(mode="json"),
            "bytes_written": result.bytes_written,
            "created": result.created,
        }
        return Command(
            update={
                "artifacts": [result.artifact],
                "messages": [
                    ToolMessage(
                        content=json.dumps(payload, ensure_ascii=False),
                        tool_call_id=(
                            runtime.tool_call_id or "missing-tool-call-id"
                        ),
                        name="write_workspace_file",
                    )
                ],
            }
        )

    sandbox_read_workspace_file.metadata = {
        "required_permission": "workspace:read",
        "sandboxed": True,
    }
    sandbox_write_workspace_file.metadata = {
        "required_permission": "workspace:write",
        "sandboxed": True,
    }
    return sandbox_read_workspace_file, sandbox_write_workspace_file


__all__ = ["build_sandbox_workspace_tools"]
