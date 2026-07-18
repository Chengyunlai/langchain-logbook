"""Thread-scoped Agent facts and checkpoint-safety guardrails."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import operator
import re
from typing import Annotated, Any, Literal

from langchain.agents import AgentState
from pydantic import BaseModel, ConfigDict, Field

from mini_deerflow.schemas import ArtifactRef


class UnsafeStateError(ValueError):
    """A secret-like field was placed in state that may be checkpointed or traced."""


def merge_artifacts(
    current: list[ArtifactRef] | None,
    updates: list[ArtifactRef] | None,
) -> list[ArtifactRef]:
    """按工作区路径合并 Artifact；同一路径由新事实替换，顺序保持稳定。"""

    merged = [ArtifactRef.model_validate(item) for item in (current or [])]
    positions = {artifact.path: index for index, artifact in enumerate(merged)}
    for raw_artifact in updates or []:
        artifact = ArtifactRef.model_validate(raw_artifact)
        position = positions.get(artifact.path)
        if position is None:
            positions[artifact.path] = len(merged)
            merged.append(artifact)
        else:
            merged[position] = artifact
    return merged


# region tutorial:05-thread-state
class MiddlewareTraceEvent(BaseModel):
    """A typed lifecycle fact, rather than a convention encoded in a string."""

    model_config = ConfigDict(frozen=True)

    middleware: str = Field(min_length=1)
    hook: Literal["before_model", "wrap_model_exit", "after_model"]

    def as_text(self) -> str:
        """Render the event for logs and tutorial assertions."""

        return f"{self.middleware}:{self.hook}"


class ThreadState(AgentState):
    """State shared by Lead Agent nodes within one thread."""

    artifacts: Annotated[list[ArtifactRef], merge_artifacts]
    middleware_trace: Annotated[list[MiddlewareTraceEvent], operator.add]


_SECRET_FIELD_NAMES = {
    "access_token",
    "api_key",
    "auth_token",
    "authorization",
    "password",
    "refresh_token",
    "secret",
    "token",
}

_SECRET_FIELD_SUFFIXES = (
    "_api_key",
    "_secret",
    "_password",
    "_auth_token",
    "_access_token",
    "_refresh_token",
)


def is_secret_field_name(value: str) -> bool:
    """识别常见 Secret 字段别名；这是一条 guardrail，不替代数据分类。"""

    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized in _SECRET_FIELD_NAMES or normalized.endswith(
        _SECRET_FIELD_SUFFIXES
    )


def assert_checkpoint_safe(value: object, *, path: str = "state") -> None:
    """Reject secret-shaped keys before state is persisted or emitted to a trace."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}"
            if is_secret_field_name(key_text):
                raise UnsafeStateError(f"{nested_path} 不能进入可持久化 Graph State")
            assert_checkpoint_safe(nested, path=nested_path)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            assert_checkpoint_safe(nested, path=f"{path}[{index}]")
# endregion tutorial:05-thread-state


__all__ = [
    "MiddlewareTraceEvent",
    "ThreadState",
    "UnsafeStateError",
    "assert_checkpoint_safe",
    "is_secret_field_name",
    "merge_artifacts",
]
