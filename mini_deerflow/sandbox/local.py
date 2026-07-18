"""默认禁用宿主命令、按用户和线程隔离目录的本地 Sandbox provider。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from threading import RLock
import tempfile
from typing import Literal

from mini_deerflow.sandbox.contracts import (
    SandboxAuditEvent,
    SandboxCommand,
    SandboxPathError,
    SandboxResult,
    SandboxWriteResult,
)
from mini_deerflow.schemas import ArtifactRef


def _identity_digest(value: str, *, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} 不能为空")
    if len(normalized) > 512:
        raise ValueError(f"{label} 过长")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


class LocalSandboxSession:
    """真实读写本地线程目录，但绝不把宿主 shell 冒充为隔离执行。"""

    def __init__(self, *, sandbox_id: str, workspace_path: Path) -> None:
        self._sandbox_id = sandbox_id
        self._workspace_path = workspace_path.resolve()
        self._workspace_path.mkdir(parents=True, exist_ok=True)
        self._events: list[SandboxAuditEvent] = []
        self._lock = RLock()

    @property
    def sandbox_id(self) -> str:
        return self._sandbox_id

    @property
    def workspace_path(self) -> Path:
        """仅供本地 adapter/运维检查；模型工具 schema 不暴露宿主路径。"""

        return self._workspace_path

    @staticmethod
    def _relative_parts(path: str) -> tuple[str, ...]:
        candidate = PurePosixPath(path)
        if (
            not path.strip()
            or candidate.is_absolute()
            or ".." in candidate.parts
            or candidate.parts in {(), (".",)}
        ):
            raise SandboxPathError("Sandbox path 必须是 workspace 内的相对路径")
        return tuple(part for part in candidate.parts if part != ".")

    def _record(
        self,
        action: Literal["read_text", "write_text", "execute"],
        outcome: Literal["completed", "rejected", "denied"],
        *,
        path: str | None = None,
        detail: str | None = None,
    ) -> None:
        self._events.append(
            SandboxAuditEvent(
                sequence=len(self._events) + 1,
                sandbox_id=self.sandbox_id,
                action=action,
                outcome=outcome,
                path=path,
                detail=detail,
            )
        )

    def _walk_to_parent(self, path: str, *, create: bool) -> tuple[Path, str]:
        parts = self._relative_parts(path)
        current = self._workspace_path
        for part in parts[:-1]:
            candidate = current / part
            if candidate.is_symlink():
                raise SandboxPathError("Sandbox 拒绝经过符号链接解析路径")
            if candidate.exists():
                if not candidate.is_dir():
                    raise SandboxPathError("Sandbox path 的父级不是目录")
            elif create:
                candidate.mkdir()
            else:
                raise FileNotFoundError(path)
            current = candidate
        return current, parts[-1]

    def _existing_file(self, path: str) -> Path:
        parent, name = self._walk_to_parent(path, create=False)
        candidate = parent / name
        if candidate.is_symlink():
            raise SandboxPathError("Sandbox 拒绝读取符号链接")
        if not candidate.is_file():
            raise FileNotFoundError(path)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(self._workspace_path):
            raise SandboxPathError("Sandbox path 解析后越出 workspace")
        return resolved

    def read_text(self, path: str, *, max_bytes: int = 1_000_000) -> str:
        if max_bytes < 1:
            raise ValueError("max_bytes 必须大于 0")
        with self._lock:
            try:
                candidate = self._existing_file(path)
                size = candidate.stat().st_size
                if size > max_bytes:
                    raise ValueError(
                        f"文件 {size} bytes，超过 {max_bytes} bytes 读取预算"
                    )
                content = candidate.read_text(encoding="utf-8")
            except Exception as error:
                self._record(
                    "read_text",
                    "rejected",
                    path=path,
                    detail=type(error).__name__,
                )
                raise
            self._record("read_text", "completed", path=path, detail=f"{size} bytes")
            return content

    def write_text(
        self,
        path: str,
        content: str,
        *,
        media_type: str = "text/plain",
        overwrite: bool = True,
    ) -> SandboxWriteResult:
        encoded = content.encode("utf-8")
        if len(encoded) > 1_000_000:
            raise ValueError("单次 Sandbox 文本写入不能超过 1000000 bytes")
        with self._lock:
            try:
                self._relative_parts(path)
                artifact = ArtifactRef(path=path, media_type=media_type)
                parent, name = self._walk_to_parent(path, create=True)
                destination = parent / name
                if destination.is_symlink():
                    raise SandboxPathError("Sandbox 拒绝覆盖符号链接")
                existed = destination.exists()
                if existed and not destination.is_file():
                    raise SandboxPathError("Sandbox write 目标不是普通文件")
                if existed and not overwrite:
                    raise FileExistsError(path)
                file_descriptor, temporary_name = tempfile.mkstemp(
                    dir=parent,
                    prefix=f".{name}.",
                    suffix=".tmp",
                )
                try:
                    with os.fdopen(file_descriptor, "wb") as temporary:
                        temporary.write(encoded)
                    os.replace(temporary_name, destination)
                except Exception:
                    Path(temporary_name).unlink(missing_ok=True)
                    raise
            except Exception as error:
                self._record(
                    "write_text",
                    "rejected",
                    path=path,
                    detail=type(error).__name__,
                )
                raise
            self._record(
                "write_text",
                "completed",
                path=path,
                detail=f"{len(encoded)} bytes",
            )
            return SandboxWriteResult(
                artifact=artifact,
                bytes_written=len(encoded),
                created=not existed,
            )

    def execute(self, command: SandboxCommand) -> SandboxResult:
        with self._lock:
            self._record(
                "execute",
                "denied",
                detail="host_command_execution_disabled",
            )
        return SandboxResult(
            exit_code=126,
            stdout="",
            stderr=(
                "host command execution disabled: LocalSandboxProvider 只提供"
                "线程文件隔离，不是进程或容器安全边界"
            ),
        )

    def audit_events(self) -> tuple[SandboxAuditEvent, ...]:
        with self._lock:
            return tuple(self._events)


class LocalSandboxProvider:
    """为每个 ``(user_id, thread_id)`` 缓存独立本地会话。"""

    name = "local-workspace"

    def __init__(self, base_dir: str | Path) -> None:
        # ``abspath`` 规范化相对路径，但故意不解析 symlink；
        # provider 必须能在 acquire 时审查配置的 root 本身。
        self.base_dir = Path(os.path.abspath(base_dir))
        self._sessions: dict[str, LocalSandboxSession] = {}
        self._lock = RLock()

    def _safe_workspace(self, relative: Path) -> Path:
        """逐级创建 provider 目录，并拒绝已有 symlink/非目录组件。"""

        if self.base_dir.is_symlink():
            raise SandboxPathError("Sandbox provider root 不能是符号链接")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.base_dir.is_dir():
            raise SandboxPathError("Sandbox provider root 不是目录")
        resolved_root = self.base_dir.resolve(strict=True)
        current = self.base_dir
        for part in relative.parts:
            candidate = current / part
            if candidate.is_symlink():
                raise SandboxPathError("Sandbox workspace 路径不能包含符号链接")
            if candidate.exists():
                if not candidate.is_dir():
                    raise SandboxPathError("Sandbox workspace 路径组件不是目录")
            else:
                candidate.mkdir()
            current = candidate
        resolved = current.resolve(strict=True)
        if not resolved.is_relative_to(resolved_root):
            raise SandboxPathError("Sandbox workspace 解析后越出 provider root")
        return resolved

    @staticmethod
    def _identity(thread_id: str, user_id: str) -> tuple[str, Path]:
        user_digest = _identity_digest(user_id, label="user_id")
        thread_digest = _identity_digest(thread_id, label="thread_id")
        sandbox_id = f"local:{user_digest}:{thread_digest}"
        relative = Path("users") / user_digest / "threads" / thread_digest / "workspace"
        return sandbox_id, relative

    def acquire(self, thread_id: str, *, user_id: str) -> LocalSandboxSession:
        sandbox_id, relative = self._identity(thread_id, user_id)
        with self._lock:
            existing = self._sessions.get(sandbox_id)
            if existing is not None:
                return existing
            session = LocalSandboxSession(
                sandbox_id=sandbox_id,
                workspace_path=self._safe_workspace(relative),
            )
            self._sessions[sandbox_id] = session
            return session

    def get(self, sandbox_id: str) -> LocalSandboxSession | None:
        with self._lock:
            return self._sessions.get(sandbox_id)

    def release(self, sandbox_id: str) -> None:
        with self._lock:
            self._sessions.pop(sandbox_id, None)


__all__ = ["LocalSandboxProvider", "LocalSandboxSession"]
