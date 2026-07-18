"""LangSmith 追踪边界：一次请求只能有一个人为创建的根 span。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal, TypeVar

from langsmith import traceable, tracing_context
from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class DuplicateTraceRootError(RuntimeError):
    """Gateway 模式下，业务操作已经被其他组件包装为 root trace。"""


class LangSmithTracingConfig(BaseModel):
    """追踪开关与 root span 所有权，不保存 API key。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool | Literal["local"] = False
    project_name: str = Field(default="mini-deerflow", min_length=1)
    root_owner: Literal["graph", "gateway"] = "graph"
    tags: tuple[str, ...] = ()


class LangSmithObservability:
    """把关联元数据放入 tracing context，并显式约束 root 所有权。"""

    def __init__(
        self,
        config: LangSmithTracingConfig,
        *,
        client: Any | None = None,
    ) -> None:
        self._config = config
        self._client = client

    def run(
        self,
        operation_name: str,
        operation: Callable[[], T],
        *,
        correlation_id: str,
        user_id: str,
        metadata: Mapping[str, Any] | None = None,
        operation_already_traced: bool = False,
    ) -> T:
        """执行一次请求；Graph-owned 模式不额外套 traceable root。"""

        inherited_metadata = {
            **dict(metadata or {}),
            "correlation_id": correlation_id,
            "user_id": user_id,
        }
        with tracing_context(
            project_name=self._config.project_name,
            tags=list(self._config.tags),
            metadata=inherited_metadata,
            enabled=self._config.enabled,
            client=self._client,
        ):
            if self._config.root_owner == "graph":
                return operation()
            if operation_already_traced:
                raise DuplicateTraceRootError(
                    "gateway 声明拥有 root，但 operation 已被追踪；请只保留一个 root"
                )
            wrapped = traceable(
                name=operation_name,
                run_type="chain",
                client=self._client,
            )(operation)
            return wrapped()


__all__ = [
    "DuplicateTraceRootError",
    "LangSmithObservability",
    "LangSmithTracingConfig",
]
