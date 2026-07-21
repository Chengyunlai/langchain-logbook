# 审计全书概念实验与工程迁移的倒置点

Status: resolved
Triage: ready-for-agent
Type: research
Blocked by:

## Why

全书已经包含大量正确结论和工程封装，但概念的首次出现常早于失败体验，最小示例又直接依赖 Mini DeerFlow。必须先建立信息依赖清单，才能避免只重排标题而没有改变学习过程。

## Question

逐节检查序章、第 01–11 章、工程专题和综合实战：学习者在看到术语、判断表或工程封装之前，是否已经亲手遇到需要该机制的问题？哪些代码只验证封装，哪些输出只用 `assert` 隐藏了执行过程？

## Acceptance

- 为模型调用、结构化输出、RAG、工具循环、Context、State、Store、Middleware、StateGraph、并行、Reducer、持久化、HITL、多 Agent、Sandbox、Gateway、评测与综合实战建立“前置能力 → 失败 → 新概念 → 最小实验 → 工程迁移”依赖表。
- 标记应保留、后移、拆分或重写的现有段落和 sync 实验。
- 给出第 07 章样章的具体缺口，不提前重写正文。
- 给出其余章节的改造强度和先后依赖，不能只写统一模板。
- 结果保存为本地图下的中文 Markdown 调查工件。

## Answer

已完成序章、第 01–11 章、7 篇工程专题和全部 Notebook 的逐篇审计，结果见[全书概念实验与工程迁移倒置审计](../research/01-full-book-concept-migration-audit.md)。

结论是课程“叙述上 problem-first，执行上 solution-first”。第 01–07、09、Sandbox 和 Capstone 需要结构性 P0 重写；第 08、11、Runtime/Gateway 和 Evaluation 需要 P1 补透明原生桥；第 10、Architecture、Lead Agent Core 和 DeerFlow Guide 以 P2 可观察输出与导航修正为主。

最严重的跨章倒置包括：完整 Agent 循环在第 01 与第 04 章重复争夺首次教学；Reducer 在第 05 章先讲、第 08 章才发生并行冲突；工具早于工具契约；Notebook 生成器丢失正文因果，只留下按类型分组的断言代码。

调查给出了逐篇强度、目标动作、第 07 章新顺序、Notebook 系统缺口和全书概念依赖。审计期间未修改任何教程，现有第 02 章 Notebook 改动保持不动。
