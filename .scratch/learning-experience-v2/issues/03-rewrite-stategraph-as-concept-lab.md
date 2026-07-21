# 用双层案例重写第 07 章 StateGraph

Status: open
Triage: ready-for-agent
Type: task
Blocked by: 02

## Why

第 07 章是学习者建立 LangGraph 心智模型的入口。当前正文在读者亲手搭建并行 Graph 之前介绍 Reducer，无法形成“冲突发生 → 需要合并协议”的因果链。

## Work

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
- 现有显式 ReAct、streaming、循环预算等内容被合理后移或保留，不丢失工程深度。
