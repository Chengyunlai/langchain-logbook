from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage
from pydantic import ValidationError

from mini_deerflow.models import create_offline_model
from mini_deerflow.schemas import (
    ArtifactRef,
    PlanStep,
    ResearchRequest,
    StructuredFailure,
    SubagentResult,
    TaskPlan,
    validate_research_request,
)


class ProjectSchemaTests(unittest.TestCase):
    def test_model_structured_output_returns_a_research_request(self) -> None:
        model = create_offline_model(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ResearchRequest",
                            "args": {
                                "question": "LangGraph 如何恢复长任务？",
                                "deliverable": "带引用的中文说明",
                                "max_sources": 4,
                            },
                            "id": "structured-1",
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        )

        result = model.with_structured_output(ResearchRequest).invoke("整理研究请求")

        self.assertIsInstance(result, ResearchRequest)
        self.assertEqual(result.max_sources, 4)

    def test_refusal_and_unrepairable_validation_are_explicit_results(self) -> None:
        refusal = StructuredFailure.refused("请求涉及未授权数据")
        invalid = validate_research_request(
            {"question": "", "deliverable": "报告", "max_sources": 0}
        )

        self.assertEqual(refusal.kind, "refusal")
        self.assertIsInstance(invalid, StructuredFailure)
        self.assertEqual(invalid.kind, "validation_error")

    def test_task_plan_has_an_explicit_version_and_ordered_steps(self) -> None:
        plan = TaskPlan(
            objective="解释 LangGraph durable execution",
            steps=[
                PlanStep(id="research", instruction="检索官方资料"),
                PlanStep(id="write", instruction="生成中文说明", depends_on=["research"]),
            ],
        )

        self.assertEqual(plan.schema_version, 1)
        self.assertEqual(plan.steps[1].depends_on, ["research"])

    def test_invalid_artifact_path_is_rejected_at_the_boundary(self) -> None:
        with self.assertRaises(ValidationError):
            ArtifactRef(path="../secret.txt", media_type="text/plain")

    def test_subagent_failure_is_data_not_a_missing_field(self) -> None:
        result = SubagentResult.failed("research", "timeout")

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "timeout")
        self.assertEqual(result.artifacts, [])


if __name__ == "__main__":
    unittest.main()
