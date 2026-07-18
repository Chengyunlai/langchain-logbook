"""传输无关的 API DTO；HTTP 只是这些稳定契约的一种适配器。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from mini_deerflow.runtime.models import (
    DisconnectMode,
    RunStatus,
    StreamMode,
)
from mini_deerflow.streaming import JSONValue


_THREAD_ID = r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$"


class GatewayModel(BaseModel):
    """Gateway DTO 的共同约束：拒绝悄悄吞掉拼错的字段。"""

    model_config = ConfigDict(extra="forbid")


class ConversationRequest(GatewayModel):
    """API adapter 接受的最小对话请求，而不是 Graph State。"""

    message: str = Field(min_length=1, max_length=20_000)
    thread_id: str | None = Field(default=None, min_length=1, max_length=160)
    request_id: str | None = Field(default=None, min_length=1, max_length=160)


class ConversationResponse(GatewayModel):
    """稳定的客户端投影；完整 state 和 stream event 不直接泄漏给调用方。"""

    thread_id: str
    request_id: str
    final_text: str
    artifact_count: int = Field(default=0, ge=0)


class CreateThreadRequest(GatewayModel):
    """创建产品 thread；身份只能来自认证边界，不能来自请求体。"""

    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        pattern=_THREAD_ID,
    )
    metadata: dict[str, JSONValue] = Field(default_factory=dict)


class ThreadResponse(GatewayModel):
    thread_id: str
    metadata: dict[str, JSONValue]
    created_at: str


class RunCreateRequest(GatewayModel):
    message: str = Field(min_length=1, max_length=20_000)
    stream_modes: tuple[StreamMode, ...] = Field(
        default=("updates",),
        min_length=1,
        max_length=4,
    )
    on_disconnect: DisconnectMode = "continue"


class RunResumeRequest(GatewayModel):
    resume: JSONValue
    stream_modes: tuple[StreamMode, ...] = Field(
        default=("updates",),
        min_length=1,
        max_length=4,
    )
    on_disconnect: DisconnectMode = "continue"


class RunResponse(GatewayModel):
    run_id: str
    thread_id: str
    status: RunStatus
    stream_modes: tuple[StreamMode, ...]
    on_disconnect: DisconnectMode
    cancel_requested: bool
    error_code: str | None
    error_message: str | None
    created_at: str
    updated_at: str


class ThreadStateResponse(GatewayModel):
    thread_id: str
    values: dict[str, JSONValue]
    next: tuple[str, ...]
    interrupts: tuple[JSONValue, ...]


class ErrorResponse(GatewayModel):
    code: str
    message: str


__all__ = [
    "ConversationRequest",
    "ConversationResponse",
    "CreateThreadRequest",
    "ErrorResponse",
    "RunCreateRequest",
    "RunResponse",
    "RunResumeRequest",
    "ThreadResponse",
    "ThreadStateResponse",
]
