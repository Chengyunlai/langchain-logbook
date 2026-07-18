"""离线知识索引：先固定索引与检索契约，再替换具体向量后端。"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable


TOKEN = re.compile(r"[a-z0-9_-]+|[\u3400-\u9fff]", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN.findall(text)}


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    id: str
    text: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    id: str
    text: str
    source: str
    score: float
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class IndexReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0


class LocalKnowledgeIndex:
    """确定性、无网络的教学索引。

    它用词项重叠实现稳定召回，只承担课程的 repository seam；第 03 章会
    解释如何在不改变调用方的前提下换成 dense/hybrid adapter。
    """

    def __init__(self) -> None:
        self._documents: dict[str, KnowledgeDocument] = {}

    def __len__(self) -> int:
        return len(self._documents)

    def upsert(self, documents: Iterable[KnowledgeDocument]) -> IndexReport:
        added = updated = unchanged = 0
        for document in documents:
            previous = self._documents.get(document.id)
            if previous is None:
                added += 1
                self._documents[document.id] = document
            elif previous == document:
                unchanged += 1
            else:
                updated += 1
                self._documents[document.id] = document
        return IndexReport(added=added, updated=updated, unchanged=unchanged)

    def search(self, query: str, *, limit: int = 3) -> list[KnowledgeHit]:
        if limit < 1:
            raise ValueError("limit 必须大于 0")
        query_tokens = _tokens(query)
        ranked: list[KnowledgeHit] = []
        for document in self._documents.values():
            document_tokens = _tokens(f"{document.text} {document.source}")
            overlap = query_tokens & document_tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            ranked.append(
                KnowledgeHit(
                    id=document.id,
                    text=document.text,
                    source=document.source,
                    score=score,
                    metadata=document.metadata,
                )
            )
        return sorted(ranked, key=lambda hit: (-hit.score, hit.id))[:limit]


__all__ = [
    "IndexReport",
    "KnowledgeDocument",
    "KnowledgeHit",
    "LocalKnowledgeIndex",
]
