"""Run-scoped dependencies that must not become checkpointed Agent state."""

from __future__ import annotations

from dataclasses import dataclass, field


# region tutorial:05-runtime-context
@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Application-controlled dependencies and identity for one graph invocation.

    ``auth_token`` is intentionally hidden from ``repr`` and from
    :func:`safe_context_view`. Hiding it is not authorization: tools must still check
    explicit permissions at the service boundary.
    """

    user_id: str
    workspace_root: str
    request_id: str = "offline-request"
    permissions: frozenset[str] = frozenset()
    locale: str = "zh-CN"
    model_profile: str = "offline"
    auth_token: str | None = field(default=None, repr=False)


def safe_context_view(context: RuntimeContext) -> dict[str, object]:
    """Return context metadata safe for prompts, logs, and teaching assertions."""

    return {
        "user_id": context.user_id,
        "request_id": context.request_id,
        "permissions": sorted(context.permissions),
        "locale": context.locale,
        "model_profile": context.model_profile,
    }
# endregion tutorial:05-runtime-context


__all__ = ["RuntimeContext", "safe_context_view"]
