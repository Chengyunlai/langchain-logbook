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
    model_provider="deepseek", # 底层协议驱动
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
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

#### **核心思想：理解 astream 的“心智模型”**

很多新手会困惑：为什么要写那么多 `if` 判断？为什么要用 `+` 聚合？我们可以把 Agent 的运行想象成一场**多方参与的实时广播**。

1. **为什么判断 `part["type"] == "messages"`?**
   `astream` 是全能的，它不仅推送消息，还会推送状态更新（updates）、全量快照（values）等。通过判断 `type`，我们相当于在收音机上切到了“语音频道”，过滤掉了数据信号。

2. **为什么判断 `metadata.get("langgraph_node") == "model"`?**
   在一个复杂的 Agent 体系中，可能有多个节点在说话（比如：一个节点在反思，一个节点在调用工具，一个节点在最终回复）。
   - **痛点**：在 Web UI 中，用户通常**只想看到最终的 AI 回复**，而不想看到中间的“内心戏”或工具运行的原始日志。
   - **解法**：通过 `langgraph_node` 过滤，我们只把来自 `model` 节点的文本显示在终端或前端。

3. **为什么使用 `+` 聚合 (AIMessageChunk)?**
   LLM 生成内容是像“挤牙膏”一样一个字一个字出来的。
   - **碎片 (Chunks)**：为了让用户感觉响应快，我们需要实时分发这些碎片。
   - **完整包 (Full Message)**：但在程序结束时，我们需要一个完整的、带元数据的消息对象存入数据库或记忆中。
   - **LangChain 魔法**：`AIMessageChunk` 重载了 `+` 运算符。你不需要手动拼接字符串，直接 `chunk1 + chunk2`，它会自动帮你把文本、Token 统计、工具调用 ID 全部完美合并。

#### **工业级流处理模版 (Boilerplate)**

这套模版是 2026 年处理 Agent 输出的标准姿势。建议直接复用：

```python
# full_response 是我们程序需要的“最终成品”
full_response = None

async for part in agent.astream(input_dict, stream_mode="messages", version="v2"):
    if part["type"] == "messages":
        chunk, metadata = part["data"]
        
        # 1. 业务逻辑：判断发件人，只有 model 节点的文本才展示给前端
        # 如果你有自定义节点名，可以在这里修改判断逻辑
        if metadata.get("langgraph_node") == "model" and chunk.content:
            # 实时推送到 UI
            print(chunk.content, end="", flush=True)
            
        # 2. 状态逻辑：积累碎片
        # 只要是 model 发出的，我们就往成品里堆叠
        if metadata.get("langgraph_node") == "model":
            full_response = chunk if full_response is None else full_response + chunk

# 运行结束，可以把成品存入数据库或上下文
print(f"\n\n[系统通知] 消息处理完毕，总消耗 Token: {full_response.usage_metadata}")
```

---

## 5. 举一反三：自定义你的 Prompt 管道

### 1. 组织输入的“三层结构”

在真实程序中，不要每次都手动写元组列表。通常采用以下心智模型：

- **System 层**：定义人设、工具使用规范（通常硬编码或从配置读取）。
- **History 层**：从数据库读取之前的对话，转化为 `HumanMessage`/`AIMessage`。
- **User 层**：当前的实时输入。

```python
def prepare_inputs(user_query: str, chat_history: list):
    # 将业务数据转化为 Agent 理解的“全量协议”
    return {
        "messages": [
            ("system", "你是一个资深专家..."),
            *chat_history,
            ("user", user_query)
        ]
    }
```

- **深度参考**：
关于流切四态的选型矩阵，详见 [附录 A5：揭开流切四态切分仪之谜](../APPENDIX.md#a5-揭开流切四态切分仪之谜-stream_mode-matrix)。

---

## 🆘 常见问题与调试 (Troubleshooting)

在实战过程中，你可能会遇到以下两类典型问题：

### 1. 连通性错误 (ConnectError / APIConnectionError)

**现象**：提示 `SSL_ERROR_SYSCALL` 或 `Connection error`。

**原因**：通常是由于本地网络无法直接访问 `api.deepseek.com`（防火墙或 SSL 拦截）。

**对策**：

- **网络诊断**：在 Notebook 中运行以下片段测试：

  ```python
  import requests
  try:
      r = requests.get("https://api.deepseek.com", timeout=5)
      print(f"连通成功：{r.status_code}")
  except Exception as e:
      print(f"连接失败: {e}")
  ```

- **使用代理**：在 `.env` 中配置 `HTTPS_PROXY`，或尝试使用国内镜像（如阿里云百炼）。

### 2. 语法错误 (Parse Error)

**现象**：`Simple statements must be separated by newlines or semicolons`。

**原因**：Jupyter 单元格中的两行代码被意外合并到了同一行，且中间没有分号。

**对策**：确保每条 Python 语句独占一行，或者使用 `;` 明确分隔。

---

## 🚀 实验验证 (Lab)

讲义到此结束。请打开 [01_Getting_Started.ipynb](./01_Getting_Started.ipynb) 文件：

1. **测试消息结构**：打印 `agent.invoke()` 的返回值，观察最后一条 `AIMessage` 中是否包含 `tool_calls`。
2. **测试流模式**：尝试切换三种不同的 `stream_mode`，结合上述结构说明，观察控制台输出的差异。

---
*Antigravity 教学规范体系 (2026)*
