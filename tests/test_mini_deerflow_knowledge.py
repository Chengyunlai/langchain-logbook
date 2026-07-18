from __future__ import annotations

import unittest

from mini_deerflow.knowledge import KnowledgeDocument, LocalKnowledgeIndex
from mini_deerflow.tools import build_search_knowledge_tool


class LocalKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = LocalKnowledgeIndex()
        self.document = KnowledgeDocument(
            id="durable-execution",
            text="Durable execution 通过 checkpoint 和 thread 恢复长任务。",
            source="official/persistence.md",
        )

    def test_repeated_indexing_is_idempotent(self) -> None:
        first = self.index.upsert([self.document])
        second = self.index.upsert([self.document])

        self.assertEqual((first.added, first.unchanged), (1, 0))
        self.assertEqual((second.added, second.unchanged), (0, 1))
        self.assertEqual(len(self.index), 1)

    def test_search_returns_content_with_a_source_citation(self) -> None:
        self.index.upsert([self.document])

        hits = self.index.search("checkpoint 如何恢复 durable execution", limit=1)

        self.assertEqual(hits[0].source, "official/persistence.md")
        self.assertIn("thread", hits[0].text)

    def test_retriever_is_exposed_as_an_agent_tool(self) -> None:
        self.index.upsert([self.document])
        search_knowledge = build_search_knowledge_tool(self.index)

        result = search_knowledge.invoke({"query": "checkpoint", "limit": 1})

        self.assertIn("official/persistence.md", result)
        self.assertIn("Durable execution", result)


if __name__ == "__main__":
    unittest.main()
