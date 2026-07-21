"""Mini DeerFlow composition root 与标准 LangGraph graph 导出。"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Iterator, Mapping
from typing import Any, Protocol

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from mini_deerflow.agents import create_lead_agent
from mini_deerflow.config import ApplicationSettings
from mini_deerflow.context import RuntimeContext
from mini_deerflow.fixtures import (
    create_demo_index,
    create_repeating_demo_lead_model,
    create_repeating_demo_summary_model,
)
from mini_deerflow.knowledge import LocalKnowledgeIndex
from mini_deerflow.middleware import build_lead_middleware
from mini_deerflow.models import create_model
from mini_deerflow.persistence import create_memory_checkpointer
from mini_deerflow.runtime import RunDescriptor
from mini_deerflow.sandbox import LocalSandboxProvider, SandboxProvider
from mini_deerflow.subagents import (
    DelegationLedger,
    SubagentExecutor,
    SubagentRegistry,
    build_demo_subagent_registry,
    build_task_tool,
)
from mini_deerflow.streaming import StreamEvent, normalize_stream_part
from mini_deerflow.tools import build_tool_registry


class InvocationObservability(Protocol):
    """组合根依赖的最小观测端口；LangSmith 只是一个 adapter。"""

    def run(
        self,
        operation_name: str,
        operation: Callable[[], Any],
        *,
        correlation_id: str,
        user_id: str,
        metadata: Mapping[str, Any] | None = None,
        operation_already_traced: bool = False,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class ApplicationDependencies:
    """组合根的可替换依赖；测试和真实 adapter 复用同一组接缝。"""

    model: BaseChatModel
    summary_model: BaseChatModel
    knowledge_index: LocalKnowledgeIndex
    store: BaseStore
    checkpointer: BaseCheckpointSaver[Any]
    subagent_registry: SubagentRegistry
    delegation_ledger: DelegationLedger
    sandbox_provider: SandboxProvider
    extension_tools: tuple[BaseTool, ...] = ()


@dataclass(slots=True)
class MiniDeerFlowApplication:
    """把 compiled graph 与调用策略绑在一起的本地应用对象。"""

    settings: ApplicationSettings
    dependencies: ApplicationDependencies
    graph: Any
    tool_names: tuple[str, ...]
    observability: InvocationObservability | None = None

    @staticmethod
    def _config_for(run: RunDescriptor) -> RunnableConfig:
        return {"configurable": {"thread_id": run.thread_id}}

    def context_for(
        self,
        *,
        request_id: str,
        user_id: str | None = None,
        permissions: set[str] | frozenset[str] | None = None,
    ) -> RuntimeContext:
        """由应用创建 Runtime Context；模型不能提交或改写这些字段。"""

        return RuntimeContext(
            user_id=user_id or self.settings.default_user_id,
            workspace_root=str(self.settings.workspace_root),
            request_id=request_id,
            permissions=(
                frozenset(permissions)
                if permissions is not None
                else self.settings.default_permissions
            ),
            model_profile=self.settings.model.profile.value,
        )

    def invoke(
        self,
        message: str | BaseMessage,
        *,
        run: RunDescriptor | None = None,
        permissions: set[str] | frozenset[str] | None = None,
    ) -> dict[str, Any]:
        """运行一次最小对话；正式 Gateway 将复用 graph 而不是包装本方法。"""

        descriptor = run or RunDescriptor.create(
            user_id=self.settings.default_user_id
        )
        context = self.context_for(
            request_id=descriptor.request_id,
            user_id=descriptor.user_id,
            permissions=permissions,
        )
        def invoke_graph() -> dict[str, Any]:
            return self.graph.invoke(
                {"messages": [message]},
                config=self._config_for(descriptor),
                context=context,
            )

        if self.observability is None:
            return invoke_graph()
        return self.observability.run(
            "mini-deerflow.invoke",
            invoke_graph,
            correlation_id=descriptor.request_id,
            user_id=descriptor.user_id,
            metadata={
                "thread_id": descriptor.thread_id,
                "request_id": descriptor.request_id,
                "model_profile": self.settings.model.profile.value,
            },
        )

    def state_for(self, run: RunDescriptor) -> dict[str, Any]:
        """读取 thread 的最新 checkpoint state，不暴露 StateSnapshot 内部结构。"""

        return dict(self.graph.get_state(self._config_for(run)).values)

    def stream(
        self,
        message: str | BaseMessage,
        *,
        run: RunDescriptor,
        permissions: set[str] | frozenset[str] | None = None,
    ) -> Iterator[StreamEvent]:
        """以 v2 ``updates`` 模式运行，并只暴露稳定的领域事件。"""

        context = self.context_for(
            request_id=run.request_id,
            user_id=run.user_id,
            permissions=permissions,
        )
        for part in self.graph.stream(
            {"messages": [message]},
            config=self._config_for(run),
            context=context,
            stream_mode=["updates"],
            version="v2",
        ):
            yield normalize_stream_part(part)

    def draw_mermaid(self) -> str:
        """导出 compiled graph 的可版本化 Mermaid 文本。"""

        return str(self.graph.get_graph().draw_mermaid())


def build_default_dependencies(
    settings: ApplicationSettings | None = None,
) -> ApplicationDependencies:
    """按 settings 创建默认依赖；offline 默认完全在进程内运行。"""

    resolved_settings = settings or ApplicationSettings.offline()
    if resolved_settings.model.profile.value == "offline":
        model = create_repeating_demo_lead_model()
        summary_model = create_repeating_demo_summary_model()
    else:
        model = create_model(resolved_settings.model)
        summary_model = create_model(resolved_settings.model)
    return ApplicationDependencies(
        model=model,
        summary_model=summary_model,
        knowledge_index=create_demo_index(),
        store=InMemoryStore(),
        checkpointer=create_memory_checkpointer(),
        subagent_registry=build_demo_subagent_registry(),
        delegation_ledger=DelegationLedger(),
        sandbox_provider=LocalSandboxProvider(
            resolved_settings.workspace_root / ".mini-deerflow" / "sandboxes"
        ),
    )


def build_application(
    settings: ApplicationSettings | None = None,
    *,
    dependencies: ApplicationDependencies | None = None,
    observability: InvocationObservability | None = None,
) -> MiniDeerFlowApplication:
    """本地应用组合入口：装配 Lead Agent、治理链、工具与 Subagent。"""

    resolved_settings = settings or ApplicationSettings.offline()
    resolved_dependencies = dependencies or build_default_dependencies(resolved_settings)
    compiled_graph, tool_names = _assemble_graph(
        resolved_settings,
        resolved_dependencies,
        attach_local_persistence=True,
    )
    return MiniDeerFlowApplication(
        settings=resolved_settings,
        dependencies=resolved_dependencies,
        graph=compiled_graph,
        tool_names=tool_names,
        observability=observability,
    )


def _assemble_graph(
    settings: ApplicationSettings,
    dependencies: ApplicationDependencies,
    *,
    attach_local_persistence: bool,
) -> tuple[Any, tuple[str, ...]]:
    """共享 Agent 装配逻辑；持久化由本地应用或 Agent Server 二选一管理。"""

    executor = SubagentExecutor(
        dependencies.subagent_registry,
        max_concurrency=settings.subagent_max_concurrency,
        timeout_seconds=settings.subagent_timeout_seconds,
        ledger=dependencies.delegation_ledger,
    )
    tools = [
        *build_tool_registry(
            dependencies.knowledge_index,
            sandbox_provider=dependencies.sandbox_provider,
        ),
        build_task_tool(
            executor,
            sandbox_provider=dependencies.sandbox_provider,
        ),
        *dependencies.extension_tools,
    ]
    tool_names = [tool.name for tool in tools]
    if len(tool_names) != len(set(tool_names)):
        duplicates = sorted(
            name for name in set(tool_names) if tool_names.count(name) > 1
        )
        raise ValueError(f"组合根发现重复 tool name: {', '.join(duplicates)}")
    compiled_graph = create_lead_agent(
        model=dependencies.model,
        tools=tools,
        middleware=build_lead_middleware(
            model_call_limit=settings.model_call_limit,
            summary_model=dependencies.summary_model,
            summary_trigger_messages=settings.summary_trigger_messages,
            summary_keep_messages=settings.summary_keep_messages,
        ),
        store=dependencies.store if attach_local_persistence else None,
        checkpointer=dependencies.checkpointer if attach_local_persistence else None,
    )
    return compiled_graph, tuple(tool_names)


def make_graph(config: RunnableConfig | None = None) -> Any:
    """为 Agent Server/Studio 创建不绑定本地持久化后端的新 graph。

    Agent Server 会在运行时注入自己的 Checkpointer 与 Store。当前离线 fake model
    使用脚本迭代器，因此 factory 还确保不同 run 不共享已消费的模型实例。后续可
    从 ``config`` 读取 assistant 级的、经过应用验证的模型或工具选择。
    """

    del config
    settings = ApplicationSettings.offline()
    dependencies = build_default_dependencies(settings)
    compiled_graph, _ = _assemble_graph(
        settings,
        dependencies,
        attach_local_persistence=False,
    )
    return compiled_graph


__all__ = [
    "ApplicationDependencies",
    "InvocationObservability",
    "MiniDeerFlowApplication",
    "build_application",
    "build_default_dependencies",
    "make_graph",
]
