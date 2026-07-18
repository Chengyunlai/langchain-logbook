"""产品运行时的 Thread、Run 与持久化事件契约。"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from mini_deerflow.streaming import JSONValue


StreamMode = Literal["messages", "updates", "values", "custom"]
RunInputKind = Literal["message", "resume"]
DisconnectMode = Literal["cancel", "continue"]


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    interrupted = "interrupted"
    success = "success"
    error = "error"
    cancelled = "cancelled"


class ThreadRecord(BaseModel):
    """业务数据库中的线程 ownership；不是 LangGraph checkpoint。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    thread_id: str = Field(
        min_length=1,
        max_length=160,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$",
    )
    user_id: str = Field(min_length=1, max_length=512)
    metadata: dict[str, JSONValue] = Field(default_factory=dict)
    created_at: str


class RunRecord(BaseModel):
    """一次可查询的产品运行；Graph State 仍由 Checkpointer 保存。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(
        min_length=1,
        max_length=160,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$",
    )
    thread_id: str = Field(
        min_length=1,
        max_length=160,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$",
    )
    user_id: str = Field(min_length=1, max_length=512)
    status: RunStatus
    input_kind: RunInputKind
    input_data: dict[str, JSONValue]
    stream_modes: tuple[StreamMode, ...]
    on_disconnect: DisconnectMode
    cancel_requested: bool = False
    error_code: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class RunEvent(BaseModel):
    """先持久化后发送的 SSE 事件事实。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    sequence: int = Field(ge=1)
    event: str = Field(pattern=r"^[a-z][a-z0-9_-]*$", max_length=80)
    data: JSONValue
    created_at: str

    @computed_field
    @property
    def event_id(self) -> str:
        return f"{self.run_id}:{self.sequence}"


class ThreadStateView(BaseModel):
    """API 可读取的 checkpoint 投影，不暴露 StateSnapshot 内部对象。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    thread_id: str
    values: dict[str, JSONValue]
    next: tuple[str, ...]
    interrupts: tuple[JSONValue, ...]


__all__ = [
    "DisconnectMode",
    "RunEvent",
    "RunInputKind",
    "RunRecord",
    "RunStatus",
    "StreamMode",
    "ThreadRecord",
    "ThreadStateView",
]
