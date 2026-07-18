"""把易变的 LangGraph 流式协议隔离为课程自己的稳定事件。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime, time
from enum import Enum
import json
import math
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel


type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]


def _normalize_json_value(value: object, *, path: str = "data") -> JSONValue:
    """把 Graph update 投影成确定、严格的 JSON 数据；未知对象直接失败。"""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} 含有 JSON 不支持的非有限浮点数")
        return value
    if isinstance(value, BaseModel):
        return _normalize_json_value(value.model_dump(mode="json"), path=path)
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize_json_value(asdict(value), path=path)
    if isinstance(value, Enum):
        return _normalize_json_value(value.value, path=path)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (Path, UUID)):
        return str(value)
    if isinstance(value, Mapping):
        normalized: dict[str, JSONValue] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} 的 JSON object key 必须是字符串")
            normalized[key] = _normalize_json_value(
                nested,
                path=f"{path}.{key}",
            )
        return normalized
    if isinstance(value, Set):
        items = [
            _normalize_json_value(item, path=f"{path}[]") for item in value
        ]
        return sorted(
            items,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return [
            _normalize_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise ValueError(
        f"{path} 含有不支持的流式事件对象 {type(value).__name__}；"
        "请先在 Graph 边界建立显式投影"
    )


def normalize_json_value(value: object, *, path: str = "data") -> JSONValue:
    """公共 JSON 投影 seam；Runtime repository 与 SSE adapter 复用。"""

    return _normalize_json_value(value, path=path)


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """Mini DeerFlow 内部消费的最小流式事件。"""

    type: str
    namespace: tuple[str, ...]
    data: JSONValue

    def as_dict(self) -> dict[str, JSONValue]:
        """返回可直接进入 JSON/SSE adapter 的稳定字段投影。"""

        return {
            "type": self.type,
            "namespace": list(self.namespace),
            "data": self.data,
        }


# region tutorial:01-stream-normalizer
def normalize_stream_part(part: object) -> StreamEvent:
    """验证并转换 LangGraph v2 ``StreamPart``。

    未知 ``type`` 会原样保留，让后续 adapter 可以渐进支持新事件；旧版 tuple
    不会被猜测性转换，因为 tuple 的形状受 stream mode 数量和 subgraph 参数
    影响，静默兼容反而容易错读数据。
    """

    if not isinstance(part, dict) or not {"type", "ns", "data"}.issubset(part):
        raise ValueError(
            "需要 LangGraph v2 事件 envelope，必须包含 type、ns、data；"
            "请调用 stream/astream(..., version='v2')"
        )
    event_type = part["type"]
    namespace = part["ns"]
    if not isinstance(event_type, str):
        raise ValueError("v2 事件 type 必须是字符串")
    if not isinstance(namespace, (tuple, list)) or not all(
        isinstance(item, str) for item in namespace
    ):
        raise ValueError("v2 事件 ns 必须是字符串序列")
    return StreamEvent(
        type=event_type,
        namespace=tuple(namespace),
        data=_normalize_json_value(part["data"]),
    )
# endregion tutorial:01-stream-normalizer


__all__ = [
    "JSONValue",
    "StreamEvent",
    "normalize_json_value",
    "normalize_stream_part",
]
