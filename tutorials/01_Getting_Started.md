# 第 01 章：环境配置与智能体底层逻辑

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
| **`AIMessage`** | 模型 (LLM) | 模型做出的决策或回复。如果包含 `tool_calls` 列表，说明模型请求调用工具。 |
| **`ToolMessage`** | 工具 (Tool) | 存储工具运行的结果，用于回传给模型。**必须包含 `tool_call_id`**。 |
| **`SystemMessage`** | 系统 (Developer) | 预设的全局指令，规定了智能体的人设与边界。 |

- **⚠️ 误区纠正**：用户输入并不是 `AIMessage`。对话是不同角色的消息在 `State`（状态台账）中不断追加的过程。具体的 `AIMessage` 结构细节详见 [附录 A2：现代 Agent 的包裹状态引擎特征](../APPENDIX.md#a2-现代-agent-的包裹状态引擎特征)。

---

## 知识点四：驱动模式 (Invoke vs Streaming)

Agent 提供了多种驱动方式，选择哪一种取决于你对“过程可见性”的要求。

### 1. 三大核心方法对比

| 方法 | 运行模式 | 返回行为 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **`invoke()`** | 同步阻塞 | **最终状态**：仅在所有循环结束后返回。 | 自动化脚本、批处理、单元测试。 |
| **`stream()`** | 同步迭代 | **分块包裹**：运行中实时推送中间状态。 | 本地命令行交互、日志监控。 |
| **`astream()`** | **异步迭代** | **分块包裹**：非阻塞实时推送，性能更高。 | **2026 生产标配** (FastAPI, React)。 |

#### **代码直觉对比**

```python
# A. invoke: 一次性拿结果
result = agent.invoke({"messages": [("user", "你好")]})
print(result["messages"][-1].content) # 只能看到最后一句回复

# B. stream/astream: 边走边看
async for part in agent.astream(input_dict, stream_mode="messages", version="v2"):
    # 你可以拦截到每一个字符，甚至是工具正在被调用的瞬间
    pass
```

### 2. 核心模式的返回结构 (v2 协议)

当使用 `version="v2"` 时，产生的每个碎片 (`chunk`) 都是一个字典，其 `data` 字段结构如下：

#### **模式 A: `stream_mode="values"` (全量快照)**

- **作用**：每次节点变更后，返回当下的“全量台账”。
- **返回结构**：

```python
{
  "type": "values",
  "data": { "messages": [HumanMessage(...), AIMessage(...)], "other_key": "..." }
}
```

#### **模式 B: `stream_mode="updates"` (节点增量)**

- **作用**：告诉你当前哪个节点运行完了，它改动了什么。
- **返回结构**：

```python
{
  "type": "updates",
  "data": { "model": { "messages": [AIMessage(...)] } } # key 是节点名称
}
```

#### **模式 C: `stream_mode="messages"` (Token 碎片 - 推荐)**

- **作用**：实时推送 LLM 吐出来的每一个字符。
- **返回结构 (Tuple)**：

```python
{
  "type": "messages",
  "data": (message_chunk, metadata) # metadata 中包含 langgraph_node 等发件信息
}
```

### 3. 处理最佳实践

```python
# 明确开启 v2 标准，杜绝解包报错
async for part in agent.astream(input_dict, stream_mode="messages", version="v2"):
    if part["type"] == "messages":
        message, metadata = part["data"]
        # 拦截：排除工具执行日志，只看模型的回复文本
        if metadata.get("langgraph_node") == "model" and message.content:
            print(message.content, end="", flush=True)
```

- **深度参考**：
关于流切四态的选型矩阵，详见 [附录 A5：揭开流切四态切分仪之谜](../APPENDIX.md#a5-揭开流切四态切分仪之谜-stream_mode-matrix)。

---

## 🚀 实验验证 (Lab)
讲义到此结束。请打开 [01_Getting_Started.ipynb](./01_Getting_Started.ipynb) 文件：
1. **测试消息结构**：打印 `agent.invoke()` 的返回值，观察最后一条 `AIMessage` 中是否包含 `tool_calls`。
2. **测试流模式**：尝试切换三种不同的 `stream_mode`，结合上述结构说明，观察控制台输出的差异。

---
*Antigravity 教学规范体系 (2026)*
