"""最终长任务实战：只编排 Mini DeerFlow 已有公共边界。"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import hashlib

from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mini_deerflow.app import build_application
from mini_deerflow.config import ApplicationSettings
from mini_deerflow.evals import (
    AgentObservation,
    EvaluationCase,
    EvaluationDataset,
    EvaluationReport,
    evaluate_dataset,
    observation_from_agent_state,
)
from mini_deerflow.graph import ApprovalDecision, create_approval_workflow
from mini_deerflow.persistence import SqliteEffectLedger, open_sqlite_checkpointer
from mini_deerflow.runtime import RunDescriptor
from mini_deerflow.subagents import SubagentExecutor, SubagentRequest


class CapstoneRequest(BaseModel):
    """长任务的稳定入口；身份和交付路径由应用验证。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$")
    thread_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$")
    user_id: str = Field(min_length=1, max_length=160)
    objective: str = Field(min_length=1, max_length=2_000)
    report_path: str = Field(min_length=1, max_length=240)

    @field_validator("report_path")
    @classmethod
    def report_path_must_stay_in_workspace(cls, value: str) -> str:
        candidate = PurePosixPath(value)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValueError("report_path 必须是工作区内的相对路径")
        return value


class CapstoneResult(BaseModel):
    """综合实战的可验证交付，而不是只返回一段聊天文本。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    thread_id: str
    status: str
    draft_path: str
    artifact_path: str | None = None
    subagent_statuses: tuple[str, ...]
    effect_status: str | None = None
    effect_count: int = Field(ge=0)
    checkpoint_reopened: bool
    evaluation: EvaluationReport


class PublishIntent(BaseModel):
    """审批与幂等 ledger 之间的受验证发布意图。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(min_length=1, max_length=240)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def path_must_stay_in_workspace(cls, value: str) -> str:
        candidate = PurePosixPath(value)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValueError("发布 path 必须是工作区内的相对路径")
        return value


def _capstone_dataset(
    request: CapstoneRequest,
    *,
    resume_decision: str,
    include_write: bool = True,
) -> EvaluationDataset:
    expected_trajectory = (
        "model",
        "search_knowledge",
        "model",
        "subagent:research",
        "subagent:coding",
        "interrupt:risk",
        f"resume:{resume_decision}",
    )
    if include_write:
        expected_trajectory = (*expected_trajectory, "write_workspace_file")
    return EvaluationDataset(
        name="mini-deerflow-capstone",
        version="2026-07-14",
        cases=(
            EvaluationCase(
                case_id=request.request_id,
                prompt=request.objective,
                required_terms=("引用", "研究摘要", "代码建议"),
                forbidden_terms=("specialist 未完成",),
                expected_trajectory=expected_trajectory,
                trajectory_match="exact",
                max_model_calls=6,
                max_tool_calls=3,
                tags=("capstone", "long-running", "critical"),
            ),
        ),
    )


def _draft_quality_dataset(request: CapstoneRequest) -> EvaluationDataset:
    """在审批和 effect intent 之前拒绝不完整的专家交付。"""

    return EvaluationDataset(
        name="mini-deerflow-capstone-draft-gate",
        version="2026-07-14",
        cases=(
            EvaluationCase(
                case_id=request.request_id,
                prompt=request.objective,
                required_terms=("引用", "研究摘要", "代码建议"),
                forbidden_terms=("specialist 未完成",),
                expected_trajectory=(
                    "model",
                    "search_knowledge",
                    "model",
                    "subagent:research",
                    "subagent:coding",
                ),
                trajectory_match="exact",
                max_model_calls=6,
                max_tool_calls=3,
                tags=("capstone", "draft-gate", "critical"),
            ),
        ),
    )


async def run_capstone_scenario(
    request: CapstoneRequest,
    *,
    workspace_root: str | Path,
    decision: ApprovalDecision | None = None,
    subagent_executor: SubagentExecutor | None = None,
) -> CapstoneResult:
    """运行研究、委派、草稿、跨重建审批、发布和评测闭环。"""

    settings = ApplicationSettings.offline(workspace_root=workspace_root)
    application = build_application(settings)
    descriptor = RunDescriptor.create(
        request_id=request.request_id,
        thread_id=request.thread_id,
        user_id=request.user_id,
    )

    # 真实 create_agent / LangGraph 路径：离线模型仍实际调用知识工具。
    lead_state = application.invoke(request.objective, run=descriptor)
    lead_observation = observation_from_agent_state(lead_state)

    sandbox = application.dependencies.sandbox_provider.acquire(
        request.thread_id,
        user_id=request.user_id,
    )
    executor = subagent_executor or SubagentExecutor(
        application.dependencies.subagent_registry,
        max_concurrency=settings.subagent_max_concurrency,
        timeout_seconds=settings.subagent_timeout_seconds,
        ledger=application.dependencies.delegation_ledger,
    )
    subagent_results = await executor.dispatch_many(
        [
            SubagentRequest(
                task_id=f"{request.request_id}-research",
                agent_name="research",
                description="检索并压缩证据",
                prompt=request.objective,
            ),
            SubagentRequest(
                task_id=f"{request.request_id}-coding",
                agent_name="coding",
                description="形成可测试实现建议",
                prompt=request.objective,
            ),
        ],
        parent_context={
            "locale": "zh-CN",
            "request_id": request.request_id,
            "sandbox_id": sandbox.sandbox_id,
        },
    )
    summaries = {
        result.agent_name: result.summary
        for result in subagent_results
        if result.status == "completed"
    }
    report_content = "\n".join(
        [
            f"# {request.objective}",
            "",
            "## Lead Agent 检索结论",
            lead_observation.output,
            "",
            "## 研究摘要",
            summaries.get("research", "研究 specialist 未完成"),
            "",
            "## 代码建议",
            summaries.get("coding", "coding specialist 未完成"),
            "",
            "## 引用",
            "- offline-docs（课程确定性知识 fixture）",
        ]
    )
    draft_relative = f"drafts/{request.request_id}.md"
    sandbox.write_text(draft_relative, report_content, media_type="text/markdown")

    persistence_root = Path(workspace_root) / ".mini-deerflow" / "capstone"
    checkpoint_path = persistence_root / "checkpoints.sqlite"
    draft_observation = AgentObservation(
        output=report_content,
        trajectory=(
            *lead_observation.trajectory,
            "subagent:research",
            "subagent:coding",
        ),
        model_calls=lead_observation.model_calls + 4,
        tool_calls=lead_observation.tool_calls + 2,
        total_tokens=lead_observation.total_tokens,
    )
    draft_evaluation = evaluate_dataset(
        _draft_quality_dataset(request),
        lambda _case: draft_observation,
    )
    if not draft_evaluation.results[0].passed:
        application.dependencies.sandbox_provider.release(sandbox.sandbox_id)
        return CapstoneResult(
            request_id=request.request_id,
            thread_id=request.thread_id,
            status="quality_rejected",
            draft_path=str(sandbox.workspace_path / draft_relative),
            artifact_path=None,
            subagent_statuses=tuple(result.status for result in subagent_results),
            effect_status=None,
            effect_count=0,
            checkpoint_reopened=False,
            evaluation=draft_evaluation,
        )

    effect_ledger = SqliteEffectLedger(persistence_root / "effects.sqlite")
    config = {"configurable": {"thread_id": request.thread_id}}
    content_sha256 = hashlib.sha256(report_content.encode("utf-8")).hexdigest()
    effect_payload = PublishIntent(
        path=request.report_path,
        content_sha256=content_sha256,
    ).model_dump(mode="json")

    # 第一个进程生命周期只负责运行到 interrupt。
    with open_sqlite_checkpointer(checkpoint_path) as checkpointer:
        approval = create_approval_workflow(
            checkpointer=checkpointer,
            effect_ledger=effect_ledger,
        )
        paused = approval.invoke(
            {
                "request_id": request.request_id,
                "action": "write_workspace_file",
                "payload": effect_payload,
                "review_stages": ["risk"],
            },
            config=config,
        )
        if not paused.get("__interrupt__"):
            raise RuntimeError("capstone 预期在发布报告前进入 durable interrupt")

    # 释放会话并重新打开 checkpointer，模拟服务重建而不是内存内继续。
    sandbox_id = sandbox.sandbox_id
    application.dependencies.sandbox_provider.release(sandbox_id)
    chosen_decision = decision or ApprovalDecision(decision="approve")
    if chosen_decision.decision == "edit":
        edited_intent = PublishIntent.model_validate(
            {
                **effect_payload,
                **(chosen_decision.edited_payload or {}),
            }
        )
        chosen_decision = chosen_decision.model_copy(
            update={"edited_payload": edited_intent.model_dump(mode="json")}
        )
    with open_sqlite_checkpointer(checkpoint_path) as checkpointer:
        restored_approval = create_approval_workflow(
            checkpointer=checkpointer,
            effect_ledger=effect_ledger,
        )
        approved_state = restored_approval.invoke(
            Command(resume=chosen_decision.model_dump(mode="json")),
            config=config,
        )

    restored_sandbox = application.dependencies.sandbox_provider.acquire(
        request.thread_id,
        user_id=request.user_id,
    )
    restored_report = restored_sandbox.read_text(draft_relative)
    artifact_path: str | None = None
    observed_trajectory = [
        *lead_observation.trajectory,
        "subagent:research",
        "subagent:coding",
        "interrupt:risk",
        f"resume:{chosen_decision.decision}",
    ]
    prepublish_observation = AgentObservation(
        output=restored_report,
        trajectory=tuple(observed_trajectory),
        model_calls=lead_observation.model_calls + 4,
        tool_calls=lead_observation.tool_calls + 2,
        total_tokens=lead_observation.total_tokens,
    )
    prepublish_evaluation = evaluate_dataset(
        _capstone_dataset(
            request,
            resume_decision=chosen_decision.decision,
            include_write=False,
        ),
        lambda _case: prepublish_observation,
    )
    prepublish_passed = prepublish_evaluation.results[0].passed
    if approved_state.get("status") == "completed" and prepublish_passed:
        approved_payload = approved_state.get("payload", {})
        publish_path = str(approved_payload.get("path", request.report_path))
        if approved_payload.get("content_sha256") != content_sha256:
            raise ValueError("审批后的 content_sha256 与持久化草稿不一致")
        write_result = restored_sandbox.write_text(
            publish_path,
            restored_report,
            media_type="text/markdown",
        )
        artifact_path = str(restored_sandbox.workspace_path / write_result.artifact.path)
        observed_trajectory.append("write_workspace_file")

    observation = AgentObservation(
        output=restored_report,
        trajectory=tuple(observed_trajectory),
        model_calls=lead_observation.model_calls + 4,
        tool_calls=lead_observation.tool_calls + 2,
        total_tokens=lead_observation.total_tokens,
    )
    evaluation = evaluate_dataset(
        _capstone_dataset(
            request,
            resume_decision=chosen_decision.decision,
            include_write=approved_state.get("status") == "completed",
        ),
        lambda _case: observation,
    )
    result_status = str(approved_state.get("status", "rejected"))
    if result_status == "completed" and not prepublish_passed:
        result_status = "quality_rejected"
    return CapstoneResult(
        request_id=request.request_id,
        thread_id=request.thread_id,
        status=result_status,
        draft_path=str(restored_sandbox.workspace_path / draft_relative),
        artifact_path=artifact_path,
        subagent_statuses=tuple(result.status for result in subagent_results),
        effect_status=approved_state.get("effect_status"),
        effect_count=effect_ledger.count(request.request_id),
        checkpoint_reopened=True,
        evaluation=evaluation,
    )


__all__ = [
    "CapstoneRequest",
    "CapstoneResult",
    "PublishIntent",
    "run_capstone_scenario",
]


def main() -> None:
    """运行可重复的本地综合实战；默认批准并发布报告。"""

    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="运行 Mini DeerFlow 最终长任务实战")
    parser.add_argument("--workspace-root", default=".capstone-demo")
    parser.add_argument(
        "--decision",
        choices=("approve", "reject"),
        default="approve",
    )
    args = parser.parse_args()
    request = CapstoneRequest(
        request_id="capstone-demo-001",
        thread_id="thread-capstone-demo-001",
        user_id="offline-learner",
        objective="研究 LangGraph persistence，并交付带引用的实现建议",
        report_path="reports/persistence.md",
    )
    result = asyncio.run(
        run_capstone_scenario(
            request,
            workspace_root=args.workspace_root,
            decision=ApprovalDecision(decision=args.decision),
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
