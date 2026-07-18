from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from mini_deerflow.capstone import CapstoneRequest, run_capstone_scenario
from mini_deerflow.graph import ApprovalDecision
from mini_deerflow.persistence import SqliteEffectLedger
from mini_deerflow.subagents import (
    SubagentExecutor,
    SubagentOutput,
    SubagentRegistry,
    SubagentSpec,
)


class MiniDeerFlowCapstoneTests(unittest.TestCase):
    def test_report_path_is_rejected_before_any_workspace_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            with self.assertRaises(ValidationError):
                CapstoneRequest(
                    request_id="capstone-traversal",
                    thread_id="thread-capstone-traversal",
                    user_id="learner",
                    objective="尝试越出工作区",
                    report_path="../escaped.md",
                )

            self.assertEqual(tuple(root.iterdir()), ())

    def test_long_task_research_delegation_approval_recovery_and_eval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = CapstoneRequest(
                request_id="capstone-001",
                thread_id="thread-capstone-001",
                user_id="learner",
                objective="研究 LangGraph persistence，并交付带引用的实现建议",
                report_path="reports/persistence.md",
            )

            first = asyncio.run(run_capstone_scenario(request, workspace_root=root))
            replay = asyncio.run(run_capstone_scenario(request, workspace_root=root))

            self.assertEqual(first.status, "completed")
            self.assertTrue(first.checkpoint_reopened)
            self.assertEqual(first.subagent_statuses, ("completed", "completed"))
            self.assertEqual(first.effect_status, "recorded")
            self.assertEqual(replay.effect_status, "already_recorded")
            self.assertEqual(replay.effect_count, 1)
            self.assertTrue(first.evaluation.results[0].passed)
            self.assertEqual(
                first.evaluation.results[0].metrics[1].details["observed"],
                [
                    "model",
                    "search_knowledge",
                    "model",
                    "subagent:research",
                    "subagent:coding",
                    "interrupt:risk",
                    "resume:approve",
                    "write_workspace_file",
                ],
            )
            report = Path(first.artifact_path)
            self.assertTrue(report.is_file())
            content = report.read_text(encoding="utf-8")
            self.assertIn("研究摘要", content)
            self.assertIn("代码建议", content)
            self.assertIn("引用", content)

    def test_rejection_preserves_draft_but_never_publishes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = asyncio.run(
                run_capstone_scenario(
                    CapstoneRequest(
                        request_id="capstone-reject",
                        thread_id="thread-capstone-reject",
                        user_id="learner",
                        objective="研究安全恢复",
                        report_path="reports/rejected.md",
                    ),
                    workspace_root=root,
                    decision=ApprovalDecision(
                        decision="reject",
                        reason="引用不足",
                    ),
                )
            )

            self.assertEqual(result.status, "rejected")
            self.assertIsNone(result.artifact_path)
            self.assertIsNone(result.effect_status)
            self.assertEqual(result.effect_count, 0)
            self.assertTrue(Path(result.draft_path).is_file())

    def test_edit_decision_can_change_the_publish_path_without_changing_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(
                run_capstone_scenario(
                    CapstoneRequest(
                        request_id="capstone-edit",
                        thread_id="thread-capstone-edit",
                        user_id="learner",
                        objective="研究可编辑审批",
                        report_path="reports/original.md",
                    ),
                    workspace_root=directory,
                    decision=ApprovalDecision(
                        decision="edit",
                        edited_payload={"path": "reports/edited.md"},
                    ),
                )
            )

            self.assertEqual(result.status, "completed")
            self.assertTrue(str(result.artifact_path).endswith("reports/edited.md"))
            self.assertEqual(result.effect_count, 1)
            self.assertTrue(result.evaluation.results[0].passed)

    def test_edit_path_is_validated_before_effect_intent_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_id = "capstone-edit-traversal"

            with self.assertRaises(ValidationError):
                asyncio.run(
                    run_capstone_scenario(
                        CapstoneRequest(
                            request_id=request_id,
                            thread_id="thread-capstone-edit-traversal",
                            user_id="learner",
                            objective="审批编辑不能越出工作区",
                            report_path="reports/safe.md",
                        ),
                        workspace_root=root,
                        decision=ApprovalDecision(
                            decision="edit",
                            edited_payload={"path": "../escaped.md"},
                        ),
                    )
                )

            ledger = SqliteEffectLedger(
                root / ".mini-deerflow" / "capstone" / "effects.sqlite"
            )
            self.assertEqual(ledger.count(request_id), 0)
            self.assertEqual(list(root.rglob("escaped.md")), [])

    def test_subagent_timeout_fails_quality_gate_before_approval_or_publish(self) -> None:
        async def slow_research(_invocation) -> SubagentOutput:
            await asyncio.sleep(0.05)
            return SubagentOutput(summary="不应到达")

        async def quick_coding(_invocation) -> SubagentOutput:
            return SubagentOutput(summary="可测试的代码建议")

        executor = SubagentExecutor(
            SubagentRegistry(
                [
                    SubagentSpec(
                        name="research",
                        description="超时研究",
                        handler=slow_research,
                    ),
                    SubagentSpec(
                        name="coding",
                        description="快速代码分析",
                        handler=quick_coding,
                    ),
                ]
            ),
            timeout_seconds=0.005,
        )

        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(
                run_capstone_scenario(
                    CapstoneRequest(
                        request_id="capstone-timeout",
                        thread_id="thread-capstone-timeout",
                        user_id="learner",
                        objective="研究超时必须阻止正式发布",
                        report_path="reports/timeout.md",
                    ),
                    workspace_root=directory,
                    subagent_executor=executor,
                )
            )

            self.assertEqual(result.status, "quality_rejected")
            self.assertEqual(result.subagent_statuses, ("timed_out", "completed"))
            self.assertFalse(result.checkpoint_reopened)
            self.assertIsNone(result.artifact_path)
            self.assertEqual(result.effect_count, 0)
            self.assertFalse(result.evaluation.results[0].passed)


if __name__ == "__main__":
    unittest.main()
