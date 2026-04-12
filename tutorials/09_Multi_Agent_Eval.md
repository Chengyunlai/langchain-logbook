# 第 09 章：实战演练：多智能体协作与质检

## 💡 本章核心目标

目前为止，我们已经掌握了打造单个超级特工（Agent）的所有武器库。但在 2026 年的生成式 AI 工程中，复杂系统往往是由多个职责专一的“小特工”协作完成的（Multi-Agent Architecture）。

本章重点：
1. 理解如何利用 LangGraph 的 `SubGraph` 特性，构建多智能体分层协作系统。
2. 将我们的 Agent 工程整合进持续集成环境，利用 LangSmith Evaluation 进行智能材质检。

---

## 知识点一：多智能体协作 (Multi-Agent Routing)

多智能体系统的核心不是模型大，而是**低耦合、高内聚**。我们可以让“路由节点”或者一个“主 Agent”根据情况调度不同的“子 Agent”。

- **范式：主从架构（Supervisor Pattern）**
一个 Supervisor Agent 负责接客，将其拆解并分发给 Researcher Node 或 Coder Node，两者做完后交回给 Supervisor 汇报。

在 LangGraph 中，因为节点本身可以是一个复杂函数，甚至可以是**另一个编译好的图 (Compiled Graph)**，这就天然支持了多智能体的嵌套：

```python
from langgraph.graph import StateGraph

# 构建子图 1: 研究员
researcher_graph = StateGraph(ResearchState)
# ... 给研究员配置工具节点 ...
researcher = researcher_graph.compile()

# 构建子图 2: 程序员
coder_graph = StateGraph(CoderState)
# ... 给程序员配置代码解释器 ...
coder = coder_graph.compile()

# 构建主图: 组长
supervisor_graph = StateGraph(GlobalState)
supervisor_graph.add_node("researcher_team", researcher) # 直接插入 Compiled Graph
supervisor_graph.add_node("coder_team", coder)

# 然后通过条件边让组长路由任务
```

将子图作为节点插入，不仅隔离了状态 (`State`) 名称空间，还让每一个智能体团队都可以单独进行测试和 Debug。

---

## 知识点二：工业级质检：LangSmith Evaluation

大模型应用最大的痛点是“改了一个 Prompt，不知道会不会影响其他 100 个场景”。
在 2026 年，我们绝不允许“蒙着眼睛上线”。

LangSmith 提供了无缝的 Eval 框架：
1. **建立数据集 (Dataset)**：收集线上的真实用户 Query 和期望回答。
2. **定义评估器 (Evaluator)**：编写判断逻辑（是普通的 Python `==` 判断，还是用另一个 LLM 来打分：LLM-as-a-judge）。
3. **执行测试 (Evaluate)**：一键对所有数据点跑测。

```python
from langsmith.evaluation import evaluate, LangChainStringEvaluator

# 1. 准备大模型裁判
qa_evaluator = LangChainStringEvaluator("qa")

# 2. 从 LangSmith 拉取数据集并开跑
results = evaluate(
    lambda x: agent.invoke(x),       # 目标函数：我们的 Agent
    data="my-production-dataset",    # LangSmith 上的数据集名称
    evaluators=[qa_evaluator],       # 使用 QA 打分员裁判
    experiment_prefix="v1.2_update"  # 实验批次号
)
```

通过这一层面的集成，我们的每一次 Prompt 变更都会生成一张测试报告（准确率、跑测耗时等），实现类似传统软件的 CI/CD 防护网。

---

## 知识点三：从 Notebook 到 API 交付 (Deployment via LangServe)

当我们在 Jupyter Notebook 中打磨好模型后，最终要交付给前端调用。LangChain 的配套组件 **LangServe** 可以一行代码将 `Runnable`（包括我们的 Graph）转化为生产级 FastAPI 接口。

它的内部实现了对 `stream`, `invoke`, `batch` 的全面 RESTful 支持，并自带了 OpenAPI 文档：

```python
from fastapi import FastAPI
from langserve import add_routes

app = FastAPI(title="Company Agent API")

# 只需一行代码，无缝挂接已经编译好的 LangGraph
add_routes(app, compiled_graph, path="/my-agent")

# 通过 python -m uvicorn server:app 即可启动服务
```

前端可以通过官方提供的 `@langchain/core/remote` (TS) 直接以流式的方式对接 API，就像在本地调用一样顺滑。

---

## 🚀 实验验证 (Lab)

请打开 `09_Multi_Agent_Eval.ipynb` 文件，开始我们最终的实战验收：

1. 实现一个微型的“主从协作网络”。
2. (可选) 到 LangSmith 平台上创建一个测试数据集。
3. 把所有的知识点串联，欣赏我们的智能体生态。

*恭喜你，完成了 LangChain 1.2+ Agent-First 实战教程的所有核心内容。The Future is Built by Agents.*

---
*Antigravity 教学规范体系 (2026)*
