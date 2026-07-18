"""应用运行层的稳定请求标识；不包含 HTTP 或供应商细节。"""

from __future__ import annotations

from dataclasses import dataclass
import uuid


@dataclass(frozen=True, slots=True)
class RunDescriptor:
    """描述一次 graph invocation，连接 thread、request 与 user 三种身份。"""

    thread_id: str
    request_id: str
    user_id: str

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        thread_id: str | None = None,
        request_id: str | None = None,
    ) -> RunDescriptor:
        return cls(
            thread_id=thread_id or f"thread-{uuid.uuid4().hex}",
            request_id=request_id or f"request-{uuid.uuid4().hex}",
            user_id=user_id,
        )
