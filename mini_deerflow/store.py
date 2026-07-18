"""Cross-thread application memory policy built on the LangGraph Store protocol."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from langgraph.store.base import BaseStore
from pydantic import BaseModel, ConfigDict, Field

from mini_deerflow.state import assert_checkpoint_safe


# region tutorial:05-store-policy
class UserPreferences(BaseModel):
    """Small allowlisted preference document safe to inject into a prompt."""

    model_config = ConfigDict(extra="forbid")

    language: str | None = Field(default=None, min_length=2, max_length=32, pattern=r"^[\w-]+$")
    answer_detail: Literal["low", "medium", "high"] | None = None
    citation_style: Literal["source-first", "inline"] | None = None


def preference_namespace(user_id: str) -> tuple[str, ...]:
    """Keep each user's long-term preferences in an explicit namespace."""

    normalized = user_id.strip()
    if not normalized:
        raise ValueError("user_id 不能为空")
    return ("users", normalized)


class UserPreferenceRepository:
    """Persist only explicitly selected cross-thread preferences, not whole state."""

    def __init__(self, store: BaseStore) -> None:
        self._store = store

    def save(
        self,
        user_id: str,
        preferences: UserPreferences | Mapping[str, Any],
    ) -> None:
        validated = UserPreferences.model_validate(preferences)
        payload = validated.model_dump(exclude_none=True)
        assert_checkpoint_safe(payload, path="store.preferences")
        self._store.put(preference_namespace(user_id), "preferences", payload)

    def load(self, user_id: str) -> dict[str, Any]:
        item = self._store.get(preference_namespace(user_id), "preferences")
        if item is None:
            return {}
        return UserPreferences.model_validate(item.value).model_dump(exclude_none=True)
# endregion tutorial:05-store-policy


__all__ = ["UserPreferenceRepository", "UserPreferences", "preference_namespace"]
