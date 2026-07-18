"""Typed workflow observability events shared by explicit Mini DeerFlow graphs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkflowEvent(BaseModel):
    """A checkpoint-safe node event with a separate optional detail field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    detail: str | None = None

    def as_text(self) -> str:
        """Render a compact human-readable form without making it the State contract."""

        return self.name if self.detail is None else f"{self.name}:{self.detail}"


__all__ = ["WorkflowEvent"]
