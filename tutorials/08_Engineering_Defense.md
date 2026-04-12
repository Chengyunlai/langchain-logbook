# 第 08 章：工程防御：安全断点与状态注入

## 💡 本章核心目标

在单体智能体转变为工业级应用的道路上，**安全可控**是最大的挑战。大模型常常会产生幻觉，如何防止 Agent 执行危险动作（如删表、转账、发送敏感邮件）？

本章将通过 LangGraph 的高级特性，掌握 Agent 的“工程防御”体系：如何设置安全断点实现“Human-in-the-loop (HITL)”（人机协同操作），如何动态注入和回溯状态（Time Travel 面向过去开发），以及如何利用 `InjectedState` 安全地传递上下文。

---

## 知识点一：Human-in-the-loop (HITL) 与断点 (Breakpoints)

在工业级 Agent 中，并非所有的决定都可以让大模型自己全权拍板。对于高危操作（如调用系统命令、修改数据库、发送外部消息），我们必须设置人工审批流。

- **为什么不用普通的 `input()`？**
传统的对话流通常是一问一答。但在 Graph 模式下，智能体可能自己循环思考了五步，突然打算调用“删除用户表”的工具。此时，整个图的执行必须**挂起 (Suspend)**，而非单纯阻塞。

- **LangGraph 的 `interrupt_before`**：
在编译 Graph 时，我们可以指定在哪些 Node 执行前强制暂停：

```python
from langgraph.graph import StateGraph

# builder = StateGraph(State)
# ... 配置节点与边 ...

# 关键设置：编译时指定断点，挂起执行，直到人工介入
graph = builder.compile(
    checkpointer=memory, # 必须有持久化
    interrupt_before=["execute_sensitive_tool"] # 在执行敏感工具前停下
)
```

当图执行到 `execute_sensitive_tool` 前，它会抛出特殊的空投事件停止。此时，我们可以将状态展示给用户（前端 UI 会显示审批框）。用户同意后，再驱动图继续往下走。

---

## 知识点二：状态更新与时间旅行 (Time Travel)

一旦 Graph 暂停，开发者（或有权限的用户）就可以直接修改图的状态。如果模型生成了一个错误的提议，我们不必让它重新思考，可以直接“覆写”它的决定，然后继续运行。

### 1. 更新当前状态 (Update State)

通过 `graph.update_state()`，你可以把人工纠偏的数据强行注入到状态字典中：

```python
# 假设状态停在了断点，模型打算执行 {"tool": "delete", "args": {"id": 1}}
# 我们拦截并手动修改它的意图
graph.update_state(
    config, 
    {"messages": [AIMessage(content="操作被管理员取消。")]},
    as_node="model" # 伪装成是模型自己改口的
)
# 继续运行图
graph.invoke(None, config)
```

### 2. 时间旅行 (Time Travel)

得益于 Checkpointer 每一层执行都保存了快照（Snapshot），你可以随时跳转回过去的历史节点，甚至以此为分叉点展开新的平行宇宙执行。这极大地方便了 Debug：

```python
# 获取历史快照
snapshots = list(graph.get_state_history(config))
past_config = snapshots[-3].config # 回到 3 步之前的状态

# 从过去的时间点重新执行，且覆盖原有的下一步操作
graph.invoke(None, past_config)
```

---

## 知识点三：InjectedState 与依赖倒置

在处理复杂工具时，我们可能需要传递当前对话的状态数据（如用户的权限 Token、当前购物车列表）给工具。但我们**绝不希望**让模型自己通过工具参数来编造这些敏感数据。

- **传统痛点**：如果将 token 直接给系统级 prompt，不仅增加消费，还容易被恶意截取。而且通过普通工具参数，模型也可以造假。
- **现代化解法 (`InjectedState`)**：把特定的状态直接注入到工具的上下文中。模型在调用工具时不需要也看不见这个参数，但 LangGraph 框架会在后台自动补齐它。

```python
from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def process_refund(order_id: str, current_role: Annotated[str, InjectedState("user_role")]):
    """处理退款。模型不知道 current_role，框架自动从 State 注入。"""
    if current_role != "admin":
        return "权限不足！"
    return f"订单 {order_id} 退款成功。"
```

在这里，模型视角下的工具 Schema 只有 `order_id` 一个参数，而 `current_role` 由框架从外部直接注水进入。这就是工程上的依赖倒置，确保了绝对的安全边界。

---

## 🚀 实验验证 (Lab)

请打开 `08_Engineering_Defense.ipynb` 体验实战：

1. 尝试构建一个简单的带有 `delete_file` 工具的智能体。
2. 配置 `interrupt_before` 断点，看代码是如何优雅暂停的。
3. 手动获取 `get_state`，尝试同意或拒绝审批，再驱动 Agent。
4. 使用 `InjectedState` 建立一个带有管理员上下文隔离的工具。

---
*Antigravity 教学规范体系 (2026)*
