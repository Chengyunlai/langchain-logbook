"""传输无关的 Gateway：把认证身份、RunManager 与可重放事件连接起来。"""

from __future__ import annotations

from collections.abc import Iterator
import time

from mini_deerflow.api.contracts import (
    CreateThreadRequest,
    RunCreateRequest,
    RunResponse,
    RunResumeRequest,
    ThreadResponse,
    ThreadStateResponse,
)
from mini_deerflow.runtime.manager import LocalRunManager
from mini_deerflow.runtime.models import RunRecord, RunStatus, ThreadRecord, ThreadStateView
from mini_deerflow.runtime.repository import RuntimeConflictError, RuntimeNotFoundError
from mini_deerflow.runtime.sse import SSEEncoder


_TERMINAL = {
    RunStatus.interrupted,
    RunStatus.success,
    RunStatus.error,
    RunStatus.cancelled,
}


def _thread_response(record: ThreadRecord) -> ThreadResponse:
    return ThreadResponse(
        thread_id=record.thread_id,
        metadata=record.metadata,
        created_at=record.created_at,
    )


def _run_response(record: RunRecord) -> RunResponse:
    return RunResponse(
        run_id=record.run_id,
        thread_id=record.thread_id,
        status=record.status,
        stream_modes=record.stream_modes,
        on_disconnect=record.on_disconnect,
        cancel_requested=record.cancel_requested,
        error_code=record.error_code,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _state_response(state: ThreadStateView) -> ThreadStateResponse:
    return ThreadStateResponse(**state.model_dump())


class MiniDeerFlowGateway:
    """应用服务层；不知道 FastAPI，也不信任客户端提交的 user_id。"""

    def __init__(
        self,
        manager: LocalRunManager,
        *,
        encoder: SSEEncoder | None = None,
        poll_interval: float = 0.05,
        heartbeat_interval: float = 15.0,
    ) -> None:
        if poll_interval <= 0 or heartbeat_interval <= 0:
            raise ValueError("poll/heartbeat interval 必须大于 0")
        self.manager = manager
        self.encoder = encoder or SSEEncoder()
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval

    def create_thread(
        self,
        request: CreateThreadRequest,
        *,
        user_id: str,
    ) -> ThreadResponse:
        return _thread_response(
            self.manager.create_thread(
                user_id=user_id,
                metadata=request.metadata,
                thread_id=request.thread_id,
            )
        )

    def start_run(
        self,
        thread_id: str,
        request: RunCreateRequest,
        *,
        user_id: str,
    ) -> RunResponse:
        return _run_response(
            self.manager.start_message(
                user_id=user_id,
                thread_id=thread_id,
                message=request.message,
                stream_modes=request.stream_modes,
                on_disconnect=request.on_disconnect,
            )
        )

    def resume_thread(
        self,
        thread_id: str,
        request: RunResumeRequest,
        *,
        user_id: str,
    ) -> RunResponse:
        return _run_response(
            self.manager.start_resume(
                user_id=user_id,
                thread_id=thread_id,
                resume=request.resume,
                stream_modes=request.stream_modes,
                on_disconnect=request.on_disconnect,
            )
        )

    def get_run(self, thread_id: str, run_id: str, *, user_id: str) -> RunResponse:
        record = self.manager.get_run(run_id, user_id=user_id)
        self._require_thread(record, thread_id)
        return _run_response(record)

    def wait_run(
        self,
        thread_id: str,
        run_id: str,
        *,
        user_id: str,
        timeout: float | None,
    ) -> RunResponse:
        record = self.manager.get_run(run_id, user_id=user_id)
        self._require_thread(record, thread_id)
        return _run_response(
            self.manager.wait(run_id, user_id=user_id, timeout=timeout)
        )

    def cancel_run(self, thread_id: str, run_id: str, *, user_id: str) -> RunResponse:
        record = self.manager.get_run(run_id, user_id=user_id)
        self._require_thread(record, thread_id)
        return _run_response(self.manager.request_cancel(run_id, user_id=user_id))

    def get_state(self, thread_id: str, *, user_id: str) -> ThreadStateResponse:
        return _state_response(
            self.manager.get_thread_state(thread_id, user_id=user_id)
        )

    def iter_run_events(
        self,
        thread_id: str,
        run_id: str,
        *,
        user_id: str,
        last_event_id: str | None = None,
    ) -> Iterator[str]:
        record = self.manager.get_run(run_id, user_id=user_id)
        self._require_thread(record, thread_id)
        sequence = self.encoder.sequence_after(last_event_id, run_id=run_id)
        last_heartbeat = time.monotonic()
        observed_end = False
        try:
            while True:
                events = self.manager.list_events(
                    run_id,
                    user_id=user_id,
                    after_sequence=sequence,
                )
                for event in events:
                    sequence = event.sequence
                    yield self.encoder.encode(event)
                    if event.event == "end":
                        observed_end = True
                        return
                current = self.manager.get_run(run_id, user_id=user_id)
                if current.status in _TERMINAL:
                    latest = self.manager.get_latest_event(run_id, user_id=user_id)
                    if latest is not None and latest.event == "end":
                        # Last-Event-ID 已经指向 end 时，空重放是正常结果。
                        return
                    raise RuntimeConflictError(
                        f"run {run_id} 已终结，但事件日志缺少 end"
                    )
                now = time.monotonic()
                if now - last_heartbeat >= self.heartbeat_interval:
                    yield self.encoder.heartbeat()
                    last_heartbeat = now
                time.sleep(self.poll_interval)
        finally:
            if not observed_end:
                current = self.manager.get_run(run_id, user_id=user_id)
                if (
                    current.status not in _TERMINAL
                    and current.on_disconnect == "cancel"
                    and not current.cancel_requested
                ):
                    try:
                        self.manager.request_cancel(run_id, user_id=user_id)
                    except RuntimeConflictError:
                        # Run 在检查与请求之间刚好结束，断连清理无需覆盖终态。
                        pass

    @staticmethod
    def _require_thread(record: RunRecord, thread_id: str) -> None:
        if record.thread_id != thread_id:
            # 与 ownership 查询相同：不暴露 run 实际属于哪个 thread。
            raise RuntimeNotFoundError(f"run 不存在: {record.run_id}")


__all__ = ["MiniDeerFlowGateway"]
