"""可选 MCP 工具适配；核心离线 profile 不导入第三方 adapter。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.tools import BaseTool


class MCPAdapterUnavailableError(RuntimeError):
    """用户启用 MCP，但没有安装可选 adapter 依赖。"""


class MCPToolClient(Protocol):
    """与 ``MultiServerMCPClient.get_tools`` 对齐的最小异步接口。"""

    def get_tools(self) -> Awaitable[Sequence[BaseTool]]: ...


@dataclass(frozen=True, slots=True)
class MCPToolAdapter:
    """延迟创建 client，并把远端工具收缩到应用 allowlist。"""

    client_factory: Callable[[], MCPToolClient]
    enabled: bool = False
    allowed_tool_names: frozenset[str] = frozenset()

    async def load_tools(self) -> tuple[BaseTool, ...]:
        if not self.enabled:
            return ()
        client = self.client_factory()
        discovered = await client.get_tools()
        loaded: list[BaseTool] = []
        names: set[str] = set()
        for candidate in discovered:
            if not isinstance(candidate, BaseTool):
                raise TypeError("MCP client 必须返回 LangChain BaseTool")
            if candidate.name not in self.allowed_tool_names:
                continue
            if candidate.name in names:
                raise ValueError(f"MCP tool name 重复: {candidate.name}")
            names.add(candidate.name)
            candidate.metadata = {
                **(candidate.metadata or {}),
                "source": "mcp",
                "optional_extension": True,
            }
            loaded.append(candidate)
        return tuple(loaded)

    @classmethod
    def from_langchain_servers(
        cls,
        servers: Mapping[str, Mapping[str, Any]],
        *,
        enabled: bool = False,
        allowed_tool_names: frozenset[str] = frozenset(),
    ) -> MCPToolAdapter:
        """延迟构造官方 ``MultiServerMCPClient``；关闭时不会触发 import。"""

        frozen_servers = {
            name: dict(configuration) for name, configuration in servers.items()
        }

        def factory() -> MCPToolClient:
            try:
                from langchain_mcp_adapters.client import MultiServerMCPClient
            except ImportError as error:
                raise MCPAdapterUnavailableError(
                    "MCP 已启用，但未安装可选依赖 langchain-mcp-adapters；"
                    "请先运行 uv sync --locked --group dev --extra mcp，再显式启用"
                ) from error
            return MultiServerMCPClient(frozen_servers)

        return cls(
            client_factory=factory,
            enabled=enabled,
            allowed_tool_names=allowed_tool_names,
        )


__all__ = [
    "MCPAdapterUnavailableError",
    "MCPToolAdapter",
    "MCPToolClient",
]
