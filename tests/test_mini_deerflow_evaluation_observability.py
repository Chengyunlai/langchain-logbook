from __future__ import annotations

import ast
from contextlib import contextmanager
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from langsmith import tracing_context as actual_tracing_context

from mini_deerflow.evals import (
    AgentObservation,
    EvaluationCase,
    EvaluationDataset,
    LangSmithDatasetAdapter,
    RegressionPolicy,
    compare_reports,
    evaluate_dataset,
    observation_from_agent_state,
    run_langsmith_offline,
    run_langsmith_online,
    to_langsmith_examples,
)
from mini_deerflow.app import build_application
from mini_deerflow.observability import (
    DuplicateTraceRootError,
    LangSmithObservability,
    LangSmithTracingConfig,
)
from mini_deerflow.runtime import RunDescriptor


class OfflineEvaluationTests(unittest.TestCase):
    def test_real_mini_deerflow_state_becomes_an_evaluable_observation(self) -> None:
        application = build_application()
        state = application.invoke(
            "解释 LangGraph persistence 并给出引用",
            run=RunDescriptor.create(
                thread_id="thread-eval-real",
                request_id="request-eval-real",
                user_id="learner",
            ),
        )
        dataset = EvaluationDataset(
            name="mini-deerflow-real",
            version="v1",
            cases=(
                EvaluationCase(
                    case_id="real-tool-loop",
                    prompt="解释 LangGraph persistence 并给出引用",
                    required_terms=("引用",),
                    expected_trajectory=("model", "search_knowledge", "model"),
                    max_model_calls=2,
                    max_tool_calls=1,
                ),
            ),
        )

        observation = observation_from_agent_state(state)
        report = evaluate_dataset(dataset, lambda _case: observation)

        self.assertEqual(
            observation.trajectory,
            ("model", "search_knowledge", "model"),
        )
        self.assertEqual(observation.model_calls, 2)
        self.assertEqual(observation.tool_calls, 1)
        self.assertTrue(report.results[0].passed)

    def test_dataset_scores_outcome_trajectory_and_budget_with_explanations(self) -> None:
        dataset = EvaluationDataset(
            name="mini-deerflow-core",
            version="2026-07-13",
            cases=(
                EvaluationCase(
                    case_id="research-pass",
                    prompt="研究 LangGraph persistence",
                    required_terms=("引用", "checkpoint"),
                    forbidden_terms=("无法验证",),
                    expected_trajectory=("model", "search_knowledge", "model"),
                    forbidden_trajectory=("write_workspace_file",),
                    max_model_calls=2,
                    max_tool_calls=1,
                    max_total_tokens=300,
                ),
                EvaluationCase(
                    case_id="research-regression",
                    prompt="研究 interrupt",
                    required_terms=("interrupt", "resume"),
                    expected_trajectory=("model", "search_knowledge", "model"),
                    max_model_calls=2,
                    max_tool_calls=1,
                    max_total_tokens=300,
                ),
            ),
        )
        observations = {
            "research-pass": AgentObservation(
                output="结论包含 checkpoint，并给出官方引用。",
                trajectory=("model", "search_knowledge", "model"),
                model_calls=2,
                tool_calls=1,
                total_tokens=240,
            ),
            "research-regression": AgentObservation(
                output="只说明 interrupt。",
                trajectory=("model", "write_workspace_file", "model"),
                model_calls=3,
                tool_calls=1,
                total_tokens=420,
            ),
        }

        report = evaluate_dataset(dataset, lambda case: observations[case.case_id])

        self.assertEqual(report.dataset_name, "mini-deerflow-core")
        self.assertEqual(report.dataset_version, "2026-07-13")
        self.assertEqual(report.pass_rate, 0.5)
        self.assertTrue(report.results[0].passed)
        self.assertFalse(report.results[1].passed)
        metrics = {metric.key: metric for metric in report.results[1].metrics}
        self.assertFalse(metrics["outcome"].passed)
        self.assertIn("resume", metrics["outcome"].details["missing_terms"])
        self.assertFalse(metrics["trajectory"].passed)
        self.assertFalse(metrics["budget"].passed)
        self.assertIn("model_calls", metrics["budget"].details["exceeded"])
        self.assertIn("total_tokens", metrics["budget"].details["exceeded"])

    def test_regression_comparison_blocks_pass_rate_drop_and_new_case_failures(self) -> None:
        dataset = EvaluationDataset(
            name="regression-suite",
            version="v1",
            cases=(
                EvaluationCase(case_id="case-a", prompt="A", required_terms=("ok",)),
                EvaluationCase(case_id="case-b", prompt="B", required_terms=("ok",)),
            ),
        )
        baseline = evaluate_dataset(
            dataset,
            lambda _case: AgentObservation(output="ok"),
        )
        candidate = evaluate_dataset(
            dataset,
            lambda case: AgentObservation(
                output="bad" if case.case_id == "case-b" else "ok"
            ),
        )

        comparison = compare_reports(
            baseline,
            candidate,
            policy=RegressionPolicy(
                min_pass_rate=0.8,
                max_pass_rate_drop=0.05,
            ),
        )

        self.assertFalse(comparison.passed)
        self.assertEqual(comparison.pass_rate_drop, 0.5)
        self.assertEqual(comparison.new_failures, ("case-b",))
        self.assertEqual(comparison.improvements, ())
        self.assertIn("min_pass_rate", comparison.failed_rules)
        self.assertIn("max_pass_rate_drop", comparison.failed_rules)
        self.assertIn("new_failures", comparison.failed_rules)

    def test_langsmith_adapter_uses_in_memory_examples_without_uploading(self) -> None:
        dataset = EvaluationDataset(
            name="local-contracts",
            version="v1",
            cases=(
                EvaluationCase(
                    case_id="case-local",
                    prompt="解释 checkpoint",
                    required_terms=("checkpoint",),
                    expected_trajectory=("model",),
                    max_model_calls=1,
                ),
            ),
        )
        observations = {
            "case-local": AgentObservation(
                output="checkpoint 保存图状态。",
                trajectory=("model",),
                model_calls=1,
            )
        }

        examples = to_langsmith_examples(dataset)
        with patch(
            "mini_deerflow.evals.langsmith.tracing_context",
            wraps=actual_tracing_context,
        ) as local_tracing:
            result = run_langsmith_offline(
                dataset,
                lambda case: observations[case.case_id],
            )

        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].inputs["case_id"], "case-local")
        self.assertEqual(examples[0].outputs["case"]["required_terms"], ["checkpoint"])
        self.assertEqual(result.report.pass_rate, 1.0)
        self.assertEqual(local_tracing.call_count, 2)
        self.assertTrue(
            all(call.kwargs == {"enabled": False} for call in local_tracing.call_args_list)
        )
        self.assertEqual(result.row_count, 1)
        self.assertEqual(
            {(item.case_id, item.key, item.score) for item in result.feedback},
            {
                ("case-local", "outcome", 1.0),
                ("case-local", "trajectory", 1.0),
                ("case-local", "budget", 1.0),
            },
        )

    def test_online_dataset_sync_is_an_explicit_client_boundary(self) -> None:
        class FakeDataset:
            id = "dataset-123"

        class FakeClient:
            def __init__(self) -> None:
                self.created_dataset: dict[str, object] | None = None
                self.examples: list[dict[str, object]] = []

            def has_dataset(self, *, dataset_name: str) -> bool:
                self.checked_name = dataset_name
                return False

            def create_dataset(self, dataset_name: str, **kwargs):
                self.created_dataset = {"name": dataset_name, **kwargs}
                return FakeDataset()

            def create_examples(self, *, dataset_id: str, examples):
                self.created_examples_dataset_id = dataset_id
                self.examples = list(examples)
                return {"count": len(self.examples)}

        dataset = EvaluationDataset(
            name="lead-agent-contracts",
            version="v2",
            cases=(EvaluationCase(case_id="one", prompt="研究 interrupt"),),
        )
        client = FakeClient()

        result = LangSmithDatasetAdapter(client).sync(dataset)

        self.assertEqual(result.dataset_name, "lead-agent-contracts:v2")
        self.assertEqual(result.dataset_id, "dataset-123")
        self.assertEqual(result.example_count, 1)
        self.assertEqual(client.created_dataset["metadata"]["version"], "v2")
        self.assertEqual(client.examples[0]["inputs"]["case_id"], "one")
        self.assertIn("id", client.examples[0])

    def test_online_evaluation_explicitly_uploads_to_a_named_remote_dataset(self) -> None:
        class FakeExperiment:
            experiment_name = "lead-agent-online-123"
            url = "https://example.invalid/experiment/123"

            def __iter__(self):
                return iter([{"run": object()}])

        captured: dict[str, object] = {}

        def fake_evaluate(target, **kwargs):
            captured.update(kwargs)
            output = target({"case_id": "one", "prompt": "研究 interrupt"})
            self.assertEqual(output["output"], "interrupt 已说明")
            return FakeExperiment()

        client = object()
        with patch("langsmith.evaluate", fake_evaluate):
            result = run_langsmith_online(
                "lead-agent-contracts:v2",
                lambda _case: AgentObservation(output="interrupt 已说明"),
                client=client,
                experiment_prefix="release-candidate",
            )

        self.assertEqual(result.dataset_name, "lead-agent-contracts:v2")
        self.assertEqual(result.experiment_name, "lead-agent-online-123")
        self.assertEqual(result.row_count, 1)
        self.assertEqual(captured["data"], "lead-agent-contracts:v2")
        self.assertIs(captured["client"], client)
        self.assertTrue(captured["upload_results"])


class ObservabilityBoundaryTests(unittest.TestCase):
    def test_composition_root_observability_wraps_a_real_graph_invocation(self) -> None:
        calls: list[dict[str, object]] = []

        class RecordingObservability:
            def run(self, operation_name, operation, **kwargs):
                calls.append({"operation_name": operation_name, **kwargs})
                return operation()

        application = build_application(observability=RecordingObservability())
        result = application.invoke(
            "解释 persistence",
            run=RunDescriptor.create(
                thread_id="thread-observed",
                request_id="request-observed",
                user_id="learner-observed",
            ),
        )

        self.assertEqual(result["messages"][-1].content.startswith("离线工具循环"), True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["operation_name"], "mini-deerflow.invoke")
        self.assertEqual(calls[0]["correlation_id"], "request-observed")
        self.assertEqual(calls[0]["user_id"], "learner-observed")
        self.assertEqual(calls[0]["metadata"]["thread_id"], "thread-observed")

    def test_graph_owned_root_inherits_context_without_an_extra_trace_wrapper(self) -> None:
        events: list[tuple[str, object]] = []

        @contextmanager
        def fake_context(**kwargs):
            events.append(("context", kwargs))
            yield

        def forbidden_traceable(**_kwargs):
            raise AssertionError("Graph 已拥有 root span，不应再创建 wrapper")

        tracer = LangSmithObservability(
            LangSmithTracingConfig(
                enabled=False,
                project_name="local-quality",
                root_owner="graph",
                tags=("offline",),
            )
        )
        with (
            patch("mini_deerflow.observability.tracing_context", fake_context),
            patch("mini_deerflow.observability.traceable", forbidden_traceable),
        ):
            value = tracer.run(
                "lead-agent",
                lambda: "done",
                correlation_id="run-1",
                user_id="learner",
            )

        self.assertEqual(value, "done")
        context = events[0][1]
        self.assertEqual(context["project_name"], "local-quality")
        self.assertEqual(context["tags"], ["offline"])
        self.assertEqual(context["metadata"]["correlation_id"], "run-1")
        self.assertEqual(context["metadata"]["user_id"], "learner")

    def test_gateway_owned_root_wraps_once_and_rejects_a_second_root(self) -> None:
        wrapper_calls: list[dict[str, object]] = []

        @contextmanager
        def fake_context(**_kwargs):
            yield

        def fake_traceable(**kwargs):
            wrapper_calls.append(kwargs)

            def decorate(operation):
                def wrapped():
                    return operation()

                return wrapped

            return decorate

        tracer = LangSmithObservability(
            LangSmithTracingConfig(enabled=False, root_owner="gateway")
        )
        with (
            patch("mini_deerflow.observability.tracing_context", fake_context),
            patch("mini_deerflow.observability.traceable", fake_traceable),
        ):
            value = tracer.run(
                "api-request",
                lambda: 42,
                correlation_id="run-2",
                user_id="learner",
            )
            with self.assertRaises(DuplicateTraceRootError):
                tracer.run(
                    "api-request",
                    lambda: 42,
                    correlation_id="run-2",
                    user_id="learner",
                    operation_already_traced=True,
                )

        self.assertEqual(value, 42)
        self.assertEqual(len(wrapper_calls), 1)
        self.assertEqual(wrapper_calls[0]["name"], "api-request")
        self.assertEqual(wrapper_calls[0]["run_type"], "chain")


class CriticalRegressionManifestTests(unittest.TestCase):
    def test_every_critical_security_and_recovery_contract_maps_to_a_real_test(self) -> None:
        root = Path(__file__).resolve().parents[1]
        contracts = json.loads(
            (root / "quality" / "critical-regressions.json").read_text(
                encoding="utf-8"
            )
        )
        required_categories = {
            "prompt_injection",
            "tool_authorization",
            "path_traversal",
            "duplicate_effect",
            "token_budget",
            "durable_recovery",
        }

        self.assertTrue(required_categories.issubset(
            {contract["category"] for contract in contracts}
        ))
        self.assertTrue(all(contract["severity"] == "critical" for contract in contracts))
        for contract in contracts:
            relative_path, class_name, method_name = contract["test_nodeid"].split("::")
            test_path = root / relative_path
            tree = ast.parse(test_path.read_text(encoding="utf-8"))
            methods = {
                child.name
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == class_name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            self.assertIn(
                method_name,
                methods,
                msg=f"critical contract 映射已失效: {contract['id']}",
            )


if __name__ == "__main__":
    unittest.main()
