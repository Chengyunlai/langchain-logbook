"""Deterministic workflow that demonstrates explicit LangGraph control-flow shapes."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Send
from pydantic import BaseModel, ConfigDict, Field

from mini_deerflow.graph.events import WorkflowEvent


class ResearchFinding(BaseModel):
    """One typed result produced by a dynamically fanned-out research task."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    section: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class ResearchWorkflowState(TypedDict, total=False):
    """Shared parent state for the deterministic research workflow."""

    objective: str
    sections: list[str]
    findings: Annotated[list[ResearchFinding], operator.add]
    draft: str
    revision_count: int
    quality_score: int
    status: Literal["rejected", "completed"]
    trace: Annotated[list[WorkflowEvent], operator.add]


class ResearchTaskState(TypedDict):
    """Private input delivered to one map task through ``Send``."""

    section: str


class ReviewState(TypedDict, total=False):
    """Only the fields the review subgraph is allowed to observe and update."""

    draft: str
    revision_count: int
    quality_score: int


def _create_review_subgraph() -> CompiledStateGraph:
    def score(state: ReviewState) -> dict[str, object]:
        score_value = 2 if state.get("revision_count", 0) >= 1 else 1
        return {"quality_score": score_value}

    builder = StateGraph(ReviewState)
    builder.add_node("score", score)
    builder.add_edge(START, "score")
    builder.add_edge("score", END)
    return builder.compile()


# region tutorial:08-deterministic-research-workflow
def create_research_workflow(
    *, checkpointer: BaseCheckpointSaver[Any] | None = None
) -> CompiledStateGraph:
    """Compile serial, conditional, loop, parallel and subgraph paths in one workflow."""

    review_subgraph = _create_review_subgraph()

    def intake(
        state: ResearchWorkflowState,
    ) -> Command[Literal["plan", "reject"]]:
        if not state.get("objective", "").strip():
            return Command(
                update={
                    "status": "rejected",
                    "trace": [WorkflowEvent(name="intake", detail="reject")],
                },
                goto="reject",
            )
        return Command(
            update={"trace": [WorkflowEvent(name="intake", detail="accept")]},
            goto="plan",
        )

    def plan(state: ResearchWorkflowState) -> dict[str, object]:
        sections = state.get("sections") or ["architecture", "failure-boundary"]
        return {
            "sections": sections,
            "revision_count": 0,
            "trace": [WorkflowEvent(name="plan")],
        }

    def fan_out(state: ResearchWorkflowState) -> list[Send]:
        return [Send("research_section", {"section": item}) for item in state["sections"]]

    def research_section(state: ResearchTaskState) -> dict[str, object]:
        section = state["section"]
        return {
            "findings": [
                ResearchFinding(
                    section=section,
                    evidence=f"deterministic evidence for {section}",
                )
            ],
            "trace": [WorkflowEvent(name="research", detail=section)],
        }

    def synthesize(state: ResearchWorkflowState) -> dict[str, object]:
        evidence = " | ".join(
            finding.evidence
            for finding in sorted(state["findings"], key=lambda item: item.section)
        )
        return {
            "draft": f"{state['objective']}: {evidence}",
            "trace": [WorkflowEvent(name="synthesize")],
        }

    def route_after_review(state: ResearchWorkflowState) -> Literal["revise", "finalize"]:
        return "finalize" if state.get("quality_score", 0) >= 2 else "revise"

    def record_review(state: ResearchWorkflowState) -> dict[str, object]:
        del state
        return {"trace": [WorkflowEvent(name="review", detail="score")]}

    def revise(state: ResearchWorkflowState) -> dict[str, object]:
        return {
            "draft": f"{state['draft']} [revised]",
            "revision_count": state.get("revision_count", 0) + 1,
            "trace": [WorkflowEvent(name="revise")],
        }

    def finalize(state: ResearchWorkflowState) -> dict[str, object]:
        del state
        return {"status": "completed", "trace": [WorkflowEvent(name="finalize")]}

    builder = StateGraph(ResearchWorkflowState)
    builder.add_node("intake", intake)
    builder.add_node("plan", plan)
    builder.add_node("reject", lambda state: {})
    builder.add_node("research_section", research_section)
    builder.add_node("synthesize", synthesize)
    builder.add_node("review", review_subgraph)
    builder.add_node("record_review", record_review)
    builder.add_node("revise", revise)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "intake")
    builder.add_edge("reject", END)
    builder.add_conditional_edges("plan", fan_out, ["research_section"])
    builder.add_edge("research_section", "synthesize")
    builder.add_edge("synthesize", "review")
    builder.add_edge("review", "record_review")
    builder.add_conditional_edges("record_review", route_after_review)
    builder.add_edge("revise", "review")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)
# endregion tutorial:08-deterministic-research-workflow


__all__ = ["ResearchFinding", "ResearchWorkflowState", "create_research_workflow"]
