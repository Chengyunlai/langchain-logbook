"""贯穿课程的结构化业务契约。"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, ValidationError, field_validator


# region tutorial:02-domain-schemas
class ResearchRequest(BaseModel):
    """从自然语言需求提取出的可执行研究请求。"""

    question: str = Field(min_length=1)
    deliverable: str = Field(min_length=1)
    max_sources: int = Field(default=5, ge=1, le=20)


class StructuredFailure(BaseModel):
    """拒答和不可修复验证错误的显式结果。"""

    kind: Literal["refusal", "validation_error"]
    message: str

    @classmethod
    def refused(cls, message: str) -> StructuredFailure:
        return cls(kind="refusal", message=message)

    @classmethod
    def validation_error(cls, error: ValidationError) -> StructuredFailure:
        return cls(kind="validation_error", message=str(error))


def validate_research_request(payload: object) -> ResearchRequest | StructuredFailure:
    """把不可修复的 payload 验证错误转成调用方可穷尽处理的结果。"""

    try:
        return ResearchRequest.model_validate(payload)
    except ValidationError as error:
        return StructuredFailure.validation_error(error)


class PlanStep(BaseModel):
    """一个可被后续 Graph 节点或 Subagent 执行的计划步骤。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    instruction: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)


class TaskPlan(BaseModel):
    """模型输出进入业务代码前必须满足的计划契约。"""

    schema_version: Literal[1] = 1
    objective: str = Field(min_length=1)
    steps: list[PlanStep] = Field(min_length=1)


class ArtifactRef(BaseModel):
    """工作区内产物引用；路径不能逃出未来的 Sandbox 根目录。"""

    path: str = Field(min_length=1, max_length=512)
    media_type: str = Field(max_length=128, pattern=r"^[^/\s]+/[^/\s]+$")

    @field_validator("path")
    @classmethod
    def path_must_stay_in_workspace(cls, value: str) -> str:
        candidate = PurePosixPath(value)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValueError("artifact path 必须是工作区内的相对路径")
        return value


SubagentStatus: TypeAlias = Literal[
    "completed",
    "failed",
    "timed_out",
    "output_too_large",
    "rejected",
]


class SubagentResult(BaseModel):
    """Subagent 成功与失败共享的稳定返回形状。"""

    task_id: str | None = None
    agent_name: str
    status: SubagentStatus
    summary: str = ""
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    error: str | None = Field(default=None, max_length=500)
    output_chars: int = Field(default=0, ge=0)
    output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    truncated: bool = False

    @classmethod
    def failed(
        cls,
        agent_name: str,
        error: str,
        *,
        task_id: str | None = None,
    ) -> SubagentResult:
        bounded_error = error if len(error) <= 500 else error[:497] + "..."
        return cls(
            task_id=task_id,
            agent_name=agent_name,
            status="failed",
            error=bounded_error,
        )
# endregion tutorial:02-domain-schemas


__all__ = [
    "ArtifactRef",
    "PlanStep",
    "ResearchRequest",
    "StructuredFailure",
    "SubagentResult",
    "SubagentStatus",
    "TaskPlan",
    "validate_research_request",
]
