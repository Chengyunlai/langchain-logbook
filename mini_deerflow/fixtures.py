"""Deterministic course fixtures; production factories remain free of demo data."""

from __future__ import annotations

from itertools import cycle

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from mini_deerflow.knowledge import KnowledgeDocument, LocalKnowledgeIndex
from mini_deerflow.models import create_offline_model


def create_demo_index() -> LocalKnowledgeIndex:
    """Return the small, deterministic knowledge base used by offline lessons."""

    index = LocalKnowledgeIndex()
    index.upsert(
        [
            KnowledgeDocument(
                id="course-boundary",
                text="create_agent 是构建在 LangGraph runtime 上的高层 Agent 工厂。",
                source="course/agent-boundary.md",
            )
        ]
    )
    return index


def _demo_lead_responses() -> tuple[AIMessage, AIMessage]:
    return (
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_knowledge",
                    "args": {"query": "create_agent LangGraph", "limit": 1},
                    "id": "offline-search-1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(content="离线工具循环已完成；请查看 ToolMessage 中的引用。"),
    )


def create_demo_lead_model() -> BaseChatModel:
    """Return a bounded script for tests that should make exactly one tool loop."""

    return create_offline_model(_demo_lead_responses())


def create_repeating_demo_lead_model() -> BaseChatModel:
    """Return the reusable offline application model: one tool loop per invocation."""

    return create_offline_model(cycle(_demo_lead_responses()))


def create_repeating_demo_summary_model() -> BaseChatModel:
    """Return a reusable deterministic model dedicated to context summarization."""

    return create_offline_model(
        cycle(["摘要：本线程正在组合 Context、State、Tools 与 Middleware。"])
    )


__all__ = [
    "create_demo_index",
    "create_demo_lead_model",
    "create_repeating_demo_lead_model",
    "create_repeating_demo_summary_model",
]
