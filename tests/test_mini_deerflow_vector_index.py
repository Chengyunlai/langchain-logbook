from __future__ import annotations

import unittest

from mini_deerflow.knowledge import KnowledgeDocument
from mini_deerflow.knowledge.evaluation import RetrievalCase, recall_at_k
from mini_deerflow.knowledge.indexer import VectorKnowledgeIndex


class VectorIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = [
            KnowledgeDocument(
                id="persistence",
                text="checkpoint thread durable execution recovery",
                source="official/persistence.md",
                metadata={"topic": "runtime"},
            ),
            KnowledgeDocument(
                id="structured-output",
                text="structured output schema validation",
                source="official/structured-output.md",
                metadata={"topic": "model"},
            ),
        ]
        self.index = VectorKnowledgeIndex(embedding_size=64)
        self.index.upsert(self.documents)

    def test_metadata_filter_limits_the_vector_search_domain(self) -> None:
        hits = self.index.search(
            "checkpoint thread durable execution recovery",
            limit=2,
            metadata_filter={"topic": "runtime"},
        )

        self.assertEqual([hit.id for hit in hits], ["persistence"])

    def test_fixed_retrieval_cases_have_perfect_recall_at_one(self) -> None:
        cases = [
            RetrievalCase(
                query="checkpoint thread durable execution recovery",
                expected_ids={"persistence"},
            ),
            RetrievalCase(
                query="structured output schema validation",
                expected_ids={"structured-output"},
            ),
        ]

        self.assertEqual(recall_at_k(self.index, cases, k=1), 1.0)


if __name__ == "__main__":
    unittest.main()
