"""可执行的 Mini DeerFlow 离线结果/轨迹/预算评测示例。"""

from __future__ import annotations

import argparse
import os

from mini_deerflow.app import build_application
from mini_deerflow.evals import (
    EvaluationCase,
    EvaluationDataset,
    evaluate_dataset,
    observation_from_agent_state,
    run_langsmith_offline,
    run_langsmith_online,
)
from mini_deerflow.runtime import RunDescriptor


def build_course_dataset() -> EvaluationDataset:
    """课程内置的小型回归集；真实项目应把案例迁到版本化数据文件。"""

    return EvaluationDataset(
        name="mini-deerflow-course",
        version="2026-07-13",
        cases=(
            EvaluationCase(
                case_id="persistence-with-source",
                prompt="解释 LangGraph persistence 并给出引用",
                required_terms=("引用",),
                forbidden_terms=("无法验证",),
                expected_trajectory=("model", "search_knowledge", "model"),
                forbidden_trajectory=("write_workspace_file",),
                max_model_calls=2,
                max_tool_calls=1,
                tags=("retrieval", "critical"),
            ),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="运行不访问外部模型的 Mini DeerFlow 评测",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--langsmith-local",
        action="store_true",
        help="额外走 LangSmith 内存 Example/evaluator；仍不上传结果",
    )
    mode.add_argument(
        "--langsmith-online-dataset",
        metavar="DATASET_NAME",
        help="对已存在的远程 Dataset 运行并上传 experiment",
    )
    parser.add_argument(
        "--experiment-prefix",
        default="mini-deerflow-manual",
        help="在线 experiment 名称前缀",
    )
    parser.add_argument(
        "--confirm-upload",
        action="store_true",
        help="确认本次命令会向 LangSmith 写入 experiment/trace",
    )
    args = parser.parse_args()
    application = build_application()
    dataset = build_course_dataset()

    def target(case: EvaluationCase):
        state = application.invoke(
            case.prompt,
            run=RunDescriptor.create(
                thread_id=f"eval-{case.case_id}",
                request_id=f"eval-{case.case_id}",
                user_id="offline-evaluator",
            ),
        )
        return observation_from_agent_state(state)

    if args.langsmith_local:
        result = run_langsmith_offline(dataset, target)
        print(result.model_dump_json(indent=2))
        return
    if args.langsmith_online_dataset:
        if not args.confirm_upload:
            parser.error("在线评测必须同时提供 --confirm-upload")
        if not os.getenv("LANGSMITH_API_KEY"):
            parser.error("在线评测需要 LANGSMITH_API_KEY")
        from langsmith import Client  # noqa: PLC0415

        result = run_langsmith_online(
            args.langsmith_online_dataset,
            target,
            client=Client(),
            experiment_prefix=args.experiment_prefix,
        )
        print(result.model_dump_json(indent=2))
        return
    if args.confirm_upload:
        parser.error("--confirm-upload 只能与 --langsmith-online-dataset 一起使用")
    report = evaluate_dataset(dataset, target)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
