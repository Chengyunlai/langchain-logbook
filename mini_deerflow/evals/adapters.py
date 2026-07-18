"""把真实 Agent State 投影为 provider-neutral 的评测 observation。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from mini_deerflow.evals.contracts import AgentObservation


def _message_type(message: object) -> str | None:
    if isinstance(message, AIMessage):
        return "ai"
    if isinstance(message, ToolMessage):
        return "tool"
    if isinstance(message, Mapping):
        raw_type = message.get("type")
        return str(raw_type) if raw_type is not None else None
    return None


def _message_name(message: object) -> str | None:
    if isinstance(message, BaseMessage):
        return message.name
    if isinstance(message, Mapping):
        raw_name = message.get("name")
        return str(raw_name) if raw_name else None
    return None


def _message_text(message: object) -> str:
    if isinstance(message, BaseMessage):
        return message.text
    if isinstance(message, Mapping):
        content = message.get("content", "")
        return content if isinstance(content, str) else str(content)
    return ""


def _message_total_tokens(message: object) -> int:
    if isinstance(message, AIMessage) and message.usage_metadata:
        usage = message.usage_metadata
        return int(
            usage.get(
                "total_tokens",
                int(usage.get("input_tokens", 0))
                + int(usage.get("output_tokens", 0)),
            )
        )
    if isinstance(message, Mapping):
        usage = message.get("usage_metadata")
        if isinstance(usage, Mapping):
            return int(
                usage.get(
                    "total_tokens",
                    int(usage.get("input_tokens", 0))
                    + int(usage.get("output_tokens", 0)),
                )
            )
    return 0


def observation_from_agent_state(
    state: Mapping[str, object],
) -> AgentObservation:
    """从 Agent messages 提取最终回答、model/tool 轨迹与 token 使用。"""

    raw_messages = state.get("messages", ())
    if not isinstance(raw_messages, Sequence) or isinstance(
        raw_messages,
        (str, bytes, bytearray),
    ):
        raise ValueError("Agent State.messages 必须是消息序列")
    trajectory: list[str] = []
    final_output = ""
    model_calls = 0
    tool_calls = 0
    total_tokens = 0
    for message in raw_messages:
        message_type = _message_type(message)
        if message_type == "ai":
            trajectory.append("model")
            model_calls += 1
            text = _message_text(message)
            if text:
                final_output = text
            total_tokens += _message_total_tokens(message)
        elif message_type == "tool":
            trajectory.append(_message_name(message) or "tool")
            tool_calls += 1
    return AgentObservation(
        output=final_output,
        trajectory=tuple(trajectory),
        model_calls=model_calls,
        tool_calls=tool_calls,
        total_tokens=total_tokens,
    )


__all__ = ["observation_from_agent_state"]
