"""Sandbox provider、线程会话与有界结果契约。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from mini_deerflow.schemas import ArtifactRef


class SandboxPathError(ValueError):
    """请求路径无法安全解析到当前线程 workspace。"""


@dataclass(frozen=True, slots=True)
class SandboxCommand:
    """交给 Sandbox 的显式命令与资源预算。"""

    argv: tuple[str, ...]
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.argv:
            raise ValueError("SandboxCommand.argv 不能为空")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须大于 0")


@dataclass(frozen=True, slots=True)
class SandboxResult:
    """Provider 归一化后的有限结果。"""

    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class SandboxWriteResult:
    """一次成功写入返回的 Artifact 引用和字节数。"""

    artifact: ArtifactRef
    bytes_written: int
    created: bool


@dataclass(frozen=True, slots=True)
class SandboxAuditEvent:
    """Sandbox 会话内有序、无正文的最小审计事实。"""

    sequence: int
    sandbox_id: str
    action: Literal["read_text", "write_text", "execute"]
    outcome: Literal["completed", "rejected", "denied"]
    path: str | None = None
    detail: str | None = None


@runtime_checkable
class SandboxSession(Protocol):
    """一个用户线程拥有的工作区会话；模型只能通过工具间接使用。"""

    @property
    def sandbox_id(self) -> str: ...

    @property
    def workspace_path(self) -> Path: ...

    def read_text(self, path: str, *, max_bytes: int = 1_000_000) -> str: ...

    def write_text(
        self,
        path: str,
        content: str,
        *,
        media_type: str = "text/plain",
        overwrite: bool = True,
    ) -> SandboxWriteResult: ...

    def execute(self, command: SandboxCommand) -> SandboxResult: ...

    def audit_events(self) -> tuple[SandboxAuditEvent, ...]: ...


@runtime_checkable
class SandboxProvider(Protocol):
    """管理 thread-scoped SandboxSession 生命周期的 provider。"""

    @property
    def name(self) -> str: ...

    def acquire(self, thread_id: str, *, user_id: str) -> SandboxSession: ...

    def get(self, sandbox_id: str) -> SandboxSession | None: ...

    def release(self, sandbox_id: str) -> None: ...


__all__ = [
    "SandboxAuditEvent",
    "SandboxCommand",
    "SandboxPathError",
    "SandboxProvider",
    "SandboxResult",
    "SandboxSession",
    "SandboxWriteResult",
]
