# 从概念实验到 Mini DeerFlow 的课程迭代地图

## Destination

把全部 Web 章节和 Jupyter 练习改造成一条适合初学者动手推导的 LangChain / LangGraph 学习路线。

每个新概念先在透明、最小、可运行的“概念实验室”中由真实失败引出，再迁移到 Mini DeerFlow。

最终由未参与改写的初学者验收 Agent 从头盲读，证明学习者能解释机制、完成练习并读懂 Mini DeerFlow。

## Notes

- 本地图承载决策和后续实施。`task` 类型可以直接修改教程、Notebook、站点文章、同步工具和测试；每次只解决一个前沿任务。
- 写作使用 `edit-article`：信息依赖先于术语顺序，每段不超过 240 个字符。
- 主线是 LangChain / LangGraph 心智模型与最小实验；Mini DeerFlow 是第二层工程迁移和跨章整合，不再承担概念的首次解释。
- 概念实验室不得导入 `mini_deerflow`，控制在 20–60 行；先展示错误或错误结果，再只增加当前概念，并打印 State、事件、patch、Reducer 或执行顺序。
- 工程迁移必须明确指出 Mini DeerFlow 比最小实验增加了哪些安全、持久化、抽象和测试边界；保留现有工程深度，不以删减内容换取易读性。
- 全部章节都进入改造范围。第 07 章先作为教学结构样章校准粒度，随后重写第 05、06 章并扩展到第 01–04、08–11 章、工程专题与综合实战。
- 最终盲读使用全新子 Agent：不继承改写对话，不读取规划和实现讨论，只假设具备基础 Python；课程明确要求前不得查看 Mini DeerFlow 源码、测试答案或任务地图。
- 第一次盲读只记录阻塞，不由主 Agent 现场解释；修复后必须更换另一个全新子 Agent 复验，避免熟悉度伪装成可理解性。
- 当前工作区已有 `tutorials/02_Structured_Output.ipynb` 的未提交修改，所有任务必须保留并避开这项改动。

## Decisions so far

- [审计全书概念实验与工程迁移的倒置点](./issues/01-audit-concept-migration-inversions.md) — 已按 P0/P1/P2 标出全书改造强度，并确认 Notebook 因果与可观察输出需要独立契约。
- [定义双层案例章节契约与可观察反馈格式](./issues/02-define-two-layer-lesson-contract.md) — 定义 lesson-lab、稳定输出、Notebook 原序生成和概念/迁移自动边界。
- [用双层案例重写第 07 章 StateGraph](./issues/03-rewrite-stategraph-as-concept-lab.md) — 12 个连续实验已跑通，并由 v2 同步器和 validator 锁定顺序、输出与两层边界。
- [评审第 07 章双层案例样章](./issues/04-review-stategraph-sample.md) — 用户确认全书按样章方向改造；内部 marker 只存在于课程源，不进入 Web。
- [从“万能 State”失败重写第 05 章 Context Engineering](./issues/05-rewrite-context-from-universal-state-failure.md) — 由真实失败推导四类数据边界，9 个实验已跑通。
- [从重复治理逻辑重写第 06 章 Middleware](./issues/06-rewrite-middleware-from-duplication.md) — 从权限遗漏推导四类 hook，14 个 Web/Notebook 实验已跑通。

## Frontier

- [把双层案例扩展到其余章节](./issues/07-propagate-two-layer-cases.md) — 正在执行；第 01–09 章已完成，下一步从“恢复会重跑节点”重写第 10 章 interrupt、resume 与幂等副作用。

## Not yet specified

- 纯文本 transcript 是否足以表达复杂并发与恢复，要在第 07 章样章和后续初学者盲读中验证；当前不提前建设交互式 trace 组件。

## Out of scope

- 在 Web 页面中嵌入远程 Python 执行环境；本轮以可复制代码、已执行 Notebook 和确定性输出为反馈闭环。
- 降低 Mini DeerFlow 的工程完整性，或删除持久化、安全、评测、Sandbox、Gateway 与 DeerFlow 源码映射。
- 用另一套教学 Demo 替换 Mini DeerFlow；两层案例共享业务情境，但承担不同教学职责。
