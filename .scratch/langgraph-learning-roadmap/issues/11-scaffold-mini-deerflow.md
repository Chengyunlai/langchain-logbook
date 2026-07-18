# 设计并搭建 Mini DeerFlow 工程骨架

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 02, 04, 06

## Why

学习者必须从 Notebook 过渡到真实 Python 项目。工程骨架负责承接逐章产物，并为测试、部署和 DeerFlow 源码映射提供稳定边界。

## Work

- 建立包结构、配置、依赖注入、Agent 工厂和 `langgraph.json`。
- 设计 state、middlewares、tools、subagents、sandbox、runtime、api、tests、evals 模块边界。
- 提供 fake model 与本地默认配置，让核心流程无需付费 API 即可验证。
- 编写架构总览和开发命令。

## Acceptance

- 项目可以安装、导入、构图并运行最小对话。
- 模块名称与课程术语一致，但不复制 DeerFlow 私有复杂度。
- 每个后续课程任务都有明确落点。
- 工程骨架拥有最小测试和清晰的扩展接口。

## Answer

已完成 Mini DeerFlow 的正式工程骨架。`mini_deerflow.app` 现在是唯一组合模块：`ApplicationSettings` 与 `ApplicationDependencies` 分离非敏感配置和活依赖，`build_application()` 为本地 CLI/测试绑定独享内存持久化，`make_graph()` 则作为 `langgraph.json` 的 Agent Server factory，不绑定 Checkpointer/Store。

新增 `runtime/`、`api/`、`sandbox/`、`evals/` 的真实契约和架构依赖测试；默认 fake model 可在同一应用上重复完成真实 model → tool → model 循环；`python -m mini_deerflow` 与 `make mini-deerflow` 提供无 Key smoke path。完整架构、时序、数据边界、后续任务落点和 DeerFlow 固定提交映射见[实现记录](../artifacts/11-mini-deerflow-scaffold.md)与 [`mini_deerflow/ARCHITECTURE.md`](../../../mini_deerflow/ARCHITECTURE.md)。

最终验证为 `90 passed, 1 skipped`，教程债务 `0/0/0`，wheel 包含全部新子包，文档站 25 页/Pagefind 15 页/断链 0；Standards 与 Spec 双轴复审均为 `CLOSED`。
