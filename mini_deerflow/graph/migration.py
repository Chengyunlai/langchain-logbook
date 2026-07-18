"""Versioned State migration for checkpoints created by an older graph schema."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, Field


class DraftDocument(BaseModel):
    """Version-2 draft representation that makes media type explicit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content: str = Field(min_length=1)
    media_type: Literal["text/markdown"] = "text/markdown"


class LegacyResearchStateV1(TypedDict):
    """The exact channel names used by the historical version-1 graph."""

    schema_version: Literal[1]
    request_id: str
    draft: str


class VersionedResearchState(TypedDict, total=False):
    """Read both v1 string drafts and v2 typed drafts during the migration window."""

    schema_version: int
    request_id: str
    draft: str | DraftDocument
    migration_status: Literal["migrated", "already_current"]


# region tutorial:09-state-migration
def create_research_state_migration_graph(
    *, checkpointer: BaseCheckpointSaver[Any]
) -> CompiledStateGraph:
    """Upgrade a v1 checkpoint's string draft to the version-2 typed contract."""

    def migrate(state: VersionedResearchState) -> dict[str, object]:
        version = state.get("schema_version")
        draft = state.get("draft")
        if version == 2:
            DraftDocument.model_validate(draft)
            return {"migration_status": "already_current"}
        if version != 1 or not isinstance(draft, str) or not draft.strip():
            raise ValueError("仅支持包含非空 draft 的 research state v1 → v2 迁移")
        return {
            "schema_version": 2,
            "draft": DraftDocument(content=draft),
            "migration_status": "migrated",
        }

    builder = StateGraph(VersionedResearchState)
    builder.add_node("migrate", migrate)
    builder.add_edge(START, "migrate")
    builder.add_edge("migrate", END)
    return builder.compile(checkpointer=checkpointer)
# endregion tutorial:09-state-migration


__all__ = [
    "DraftDocument",
    "LegacyResearchStateV1",
    "VersionedResearchState",
    "create_research_state_migration_graph",
]
