"""把持久化 RunEvent 编码为可重放的 SSE wire frame。"""

from __future__ import annotations

import json

from mini_deerflow.runtime.models import RunEvent


class SSEEncoder:
    """实现最小 ``id/event/data``、heartbeat 与 Last-Event-ID 解析。"""

    def encode(self, event: RunEvent) -> str:
        data = json.dumps(
            event.data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return (
            f"id: {event.event_id}\n"
            f"event: {event.event}\n"
            f"data: {data}\n\n"
        )

    @staticmethod
    def heartbeat() -> str:
        """SSE comment 不推进 event id，因此重连不会跳过业务事件。"""

        return ": heartbeat\n\n"

    @staticmethod
    def sequence_after(last_event_id: str | None, *, run_id: str) -> int:
        if last_event_id in {None, "", "-"}:
            return 0
        try:
            event_run_id, raw_sequence = last_event_id.rsplit(":", 1)
            sequence = int(raw_sequence)
        except (TypeError, ValueError) as error:
            raise ValueError("Last-Event-ID 必须是 <run_id>:<sequence>") from error
        if event_run_id != run_id or sequence < 0:
            raise ValueError("Last-Event-ID 不属于当前 run")
        return sequence


__all__ = ["SSEEncoder"]
