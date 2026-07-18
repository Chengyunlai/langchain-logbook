"""SQLite Thread/Run/Event repository；独立于 LangGraph checkpoint。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sqlite3
import uuid

from mini_deerflow.runtime.models import (
    DisconnectMode,
    RunEvent,
    RunInputKind,
    RunRecord,
    RunStatus,
    StreamMode,
    ThreadRecord,
)
from mini_deerflow.streaming import JSONValue


class RuntimeRepositoryError(RuntimeError):
    """本地产品运行时 repository 的稳定错误基类。"""


class RuntimeNotFoundError(RuntimeRepositoryError):
    """记录不存在，或不属于当前 authenticated user。"""


class RuntimeConflictError(RuntimeRepositoryError):
    """状态转换或同线程并发策略冲突。"""


_ACTIVE_STATUSES = (RunStatus.pending.value, RunStatus.running.value)
_STREAM_MODES = {"messages", "updates", "values", "custom"}
_EVENT_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,79}$")
_TRANSITIONS = {
    RunStatus.pending: {
        RunStatus.running,
        RunStatus.cancelled,
        RunStatus.error,
    },
    RunStatus.running: {
        RunStatus.interrupted,
        RunStatus.success,
        RunStatus.error,
        RunStatus.cancelled,
    },
    RunStatus.interrupted: set(),
    RunStatus.success: set(),
    RunStatus.error: set(),
    RunStatus.cancelled: set(),
}
_TERMINAL_STATUSES = {
    RunStatus.interrupted,
    RunStatus.success,
    RunStatus.error,
    RunStatus.cancelled,
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


class SqliteRuntimeRepository:
    """保存产品 thread/run/event，并在 SQL 查询层执行 ownership。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runtime_threads (
                    thread_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runtime_runs (
                    run_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_kind TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    stream_modes_json TEXT NOT NULL,
                    on_disconnect TEXT NOT NULL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    error_message TEXT,
                    next_sequence INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(thread_id) REFERENCES runtime_threads(thread_id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS one_active_run_per_thread
                ON runtime_runs(thread_id)
                WHERE status IN ('pending', 'running');

                CREATE TABLE IF NOT EXISTS runtime_events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(run_id, sequence),
                    FOREIGN KEY(run_id) REFERENCES runtime_runs(run_id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _thread_from_row(row: sqlite3.Row) -> ThreadRecord:
        return ThreadRecord(
            thread_id=row["thread_id"],
            user_id=row["user_id"],
            metadata=json.loads(row["metadata_json"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            thread_id=row["thread_id"],
            user_id=row["user_id"],
            status=RunStatus(row["status"]),
            input_kind=row["input_kind"],
            input_data=json.loads(row["input_json"]),
            stream_modes=tuple(json.loads(row["stream_modes_json"])),
            on_disconnect=row["on_disconnect"],
            cancel_requested=bool(row["cancel_requested"]),
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> RunEvent:
        return RunEvent(
            run_id=row["run_id"],
            sequence=row["sequence"],
            event=row["event"],
            data=json.loads(row["data_json"]),
            created_at=row["created_at"],
        )

    def create_thread(
        self,
        *,
        user_id: str,
        metadata: Mapping[str, JSONValue] | None = None,
        thread_id: str | None = None,
    ) -> ThreadRecord:
        created_at = _now()
        record = ThreadRecord(
            thread_id=thread_id or f"thread-{uuid.uuid4().hex}",
            user_id=user_id,
            metadata=dict(metadata or {}),
            created_at=created_at,
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO runtime_threads(thread_id, user_id, metadata_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        record.thread_id,
                        record.user_id,
                        _json(record.metadata),
                        record.created_at,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RuntimeConflictError(
                f"thread_id 已存在: {record.thread_id}"
            ) from error
        return record

    def get_thread(self, thread_id: str, *, user_id: str) -> ThreadRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM runtime_threads
                WHERE thread_id = ? AND user_id = ?
                """,
                (thread_id, user_id),
            ).fetchone()
        if row is None:
            raise RuntimeNotFoundError(f"thread 不存在: {thread_id}")
        return self._thread_from_row(row)

    def create_run(
        self,
        *,
        user_id: str,
        thread_id: str,
        input_kind: RunInputKind,
        input_data: Mapping[str, JSONValue],
        stream_modes: Sequence[StreamMode],
        on_disconnect: DisconnectMode,
        run_id: str | None = None,
    ) -> RunRecord:
        self.get_thread(thread_id, user_id=user_id)
        normalized_modes = tuple(dict.fromkeys(stream_modes))
        if not normalized_modes or any(mode not in _STREAM_MODES for mode in normalized_modes):
            raise ValueError("stream_modes 只能包含 messages/updates/values/custom")
        if on_disconnect not in {"cancel", "continue"}:
            raise ValueError("on_disconnect 只能是 cancel 或 continue")
        now = _now()
        record = RunRecord(
            run_id=run_id or f"run-{uuid.uuid4().hex}",
            thread_id=thread_id,
            user_id=user_id,
            status=RunStatus.pending,
            input_kind=input_kind,
            input_data=dict(input_data),
            stream_modes=normalized_modes,
            on_disconnect=on_disconnect,
            created_at=now,
            updated_at=now,
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO runtime_runs(
                        run_id, thread_id, user_id, status, input_kind, input_json,
                        stream_modes_json, on_disconnect, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.run_id,
                        record.thread_id,
                        record.user_id,
                        record.status.value,
                        record.input_kind,
                        _json(record.input_data),
                        _json(record.stream_modes),
                        record.on_disconnect,
                        record.created_at,
                        record.updated_at,
                    ),
                )
        except sqlite3.IntegrityError as error:
            message = str(error).lower()
            if "one_active_run_per_thread" in message or "runtime_runs.thread_id" in message:
                raise RuntimeConflictError(
                    f"thread {thread_id} 已有 pending/running run"
                ) from error
            raise RuntimeConflictError(f"run_id 已存在: {record.run_id}") from error
        return record

    def get_run(self, run_id: str, *, user_id: str) -> RunRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM runtime_runs WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone()
        if row is None:
            raise RuntimeNotFoundError(f"run 不存在: {run_id}")
        return self._run_from_row(row)

    def list_runs(self, thread_id: str, *, user_id: str) -> tuple[RunRecord, ...]:
        self.get_thread(thread_id, user_id=user_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM runtime_runs
                WHERE thread_id = ? AND user_id = ?
                ORDER BY created_at ASC, run_id ASC
                """,
                (thread_id, user_id),
            ).fetchall()
        return tuple(self._run_from_row(row) for row in rows)

    def transition_run(
        self,
        run_id: str,
        *,
        user_id: str,
        to_status: RunStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> RunRecord:
        if to_status in _TERMINAL_STATUSES:
            raise ValueError("terminal status 必须通过 finish_run 原子写入 end")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM runtime_runs WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeNotFoundError(f"run 不存在: {run_id}")
            current = RunStatus(row["status"])
            if to_status not in _TRANSITIONS[current]:
                raise RuntimeConflictError(
                    f"非法 run 状态转换: {current.value} -> {to_status.value}"
                )
            connection.execute(
                """
                UPDATE runtime_runs
                SET status = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE run_id = ? AND user_id = ?
                """,
                (
                    to_status.value,
                    error_code,
                    (error_message[:2000] if error_message else None),
                    _now(),
                    run_id,
                    user_id,
                ),
            )
        return self.get_run(run_id, user_id=user_id)

    def request_cancel(self, run_id: str, *, user_id: str) -> RunRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM runtime_runs WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeNotFoundError(f"run 不存在: {run_id}")
            status = RunStatus(row["status"])
            if status not in {RunStatus.pending, RunStatus.running}:
                raise RuntimeConflictError(
                    f"run {run_id} 当前状态不可取消: {status.value}"
                )
            connection.execute(
                """
                UPDATE runtime_runs
                SET cancel_requested = 1, updated_at = ?
                WHERE run_id = ? AND user_id = ?
                """,
                (_now(), run_id, user_id),
            )
        return self.get_run(run_id, user_id=user_id)

    def finish_run(
        self,
        run_id: str,
        *,
        user_id: str,
        to_status: RunStatus,
        error_code: str | None = None,
        error_message: str | None = None,
        terminal_event: tuple[str, JSONValue] | None = None,
    ) -> RunRecord:
        """原子写入终态、可选终端业务事件与强制 ``end``。"""

        if to_status not in _TERMINAL_STATUSES:
            raise ValueError("finish_run 只接受 terminal status")
        if terminal_event is not None and not _EVENT_NAME.fullmatch(terminal_event[0]):
            raise ValueError("terminal event name 必须是安全的小写标识符")
        occurred_at = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, next_sequence FROM runtime_runs
                WHERE run_id = ? AND user_id = ?
                """,
                (run_id, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeNotFoundError(f"run 不存在: {run_id}")
            current = RunStatus(row["status"])
            if to_status not in _TRANSITIONS[current]:
                raise RuntimeConflictError(
                    f"非法 run 状态转换: {current.value} -> {to_status.value}"
                )
            sequence = int(row["next_sequence"])
            connection.execute(
                """
                UPDATE runtime_runs
                SET status = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE run_id = ? AND user_id = ?
                """,
                (
                    to_status.value,
                    error_code,
                    (error_message[:2000] if error_message else None),
                    occurred_at,
                    run_id,
                    user_id,
                ),
            )
            if terminal_event is not None:
                event, data = terminal_event
                connection.execute(
                    """
                    INSERT INTO runtime_events(
                        run_id, sequence, event, data_json, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (run_id, sequence, event, _json(data), occurred_at),
                )
                sequence += 1
            connection.execute(
                """
                INSERT INTO runtime_events(
                    run_id, sequence, event, data_json, created_at
                ) VALUES (?, ?, 'end', ?, ?)
                """,
                (
                    run_id,
                    sequence,
                    _json({"status": to_status.value}),
                    occurred_at,
                ),
            )
            connection.execute(
                "UPDATE runtime_runs SET next_sequence = ? WHERE run_id = ?",
                (sequence + 1, run_id),
            )
        return self.get_run(run_id, user_id=user_id)

    def recover_inflight_runs(
        self,
        *,
        error_code: str = "worker_restarted",
        error_message: str = "本地 worker 重启，原执行上下文已丢失",
    ) -> tuple[RunRecord, ...]:
        """单 worker 启动恢复：终止孤儿 run，并留下可重放的错误事实。"""

        recovered_keys: list[tuple[str, str]] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT run_id, user_id, next_sequence
                FROM runtime_runs
                WHERE status IN (?, ?)
                ORDER BY created_at ASC, run_id ASC
                """,
                _ACTIVE_STATUSES,
            ).fetchall()
            for row in rows:
                run_id = str(row["run_id"])
                user_id = str(row["user_id"])
                first_sequence = int(row["next_sequence"])
                occurred_at = _now()
                connection.execute(
                    """
                    UPDATE runtime_runs
                    SET status = ?, error_code = ?, error_message = ?,
                        next_sequence = ?, updated_at = ?
                    WHERE run_id = ?
                    """,
                    (
                        RunStatus.error.value,
                        error_code,
                        error_message[:2000],
                        first_sequence + 2,
                        occurred_at,
                        run_id,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO runtime_events(
                        run_id, sequence, event, data_json, created_at
                    ) VALUES (?, ?, 'error', ?, ?)
                    """,
                    (
                        run_id,
                        first_sequence,
                        _json({"code": error_code, "message": error_message[:500]}),
                        occurred_at,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO runtime_events(
                        run_id, sequence, event, data_json, created_at
                    ) VALUES (?, ?, 'end', ?, ?)
                    """,
                    (
                        run_id,
                        first_sequence + 1,
                        _json({"status": RunStatus.error.value}),
                        occurred_at,
                    ),
                )
                recovered_keys.append((run_id, user_id))
        return tuple(
            self.get_run(run_id, user_id=user_id)
            for run_id, user_id in recovered_keys
        )

    def append_event(
        self,
        run_id: str,
        *,
        user_id: str,
        event: str,
        data: JSONValue,
    ) -> RunEvent:
        if not _EVENT_NAME.fullmatch(event):
            raise ValueError("event name 必须是安全的小写标识符")
        created_at = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT next_sequence FROM runtime_runs
                WHERE run_id = ? AND user_id = ?
                """,
                (run_id, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeNotFoundError(f"run 不存在: {run_id}")
            sequence = int(row["next_sequence"])
            connection.execute(
                """
                INSERT INTO runtime_events(run_id, sequence, event, data_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, sequence, event, _json(data), created_at),
            )
            connection.execute(
                "UPDATE runtime_runs SET next_sequence = ? WHERE run_id = ?",
                (sequence + 1, run_id),
            )
        return RunEvent(
            run_id=run_id,
            sequence=sequence,
            event=event,
            data=data,
            created_at=created_at,
        )

    def list_events(
        self,
        run_id: str,
        *,
        user_id: str,
        after_sequence: int = 0,
        limit: int = 1000,
    ) -> tuple[RunEvent, ...]:
        self.get_run(run_id, user_id=user_id)
        if after_sequence < 0:
            raise ValueError("after_sequence 不能小于 0")
        if not 1 <= limit <= 10_000:
            raise ValueError("limit 必须在 1..10000")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM runtime_events
                WHERE run_id = ? AND sequence > ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (run_id, after_sequence, limit),
            ).fetchall()
        return tuple(self._event_from_row(row) for row in rows)

    def get_latest_event(
        self,
        run_id: str,
        *,
        user_id: str,
    ) -> RunEvent | None:
        self.get_run(run_id, user_id=user_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM runtime_events
                WHERE run_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return self._event_from_row(row) if row is not None else None


__all__ = [
    "RuntimeConflictError",
    "RuntimeNotFoundError",
    "RuntimeRepositoryError",
    "SqliteRuntimeRepository",
]
