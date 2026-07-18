"""不含 Secret 的模型配置契约。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from mini_deerflow.context import RuntimeContext


class ModelProfile(StrEnum):
    """课程支持的模型运行档位，而不是供应商能力大全。"""

    OFFLINE = "offline"
    DEEPSEEK = "deepseek"


@dataclass(frozen=True, slots=True)
class ModelSettings:
    """创建聊天模型所需的非敏感设置。"""

    profile: ModelProfile = ModelProfile.OFFLINE
    model_name: str | None = None
    temperature: float = 0.0


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    """Mini DeerFlow 组合根所需的非敏感应用配置。

    用户身份和权限仍会在每次调用时变成 :class:`RuntimeContext`；这里保存的只是
    离线演示默认值。生产环境不能把这组默认值当成认证结果。
    """

    model: ModelSettings = field(default_factory=ModelSettings)
    workspace_root: Path = Path(".")
    default_user_id: str = "offline-learner"
    default_permissions: frozenset[str] = frozenset({"knowledge:read"})
    model_call_limit: int = 6
    summary_trigger_messages: int = 12
    summary_keep_messages: int = 4
    subagent_max_concurrency: int = 2
    subagent_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_root", Path(self.workspace_root).resolve())
        normalized_user = self.default_user_id.strip()
        if not normalized_user:
            raise ValueError("default_user_id 不能为空")
        object.__setattr__(self, "default_user_id", normalized_user)
        object.__setattr__(
            self,
            "default_permissions",
            frozenset(self.default_permissions),
        )
        if self.model_call_limit < 1:
            raise ValueError("model_call_limit 必须大于 0")
        if self.summary_keep_messages < 1:
            raise ValueError("summary_keep_messages 必须大于 0")
        if self.summary_trigger_messages <= self.summary_keep_messages:
            raise ValueError(
                "summary_trigger_messages 必须大于 summary_keep_messages"
            )
        if self.subagent_max_concurrency < 1:
            raise ValueError("subagent_max_concurrency 必须大于 0")
        if self.subagent_timeout_seconds <= 0:
            raise ValueError("subagent_timeout_seconds 必须大于 0")

    @classmethod
    def offline(
        cls,
        *,
        workspace_root: str | Path = ".",
        default_user_id: str = "offline-learner",
        default_permissions: frozenset[str] = frozenset({"knowledge:read"}),
    ) -> ApplicationSettings:
        """返回无需 API Key 的课程默认配置。"""

        return cls(
            model=ModelSettings(profile=ModelProfile.OFFLINE),
            workspace_root=Path(workspace_root),
            default_user_id=default_user_id,
            default_permissions=default_permissions,
        )


LeadAgentContext = RuntimeContext
"""Backward-compatible chapter-04 name; prefer ``RuntimeContext`` from chapter 05."""


__all__ = [
    "ApplicationSettings",
    "LeadAgentContext",
    "ModelProfile",
    "ModelSettings",
]
