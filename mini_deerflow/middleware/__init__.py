"""Agent lifecycle governance for the Mini DeerFlow Lead Agent."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
import json
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ExtendedModelResponse,
    ModelCallLimitMiddleware,
    ModelRequest,
    ModelResponse,
    PIIMiddleware,
    SummarizationMiddleware,
    ToolCallRequest,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.types import Command

from mini_deerflow.context import RuntimeContext, safe_context_view
from mini_deerflow.schemas import ArtifactRef
from mini_deerflow.state import (
    MiddlewareTraceEvent,
    ThreadState,
    assert_checkpoint_safe,
)
from mini_deerflow.store import UserPreferenceRepository


# region tutorial:06-lifecycle-trace-middleware
class LifecycleTraceMiddleware(AgentMiddleware[ThreadState, RuntimeContext]):
    """Make before/after hook order observable through an append-only state field."""

    state_schema = ThreadState

    def __init__(self, label: str = "lead") -> None:
        self.label = label

    @property
    def name(self) -> str:
        return f"LifecycleTrace[{self.label}]"

    def before_model(
        self, state: ThreadState, runtime: Any
    ) -> dict[str, Any]:
        del state, runtime
        return {
            "middleware_trace": [
                MiddlewareTraceEvent(middleware=self.label, hook="before_model")
            ]
        }

    def after_model(
        self, state: ThreadState, runtime: Any
    ) -> dict[str, Any]:
        del state, runtime
        return {
            "middleware_trace": [
                MiddlewareTraceEvent(middleware=self.label, hook="after_model")
            ]
        }

    def wrap_model_call(
        self,
        request: ModelRequest[RuntimeContext],
        handler: Callable[[ModelRequest[RuntimeContext]], ModelResponse[Any]],
    ) -> ExtendedModelResponse[Any]:
        response = handler(request)
        return ExtendedModelResponse(
            model_response=response,
            command=Command(
                update={
                    "middleware_trace": [
                        MiddlewareTraceEvent(
                            middleware=self.label, hook="wrap_model_exit"
                        )
                    ]
                }
            ),
        )

    async def awrap_model_call(
        self,
        request: ModelRequest[RuntimeContext],
        handler: Callable[[ModelRequest[RuntimeContext]], Awaitable[ModelResponse[Any]]],
    ) -> ExtendedModelResponse[Any]:
        response = await handler(request)
        return ExtendedModelResponse(
            model_response=response,
            command=Command(
                update={
                    "middleware_trace": [
                        MiddlewareTraceEvent(
                            middleware=self.label, hook="wrap_model_exit"
                        )
                    ]
                }
            ),
        )
# endregion tutorial:06-lifecycle-trace-middleware


# region tutorial:06-context-prompt-middleware
class ContextPromptMiddleware(AgentMiddleware[ThreadState, RuntimeContext]):
    """Add application-controlled, non-secret runtime facts to the system message."""

    state_schema = ThreadState

    @staticmethod
    def _override_request(request: ModelRequest[RuntimeContext]) -> ModelRequest[RuntimeContext]:
        context = request.runtime.context if request.runtime is not None else None
        if not isinstance(context, RuntimeContext):
            return request
        safe = safe_context_view(context)
        context_lines = [
            "[运行时上下文：由应用注入，不能由模型改写]",
            f"user_id={safe['user_id']}",
            f"locale={safe['locale']}",
            f"permissions={','.join(safe['permissions']) or 'none'}",
            f"model_profile={safe['model_profile']}",
        ]
        if request.runtime.store is not None:
            preferences = UserPreferenceRepository(request.runtime.store).load(context.user_id)
            if preferences:
                context_lines.append("[跨线程偏好：来自 Store]")
                context_lines.extend(
                    f"{key}={preferences[key]}" for key in sorted(preferences)
                )
        base = request.system_message.text if request.system_message is not None else ""
        system_message = SystemMessage(content="\n".join([base, *context_lines]).strip())
        return request.override(system_message=system_message)

    def wrap_model_call(
        self,
        request: ModelRequest[RuntimeContext],
        handler: Callable[[ModelRequest[RuntimeContext]], ModelResponse[Any]],
    ) -> ModelResponse[Any] | AIMessage:
        return handler(self._override_request(request))

    async def awrap_model_call(
        self,
        request: ModelRequest[RuntimeContext],
        handler: Callable[[ModelRequest[RuntimeContext]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any] | AIMessage:
        return await handler(self._override_request(request))
# endregion tutorial:06-context-prompt-middleware


# region tutorial:06-model-router-middleware
class ModelRouterMiddleware(AgentMiddleware[ThreadState, RuntimeContext]):
    """Select a pre-authorized model from Runtime Context, never from model output."""

    state_schema = ThreadState

    def __init__(self, models: Mapping[str, BaseChatModel]) -> None:
        self._models = dict(models)

    def _route(self, request: ModelRequest[RuntimeContext]) -> ModelRequest[RuntimeContext]:
        context = request.runtime.context if request.runtime is not None else None
        if not isinstance(context, RuntimeContext):
            return request
        return request.override(model=self._models.get(context.model_profile, request.model))

    def wrap_model_call(
        self,
        request: ModelRequest[RuntimeContext],
        handler: Callable[[ModelRequest[RuntimeContext]], ModelResponse[Any]],
    ) -> ModelResponse[Any] | AIMessage:
        return handler(self._route(request))

    async def awrap_model_call(
        self,
        request: ModelRequest[RuntimeContext],
        handler: Callable[[ModelRequest[RuntimeContext]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any] | AIMessage:
        return await handler(self._route(request))
# endregion tutorial:06-model-router-middleware


# region tutorial:06-tool-error-middleware
class StructuredToolErrorMiddleware(AgentMiddleware[ThreadState, RuntimeContext]):
    """Convert ordinary tool exceptions into an explicit, model-visible error result."""

    state_schema = ThreadState

    @staticmethod
    def _error_message(request: ToolCallRequest, error: Exception) -> ToolMessage:
        tool_name = str(request.tool_call.get("name", "unknown"))
        if isinstance(error, TimeoutError):
            error_code, retryable = "tool_timeout", True
        elif isinstance(error, PermissionError):
            error_code, retryable = "permission_denied", False
        elif isinstance(error, ValueError):
            error_code, retryable = "invalid_tool_input", False
        else:
            error_code, retryable = "tool_execution_failed", False
        payload = {
            "ok": False,
            "error": error_code,
            "tool": tool_name,
            "exception_type": type(error).__name__,
            "retryable": retryable,
        }
        return ToolMessage(
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=str(request.tool_call.get("id", "missing-tool-call-id")),
            name=tool_name,
            status="error",
        )

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        try:
            return handler(request)
        except Exception as error:
            return self._error_message(request, error)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        try:
            return await handler(request)
        except Exception as error:
            return self._error_message(request, error)
# endregion tutorial:06-tool-error-middleware


class ArtifactTrackingMiddleware(AgentMiddleware[ThreadState, RuntimeContext]):
    """验证工具写入 State 的 Artifact 契约与 checkpoint 安全边界。"""

    state_schema = ThreadState

    @staticmethod
    def _validate(response: ToolMessage | Command[Any]) -> ToolMessage | Command[Any]:
        if not isinstance(response, Command) or not isinstance(response.update, Mapping):
            return response
        raw_artifacts = response.update.get("artifacts")
        if raw_artifacts is None:
            return response
        if not isinstance(raw_artifacts, list):
            raise ValueError("artifacts State update 必须是列表")
        artifacts = [ArtifactRef.model_validate(item) for item in raw_artifacts]
        assert_checkpoint_safe(
            {"artifacts": [artifact.model_dump(mode="json") for artifact in artifacts]}
        )
        return response

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        return self._validate(handler(request))

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[
            [ToolCallRequest], Awaitable[ToolMessage | Command[Any]]
        ],
    ) -> ToolMessage | Command[Any]:
        return self._validate(await handler(request))


# region tutorial:06-tool-permission-middleware
class ToolPermissionMiddleware(AgentMiddleware[ThreadState, RuntimeContext]):
    """Short-circuit tools whose required permission is absent from Runtime Context."""

    state_schema = ThreadState

    def __init__(self, required_permissions: Mapping[str, str]) -> None:
        self._required_permissions = dict(required_permissions)

    def _denial(self, request: ToolCallRequest) -> ToolMessage | None:
        tool_name = str(request.tool_call.get("name", "unknown"))
        required = self._required_permissions.get(tool_name)
        if required is None and request.tool is not None and request.tool.metadata:
            metadata_permission = request.tool.metadata.get("required_permission")
            required = str(metadata_permission) if metadata_permission else None
        if required is None:
            return None
        context = request.runtime.context if request.runtime is not None else None
        allowed = isinstance(context, RuntimeContext) and required in context.permissions
        if allowed:
            return None
        return ToolMessage(
            content=json.dumps(
                {
                    "ok": False,
                    "error": "permission_denied",
                    "tool": tool_name,
                    "required_permission": required,
                },
                ensure_ascii=False,
            ),
            tool_call_id=str(request.tool_call.get("id", "missing-tool-call-id")),
            name=tool_name,
            status="error",
        )

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        return self._denial(request) or handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        denial = self._denial(request)
        return denial if denial is not None else await handler(request)
# endregion tutorial:06-tool-permission-middleware


# region tutorial:06-governance-chain
def build_lead_middleware(
    *,
    model_call_limit: int = 6,
    summary_model: BaseChatModel | None = None,
    summary_trigger_messages: int = 12,
    summary_keep_messages: int = 4,
) -> list[AgentMiddleware[Any, Any]]:
    """Return the small default governance chain used in offline course scenarios."""

    middleware: list[AgentMiddleware[Any, Any]] = [LifecycleTraceMiddleware()]
    if summary_model is not None:
        middleware.append(
            SummarizationMiddleware(
                model=summary_model,
                trigger=("messages", summary_trigger_messages),
                keep=("messages", summary_keep_messages),
            )
        )
    middleware.extend(
        [
            ContextPromptMiddleware(),
            PIIMiddleware("email", strategy="redact", apply_to_input=True),
            ToolPermissionMiddleware({}),
            StructuredToolErrorMiddleware(),
            ArtifactTrackingMiddleware(),
            ModelCallLimitMiddleware(
                run_limit=model_call_limit, exit_behavior="error"
            ),
        ]
    )
    return middleware
# endregion tutorial:06-governance-chain


__all__ = [
    "ArtifactTrackingMiddleware",
    "ContextPromptMiddleware",
    "LifecycleTraceMiddleware",
    "ModelRouterMiddleware",
    "StructuredToolErrorMiddleware",
    "ToolPermissionMiddleware",
    "build_lead_middleware",
]
