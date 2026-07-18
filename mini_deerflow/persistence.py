"""Durable local persistence boundaries for Mini DeerFlow course scenarios."""

from __future__ import annotations

import json
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
import sqlite3
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore


_CHECKPOINT_TYPE_ALLOWLIST = [
    ("mini_deerflow.graph.approval", "ApprovalDecision"),
    ("mini_deerflow.graph.events", "WorkflowEvent"),
    ("mini_deerflow.schemas", "ArtifactRef"),
    ("mini_deerflow.state", "MiddlewareTraceEvent"),
]


@contextmanager
def open_sqlite_checkpointer(path: str | Path) -> Iterator[SqliteSaver]:
    """打开采用显式类型 allowlist 的本地 SQLite Checkpointer。"""

    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    try:
        yield SqliteSaver(
            connection,
            serde=JsonPlusSerializer(
                allowed_msgpack_modules=_CHECKPOINT_TYPE_ALLOWLIST
            ),
        )
    finally:
        connection.close()


@contextmanager
def open_sqlite_store(path: str | Path) -> Iterator[SqliteStore]:
    """打开本地持久化 LangGraph Store；生命周期由 composition root 拥有。"""

    store_path = Path(path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        store_path,
        check_same_thread=False,
        isolation_level=None,
    )
    try:
        store = SqliteStore(connection)
        store.setup()
        yield store
    finally:
        connection.close()


class IdempotencyConflictError(ValueError):
    """An idempotency key was reused for a different requested effect."""


class EffectReceipt(BaseModel):
    """Stable outcome returned by the local effect-intent ledger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation_id: str
    action: str
    payload: dict[str, str]
    status: Literal["recorded", "already_recorded"]


# region tutorial:10-idempotent-effect-ledger
class SqliteEffectLedger:
    """Record one local effect intent; remote delivery still needs an outbox/provider key."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS effect_intents (
                    operation_id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record_once(
        self,
        operation_id: str,
        action: str,
        payload: Mapping[str, str],
    ) -> EffectReceipt:
        """Record the effect atomically or return the matching existing record."""

        normalized_payload = dict(payload)
        payload_json = json.dumps(normalized_payload, ensure_ascii=False, sort_keys=True)
        with self._connect() as connection:
            # Serialize the read-before-insert section across local processes. The primary
            # key remains the final guard, while BEGIN IMMEDIATE avoids a check/insert race.
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT action, payload_json
                FROM effect_intents
                WHERE operation_id = ?
                """,
                (operation_id,),
            ).fetchone()
            if existing is not None:
                existing_action, existing_payload_json = existing
                if existing_action != action or existing_payload_json != payload_json:
                    raise IdempotencyConflictError(
                        f"operation_id {operation_id!r} 已用于不同副作用"
                    )
                return EffectReceipt(
                    operation_id=operation_id,
                    action=action,
                    payload=normalized_payload,
                    status="already_recorded",
                )
            connection.execute(
                """
                INSERT INTO effect_intents(operation_id, action, payload_json)
                VALUES (?, ?, ?)
                """,
                (operation_id, action, payload_json),
            )
        return EffectReceipt(
            operation_id=operation_id,
            action=action,
            payload=normalized_payload,
            status="recorded",
        )

    def count(self, operation_id: str | None = None) -> int:
        """Count durable effect rows for acceptance tests and operations."""

        with self._connect() as connection:
            if operation_id is None:
                row = connection.execute("SELECT COUNT(*) FROM effect_intents").fetchone()
            else:
                row = connection.execute(
                    "SELECT COUNT(*) FROM effect_intents WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
        return int(row[0]) if row is not None else 0
# endregion tutorial:10-idempotent-effect-ledger


__all__ = [
    "EffectReceipt",
    "IdempotencyConflictError",
    "SqliteEffectLedger",
    "open_sqlite_checkpointer",
    "open_sqlite_store",
]
