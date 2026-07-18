"""隔离 Subagent 的请求、执行输入与输出契约。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mini_deerflow.schemas import ArtifactRef
from mini_deerflow.state import is_secret_field_name


class SubagentRequest(BaseModel):
    """Lead Agent 交给 ``task`` 调度层的最小任务描述。"""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$")
    agent_name: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    description: str = Field(min_length=1, max_length=240)
    prompt: str = Field(min_length=1, max_length=8_000)


class SubagentInvocation(BaseModel):
    """一次全新的 Subagent 调用；不携带 Lead Agent 的消息历史。"""

    model_config = ConfigDict(frozen=True)

    task_id: str
    agent_name: str
    description: str
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)


class SubagentOutput(BaseModel):
    """Subagent handler 在执行器施加大小限制前返回的原始业务结果。"""

    model_config = ConfigDict(frozen=True)

    summary: str
    artifacts: list[ArtifactRef] = Field(default_factory=list)


SubagentHandler = Callable[[SubagentInvocation], Awaitable[SubagentOutput]]


@dataclass(frozen=True, slots=True)
class SubagentSpec:
    """Registry 中一个 specialist 的能力与输入/输出预算。"""

    name: str
    description: str
    handler: SubagentHandler
    allowed_context_fields: frozenset[str] = frozenset(
        {"user_id", "request_id", "locale"}
    )
    max_output_chars: int = 2_000
    max_artifacts: int = 8

    def __post_init__(self) -> None:
        if not self.name or not self.description:
            raise ValueError("Subagent name 和 description 不能为空")
        if self.max_output_chars < 1:
            raise ValueError("max_output_chars 必须大于 0")
        if self.max_artifacts < 0:
            raise ValueError("max_artifacts 不能小于 0")
        forbidden = {
            field for field in self.allowed_context_fields if is_secret_field_name(field)
        }
        if forbidden:
            names = ", ".join(sorted(forbidden))
            raise ValueError(f"secret 字段不得进入 Subagent allowlist: {names}")


__all__ = [
    "SubagentHandler",
    "SubagentInvocation",
    "SubagentOutput",
    "SubagentRequest",
    "SubagentSpec",
]
