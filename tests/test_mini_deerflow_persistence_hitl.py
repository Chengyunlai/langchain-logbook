from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
import threading
import unittest

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from mini_deerflow.graph import (
    LegacyResearchStateV1,
    create_approval_workflow,
    create_research_state_migration_graph,
)
from mini_deerflow.persistence import IdempotencyConflictError, SqliteEffectLedger


class PersistentApprovalWorkflowTests(unittest.TestCase):
    def test_sqlite_checkpoint_resumes_after_checkpointer_is_reopened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint_path = root / "checkpoints.sqlite"
            effects = SqliteEffectLedger(root / "effects.sqlite")
            config = {"configurable": {"thread_id": "publish-001"}}
            request = {
                "request_id": "publish-001",
                "action": "publish_report",
                "payload": {"path": "reports/final.md"},
                "review_stages": ["risk"],
            }

            with SqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
                graph = create_approval_workflow(
                    checkpointer=checkpointer,
                    effect_ledger=effects,
                )
                paused = graph.invoke(request, config=config)
                self.assertEqual(paused["__interrupt__"][0].value["stage"], "risk")
                self.assertEqual(graph.get_state(config).next, ("review",))

            with SqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
                restarted_graph = create_approval_workflow(
                    checkpointer=checkpointer,
                    effect_ledger=effects,
                )
                resumed = restarted_graph.invoke(
                    Command(resume={"decision": "approve"}),
                    config=config,
                )

            self.assertEqual(resumed["status"], "completed")
            self.assertEqual(resumed["effect_status"], "recorded")
            self.assertEqual(effects.count("publish-001"), 1)

    def test_edit_changes_the_approved_payload_and_reject_has_no_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            effects = SqliteEffectLedger(Path(directory) / "effects.sqlite")
            graph = create_approval_workflow(
                checkpointer=InMemorySaver(),
                effect_ledger=effects,
            )
            edit_config = {"configurable": {"thread_id": "edit-001"}}
            graph.invoke(
                {
                    "request_id": "edit-001",
                    "action": "publish_report",
                    "payload": {"path": "reports/draft.md"},
                },
                config=edit_config,
            )

            edited = graph.invoke(
                Command(
                    resume={
                        "decision": "edit",
                        "edited_payload": {"path": "reports/reviewed.md"},
                    }
                ),
                config=edit_config,
            )

            self.assertEqual(edited["payload"], {"path": "reports/reviewed.md"})
            self.assertEqual(edited["status"], "completed")
            self.assertEqual(effects.count("edit-001"), 1)

            reject_config = {"configurable": {"thread_id": "reject-001"}}
            graph.invoke(
                {
                    "request_id": "reject-001",
                    "action": "publish_report",
                    "payload": {"path": "reports/unsafe.md"},
                },
                config=reject_config,
            )
            rejected = graph.invoke(
                Command(resume={"decision": "reject", "reason": "证据不足"}),
                config=reject_config,
            )

            self.assertEqual(rejected["status"], "rejected")
            self.assertEqual(effects.count("reject-001"), 0)

    def test_multiple_interrupts_resume_in_stable_order_and_reenter_the_node(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            effects = SqliteEffectLedger(Path(directory) / "effects.sqlite")
            graph = create_approval_workflow(
                checkpointer=InMemorySaver(),
                effect_ledger=effects,
            )
            config = {"configurable": {"thread_id": "two-stage-001"}}
            request = {
                "request_id": "two-stage-001",
                "action": "publish_report",
                "payload": {"path": "reports/final.md"},
                "review_stages": ["risk", "compliance"],
            }

            first_events = list(graph.stream(request, config=config, stream_mode="custom"))
            first_interrupt = graph.get_state(config).tasks[0].interrupts[0]
            second_events = list(
                graph.stream(
                    Command(resume={"decision": "approve"}),
                    config=config,
                    stream_mode="custom",
                )
            )
            second_interrupt = graph.get_state(config).tasks[0].interrupts[0]
            final_events = list(
                graph.stream(
                    Command(resume={"decision": "approve"}),
                    config=config,
                    stream_mode="custom",
                )
            )

            self.assertEqual(first_interrupt.value["stage"], "risk")
            self.assertEqual(second_interrupt.value["stage"], "compliance")
            self.assertEqual(
                [first_events[0]["event"], second_events[0]["event"], final_events[0]["event"]],
                ["review_node_entered", "review_node_entered", "review_node_entered"],
            )
            self.assertEqual(graph.get_state(config).values["status"], "completed")

    def test_time_travel_replay_keeps_the_local_effect_intent_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            effects = SqliteEffectLedger(Path(directory) / "effects.sqlite")
            graph = create_approval_workflow(
                checkpointer=InMemorySaver(),
                effect_ledger=effects,
            )
            config = {"configurable": {"thread_id": "replay-001"}}
            graph.invoke(
                {
                    "request_id": "replay-001",
                    "action": "publish_report",
                    "payload": {"path": "reports/final.md"},
                },
                config=config,
            )
            graph.invoke(Command(resume={"decision": "approve"}), config=config)
            before_apply = next(
                snapshot
                for snapshot in graph.get_state_history(config)
                if snapshot.next == ("record_effect_intent",)
            )

            replayed = graph.invoke(None, config=before_apply.config)

            self.assertEqual(replayed["effect_status"], "already_recorded")
            self.assertEqual(effects.count("replay-001"), 1)

            with self.assertRaises(IdempotencyConflictError):
                effects.record_once(
                    "replay-001",
                    "delete_report",
                    {"path": "reports/final.md"},
                )

    def test_two_sqlite_connections_compete_for_one_idempotency_key_safely(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "effects.sqlite"
            ledgers = [SqliteEffectLedger(path), SqliteEffectLedger(path)]
            barrier = threading.Barrier(2)

            def apply(ledger: SqliteEffectLedger) -> str:
                barrier.wait()
                return ledger.record_once(
                    "concurrent-001",
                    "publish_report",
                    {"path": "reports/final.md"},
                ).status

            with ThreadPoolExecutor(max_workers=2) as executor:
                statuses = list(executor.map(apply, ledgers))

            self.assertEqual(sorted(statuses), ["already_recorded", "recorded"])
            self.assertEqual(ledgers[0].count("concurrent-001"), 1)

    def test_legacy_sqlite_checkpoint_is_migrated_to_versioned_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint_path = Path(directory) / "migration.sqlite"
            config = {"configurable": {"thread_id": "legacy-research-001"}}

            with SqliteSaver.from_conn_string(str(checkpoint_path)) as saver:
                legacy_builder = StateGraph(LegacyResearchStateV1)
                legacy_builder.add_node("save_v1", lambda state: state)
                legacy_builder.add_edge(START, "save_v1")
                legacy_builder.add_edge("save_v1", END)
                legacy_graph = legacy_builder.compile(checkpointer=saver)
                legacy_graph.invoke(
                    {
                        "schema_version": 1,
                        "request_id": "legacy-research-001",
                        "draft": "旧 checkpoint 中的 Markdown 草稿",
                    },
                    config=config,
                )

            with SqliteSaver.from_conn_string(str(checkpoint_path)) as saver:
                migration_graph = create_research_state_migration_graph(checkpointer=saver)
                migrated = migration_graph.invoke({}, config=config)

            self.assertEqual(migrated["schema_version"], 2)
            self.assertEqual(migrated["draft"].content, "旧 checkpoint 中的 Markdown 草稿")
            self.assertEqual(migrated["draft"].media_type, "text/markdown")
            self.assertEqual(migrated["migration_status"], "migrated")


if __name__ == "__main__":
    unittest.main()
