# 全书概念实验与工程迁移倒置审计

审计范围：序章、第 01–11 章、7 篇 Mini DeerFlow 工程专题、全部生成 Notebook。审计只读取当前课程，不修改教程；`tutorials/02_Structured_Output.ipynb` 的既有未提交修改保持不动。

## 1. 总结

当前课程的主要问题可以概括为：**叙述上 problem-first，执行上 solution-first**。

章节开头通常能说明业务痛点，但学习者还没运行错误版本、看到 State 或事件怎样出错，就进入术语、正确架构和 Mini DeerFlow 封装。故障实验往往放在正确实现之后，Web 又只展示 `assert`，所以读者必须相信结论，无法亲手推导结论。

改造强度定义：

- **P0**：教学因果倒置或核心结论缺乏证据，必须重排、拆分或更换首次实验。
- **P1**：主线基本成立，但需要增加透明原生实验、真实失败或可观察输出。
- **P2**：结构可保留，主要补输出、导航、反向链接或措辞。

## 2. 量化证据

| 章节 | sync 实验 | `mini_deerflow` 导入 | `assert` | `print` | 判断 |
| --- | ---: | ---: | ---: | ---: | --- |
| 01 | 5 | 6 | 11 | 10 | 已有可见输出，但 Agent 循环与第 04 章职责冲突 |
| 02 | 5 | 6 | 11 | 2 | 业务 Schema 首次运行直接依赖工程封装 |
| 03 | 6 | 4 | 11 | 0 | 检索、索引、评测都看不到命中过程 |
| 04 | 6 | 8 | 9 | 1 | 一章提前实现 Context、Command、Reducer 与 Sandbox |
| 05 | 7 | 7 | 13 | 0 | 判断表和 Repository 早于所有权失败 |
| 06 | 11 | 9 | 20 | 0 | Middleware 结果全部由断言验证 |
| 07 | 3 | 3 | 6 | 0 | 标题说“观察”，实际没有状态或 patch 输出 |
| 08 | 6 | 2 | 21 | 0 | 原生失败较好，成功路径仍由 workflow factory 隐藏 |
| 09 | 6 | 2 | 15 | 0 | 读取完成快照，未证明中途失败后的 durable execution |
| 10 | 7 | 3 | 18 | 0 | 失败链较完整，需要把 interrupt 与重放证据显示出来 |
| 11 | 12 | 13 | 40 | 1 | 模式很多，成功路径大量隐藏在 `build_*` 封装中 |

生成 Notebook 进一步放大了问题：除第 01、09、10、11 章外，多数 Notebook 没有任何已保存的可见输出；第 05 章有 9 个代码单元、8 个断言单元、0 个输出。Notebook Markdown 又主要是通用“最小成功实验/状态观察/失败实验”标题，没有带入正文的因果解释。

## 3. 全局依赖倒置

### 3.1 “第一次完整 Agent 循环”出现了三次

第 01 章已经完整运行 `create_agent`，README 和第 03 章却都把第 04 章描述为第一次观察工具循环。第 04 章的核心问题在学习者到达之前已经被解决。

目标归属：第 01 章只保留模型调用、消息、Runnable、tool intent 和基础事件；第 04 章唯一负责 `bind_tools` 停住、手动执行一次和 `create_agent` 自动循环。

### 3.2 Reducer 的因果链跨四章倒置

当前顺序是：第 05 章先解释 Reducer，第 06 章用 reducer 记录 Middleware，第 07 章再次定义，第 08 章才真正制造并行写冲突。

正确顺序应是：节点局部更新 → 并行同字段写入 → `InvalidUpdateError` → Reducer 合并协议 → Mini DeerFlow 不同字段采用不同 reducer。

还需纠正一处语义冲突：普通 Python 合并可能静默覆盖；LangGraph 同一 superstep 对无 reducer 字段的多写通常拒绝更新，不能表述为“只保留其中一份”。

### 3.3 工具在工具契约之前进入系统

第 01 章定义工具，第 03 章交付检索工具，第 04 章才解释参数 Schema、隐藏参数和执行责任。初学者先复制正确封装，再补学为什么需要它。

目标归属：第 03 章止于 Retriever；第 04 章从“固定检索总会运行”和“tool call 无人执行”开始，把 Retriever 升级为 Tool。

### 3.4 后章概念被提前实作

第 02 章使用 `SubagentResult`；第 04 章实作 Runtime Context、Command、Reducer、workspace；第 06 章实作 checkpoint、interrupt、HITL。后续章节只能重复定义，无法让问题驱动升级。

规则：路线图可以点名未来能力，但可执行机制只能在其真实问题出现后首次实现。

### 3.5 工程专题缺少桥接层

工程专题作为第二层迁移总体定位正确，但 Sandbox、Gateway、Evaluation 直接从框架原语跳到完整 Provider、Repository、Manager 和领域 evaluator，跨度仍然过大。

每篇统一增加：最小原生基线 → 可观察失败 → 最小修复 → Mini DeerFlow 深模块 → DeerFlow 对照。

### 3.6 Capstone 没有闭合产品 Runtime

默认 Capstone 在 Harness 层结束，Runtime/Gateway/SSE 仍是扩展任务。它不能证明 interrupted Run、resume 新 Run、SSE 断线重放与同一业务副作用组成完整纵切面。

Runtime/Gateway 接入应升级为必做里程碑；直接 Harness runner 保留为较低层测试入口。

## 4. 逐篇改造矩阵

| 篇章 | 强度 | 主要缺口 | 目标动作 |
| --- | --- | --- | --- |
| 序章 | P1 | 只描述研究失败，直接给完整 Mini DeerFlow 命令和最终技术地图 | 增加一次只有字符串回答的坏运行与固定输出；完整系统标为最终效果预览 |
| 01 模型与消息 | P0 | 已完成 Agent 工具循环，抢占第 04 章；adapter 早于错误消费 | 聚焦单次模型、Runnable、Messages、tool intent、基础 stream；先错读事件再引入 adapter |
| 02 结构化输出 | P0 | 首个业务 Schema、失败类型和路径校验直接导入 Mini DeerFlow | 先内联缩减 Schema 和脆弱字符串解析失败；Subagent 类型后移第 11 章 |
| 03 RAG | P0 | 一次引入完整索引栈；首个完整实验就是 `LocalKnowledgeIndex` | 先做两文档透明检索链和空召回；再迁移增量索引、来源、混合检索和评测 |
| 04 工具与 Agent | P0 | Runtime Context、Command、Reducer、workspace 等后章机制密集提前 | 严格限制为 Tool Schema、tool call、ToolMessage、registry、`create_agent`；其余后移 |
| 05 Context | P0 | “先背后理解”判断表；安全视图和 Repository 遮住原始机制 | 从万能 State 的 Secret、序列化、跨 thread、业务事实失败推导 Context/State/Store/DB |
| 06 Middleware | P0 | 先画完整生命周期；错误顺序只是人为写错列表，不是真实业务失败 | 从重复权限/日志/计数和日志泄露开始，逐个抽出最小 hook，再迁移治理链 |
| 07 StateGraph | P0 | 术语早于单节点图；Reducer 早于并行；“手写 ReAct”实为 factory 调用 | 从单节点、串行、条件、并行冲突、Reducer 到原生 ReAct，最后迁移 Mini DeerFlow |
| 08 显式控制流 | P1 | Command/Send/Subgraph 成功路径由 `create_research_workflow` 隐藏 | 分别增加原生最小图和 updates；Functional API 展开原生 decorator 或后移专题 |
| 09 持久化 | P0 | 只读取已完成快照，未证明中途故障恢复；正文声称 Store 已交付但无实验 | 三节点图在中途故障，重建 Saver 后继续；打印 `next/tasks/metadata`；补 Store 或修正文案 |
| 10 HITL | P2 | 原生失败较完整，但修复仍藏在 workflow/ledger；输出不可见 | 展示 interrupt payload、snapshot、恢复和重复副作用；补最小安全 effect node |
| 11 多 Agent | P1 | Router/Handoff/Subgraph 成功路径全由 `build_*` 隐藏 | 展开原生 Handoff 与 subagent-as-tool，后半再迁移 Registry/Executor 与隔离策略 |
| Architecture | P2 | 合适的第二层总览，但失败仅为表格 | 增加依赖方向红灯摘要与“原生概念 → 工程模块”导航 |
| Lead Agent Core | P2 | Red→Green 顺序较好，实际 StreamEvent/trace 输出不足 | 为四阶段补简短失败消息和 before/after 输出，链接回原生实验 |
| Sandbox | P0 | Provider 早于 traversal、symlink、预算和 shell denied 的真实风险 | 先用临时目录逐个制造安全失败，再引入 Provider；MCP/Skills 独立成后续关卡 |
| Runtime/Gateway | P1 | 从 `graph.stream` 直接跳到完整 Runtime，缺断线丢事件的最小服务 | 先制造 subscriber 断线丢失，再用最小 journal + Last-Event-ID 修复并显示 SSE frame |
| Evaluation | P1 | 第一个 evaluator 已是领域封装，缺 outcome 正确但 trajectory 错误的对照 | 先写纯函数 evaluator，展示三分量完整报告，再迁移 Dataset/Target/Adapter |
| Capstone | P0 | 复制完成品不等于构建；默认不接 Runtime/Gateway | Runtime 纵切面改为必做；至少展开一个里程碑从红灯到绿灯的完整实现 |
| DeerFlow Guide | P2 | 阅读路线正确，但验证主要是文字纠错 | 每条路线补 `rg`/源码定位命令、预期命中和调用链记录模板 |

## 5. 第 07 章样章顺序

1. 保留“固定流程不能只靠 Prompt”的系统快照，补一次模型跳过阶段的确定性失败。
2. 直接使用 `StateGraph` 搭建单节点图，打印运行前 State、节点输入、patch 和运行后 State。
3. 扩成 `START → A → B → END`，再命名 Node、Edge、Step 和局部更新。
4. 增加 Conditional Edge，展示 router 只读 State。
5. 从同一前驱 fork 两个节点，让它们同时写无 reducer 的字段，真实触发 `InvalidUpdateError`。
6. 加入 `operator.add` 修复，展示两个 patch 和 superstep 合并结果。
7. 把 `operator.add` 用到任务状态，展示同 ID 任务重复；再实现按 ID 合并的业务 Reducer。
8. 从零搭建最小显式 ReAct：model node、tool node、conditional edge、ToolMessage 配对和回到 model。
9. 对比 `updates` 与 `values`，再展示 recursion-limit 发生前的执行轨迹。
10. 最后迁移到 `create_explicit_react_graph()`，解释类型、工具映射、trace、复用和测试边界。

## 6. Notebook 系统性问题

当前 Notebook 生成器只提取 `sync` 代码块，再统一分组为“成功/观察/失败”。它没有保留正文中的问题、预测、失败解释、修复关系和工程迁移，因此即使 Markdown 重写，Notebook 仍可能只是无上下文测试集合。

下一任务必须决定 Notebook 契约，至少包括：

- 每个实验前写“先预测什么”和“为什么现在运行”；
- 错误与修复单元相邻，不能被成功/失败通用分组拆开；
- 保存短、稳定、可读的 stdout/JSON/State 输出；
- 断言继续负责回归，但不承担教学解释；
- 概念实验与 Mini DeerFlow 工程迁移使用明确标签；
- 练习必须要求修改一个机制并观察差异，而不是只提示去运行 pytest。

## 7. 建议的全书依赖顺序

```text
坏的字符串模型调用
→ Messages / 单次调用 / 基础流
→ 字符串无法进入程序
→ 最小 Pydantic 契约
→ 无来源回答
→ 透明 Retriever / RAG
→ 固定检索总会执行
→ bind_tools 意图与 create_agent 循环
→ Context 所有权
→ Middleware 横切治理
→ State / Node / Edge / 并行 / Reducer
→ Command / Send / Subgraph
→ Checkpoint / durable execution
→ interrupt / resume / 副作用安全
→ 多 Agent / 上下文隔离
→ Sandbox / Gateway / Evaluation
→ Capstone / DeerFlow 源码阅读
```

这个顺序不是要求每章等长，而是保证每一个核心术语都有一个可观察失败作为前因，并在进入 Mini DeerFlow 前完成最小预测、运行和修改。

## 8. 初学者验收边界

自动测试只能证明代码和文档契约稳定，不能证明课程可理解。全书改写后需要两轮互不共享上下文的初学者 Agent 盲读：第一轮只记录阻塞，修复后由第二个全新 Agent 复验。

盲读必须以正式 Web 顺序和 Jupyter 为唯一学习材料；课程明确要求前不得阅读 Mini DeerFlow 源码、测试答案或本调查。最终能力不能只看“运行成功”，还要检查能解释、能预测、能修改，以及能否把基础概念迁移到 Mini DeerFlow。
