from __future__ import annotations

import unittest

from mini_deerflow.streaming import StreamEvent, normalize_stream_part


class StreamNormalizationTests(unittest.TestCase):
    def test_v2_part_becomes_a_stable_domain_event(self) -> None:
        event = normalize_stream_part(
            {"type": "updates", "ns": ("lead",), "data": {"model": {"messages": []}}}
        )

        self.assertEqual(
            event,
            StreamEvent(
                type="updates",
                namespace=("lead",),
                data={"model": {"messages": []}},
            ),
        )

    def test_unknown_event_type_is_preserved_for_forward_compatibility(self) -> None:
        event = normalize_stream_part({"type": "future", "ns": (), "data": {"value": 1}})

        self.assertEqual(event.type, "future")
        self.assertEqual(event.data, {"value": 1})

    def test_legacy_tuple_is_rejected_with_a_migration_hint(self) -> None:
        with self.assertRaisesRegex(ValueError, "type.*ns.*data"):
            normalize_stream_part(("chunk", {"node": "model"}))

    def test_unknown_data_object_is_rejected_instead_of_stringified(self) -> None:
        with self.assertRaisesRegex(ValueError, "data.*object"):
            normalize_stream_part(
                {"type": "updates", "ns": (), "data": {"node": object()}}
            )


if __name__ == "__main__":
    unittest.main()
