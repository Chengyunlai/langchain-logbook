"""不依赖 LLM judge 的确定性检索评测。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from mini_deerflow.knowledge import KnowledgeHit


@dataclass(frozen=True, slots=True)
class RetrievalCase:
    query: str
    expected_ids: set[str]


class SearchableKnowledge(Protocol):
    def search(self, query: str, *, limit: int = 3) -> list[KnowledgeHit]: ...


# region tutorial:03-retrieval-eval
def recall_at_k(
    index: SearchableKnowledge,
    cases: Sequence[RetrievalCase],
    *,
    k: int,
) -> float:
    """计算所有 case 的 macro recall@k；空数据集不是有效评测。"""

    if not cases:
        raise ValueError("retrieval cases 不能为空")
    recalls: list[float] = []
    for case in cases:
        if not case.expected_ids:
            raise ValueError("每个 retrieval case 至少需要一个 expected id")
        actual = {hit.id for hit in index.search(case.query, limit=k)}
        recalls.append(len(actual & case.expected_ids) / len(case.expected_ids))
    return sum(recalls) / len(recalls)
# endregion tutorial:03-retrieval-eval


__all__ = ["RetrievalCase", "recall_at_k"]
