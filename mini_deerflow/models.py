"""统一模型工厂；核心课程默认不访问外部服务。"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import os
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

from mini_deerflow.config import ModelProfile, ModelSettings


class ModelConfigurationError(ValueError):
    """模型 profile 与运行环境不完整。"""


class ToolCallingFakeModel(GenericFakeChatModel):
    """支持 ``bind_tools`` 的脚本化离线模型。

    GenericFakeChatModel 的默认实现刻意不声明 tool calling。课程需要观察完整
    Agent 工具循环，所以这个 adapter 只增加“接受工具声明”的协议能力，回答
    仍完全由测试传入的 AIMessage 序列决定。
    """

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | BaseTool | Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ToolCallingFakeModel:
        del tools, tool_choice, kwargs
        return self


def create_offline_model(
    responses: Iterable[AIMessage | str] | None = None,
) -> ToolCallingFakeModel:
    """创建每次测试独享的确定性模型。"""

    scripted = responses or ["这是离线模型的确定性回答。"]
    return ToolCallingFakeModel(messages=iter(scripted))


# region tutorial:01-model-factory
def create_model(
    settings: ModelSettings | None = None,
    *,
    offline_responses: Iterable[AIMessage | str] | None = None,
) -> BaseChatModel:
    """根据显式 profile 创建模型，绝不猜测供应商或复用错误的 Key。"""

    resolved = settings or ModelSettings()
    if resolved.profile is ModelProfile.OFFLINE:
        return create_offline_model(offline_responses)

    if resolved.profile is ModelProfile.DEEPSEEK:
        if not os.getenv("DEEPSEEK_API_KEY"):
            raise ModelConfigurationError(
                "deepseek profile 需要 DEEPSEEK_API_KEY；离线学习请使用 offline profile"
            )
        return init_chat_model(
            resolved.model_name or "deepseek:deepseek-chat",
            temperature=resolved.temperature,
        )

    raise ModelConfigurationError(f"不支持的模型 profile: {resolved.profile}")
# endregion tutorial:01-model-factory


__all__ = [
    "ModelConfigurationError",
    "ToolCallingFakeModel",
    "create_model",
    "create_offline_model",
]
