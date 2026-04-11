---
title: "第 01 章：环境配置与智能体底层逻辑"
description: "LangChain Logbook content: 第 01 章：环境配置与智能体底层逻辑"
pubDatetime: 2026-04-02T00:00:00.000Z
featured: false
tags: ["tutorial"]
---

## 💡 本章核心目标
放弃传统的“线性链式调用”思维，建立以“图状态转移”为核心的 Agent-First 意识。我们将深入探讨 2026 年 LangChain 1.2+ 的核心协议，掌握模型、工具与消息流的工业级处理方式。

---

## 知识点一：统一模型声明 (The model factory)

在 2026 年，我们全面摈弃为每个模型提供商单独导包的旧做法（如 `from langchain_openai import ChatOpenAI`）。

- **统一标准**：使用 `init_chat_model` 充当跨厂商的通用转接头。它会根据参数自动探测并接驳底层驱动，同时确保模型具备标准的“工具调用”能力。

- **配置逻辑**：

```python
from langchain.chat_models import init_chat_model

# 统一实例化逻辑：隐藏厂商差异，返回标准化的 chat_model 对象
llm = init_chat_model(
    model="deepseek-chat", # 模型名称
    model_provider="openai" # 底层协议驱动
)
```

- **核心探针**：
关于模型支持的具体能力（如 `tool_calling`, `structured_output`）的深度探测逻辑，详见 [附录 A3：核心能力探针](../APPENDIX.md#a3-核心能力探针与配置-model-capabilities)。

---

## 知识点二：工具 (Tools) 的声明与描述协议

工具是智能体的“手动挡”。在 LangChain 中，工具的本质是一个**具备自描述能力的 Pydantic 管道**。

- **`@tool` 装饰器**：将普通的 Python 函数注册为工具。
- **描述驱动 (Docstring)**：Docstring 不仅仅是注释，它是模型推理时的“说明书”。如果描述不准确，模型会因无法理解而拒绝调用。

```python
from langchain.tools import tool

@tool
def get_system_time(query: str) -> str:
    """返回当前系统的具体时间。当用户询问时间相关的实时信息时，必须使用此工具。"""
    import datetime
    return f"北京时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
```

- **参数控制**：
框架会解析函数输入（如 `query: str`），自动解析出 JSON Schema。模型正是通过阅读这个 Schema 来学习如何正确传参。

---

## 知识点三：理解消息协议 (The Message Protocol)

这是新手最容易混淆的地方。智能体内部的行为流转完全建立在**消息基类 (`BaseMessage`)** 的不同实现之上：

| 类型 | 发件人 | 核心作用 |
| :--- | :--- | :--- |
| **`HumanMessage`** | 用户 (Human) | 承载用户的指令输入，是对话的起点。 |
| **`AIMessage`** | 模型 (LLM) | 模型做出的决策或回复。 |
| **`AIMessageChunk`** | 模型 (LLM) | **[新]** 流式传输中的碎片，支持通过 `+` 运算符自动聚合为完整消息。 |
| **`ToolMessage`** | 工具 (Tool) | 存储工具运行的结果，用于回传给模型。**必须包含 `tool_call_id`**。 |
| **`SystemMessage`** | 系统 (Developer) | 预设的全局指令，规定了智能体的人设与边界。 |

- **💡 现代工业级输入方案 (Organizing Inputs)**：
虽然类实例化（如 `HumanMessage(content="...")`）在架构上很严谨，但在 2026 年的实际开发中，我们更推崇更简洁的 **Tuple 列表格式**。它能大幅减少导包和代码量：

```python
# 推荐：简单直接的元组列表
messages = [
    ("system", "你是一个资深翻译官"),
    ("user", "帮我翻译一下这段话：'Hello World'")
]

# 调用示例
agent.invoke({"messages": messages})
```

- **⚠️ 误区纠正**：用户输入并不是 `AIMessage`。对话是不同角色的消息在 `State`（状态台账）中不断追加的过程。具体的 `AIMessage` 结构细节详见 [附录 A2：现代 Agent 的包裹状态引擎特征](../APPENDIX.md#a2-现代-agent-的包裹状态引擎特征)。

---

## 知识点四：驱动模式：如何获取 Agent 的回答？

Agent 提供了多种驱动方式，新手常感到困惑。其实只需根据你的场景二选一：

### 1. 极简开发流：单纯想要最终结果

如果你是在写测试脚本或批处理程序，直接使用 **`invoke()`**。

```python
# 最简单的阻塞调用，直接拿最后一条 AIMessage
result = agent.invoke({"messages": [("user", "你好")]})
print(result["messages"][-1].content)
```

### 2. 用户体验流：像 ChatGPT 一样打字机输出

在 Web 或桌面端应用中，**流式传输 (Streaming)** 是标配。掌握 `astream` 的核心范式：

#### **核心逻辑：通过 `+` 运算符聚合碎片 (Aggregation)**
`AIMessageChunk` 具备一个神奇的特性：它们可以通过 `+` 自动聚合。这省去了手动维护状态的麻烦。

```python
# 工业级流处理模版 (Boilerplate)
full_response = None

async for part in agent.astream(input_dict, stream_mode="messages", version="v2"):
    if part["type"] == "messages":
        chunk, metadata = part["data"]
        
        # 1. 实时显示给用户
        if metadata.get("langgraph_node") == "model" and chunk.content:
            print(chunk.content, end="", flush=True)
            
        # 2. 自动聚合为完整消息，供后续逻辑（如存入数据库）使用
        full_response = chunk if full_response is None else full_response + chunk

print(f"\n\n最终完整回复: {full_response.content}")
```

#### **三大 Stream 模式选型矩阵**

| 方法 | 返回内容 | 适用场景 |
| :--- | :--- | :--- |
| **`stream_mode="messages"`** | **Token 碎片** | **首选**：实现打字机效果，响应最快。 |
| **`stream_mode="updates"`** | **节点增量** | 观察哪个节点（如 model, tools）运行完了，常用于调试日志。 |
| **`stream_mode="values"`** | **全量快照** | 每次状态更新都返回整个对话列表，适合简单的本地 CLI 交互。 |

- **深度参考**：
关于流切四态的选型矩阵，详见 [附录 A5：揭开流切四态切分仪之谜](../APPENDIX.md#a5-揭开流切四态切分仪之谜-stream_mode-matrix)。

---

## 🚀 实验验证 (Lab)
讲义到此结束。请打开 [01_Getting_Started.ipynb](./01_Getting_Started.ipynb) 文件：
1. **测试消息结构**：打印 `agent.invoke()` 的返回值，观察最后一条 `AIMessage` 中是否包含 `tool_calls`。
2. **测试流模式**：尝试切换三种不同的 `stream_mode`，结合上述结构说明，观察控制台输出的差异。

---
*Antigravity 教学规范体系 (2026)*