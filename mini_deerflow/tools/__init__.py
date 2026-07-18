"""Mini DeerFlow 的基础工具契约与 registry。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command
from pydantic import BaseModel, Field

from mini_deerflow.config import LeadAgentContext
from mini_deerflow.knowledge import LocalKnowledgeIndex
from mini_deerflow.sandbox import SandboxProvider
from mini_deerflow.schemas import ArtifactRef
from mini_deerflow.tools.workspace import build_sandbox_workspace_tools


class KnowledgeSearchInput(BaseModel):
    query: str = Field(min_length=1, description="需要从课程知识库检索的问题")
    limit: int = Field(default=3, ge=1, le=10, description="最多返回的引用数量")


class CalculatorInput(BaseModel):
    operation: Literal["add", "subtract", "multiply", "divide"]
    left: float
    right: float


def build_search_knowledge_tool(index: LocalKnowledgeIndex) -> BaseTool:
    """把 retriever repository 包装为模型可见、应用可验证的工具。"""

    @tool("search_knowledge", args_schema=KnowledgeSearchInput)
    def search_knowledge(query: str, limit: int = 3) -> str:
        """检索本地知识库并返回带 source 的结果；不知道时返回空列表。"""

        hits = index.search(query, limit=limit)
        payload = [
            {
                "id": hit.id,
                "text": hit.text,
                "source": hit.source,
                "score": round(hit.score, 4),
            }
            for hit in hits
        ]
        return json.dumps(payload, ensure_ascii=False)

    search_knowledge.metadata = {"required_permission": "knowledge:read"}
    return search_knowledge


@tool("calculator", args_schema=CalculatorInput)
def calculator(operation: str, left: float, right: float) -> str:
    """执行加减乘除；除数为零时返回结构化工具错误。"""

    operations = {
        "add": lambda: left + right,
        "subtract": lambda: left - right,
        "multiply": lambda: left * right,
        "divide": lambda: left / right,
    }
    if operation == "divide" and right == 0:
        return json.dumps({"ok": False, "error": "division_by_zero"})
    return str(float(operations[operation]()))


@tool("read_workspace_file")
def read_workspace_file(
    path: str,
    runtime: ToolRuntime[LeadAgentContext, dict[str, object]],
) -> str:
    """只读工作区文本文件；根目录由 Runtime Context 注入，不暴露给模型。"""

    root = Path(runtime.context.workspace_root).resolve()
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root):
        return json.dumps({"ok": False, "error": "path_outside_workspace"})
    if not candidate.is_file():
        return json.dumps({"ok": False, "error": "file_not_found", "path": path})
    return json.dumps(
        {"ok": True, "path": path, "content": candidate.read_text(encoding="utf-8")},
        ensure_ascii=False,
    )


read_workspace_file.metadata = {"required_permission": "workspace:read"}


@tool("record_artifact")
def record_artifact(
    path: str,
    media_type: str,
    runtime: ToolRuntime[LeadAgentContext, dict[str, object]],
) -> Command:
    """登记已存在的工作区产物引用，并通过 Command 更新 Agent State。"""

    artifact = ArtifactRef(path=path, media_type=media_type)
    return Command(
        update={
            "artifacts": [artifact],
            "messages": [
                ToolMessage(
                    content=json.dumps(artifact.model_dump(), ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id or "missing-tool-call-id",
                )
            ],
        }
    )


record_artifact.metadata = {"required_permission": "artifact:write"}


# region tutorial:04-tool-registry
def build_tool_registry(
    index: LocalKnowledgeIndex,
    *,
    sandbox_provider: SandboxProvider | None = None,
) -> list[BaseTool]:
    """集中声明 Lead Agent 当前可用的最小权限工具集合。"""

    workspace_tools: tuple[BaseTool, ...] = (
        build_sandbox_workspace_tools(sandbox_provider)
        if sandbox_provider is not None
        else (read_workspace_file,)
    )
    return [
        build_search_knowledge_tool(index),
        calculator,
        *workspace_tools,
        record_artifact,
    ]
# endregion tutorial:04-tool-registry


__all__ = [
    "CalculatorInput",
    "KnowledgeSearchInput",
    "build_search_knowledge_tool",
    "build_sandbox_workspace_tools",
    "build_tool_registry",
    "calculator",
    "read_workspace_file",
    "record_artifact",
]
