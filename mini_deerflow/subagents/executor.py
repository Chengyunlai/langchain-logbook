"""受控并发、上下文隔离和结构化失败的 Subagent 执行器。"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
import hashlib
import json
from threading import Lock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mini_deerflow.schemas import SubagentResult, SubagentStatus
from mini_deerflow.state import UnsafeStateError, assert_checkpoint_safe
from mini_deerflow.subagents.contracts import SubagentInvocation, SubagentRequest
from mini_deerflow.subagents.registry import SubagentRegistry


class DelegationRecord(BaseModel):
    """Ledger 只保存有界摘要和 digest，不复制完整 Subagent 上下文。"""

    model_config = ConfigDict(frozen=True)

    task_id: str
    agent_name: str
    status: SubagentStatus
    context_keys: tuple[str, ...] = ()
    summary_preview: str = Field(default="", max_length=160)
    output_chars: int = Field(default=0, ge=0)
    output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    error_code: str | None = Field(default=None, max_length=80)


class DelegationLedger:
    """线程安全的教学 ledger；生产实现应替换为持久化 repository。"""

    def __init__(self) -> None:
        self._records: list[DelegationRecord] = []
        self._lock = Lock()

    def record(
        self,
        result: SubagentResult,
        *,
        context_keys: Sequence[str],
    ) -> None:
        record = DelegationRecord(
            task_id=result.task_id or "untracked",
            agent_name=result.agent_name,
            status=result.status,
            context_keys=tuple(sorted(context_keys)),
            summary_preview=result.summary[:160],
            output_chars=result.output_chars,
            output_sha256=result.output_sha256,
            error_code=result.status if result.error else None,
        )
        with self._lock:
            self._records.append(record)

    def list_records(self) -> tuple[DelegationRecord, ...]:
        with self._lock:
            return tuple(self._records)


# region tutorial:11-subagent-executor
class SubagentExecutor:
    """把 task 请求变成隔离 invocation，并把所有失败降为结构化结果。"""

    def __init__(
        self,
        registry: SubagentRegistry,
        *,
        max_concurrency: int = 2,
        timeout_seconds: float = 5.0,
        ledger: DelegationLedger | None = None,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency 必须大于 0")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须大于 0")
        self.registry = registry
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds
        self.ledger = ledger or DelegationLedger()
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def dispatch(
        self,
        request: SubagentRequest,
        *,
        parent_context: Mapping[str, Any] | None = None,
    ) -> SubagentResult:
        try:
            spec = self.registry.resolve(request.agent_name)
        except KeyError as error:
            result = SubagentResult.failed(
                request.agent_name,
                str(error),
                task_id=request.task_id,
            )
            self.ledger.record(result, context_keys=())
            return result

        source_context = parent_context or {}
        isolated_context = {
            key: source_context[key]
            for key in spec.allowed_context_fields
            if key in source_context
        }
        try:
            assert_checkpoint_safe(isolated_context, path="subagent.context")
        except UnsafeStateError as error:
            result = SubagentResult(
                task_id=request.task_id,
                agent_name=request.agent_name,
                status="rejected",
                error=str(error),
            )
            self.ledger.record(result, context_keys=())
            return result

        invocation = SubagentInvocation(
            task_id=request.task_id,
            agent_name=request.agent_name,
            description=request.description,
            prompt=request.prompt,
            context=isolated_context,
        )

        async with self._semaphore:
            try:
                output = await asyncio.wait_for(
                    spec.handler(invocation), timeout=self.timeout_seconds
                )
            except TimeoutError:
                result = SubagentResult(
                    task_id=request.task_id,
                    agent_name=request.agent_name,
                    status="timed_out",
                    error=f"subagent 超过 {self.timeout_seconds:g}s 执行预算",
                )
            except Exception as error:  # noqa: BLE001 - executor is the failure boundary
                result = SubagentResult.failed(
                    request.agent_name,
                    f"{type(error).__name__}: subagent handler failed",
                    task_id=request.task_id,
                )
            else:
                full_summary = output.summary
                digest_payload = json.dumps(
                    {
                        "summary": full_summary,
                        "artifacts": [
                            artifact.model_dump(mode="json") for artifact in output.artifacts
                        ],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                digest = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()
                summary_is_large = len(full_summary) > spec.max_output_chars
                artifacts_are_large = len(output.artifacts) > spec.max_artifacts
                bounded_artifacts = output.artifacts[: spec.max_artifacts]
                if summary_is_large or artifacts_are_large:
                    violations: list[str] = []
                    if summary_is_large:
                        violations.append(
                            f"输出 {len(full_summary)} 字符，超过 {spec.max_output_chars} 字符预算"
                        )
                    if artifacts_are_large:
                        violations.append(
                            f"artifact {len(output.artifacts)} 个，超过 {spec.max_artifacts} 个预算"
                        )
                    result = SubagentResult(
                        task_id=request.task_id,
                        agent_name=request.agent_name,
                        status="output_too_large",
                        summary=full_summary[: spec.max_output_chars],
                        artifacts=bounded_artifacts,
                        error="subagent " + "；".join(violations),
                        output_chars=len(full_summary),
                        output_sha256=digest,
                        truncated=True,
                    )
                else:
                    result = SubagentResult(
                        task_id=request.task_id,
                        agent_name=request.agent_name,
                        status="completed",
                        summary=full_summary,
                        artifacts=output.artifacts,
                        output_chars=len(full_summary),
                        output_sha256=digest,
                    )

        self.ledger.record(result, context_keys=tuple(isolated_context))
        return result

    async def dispatch_many(
        self,
        requests: Sequence[SubagentRequest],
        *,
        parent_context: Mapping[str, Any] | None = None,
    ) -> list[SubagentResult]:
        """并发提交但按请求顺序返回；单个失败不会取消同批其他任务。"""

        return list(
            await asyncio.gather(
                *(
                    self.dispatch(request, parent_context=parent_context)
                    for request in requests
                )
            )
        )
# endregion tutorial:11-subagent-executor


__all__ = ["DelegationLedger", "DelegationRecord", "SubagentExecutor"]
