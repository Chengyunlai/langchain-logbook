---
title: "附录：LangChain / LangGraph 协议速查"
description: "查询消息、工具调用与底层协议细节，不必在第 01 章前通读。"
pubDatetime: 2025-01-01T00:00:00Z
featured: false
tags: ["tutorial"]
sourcePath: "APPENDIX.md"
learningOrder: 19
learningStage: "reference"
learningStageTitle: "维护与协议资料"
learningGoal: "查询消息、工具调用与底层协议细节，不必在第 01 章前通读。"
contentType: "reference"
---

> - 验证窗口：LangChain 1.3.x / LangGraph 1.2.x
> - 用途：补充正文反复使用、但不适合在每章重新展开的接口与返回形状
> - 阅读方式：先读对应正文，遇到协议细节时再查本附录

附录只描述本项目实际依赖的边界。供应商私有字段、预览 API 和未经测试的自动降级行为，不作为课程契约。

---

## A1. Runnable 的统一调用接口

LangChain 组件通常实现 `Runnable` 接口，因此模型、Prompt 管道和部分已编译 Graph 可以使用相似的调用方式。

| 接口 | 返回时机 | 适用场景 |
| --- | --- | --- |
| `invoke / ainvoke` | 整次运行结束 | 只关心最终结果 |
| `batch / abatch` | 一组输入处理完成 | 输入彼此独立的批处理 |
| `stream / astream` | 运行过程中持续产生数据 | token、节点更新或长任务进度 |

`a` 前缀表示异步调用方式，不保证底层所有工作都天然并行。真正的并发度仍受模型客户端、工具实现、限流和 Runnable 配置影响。

Runnable 统一的是调用表面，不是业务语义。模型返回 `AIMessage`，检索器返回文档，Graph 返回 State；调用者仍须理解每个组件的输入输出契约。

---

## A2. `create_agent`、消息与 Checkpointer

`create_agent` 返回可调用的已编译 StateGraph。标准 Agent 在模型节点和工具节点之间循环，直到模型不再发出 tool call 或运行被中断。

`AIMessage` 是模型决策的主要载体。文本回答位于 `content`，工具请求位于 `tool_calls`，token 统计通常位于 `usage_metadata`。每个工具请求的 `id` 必须与对应 `ToolMessage.tool_call_id` 匹配。

```python
from langchain_core.messages import AIMessage

message = AIMessage(
    content="",
    tool_calls=[
        {
            "name": "search_knowledge",
            "args": {"query": "LangGraph durable execution"},
            "id": "call-1",
            "type": "tool_call",
        }
    ],
)
```

Checkpointer 按 Thread 保存 Graph checkpoint，使后续调用能够恢复状态、处理中断或查看历史快照。它不等同于产品数据库：用户、Run、权限、账单和发布记录仍应由应用层 repository 管理。

---

## A3. 结构化输出策略

模型层的 `with_structured_output(Schema)` 约束一次模型调用；Agent 层的 `response_format` 约束完整工具循环的最终结果。两者的生命周期不同，不能只因为都使用 Pydantic 就混为同一层。

Agent 可以显式选择 `ProviderStrategy` 或 `ToolStrategy`。前者使用供应商原生结构化输出，后者通过 tool call 生成结构。也可以直接传入 Schema，由 LangChain 根据模型集成选择可用策略。

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

agent = create_agent(
    model=model,
    tools=tools,
    response_format=ToolStrategy(ResearchReport),
)
```

不要依赖一个假定存在的通用 `capabilities` 字典来推断行为。策略是否可用，应以模型集成文档、显式配置和真实 integration test 为准。

如果结构化输出失败，应保留拒答、Schema 校验错误和供应商错误之间的区别。把所有失败都交给正则提取，会丢失可诊断信息，也无法证明字段语义正确。

---

## A4. 异步 Web 服务中的流式调用

同步 `stream` 并不会让 LangGraph 本身“锁死”。真正的问题是：在 FastAPI 等异步请求处理器中直接执行阻塞式模型或工具 I/O，会占用事件循环线程，拖慢同一 worker 上的其他请求。

当模型客户端和工具都提供异步实现时，优先使用 `astream`：

```python
async for event in agent.astream(
    input_data,
    stream_mode="messages",
    version="v2",
):
    if event["type"] == "messages":
        chunk, metadata = event["data"]
```

如果某个依赖只有同步接口，应在明确的线程池或任务队列边界中隔离它，并同时配置超时、取消和并发上限。只把外层函数改成 `async def`，不会自动消除内部阻塞。

---

## A5. Stream mode 与 v1/v2 返回形状

`stream_mode` 决定观察哪类运行数据，`version` 决定这些数据如何被包装。本项目 Gateway 对外暴露 `messages`、`updates`、`values` 和 `custom` 四类；上游还提供面向调试或任务跟踪的模式，使用前应核对当前版本文档。

| 模式 | `data` 的主要形状 | 本项目用途 |
| --- | --- | --- |
| `values` | 当前完整 State | 快照与恢复诊断 |
| `updates` | 节点刚写入的局部更新 | 运行轨迹和进度 |
| `messages` | `(message_chunk, metadata)` | 模型 token 流 |
| `custom` | 节点主动写出的自定义数据 | 审批、业务进度和工具状态 |

在 `version="v2"` 下，事件使用统一 envelope：

```text
{
  "type": "messages | updates | values | custom | ...",
  "ns": ["subgraph", ...],
  "data": "由 type 决定的 payload"
}
```

因此 `messages` 的二元组位于 `event["data"]`，不能把整个 v2 事件直接解包为 `chunk, metadata`。

```python
for event in graph.stream(
    input_data,
    stream_mode="messages",
    version="v2",
):
    if event["type"] != "messages":
        continue
    chunk, metadata = event["data"]
```

`ns` 标识子图命名空间。消费多 Agent 或 Subgraph 事件时，应连同 `type` 一起保留，避免不同节点的同名事件在 Gateway 中失去来源。

### v1 与 v2 的判断顺序

阅读流式代码时按三个问题判断返回形状：

1. 调用的是 `stream / astream`，还是另一套事件 API？
2. `stream_mode` 是单个模式还是多个模式？
3. `version` 是 `v1` 还是统一 envelope 的 `v2`？

本项目固定在边界 adapter 中解析 v2，再转为内部 `StreamEvent`。UI、Notebook 和 SSE Gateway 不直接依赖上游原始字典。

---

## A6. 增量索引与 RecordManager

LangChain indexing API 使用 RecordManager 记录内容哈希、写入时间和来源标识。再次索引相同内容时，可以跳过不必要的向量写入；在支持清理的模式下，也可以根据 `source_id` 删除已不再存在的旧文档。

这套机制解决的是索引同步，不负责判断文档事实是否正确。内容切分策略、metadata、`source_id` 和 embedding 模型发生变化时，仍要明确决定复用、迁移还是重建索引。

“跳过”也不意味着完全没有成本。应用仍需读取输入、计算标识并查询记录库；它避免的主要是重复 embedding 和向量存储写入。

---

## A7. 混合检索中的 RRF

BM25 分数和向量相似度不在同一量纲，直接相加通常缺少可解释性。Reciprocal Rank Fusion（RRF）只使用各检索器给出的排名：

$$
\operatorname{RRF}(d)=\sum_{r \in R}\frac{1}{k+\operatorname{rank}_r(d)}
$$

`k` 用于减弱头部名次差异，常见示例取 60，但它仍是需要用评测集验证的参数。RRF 的优势是无需校准原始分数；代价是舍弃了检索器对“第一名领先多少”的信息。

在 Mini DeerFlow 中，混合检索应同时保留来源、单路排名和融合后排名。这样评测失败时才能判断问题来自召回、排序还是引用生成。