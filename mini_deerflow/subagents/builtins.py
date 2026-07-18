"""课程离线运行所需的两个确定性 specialist。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langchain.tools import tool

from mini_deerflow.models import create_offline_model
from mini_deerflow.subagents.contracts import (
    SubagentInvocation,
    SubagentOutput,
    SubagentSpec,
)
from mini_deerflow.subagents.registry import SubagentRegistry


@tool("lookup_evidence")
def lookup_evidence(topic: str) -> str:
    """从离线 fixture 返回一条带来源的研究证据。"""

    return f"evidence:{topic}:source=offline-docs"


@tool("inspect_interface")
def inspect_interface(objective: str) -> str:
    """从离线 fixture 返回一条接口检查结果。"""

    return f"interface:{objective}:testable=true"


@dataclass(frozen=True, slots=True)
class EphemeralAgentHandler:
    """每次调用都创建无 checkpointer 的新 Agent，避免 specialist 历史串线。"""

    name: str
    system_prompt: str
    tool: BaseTool
    summary_prefix: str
    checkpointer: Literal[False] = False

    @property
    def tool_names(self) -> tuple[str, ...]:
        return (self.tool.name,)

    async def __call__(self, invocation: SubagentInvocation) -> SubagentOutput:
        locale = invocation.context.get("locale", "zh-CN")
        model = create_offline_model(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": self.tool.name,
                            "args": {
                                "topic" if self.tool.name == "lookup_evidence" else "objective": invocation.prompt
                            },
                            "id": f"{invocation.task_id}-tool",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(
                    content=f"{self.summary_prefix}[{locale}]：{invocation.prompt}"
                ),
            ]
        )
        agent = create_agent(
            model,
            tools=[self.tool],
            system_prompt=self.system_prompt,
            checkpointer=self.checkpointer,
            name=f"mini_deerflow_{self.name}_subagent",
        )
        state = await agent.ainvoke(
            {"messages": [{"role": "user", "content": invocation.prompt}]}
        )
        return SubagentOutput(summary=str(state["messages"][-1].content))


# region tutorial:11-isolated-specialists
def build_demo_subagent_registry() -> SubagentRegistry:
    """返回 research/coding 两个临时 specialist；二者不持有独立对话历史。"""

    return SubagentRegistry(
        [
            SubagentSpec(
                name="research",
                description="检索、比较并压缩证据",
                handler=EphemeralAgentHandler(
                    name="research",
                    system_prompt="你是研究 specialist，只使用带来源的证据并返回有界摘要。",
                    tool=lookup_evidence,
                    summary_prefix="研究摘要",
                ),
                allowed_context_fields=frozenset(
                    {"locale", "request_id", "sandbox_id"}
                ),
            ),
            SubagentSpec(
                name="coding",
                description="分析 Python 接口并提出可测试实现",
                handler=EphemeralAgentHandler(
                    name="coding",
                    system_prompt="你是代码 specialist，只分析接口并给出可验证建议。",
                    tool=inspect_interface,
                    summary_prefix="代码建议",
                ),
                allowed_context_fields=frozenset(
                    {"locale", "request_id", "sandbox_id"}
                ),
            ),
        ]
    )
# endregion tutorial:11-isolated-specialists


__all__ = [
    "EphemeralAgentHandler",
    "build_demo_subagent_registry",
    "inspect_interface",
    "lookup_evidence",
]
