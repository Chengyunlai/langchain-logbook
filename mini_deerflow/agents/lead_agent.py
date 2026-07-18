"""Lead Agent factory：组合工具循环、Thread State、Runtime Context 与 Middleware。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from mini_deerflow.config import LeadAgentContext
from mini_deerflow.fixtures import create_demo_index, create_demo_lead_model
from mini_deerflow.knowledge import LocalKnowledgeIndex
from mini_deerflow.state import ThreadState
from mini_deerflow.tools import build_tool_registry


LEAD_AGENT_PROMPT = """你是 Mini DeerFlow 的 Lead Agent。
先判断是否需要工具；使用检索结果时保留 source；不知道就明确说明证据不足。
可读取应用显式保存的 Store 偏好；只有 registry 注入 ``task`` 工具时才能委派 Subagent。
Subagent 只接收任务所需的裁剪上下文，Lead Agent 负责汇总结构化结果。
只有 registry 注入工作区工具时才能读写线程 Sandbox；本地 provider 默认禁用宿主命令。
MCP 与 Skills 都是应用显式启用的可选扩展，不能猜测未注册工具或未加载技能。
"""


LeadAgentState = ThreadState
"""Backward-compatible chapter-04 name; chapter 05 calls it ``ThreadState``."""


# region tutorial:04-lead-agent-factory
def create_lead_agent(
    *,
    model: BaseChatModel | None = None,
    knowledge_index: LocalKnowledgeIndex | None = None,
    tools: Sequence[BaseTool] | None = None,
    middleware: Sequence[AgentMiddleware[Any, Any]] | None = None,
    store: BaseStore | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """构建可注入 Middleware 与 Store 的 Lead Agent compiled graph。

    ``tools`` 可注入 ``task``、Sandbox workspace、MCP 与 Skills 工具；factory
    不自行扫描目录、连接 MCP 或提升权限。
    """

    resolved_index = knowledge_index if knowledge_index is not None else create_demo_index()
    resolved_tools = list(tools) if tools is not None else build_tool_registry(resolved_index)
    return create_agent(
        model or create_demo_lead_model(),
        tools=resolved_tools,
        system_prompt=LEAD_AGENT_PROMPT,
        middleware=list(middleware or []),
        state_schema=ThreadState,
        context_schema=LeadAgentContext,
        checkpointer=checkpointer,
        store=store,
        name="mini_deerflow_lead_agent",
    )
# endregion tutorial:04-lead-agent-factory


__all__ = ["LEAD_AGENT_PROMPT", "LeadAgentState", "create_lead_agent"]
