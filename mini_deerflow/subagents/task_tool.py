"""把 SubagentExecutor 暴露为 Lead Agent 可调用的单一 ``task`` 工具。"""

from __future__ import annotations

from langchain_core.tools import BaseTool
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from mini_deerflow.config import LeadAgentContext
from mini_deerflow.context import safe_context_view
from mini_deerflow.sandbox import SandboxProvider
from mini_deerflow.subagents.contracts import SubagentRequest
from mini_deerflow.subagents.executor import SubagentExecutor


class TaskToolInput(BaseModel):
    task_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$")
    description: str = Field(min_length=1, max_length=240)
    prompt: str = Field(min_length=1, max_length=8_000)
    subagent_type: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")


# region tutorial:11-task-tool
def build_task_tool(
    executor: SubagentExecutor,
    *,
    sandbox_provider: SandboxProvider | None = None,
) -> BaseTool:
    """创建单 dispatch tool；模型只选择类型并描述任务，不接触 executor。"""

    @tool("task")
    async def task(
        task_id: str,
        description: str,
        prompt: str,
        subagent_type: str,
        runtime: ToolRuntime[LeadAgentContext, dict[str, object]],
    ) -> str:
        """启动一个临时、隔离的 specialist，并返回结构化结果。"""

        invocation_context = (
            safe_context_view(runtime.context) if runtime.context is not None else {}
        )
        if sandbox_provider is not None:
            configurable = runtime.config.get("configurable", {})
            thread_id = configurable.get("thread_id")
            if not isinstance(thread_id, str) or not thread_id:
                raise ValueError("task sandbox 继承需要 configurable.thread_id")
            if runtime.context is None:
                raise ValueError("task sandbox 继承需要 RuntimeContext")
            invocation_context["sandbox_id"] = sandbox_provider.acquire(
                thread_id,
                user_id=runtime.context.user_id,
            ).sandbox_id
        validated = TaskToolInput(
            task_id=task_id,
            description=description,
            prompt=prompt,
            subagent_type=subagent_type,
        )
        result = await executor.dispatch(
            SubagentRequest(
                task_id=validated.task_id,
                agent_name=validated.subagent_type,
                description=validated.description,
                prompt=validated.prompt,
            ),
            parent_context=invocation_context,
        )
        return result.model_dump_json()

    task.metadata = {"delegation": True, "max_concurrency": executor.max_concurrency}
    return task
# endregion tutorial:11-task-tool


__all__ = ["TaskToolInput", "build_task_tool"]
