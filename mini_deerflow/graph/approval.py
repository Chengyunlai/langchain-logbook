"""Dynamic human approval graph with a durable local effect-intent record."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ConfigDict, Field, model_validator

from mini_deerflow.graph.events import WorkflowEvent
from mini_deerflow.persistence import SqliteEffectLedger


class ApprovalDecision(BaseModel):
    """Validated response supplied by an authorized approval client."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision: Literal["approve", "edit", "reject"]
    edited_payload: dict[str, str] | None = None
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def edit_requires_payload(self) -> ApprovalDecision:
        if self.decision == "edit" and self.edited_payload is None:
            raise ValueError("edit decision 必须提供 edited_payload")
        return self


class ApprovalState(TypedDict, total=False):
    """Checkpointed request, decisions and final effect outcome."""

    request_id: str
    action: str
    payload: dict[str, str]
    review_stages: list[str]
    decisions: Annotated[list[ApprovalDecision], operator.add]
    status: Literal["rejected", "completed"]
    effect_status: Literal["recorded", "already_recorded"]
    audit: Annotated[list[WorkflowEvent], operator.add]


# region tutorial:10-dynamic-approval-workflow
def create_approval_workflow(
    *,
    checkpointer: BaseCheckpointSaver[Any],
    effect_ledger: SqliteEffectLedger,
) -> CompiledStateGraph:
    """Compile dynamic interrupts followed by one durable local effect intent."""

    def review(
        state: ApprovalState,
        runtime: Runtime[None],
    ) -> Command[Literal["record_effect_intent", "finish"]]:
        runtime.stream_writer(
            {"event": "review_node_entered", "request_id": state["request_id"]}
        )
        payload = dict(state["payload"])
        accepted: list[ApprovalDecision] = []
        for stage in state.get("review_stages") or ["risk"]:
            raw_decision = interrupt(
                {
                    "kind": "approval_required",
                    "request_id": state["request_id"],
                    "stage": stage,
                    "action": state["action"],
                    "payload": payload,
                    "allowed_decisions": ["approve", "edit", "reject"],
                }
            )
            decision = ApprovalDecision.model_validate(raw_decision)
            accepted.append(decision)
            if decision.decision == "reject":
                return Command(
                    update={
                        "decisions": accepted,
                        "status": "rejected",
                        "audit": [WorkflowEvent(name=stage, detail="rejected")],
                    },
                    goto="finish",
                )
            if decision.decision == "edit":
                payload = dict(decision.edited_payload or {})

        return Command(
            update={
                "payload": payload,
                "decisions": accepted,
                "audit": [WorkflowEvent(name="review", detail="approved")],
            },
            goto="record_effect_intent",
        )

    def record_effect_intent(state: ApprovalState) -> dict[str, object]:
        receipt = effect_ledger.record_once(
            state["request_id"],
            state["action"],
            state["payload"],
        )
        return {
            "status": "completed",
            "effect_status": receipt.status,
            "audit": [WorkflowEvent(name="effect_intent", detail=receipt.status)],
        }

    builder = StateGraph(ApprovalState)
    builder.add_node("review", review)
    builder.add_node("record_effect_intent", record_effect_intent)
    builder.add_node("finish", lambda state: {})
    builder.add_edge(START, "review")
    builder.add_edge("record_effect_intent", END)
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer)
# endregion tutorial:10-dynamic-approval-workflow


__all__ = ["ApprovalDecision", "ApprovalState", "create_approval_workflow"]
