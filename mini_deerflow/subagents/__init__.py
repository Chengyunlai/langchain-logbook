"""Mini DeerFlow 的隔离 Subagent 调度纵切面。"""

from mini_deerflow.subagents.contracts import (
    SubagentInvocation,
    SubagentOutput,
    SubagentRequest,
    SubagentSpec,
)
from mini_deerflow.subagents.builtins import (
    EphemeralAgentHandler,
    build_demo_subagent_registry,
)
from mini_deerflow.subagents.executor import (
    DelegationLedger,
    DelegationRecord,
    SubagentExecutor,
)
from mini_deerflow.subagents.patterns import (
    build_handoff_graph,
    build_parallel_router_graph,
    build_shared_subgraph_graph,
    build_single_router_graph,
)
from mini_deerflow.subagents.registry import SubagentRegistry
from mini_deerflow.subagents.task_tool import TaskToolInput, build_task_tool

__all__ = [
    "DelegationLedger",
    "DelegationRecord",
    "EphemeralAgentHandler",
    "SubagentExecutor",
    "SubagentInvocation",
    "SubagentOutput",
    "SubagentRegistry",
    "SubagentRequest",
    "SubagentSpec",
    "TaskToolInput",
    "build_demo_subagent_registry",
    "build_handoff_graph",
    "build_parallel_router_graph",
    "build_shared_subgraph_graph",
    "build_single_router_graph",
    "build_task_tool",
]
