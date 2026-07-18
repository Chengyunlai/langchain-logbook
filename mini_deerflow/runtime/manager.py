"""本地后台 RunManager：Graph 执行、状态机和事件持久化的组合边界。"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import RLock
from typing import Protocol

from langgraph.types import Command

from mini_deerflow.runtime.models import (
    DisconnectMode,
    RunEvent,
    RunRecord,
    RunStatus,
    StreamMode,
    ThreadRecord,
    ThreadStateView,
)
from mini_deerflow.runtime.repository import (
    RuntimeConflictError,
    SqliteRuntimeRepository,
)
from mini_deerflow.streaming import normalize_json_value, normalize_stream_part


class GraphRuntime(Protocol):
    """RunManager 使用的最小 compiled LangGraph 公共表面。"""

    def stream(self, graph_input: object, **kwargs: object) -> Iterable[object]: ...

    def get_state(self, config: Mapping[str, object]) -> object: ...


class RunWaitTimeoutError(TimeoutError):
    """客户端等待超时，不等于后台 run 已取消。"""


def _interrupt_values(snapshot: object) -> tuple[object, ...]:
    values: list[object] = []
    for task in getattr(snapshot, "tasks", ()) or ():
        for interrupt in getattr(task, "interrupts", ()) or ():
            values.append(getattr(interrupt, "value", interrupt))
    return tuple(values)


class LocalRunManager:
    """单进程教学 worker；事件先写 SQLite，再由 SSE consumer 读取。"""

    def __init__(
        self,
        repository: SqliteRuntimeRepository,
        graph: GraphRuntime,
        *,
        context_factory: Callable[[RunRecord], object] | None = None,
        max_workers: int = 2,
        recover_inflight: bool = True,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers 必须大于 0")
        self.repository = repository
        self.graph = graph
        self._context_factory = context_factory
        if recover_inflight:
            # 此教学 worker 是单进程所有者；多 worker 必须改用 lease/queue 协议。
            self.repository.recover_inflight_runs()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="mini-deerflow-run",
        )
        self._futures: dict[str, Future[RunRecord]] = {}
        self._lock = RLock()
        self._closed = False

    def create_thread(
        self,
        *,
        user_id: str,
        metadata: Mapping[str, object] | None = None,
        thread_id: str | None = None,
    ) -> ThreadRecord:
        normalized = normalize_json_value(dict(metadata or {}), path="thread.metadata")
        if not isinstance(normalized, dict):
            raise ValueError("thread metadata 必须是 JSON object")
        return self.repository.create_thread(
            user_id=user_id,
            metadata=normalized,
            thread_id=thread_id,
        )

    def start_message(
        self,
        *,
        user_id: str,
        thread_id: str,
        message: str,
        stream_modes: Sequence[StreamMode] = ("updates",),
        on_disconnect: DisconnectMode = "continue",
        run_id: str | None = None,
    ) -> RunRecord:
        if not message.strip():
            raise ValueError("message 不能为空")
        record = self.repository.create_run(
            user_id=user_id,
            thread_id=thread_id,
            input_kind="message",
            input_data={"message": message},
            stream_modes=stream_modes,
            on_disconnect=on_disconnect,
            run_id=run_id,
        )
        self._submit(record)
        return record

    def start_resume(
        self,
        *,
        user_id: str,
        thread_id: str,
        resume: object,
        stream_modes: Sequence[StreamMode] = ("updates",),
        on_disconnect: DisconnectMode = "continue",
        run_id: str | None = None,
    ) -> RunRecord:
        state = self.get_thread_state(thread_id, user_id=user_id)
        if not state.interrupts:
            raise RuntimeConflictError(f"thread {thread_id} 当前没有可恢复 interrupt")
        normalized = normalize_json_value(resume, path="run.resume")
        record = self.repository.create_run(
            user_id=user_id,
            thread_id=thread_id,
            input_kind="resume",
            input_data={"resume": normalized},
            stream_modes=stream_modes,
            on_disconnect=on_disconnect,
            run_id=run_id,
        )
        self._submit(record)
        return record

    def _submit(self, record: RunRecord) -> None:
        with self._lock:
            if self._closed:
                self.repository.finish_run(
                    record.run_id,
                    user_id=record.user_id,
                    to_status=RunStatus.error,
                    error_code="worker_closed",
                    error_message="RunManager 已关闭",
                    terminal_event=(
                        "error",
                        {"code": "worker_closed", "message": "RunManager 已关闭"},
                    ),
                )
                raise RuntimeError("RunManager 已关闭")
            self._futures[record.run_id] = self._executor.submit(
                self._execute,
                record.run_id,
                record.user_id,
            )

    def _cancel_if_requested(self, run_id: str, user_id: str) -> RunRecord | None:
        current = self.repository.get_run(run_id, user_id=user_id)
        if not current.cancel_requested:
            return None
        return self.repository.finish_run(
            run_id,
            user_id=user_id,
            to_status=RunStatus.cancelled,
        )

    def _execute(self, run_id: str, user_id: str) -> RunRecord:
        try:
            cancelled = self._cancel_if_requested(run_id, user_id)
            if cancelled is not None:
                return cancelled
            record = self.repository.transition_run(
                run_id,
                user_id=user_id,
                to_status=RunStatus.running,
            )
            self.repository.append_event(
                run_id,
                user_id=user_id,
                event="metadata",
                data={
                    "run_id": run_id,
                    "thread_id": record.thread_id,
                    "stream_modes": list(record.stream_modes),
                },
            )
            graph_input: object
            if record.input_kind == "message":
                graph_input = {
                    "messages": [("user", str(record.input_data["message"]))]
                }
            else:
                graph_input = Command(resume=record.input_data["resume"])
            config = {"configurable": {"thread_id": record.thread_id}}
            context = (
                self._context_factory(record)
                if self._context_factory is not None
                else None
            )
            parts = self.graph.stream(
                graph_input,
                config=config,
                context=context,
                stream_mode=list(record.stream_modes),
                version="v2",
            )
            for part in parts:
                cancelled = self._cancel_if_requested(run_id, user_id)
                if cancelled is not None:
                    return cancelled
                normalized = normalize_stream_part(part)
                self.repository.append_event(
                    run_id,
                    user_id=user_id,
                    event=normalized.type,
                    data={
                        "namespace": list(normalized.namespace),
                        "data": normalized.data,
                    },
                )
            cancelled = self._cancel_if_requested(run_id, user_id)
            if cancelled is not None:
                return cancelled
            snapshot = self.graph.get_state(config)
            interrupt_values = _interrupt_values(snapshot)
            if interrupt_values:
                normalized_interrupts = normalize_json_value(
                    interrupt_values,
                    path="thread.interrupts",
                )
                terminal = self.repository.finish_run(
                    run_id,
                    user_id=user_id,
                    to_status=RunStatus.interrupted,
                    terminal_event=(
                        "interrupt",
                        {"interrupts": normalized_interrupts},
                    ),
                )
            else:
                terminal = self.repository.finish_run(
                    run_id,
                    user_id=user_id,
                    to_status=RunStatus.success,
                )
            return terminal
        except Exception as error:
            current = self.repository.get_run(run_id, user_id=user_id)
            if current.status in {RunStatus.pending, RunStatus.running}:
                public_message = f"Graph 执行失败（{type(error).__name__}）"
                return self.repository.finish_run(
                    run_id,
                    user_id=user_id,
                    to_status=RunStatus.error,
                    error_code="runtime_error",
                    error_message=public_message,
                    terminal_event=(
                        "error",
                        {
                            "code": "runtime_error",
                            "message": public_message,
                        },
                    ),
                )
            raise

    def request_cancel(self, run_id: str, *, user_id: str) -> RunRecord:
        return self.repository.request_cancel(run_id, user_id=user_id)

    def get_run(self, run_id: str, *, user_id: str) -> RunRecord:
        return self.repository.get_run(run_id, user_id=user_id)

    def wait(
        self,
        run_id: str,
        *,
        user_id: str,
        timeout: float | None = None,
    ) -> RunRecord:
        self.repository.get_run(run_id, user_id=user_id)
        with self._lock:
            future = self._futures.get(run_id)
        if future is None:
            record = self.repository.get_run(run_id, user_id=user_id)
            if record.status in {
                RunStatus.interrupted,
                RunStatus.success,
                RunStatus.error,
                RunStatus.cancelled,
            }:
                return record
            raise RuntimeConflictError(f"run {run_id} 不属于当前 worker")
        try:
            return future.result(timeout=timeout)
        except FutureTimeout as error:
            raise RunWaitTimeoutError(f"等待 run 超时: {run_id}") from error

    def list_events(
        self,
        run_id: str,
        *,
        user_id: str,
        after_sequence: int = 0,
    ) -> tuple[RunEvent, ...]:
        return self.repository.list_events(
            run_id,
            user_id=user_id,
            after_sequence=after_sequence,
        )

    def get_latest_event(self, run_id: str, *, user_id: str) -> RunEvent | None:
        return self.repository.get_latest_event(run_id, user_id=user_id)

    def get_thread_state(
        self,
        thread_id: str,
        *,
        user_id: str,
    ) -> ThreadStateView:
        self.repository.get_thread(thread_id, user_id=user_id)
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        normalized_values = normalize_json_value(
            getattr(snapshot, "values", {}) or {},
            path="thread.values",
        )
        normalized_interrupts = normalize_json_value(
            _interrupt_values(snapshot),
            path="thread.interrupts",
        )
        if not isinstance(normalized_values, dict) or not isinstance(
            normalized_interrupts,
            list,
        ):
            raise ValueError("Thread state 投影形状无效")
        return ThreadStateView(
            thread_id=thread_id,
            values=normalized_values,
            next=tuple(getattr(snapshot, "next", ()) or ()),
            interrupts=tuple(normalized_interrupts),
        )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=False)


__all__ = [
    "GraphRuntime",
    "LocalRunManager",
    "RunWaitTimeoutError",
]
