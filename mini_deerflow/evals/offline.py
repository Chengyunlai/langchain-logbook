"""确定性结果、轨迹、预算和回归评测；默认不访问外部服务。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from mini_deerflow.evals.contracts import (
    AgentObservation,
    CaseEvaluation,
    EvaluationCase,
    EvaluationDataset,
    EvaluationReport,
    MetricEvaluation,
    RegressionComparison,
    RegressionPolicy,
    match_text_constraints,
)


EvaluationTarget = Callable[[EvaluationCase], AgentObservation]


def _contains_ordered_subsequence(
    expected: Sequence[str],
    observed: Sequence[str],
) -> bool:
    if not expected:
        return True
    expected_index = 0
    for step in observed:
        if step == expected[expected_index]:
            expected_index += 1
            if expected_index == len(expected):
                return True
    return False


def _outcome_metric(
    case: EvaluationCase,
    observation: AgentObservation,
) -> MetricEvaluation:
    _, missing, present_forbidden = match_text_constraints(case, observation.output)
    passed = not missing and not present_forbidden
    return MetricEvaluation(
        key="outcome",
        passed=passed,
        score=1.0 if passed else 0.0,
        explanation=(
            "结果满足必需/禁止文本约束"
            if passed
            else "结果缺少必需术语或包含禁止文本"
        ),
        details={
            "missing_terms": list(missing),
            "present_forbidden_terms": list(present_forbidden),
        },
    )


def _trajectory_metric(
    case: EvaluationCase,
    observation: AgentObservation,
) -> MetricEvaluation:
    if case.trajectory_match == "exact":
        expected_matches = observation.trajectory == case.expected_trajectory
    else:
        expected_matches = _contains_ordered_subsequence(
            case.expected_trajectory,
            observation.trajectory,
        )
    forbidden = tuple(
        step for step in case.forbidden_trajectory if step in observation.trajectory
    )
    passed = expected_matches and not forbidden
    return MetricEvaluation(
        key="trajectory",
        passed=passed,
        score=1.0 if passed else 0.0,
        explanation=(
            "执行轨迹满足顺序与禁止步骤约束"
            if passed
            else "执行轨迹缺少期望顺序或触发禁止步骤"
        ),
        details={
            "match": case.trajectory_match,
            "expected": list(case.expected_trajectory),
            "observed": list(observation.trajectory),
            "forbidden_observed": list(forbidden),
        },
    )


def _budget_metric(
    case: EvaluationCase,
    observation: AgentObservation,
) -> MetricEvaluation:
    limits = {
        "model_calls": case.max_model_calls,
        "tool_calls": case.max_tool_calls,
        "total_tokens": case.max_total_tokens,
    }
    observed = {
        "model_calls": observation.model_calls,
        "tool_calls": observation.tool_calls,
        "total_tokens": observation.total_tokens,
    }
    exceeded = {
        key: {"observed": observed[key], "limit": limit}
        for key, limit in limits.items()
        if limit is not None and observed[key] > limit
    }
    passed = not exceeded
    return MetricEvaluation(
        key="budget",
        passed=passed,
        score=1.0 if passed else 0.0,
        explanation="资源预算内" if passed else "模型、工具或 token 预算超限",
        details={"exceeded": exceeded},
    )


def evaluate_case(
    case: EvaluationCase,
    observation: AgentObservation,
) -> CaseEvaluation:
    metrics = (
        _outcome_metric(case, observation),
        _trajectory_metric(case, observation),
        _budget_metric(case, observation),
    )
    return CaseEvaluation(
        case_id=case.case_id,
        passed=all(metric.passed for metric in metrics),
        metrics=metrics,
    )


def evaluate_dataset(
    dataset: EvaluationDataset,
    target: EvaluationTarget,
) -> EvaluationReport:
    return EvaluationReport(
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        results=tuple(
            evaluate_case(case, target(case))
            for case in dataset.cases
        ),
    )


def compare_reports(
    baseline: EvaluationReport,
    candidate: EvaluationReport,
    *,
    policy: RegressionPolicy,
) -> RegressionComparison:
    if baseline.dataset_name != candidate.dataset_name:
        raise ValueError("baseline/candidate 必须来自同一 dataset")
    baseline_status = {result.case_id: result.passed for result in baseline.results}
    candidate_status = {result.case_id: result.passed for result in candidate.results}
    if baseline_status.keys() != candidate_status.keys():
        raise ValueError("baseline/candidate case 集合必须一致")
    drop = max(0.0, baseline.pass_rate - candidate.pass_rate)
    new_failures = tuple(
        case_id
        for case_id in baseline_status
        if baseline_status[case_id] and not candidate_status[case_id]
    )
    improvements = tuple(
        case_id
        for case_id in baseline_status
        if not baseline_status[case_id] and candidate_status[case_id]
    )
    failed_rules: list[str] = []
    if candidate.pass_rate < policy.min_pass_rate:
        failed_rules.append("min_pass_rate")
    if drop > policy.max_pass_rate_drop:
        failed_rules.append("max_pass_rate_drop")
    if policy.block_new_failures and new_failures:
        failed_rules.append("new_failures")
    return RegressionComparison(
        passed=not failed_rules,
        baseline_pass_rate=baseline.pass_rate,
        candidate_pass_rate=candidate.pass_rate,
        pass_rate_drop=drop,
        new_failures=new_failures,
        improvements=improvements,
        failed_rules=tuple(failed_rules),
    )


__all__ = [
    "EvaluationTarget",
    "compare_reports",
    "evaluate_case",
    "evaluate_dataset",
]
