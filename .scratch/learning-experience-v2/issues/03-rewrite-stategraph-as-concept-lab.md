# 用双层案例重写第 07 章 StateGraph

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 02

## Why

第 07 章是学习者建立 LangGraph 心智模型的入口。当前正文在读者亲手搭建并行 Graph 之前介绍 Reducer，无法形成“冲突发生 → 需要合并协议”的因果链。

## Work

- 先升级 Notebook 同步器与教程 validator，使其能解析 `lesson-lab` marker、保留正文顺序、同步预测/解释/修改提示，并核对稳定输出。
- 从普通函数和共享字典开始，逐步引出 State、Node、Edge 与 Conditional Edge。
- 搭建 `plan → search_docs/search_web → summarize` 的最小并行 Graph。
- 先制造并发写冲突，再依次实验 `operator.add` 的正确用途、错误用途和按 ID 合并的自定义 Reducer。
- 输出运行前 State、节点 patch、合并过程和运行后 State。
- 完成概念实验后，再映射到 Mini DeerFlow 的 `artifacts` 与 `middleware_trace` reducer。
- 同步并执行 Notebook，更新站点文章与专项测试。

## Acceptance

- Reducer 首次出现前，读者已经运行并看到真实并发冲突。
- 最小实验不导入 `mini_deerflow`，每一步只增加一个机制。
- Web 文章展示可观察执行记录，Notebook 允许修改 reducer 后重跑。
- Mini DeerFlow 只在工程迁移阶段出现，并明确说明额外封装的理由。
- 第 07 章通过 `lesson-lab` marker、概念层导入、failure/repair 顺序、Web 输出与 Notebook output drift 自动检查。
- 现有显式 ReAct、streaming、循环预算等内容被合理后移或保留，不丢失工程深度。

## Answer

已把第 07 章重写为 12 个连续 lesson lab。读者先从单节点 patch、串行边和条件边建立执行直觉，再亲手触发并行写冲突；Reducer 只在冲突证据之后出现。

并行部分先用 `operator.add` 修复 append-only 搜索结果，再制造任务表重复的静默错误，最后从零实现按 ID 替换的自定义 reducer。

显式 ReAct、`updates` / `values`、recursion limit 与业务预算均保留为可执行概念实验。

Mini DeerFlow 只在最后一个 migration lab 导入。该实验同时对照显式 ReAct factory、`merge_artifacts()` 与 append-only `middleware_trace`，解释工程层新增的类型、安全、持久化和回归边界。

同步器现可解析 v2 marker，按 Markdown 原序生成“预测 → 代码与 stdout → 解释 → 修改”单元；概念层之前不再注入 Mini DeerFlow。

执行器使用独立 Python module namespace，使本地 `Annotated` State schema 可被 LangGraph 正确解析。

validator 已实现 v2 opt-in、marker / id、概念层导入、输出、assert-only、failure / repair 相邻性、migration 顺序、Notebook 顺序、stdout 和教学文本检查，并提供 `--require-v2-all` 最终发布模式。

验证证据：本章 12 个 lab 已离线执行并同步 Notebook；`make check` 通过 168 项测试（1 项外部集成跳过），教程 validator 为 0 new / 0 known / 0 stale。

Astro 构建、站内链接、发布契约与 SEO 检查全部通过。
