"""可替换向量索引 adapter；基础测试使用确定性 embedding。"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore

from mini_deerflow.knowledge import IndexReport, KnowledgeDocument, KnowledgeHit


# region tutorial:03-vector-index
class VectorKnowledgeIndex:
    """使用 LangChain VectorStore 协议的离线索引实现。"""

    def __init__(self, *, embedding_size: int = 64) -> None:
        self._store = InMemoryVectorStore(DeterministicFakeEmbedding(size=embedding_size))
        self._documents: dict[str, KnowledgeDocument] = {}

    def upsert(self, documents: Iterable[KnowledgeDocument]) -> IndexReport:
        added = updated = unchanged = 0
        changed: list[KnowledgeDocument] = []
        for document in documents:
            previous = self._documents.get(document.id)
            if previous is None:
                added += 1
                changed.append(document)
            elif previous == document:
                unchanged += 1
            else:
                updated += 1
                changed.append(document)
            self._documents[document.id] = document
        if changed:
            self._store.add_documents(
                [
                    Document(
                        page_content=document.text,
                        metadata={
                            **document.metadata,
                            "knowledge_id": document.id,
                            "source": document.source,
                        },
                    )
                    for document in changed
                ],
                ids=[document.id for document in changed],
            )
        return IndexReport(added=added, updated=updated, unchanged=unchanged)

    def search(
        self,
        query: str,
        *,
        limit: int = 3,
        metadata_filter: Mapping[str, object] | None = None,
    ) -> list[KnowledgeHit]:
        if limit < 1:
            raise ValueError("limit 必须大于 0")

        def matches(document: Document) -> bool:
            return not metadata_filter or all(
                document.metadata.get(key) == value for key, value in metadata_filter.items()
            )

        pairs = self._store.similarity_search_with_score(
            query,
            k=limit,
            filter=matches if metadata_filter else None,
        )
        return [
            KnowledgeHit(
                id=str(document.metadata["knowledge_id"]),
                text=document.page_content,
                source=str(document.metadata["source"]),
                score=score,
                metadata={
                    key: value
                    for key, value in document.metadata.items()
                    if key not in {"knowledge_id", "source"}
                },
            )
            for document, score in pairs
        ]
# endregion tutorial:03-vector-index


__all__ = ["VectorKnowledgeIndex"]
