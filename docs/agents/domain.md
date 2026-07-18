# 领域文档使用约定

本项目采用单上下文结构，用一套统一语言描述课程、示例和最终实战项目。

## 开始工作前需要阅读

- 根目录 `CONTEXT.md`：课程领域词汇和概念边界。
- `docs/adr/`：与当前修改相关、难以逆转的架构决策；目录不存在时无需提示。
- `.scratch/langgraph-learning-roadmap/map.md`：当前大型改造的目的地、执行原则和已确认决策。

## 使用统一术语

- 任务标题、章节标题、测试名称和架构说明应优先使用 `CONTEXT.md` 中确定的词汇。
- 不要把 Runtime Context、Graph State、Checkpointer、Store 和业务数据库都笼统称为“内存”。
- 不要把 Runnable 包装器、Agent Middleware 和 Graph Node 都笼统称为“中间件”。
- 如果新增概念无法使用现有词汇准确表达，应先更新领域模型，再在教程中扩散该术语。

## ADR 冲突

如果后续实现与已有 ADR 冲突，必须显式指出冲突和重新决策的理由，不得静默覆盖。
