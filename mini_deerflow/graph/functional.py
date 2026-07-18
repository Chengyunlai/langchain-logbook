"""A small Functional API flow that demonstrates durable task policies."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from langgraph.cache.memory import InMemoryCache
from langgraph.func import entrypoint, task
from langgraph.types import CachePolicy, RetryPolicy
from pydantic import BaseModel, ConfigDict, Field


class FunctionalTaskResult(BaseModel):
    """Typed success or failure aggregated by the functional entrypoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(min_length=1)
    status: Literal["completed", "failed"]
    content: str = ""
    error_type: str | None = None


class FunctionalResearchFlow:
    """Own an isolated task cache and expose only stable course-facing operations."""

    def __init__(self) -> None:
        self._attempts: dict[str, int] = {}
        task_cache = InMemoryCache()

        @task(
            retry_policy=RetryPolicy(
                max_attempts=2,
                initial_interval=0,
                jitter=False,
                retry_on=TimeoutError,
            ),
            cache_policy=CachePolicy(ttl=300),
        )
        def research_topic(topic: str) -> str:
            self._attempts[topic] = self._attempts.get(topic, 0) + 1
            if topic == "flaky" and self._attempts[topic] == 1:
                raise TimeoutError("deterministic transient failure")
            if topic == "failed":
                raise ValueError("deterministic permanent failure")
            return f"evidence:{topic}"

        @entrypoint(cache=task_cache)
        def aggregate(topics: list[str]) -> list[FunctionalTaskResult]:
            futures = [(topic, research_topic(topic)) for topic in topics]
            results: list[FunctionalTaskResult] = []
            for topic, future in futures:
                try:
                    content = future.result()
                except Exception as error:
                    results.append(
                        FunctionalTaskResult(
                            topic=topic,
                            status="failed",
                            error_type=type(error).__name__,
                        )
                    )
                else:
                    results.append(
                        FunctionalTaskResult(
                            topic=topic,
                            status="completed",
                            content=content,
                        )
                    )
            return results

        self._runnable: Any = aggregate

    def invoke(self, topics: Sequence[str]) -> list[FunctionalTaskResult]:
        """Run tasks concurrently and return failures as typed aggregate items."""

        return self._runnable.invoke(list(topics))

    def attempts_for(self, topic: str) -> int:
        """Expose task attempts so retry and cache behavior can be asserted."""

        return self._attempts.get(topic, 0)


# region tutorial:08-functional-research-flow
def create_functional_research_flow() -> FunctionalResearchFlow:
    """Create an isolated Functional API flow with retry, cache and error aggregation."""

    return FunctionalResearchFlow()
# endregion tutorial:08-functional-research-flow


__all__ = [
    "FunctionalResearchFlow",
    "FunctionalTaskResult",
    "create_functional_research_flow",
]
