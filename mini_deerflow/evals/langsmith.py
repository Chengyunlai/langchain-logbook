"""当前 LangSmith API 的本地适配；默认不上传、不读取远程数据集。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import NAMESPACE_URL, uuid5
import warnings

from langsmith import tracing_context
from langsmith.schemas import Example
from pydantic import BaseModel, ConfigDict, Field

from mini_deerflow.evals.contracts import (
    AgentObservation,
    EvaluationCase,
    EvaluationDataset,
    EvaluationReport,
)
from mini_deerflow.evals.offline import EvaluationTarget, evaluate_case, evaluate_dataset


class LangSmithFeedback(BaseModel):
    """从 vendor result 提取出的稳定反馈投影。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    key: str
    score: float = Field(ge=0, le=1)
    comment: str | None = None


class LangSmithOfflineEvaluation(BaseModel):
    """同时保留本地门禁报告与 LangSmith evaluator 反馈。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report: EvaluationReport
    row_count: int = Field(ge=0)
    feedback: tuple[LangSmithFeedback, ...]


class LangSmithDatasetSync(BaseModel):
    """一次显式远程同步的可审计摘要。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_name: str
    dataset_id: str
    example_count: int = Field(ge=0)


class LangSmithOnlineEvaluation(BaseModel):
    """显式上传的在线 experiment 摘要，不泄漏完整 vendor result。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_name: str
    experiment_name: str
    row_count: int = Field(ge=0)
    url: str | None = None


class LangSmithDatasetAdapter:
    """远程数据集写入边界；构造或导入本模块不会触发网络。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    def sync(self, dataset: EvaluationDataset) -> LangSmithDatasetSync:
        """创建/读取版本化数据集，并批量写入确定 ID 的案例。"""

        remote_name = f"{dataset.name}:{dataset.version}"
        if self._client.has_dataset(dataset_name=remote_name):
            remote = self._client.read_dataset(dataset_name=remote_name)
        else:
            remote = self._client.create_dataset(
                remote_name,
                description="Mini DeerFlow 版本化 Agent 评测集",
                metadata={"version": dataset.version, "source": "local-markdown-course"},
            )
        dataset_id = str(remote.id)
        examples = [
            {
                "id": example.id,
                "inputs": example.inputs,
                "outputs": example.outputs,
                "metadata": example.metadata,
            }
            for example in to_langsmith_examples(dataset)
        ]
        self._client.create_examples(dataset_id=dataset_id, examples=examples)
        return LangSmithDatasetSync(
            dataset_name=remote_name,
            dataset_id=dataset_id,
            example_count=len(examples),
        )


def to_langsmith_examples(dataset: EvaluationDataset) -> tuple[Example, ...]:
    """把版本化本地案例投影为确定 ID 的内存 Example。"""

    return tuple(
        Example(
            id=uuid5(
                NAMESPACE_URL,
                (
                    "langchain-logbook://evaluation/"
                    f"{dataset.name}/{dataset.version}/{case.case_id}"
                ),
            ),
            inputs={"case_id": case.case_id, "prompt": case.prompt},
            outputs={"case": case.model_dump(mode="json")},
            metadata={
                "dataset_name": dataset.name,
                "dataset_version": dataset.version,
                "tags": list(case.tags),
            },
        )
        for case in dataset.cases
    )


def _case_from_example(example: Example) -> EvaluationCase:
    if example.outputs is None or "case" not in example.outputs:
        raise ValueError("LangSmith Example.outputs.case 缺失")
    return EvaluationCase.model_validate(example.outputs["case"])


def _observation_from_run(run: Any) -> AgentObservation:
    if run.outputs is None:
        raise ValueError("被评 target 没有返回 outputs")
    return AgentObservation.model_validate(run.outputs)


def _metric_evaluator(key: str):
    def evaluator(run: Any, example: Example) -> dict[str, object]:
        result = evaluate_case(
            _case_from_example(example),
            _observation_from_run(run),
        )
        metric = next(item for item in result.metrics if item.key == key)
        return {
            "key": metric.key,
            "score": metric.score,
            "comment": metric.explanation,
            "metadata": metric.details,
        }

    evaluator.__name__ = f"mini_deerflow_{key}_evaluator"
    return evaluator


def _extract_feedback(rows: Sequence[dict[str, Any]]) -> tuple[LangSmithFeedback, ...]:
    feedback: list[LangSmithFeedback] = []
    for row in rows:
        case_id = str(row["example"].inputs["case_id"])
        for result in row["evaluation_results"]["results"]:
            feedback.append(
                LangSmithFeedback(
                    case_id=case_id,
                    key=result.key,
                    score=float(result.score),
                    comment=result.comment,
                )
            )
    return tuple(feedback)


def run_langsmith_offline(
    dataset: EvaluationDataset,
    target: EvaluationTarget,
) -> LangSmithOfflineEvaluation:
    """在内存 Example 上运行当前 LangSmith evaluator，明确禁止上传。"""

    cases = {case.case_id: case for case in dataset.cases}
    observations: dict[str, AgentObservation] = {}

    def invoke(inputs: dict[str, Any]) -> dict[str, Any]:
        case_id = str(inputs["case_id"])
        # evaluate() 会为每条 target run 建自己的本地 tracing context；因此
        # 还需在真正业务调用的最内层再次关闭，覆盖环境自动 tracing。
        with tracing_context(enabled=False):
            observation = target(cases[case_id])
        observations[case_id] = observation
        return observation.model_dump(mode="json")

    # LangSmith 0.10.x 把 upload_results=False 标为 beta；这里有意使用它来
    # 保证默认评测不上传，并把 beta 边界固定在这一处适配器内。
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="'upload_results' parameter is in beta.",
        )
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            module=r"langsmith\.evaluation\._key_extraction",
        )
        # 延迟导入把 vendor 0.10.x 的 Python 3.14 deprecation warning
        # 限制在 adapter 内，普通领域评测导入不受影响。
        from langsmith import evaluate  # noqa: PLC0415

        # upload_results=False 管实验上传；enabled=False 还要覆盖被评
        # LangGraph/LCEL 的自动 tracing。二者缺一都不能叫“无网络门禁”。
        with tracing_context(enabled=False):
            experiment = evaluate(
                invoke,
                data=to_langsmith_examples(dataset),
                evaluators=[
                    _metric_evaluator("outcome"),
                    _metric_evaluator("trajectory"),
                    _metric_evaluator("budget"),
                ],
                experiment_prefix=(
                    f"{dataset.name}-{dataset.version}-offline"
                ),
                upload_results=False,
                max_concurrency=0,
                blocking=True,
            )
    rows = list(experiment)
    report = evaluate_dataset(dataset, lambda case: observations[case.case_id])
    return LangSmithOfflineEvaluation(
        report=report,
        row_count=len(rows),
        feedback=_extract_feedback(rows),
    )


def run_langsmith_online(
    dataset_name: str,
    target: EvaluationTarget,
    *,
    client: Any,
    experiment_prefix: str,
) -> LangSmithOnlineEvaluation:
    """对一个已存在远程 Dataset 运行并上传 experiment。

    该函数没有默认 Client 或默认 Dataset；调用者必须显式提供三者，因而
    不会在普通 import、pytest 或离线 CLI 中意外产生外部写入。
    """

    if not dataset_name.strip():
        raise ValueError("在线评测必须显式提供远程 dataset_name")
    if not experiment_prefix.strip():
        raise ValueError("在线评测必须显式提供 experiment_prefix")

    def invoke(inputs: dict[str, Any]) -> dict[str, Any]:
        case = EvaluationCase(
            case_id=str(inputs["case_id"]),
            prompt=str(inputs["prompt"]),
        )
        return target(case).model_dump(mode="json")

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            module=r"langsmith\.evaluation\._key_extraction",
        )
        from langsmith import evaluate  # noqa: PLC0415

        experiment = evaluate(
            invoke,
            data=dataset_name,
            evaluators=[
                _metric_evaluator("outcome"),
                _metric_evaluator("trajectory"),
                _metric_evaluator("budget"),
            ],
            experiment_prefix=experiment_prefix,
            client=client,
            upload_results=True,
            max_concurrency=0,
            blocking=True,
        )
    rows = list(experiment)
    return LangSmithOnlineEvaluation(
        dataset_name=dataset_name,
        experiment_name=str(experiment.experiment_name),
        row_count=len(rows),
        url=str(experiment.url) if experiment.url else None,
    )


__all__ = [
    "LangSmithDatasetAdapter",
    "LangSmithDatasetSync",
    "LangSmithFeedback",
    "LangSmithOfflineEvaluation",
    "LangSmithOnlineEvaluation",
    "run_langsmith_offline",
    "run_langsmith_online",
    "to_langsmith_examples",
]
