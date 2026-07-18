"""Subagent capability registry。"""

from __future__ import annotations

from collections.abc import Iterable

from mini_deerflow.subagents.contracts import SubagentSpec


# region tutorial:11-subagent-registry
class SubagentRegistry:
    """按稳定名称解析 specialist，并拒绝静默覆盖。"""

    def __init__(self, specs: Iterable[SubagentSpec] = ()) -> None:
        self._specs: dict[str, SubagentSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: SubagentSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"重复的 Subagent: {spec.name}")
        self._specs[spec.name] = spec

    def resolve(self, name: str) -> SubagentSpec:
        try:
            return self._specs[name]
        except KeyError as error:
            raise KeyError(f"未知 Subagent: {name}") from error

    def describe(self) -> tuple[tuple[str, str], ...]:
        """返回可安全放进 Lead Agent prompt/tool discovery 的能力摘要。"""

        return tuple((spec.name, spec.description) for spec in self._specs.values())
# endregion tutorial:11-subagent-registry


__all__ = ["SubagentRegistry"]
