"""离线评测领域契约；与 LangSmith transport 和业务 Agent 解耦。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from mini_deerflow.streaming import JSONValue


class EvaluationCase(BaseModel):
    """一个可版本化输入，以及结果、轨迹和预算期望。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$")
    prompt: str = Field(min_length=1)
    required_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    expected_trajectory: tuple[str, ...] = ()
    forbidden_trajectory: tuple[str, ...] = ()
    trajectory_match: Literal["exact", "ordered_subsequence"] = (
        "ordered_subsequence"
    )
    max_model_calls: int | None = Field(default=None, ge=0)
    max_tool_calls: int | None = Field(default=None, ge=0)
    max_total_tokens: int | None = Field(default=None, ge=0)
    tags: tuple[str, ...] = ()


class AgentObservation(BaseModel):
    """被评 Agent 的稳定投影；不把 provider trace 对象带入 evaluator。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    output: str
    trajectory: tuple[str, ...] = ()
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class EvaluationDataset(BaseModel):
    """本地、可版本化、可同步到在线平台的评测集。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=80)
    cases: tuple[EvaluationCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_case_ids(self) -> "EvaluationDataset":
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("EvaluationDataset.case_id 必须唯一")
        return self


class MetricEvaluation(BaseModel):
    """一个可解释 metric；score 便于平台聚合，passed 用于 CI。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    passed: bool
    score: float = Field(ge=0, le=1)
    explanation: str
    details: dict[str, JSONValue] = Field(default_factory=dict)


class CaseEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    passed: bool
    metrics: tuple[MetricEvaluation, ...]


class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_name: str
    dataset_version: str
    results: tuple[CaseEvaluation, ...]

    @computed_field
    @property
    def pass_rate(self) -> float:
        return sum(result.passed for result in self.results) / len(self.results)


class RegressionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_pass_rate: float = Field(default=1.0, ge=0, le=1)
    max_pass_rate_drop: float = Field(default=0.0, ge=0, le=1)
    block_new_failures: bool = True


class RegressionComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    baseline_pass_rate: float
    candidate_pass_rate: float
    pass_rate_drop: float
    new_failures: tuple[str, ...]
    improvements: tuple[str, ...]
    failed_rules: tuple[str, ...]


class EvaluationResult(BaseModel):
    """任务 11 工程骨架保留的必需术语兼容投影。

    新评测代码应使用 ``CaseEvaluation``；这个窄接口让早期章节无需提前
    引入 outcome/trajectory/budget 三指标。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    passed: bool
    matched_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]


def match_text_constraints(
    case: EvaluationCase,
    output: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """共享必需/禁止文本匹配，避免 smoke 与完整 evaluator 规则漂移。"""

    matched = tuple(term for term in case.required_terms if term in output)
    missing = tuple(term for term in case.required_terms if term not in output)
    present_forbidden = tuple(
        term for term in case.forbidden_terms if term in output
    )
    return matched, missing, present_forbidden


def evaluate_required_terms(case: EvaluationCase, output: str) -> EvaluationResult:
    """早期章节兼容 smoke evaluator；完整评测请使用 ``evaluate_case``。"""

    matched, missing, present_forbidden = match_text_constraints(case, output)
    return EvaluationResult(
        case_id=case.case_id,
        passed=not missing and not present_forbidden,
        matched_terms=matched,
        missing_terms=missing,
    )


__all__ = [
    "AgentObservation",
    "CaseEvaluation",
    "EvaluationCase",
    "EvaluationDataset",
    "EvaluationReport",
    "EvaluationResult",
    "MetricEvaluation",
    "RegressionComparison",
    "RegressionPolicy",
    "evaluate_required_terms",
    "match_text_constraints",
]
