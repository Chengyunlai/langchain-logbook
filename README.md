# 🦜🔗 LangChain 1.2.x Agent-First 航海日志 (2026)

欢迎来到 2026 年最新的 LangChain 实战项目。本项目致力于以“教科书级”的严谨性，带你征服大模型时代最前沿的智能体工程。

### 🌐 [在线预览 (Online Preview)](https://HappyFrame.github.io/langchain-logbook/)

*(注：推送代码至 GitHub 后会自动更新)*

---

## 🗺️ 全局大观 (Global Big Picture)

在 2026 年，LangChain 1.2.x 已经演化为一个分层明确、高度解耦的工业级操作系统：

1.  **统一算子层 (Runnable Protocol)**: 所有的 Prompt、LLM、Retriever 都是 `Runnable`。这意味着它们具备统一个标准接口：`invoke` (同步), `ainvoke` (异步), `stream` (流式)。
2.  **感知与动作层 (Perception & Action)**: 
    *   **Models**: 通过 `init_chat_model` 屏蔽了不同 Provider (DeepSeek, OpenAI, Anthropic) 的差异。
    *   **Tools**: Agent 的手脚，通过 Schema 显式定义。
3.  **状态编排层 (LangGraph Evolution)**: 这是 1.x 的核心。Agent 不再是简单的链，而是一个“图 (Graph)”，通过节点跳转和状态持久化实现复杂的逻辑循环。
4.  **治理与观测层 (Governance & Observability)**: 
    *   **Middleware**: 在 Agent 运行的中途插入“中间件”（如隐私脱敏、审核、记录）。
    *   **LangSmith**: 全生命周期的追踪与评估。

---

## 🏛️ 教学约定 (Conventions)

本教程遵循图灵级技术书籍的编写标准，你在学习过程中会看到以下图标：

*   💡 **原理剖析 (Insight)**：对底层机制或历史演进的深度挖掘。
*   ⚠️ **避坑指南 (Warning)**：生产环境中的常见错误或 API 弃用警告。
*   🚀 **最佳实践 (Best Practice)**：行业标准的性能优化或代码组织方案。

---

## ⚓ 课程看板 (Course Roadmap)

| 状态 | 章节名称 | 核心知识点 |
| :--- | :--- | :--- |
| ✅ | [**01: 环境配置与 DeepSeek 启航**](./tutorials/01_Getting_Started.md) | Agent-First 理念, create_agent, stream_mode |
| ✅ | [**02: 结构化输出与模型特征 (Pydantic)**](./tutorials/02_Structured_Output.md) | .profile, with_structured_output, 复合 Schema |
| ✅ | [**03: RAG 2.0: 增强型数据检索**](./tutorials/03_RAG_2.0.md) | Vector Distribution, Indexing API, Context Filter |
| ✅ | [**04: 高级工具调用 (Smart Tooling)**](./tutorials/04_Smart_Tooling.md) | Context Injection, Schema Adherence |
| ✅ | [**05: Agent 中间件 (Middleware)**](./tutorials/05_Agent_Middleware.md) | PII Redaction, Human-in-the-loop, Retries |
| 🔄 | **06: 基础设施：可观测性与持久化** | LangSmith Tracing, Checkpointer, MemorySaver |
| ⬜ | **07: 核心编排：StateGraph 状态机** | TypedDict State, Nodes & Edges, Conditional Edges |
| ⬜ | **08: 工程防御：安全断点与状态注入** | Breakpoints (HITL), InjectedState, Time Travel |
| ⬜ | **09: 实战演练：多智能体协作与质检** | Multi-Agent, LangSmith Eval, API Deployment |

---

## 🚀 快速开始 (Quick Start)

为了简化环境配置和日常开发，项目提供了 `Makefile` 工具。如果你是第一次使用，可以按照以下步骤操作：

1. **环境初始化**:
   - 如果你还没有安装 `uv` (推荐的 Python 包管理工具)，可以运行：
     ```bash
     make install-uv
     ```
   - 初始化虚拟环境并创建 `.env` 文件：
     ```bash
     make setup
     ```
   - 编辑 `.env` 文件，填入你的 API Key (如 OpenAI 或 DeepSeek)。

2. **安装依赖**:
   ```bash
   make install
   ```

3. **启动学习**:
   - 运行 Jupyter Notebook 以交互式学习教程：
     ```bash
     make notebook
     ```
   - 或者运行 Jupyter Lab：
     ```bash
     make lab
     ```

4. **清理环境**:
   ```bash
   make clean
   ```

---

## 🛠️ 环境依赖

- **Python**: 3.12+ (uv 驱动)
- **核心库**: `langchain==1.2.14`, `langgraph==1.1.4`
- **附录查阅**: [APPENDIX.md](./APPENDIX.md) 包含了底层协议的深度细节。

---
*Antigravity 教学体系 (2026)*
