# 建立当前 LangChain/LangGraph 官方能力基线

Status: resolved
Triage: ready-for-agent
Type: research
Blocked by:

## Why

现有教程同时包含 LangChain 1.2.x、LangGraph 1.1.x 和历史 API。若没有基线，后续重写很容易继续混用旧式 Agent、LangServe、过期评测接口或不一致的流式协议。本任务为全部章节提供可信事实来源。

## Question

当前 LangChain、LangGraph、LangSmith 官方推荐的 Agent 开发路径、核心 API、项目结构、持久化、HITL、多 Agent、测试、评测和部署方式分别是什么？哪些优质官方教程和示例最适合转化为本项目的中文教学实验？

## Work

- 读取官方文档索引、迁移指南、API 示例、模板仓库和 release notes。
- 建立“能力 → 官方来源 → 推荐示例 → 本项目落点 → 版本风险”矩阵。
- 明确 `create_agent`、Agent Middleware、Runtime Context、Graph State、Store、Command、Send、Interrupt、Subgraph、Streaming 和 Deployment 的当前规范。
- 所有结论记录直接链接，避免只写二手摘要。

## Acceptance

- 产出一份中文、带官方链接的研究文档。
- 覆盖课程目标所需的全部核心能力，不只列 API 名称。
- 标记旧 API、兼容 API和当前推荐 API。
- 给出后续教程可复用的官方示例清单和引用边界。

## Answer

已完成官方生态基线研究，完整报告见 [LangChain / LangGraph / LangSmith 官方 Agent 开发能力基线](../artifacts/01-official-ecosystem-baseline.md)。报告只使用 LangChain 官方文档、`langchain-ai` 官方 GitHub 仓库、官方 Release 与官方模板，并以 2026-07-13 为快照日期。

### 已确认结论

1. 课程主入口应使用 `langchain.agents.create_agent`；`langgraph.prebuilt.create_react_agent` 只保留在旧教程迁移说明中。
2. Agent 治理必须以真正的 `AgentMiddleware` hooks 为主，Runnable listeners/fallbacks 只能作为底层能力补充。
3. Runtime Context、Graph State、Checkpointer 与 Store 必须分开建模和教学。
4. Graph API 与 Functional API 是共享 LangGraph runtime 的两种表达方式，不是新旧替代关系。
5. `Command`、`Send`、动态 `interrupt()`、durable execution、幂等副作用和故障恢复应进入核心课程，而不是附录。
6. 多 Agent 应区分 Router、Handoff、Skills、Subgraph、Subagent-as-tool 和 Custom Workflow；Mini DeerFlow 主线采用有状态 Lead Agent + 隔离型 subagents。
7. 稳定流式主线使用 v2 `StreamPart`，即 `type/ns/data` 事件结构；v3 event streaming 当前仍作为预览能力隔离。
8. LangServe 已弃用并归档，部署主线迁移为可导入包、`langgraph.json`、Agent Server/SDK；自建 Gateway 作为进阶架构对照。
9. 确定性行为使用离线 pytest/fake model，Agent 质量再使用轨迹评测、LangSmith experiment 与线上反馈闭环。
10. 课程必须锁定一组已验证依赖，同时保留兼容范围和升级检查；旧 checkpoint 恢复属于版本升级验收的一部分。

### 版本快照

- `langchain 1.3.13`
- `langchain-core 1.4.9`
- `langgraph 1.2.9`
- `langsmith 0.10.2`

当前仓库锁文件仍为 `langchain 1.2.14 + langgraph 1.1.4`。后续版本任务需要先运行兼容性测试，再决定是否升级，不能仅修改 README 中的版本号。

### 验证

- 报告共 384 行，包含完整能力矩阵、官方教程复用清单、逐章调整建议、Mini DeerFlow 能力映射和 3 张 Mermaid 图。
- 主线程复核了关键 API、本地签名、版本 Release 页面和 LangServe 归档状态。
- `git diff --check` 通过。
