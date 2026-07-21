# 双层案例章节契约与可观察反馈格式

> 生效日期：2026-07-21
>
> 适用范围：序章、全部课程章节（包括现有第 01–11 章与承担原第 12–16 章职责的工程专题）、Capstone、DeerFlow 源码导读、Markdown、Astro Web 与 Jupyter Notebook
>
> 上游依据：[全书概念实验与工程迁移倒置审计](../research/01-full-book-concept-migration-audit.md)

## 1. 这份契约解决什么问题

旧课程常按“概念定义 → 正确封装 → 断言 → 末尾失败实验”组织。学习者看见的是答案和测试，却没有亲手经历答案所解决的问题。

新契约把案例拆成两层：

- **概念实验室**回答“为什么需要这个机制、运行时发生了什么”；
- **Mini DeerFlow 工程迁移**回答“这个机制在完整项目中放在哪里，还需要哪些工程边界”。

两层共享同一个研究交付业务情境，但代码职责不同。透明教学代码允许短小和局部；工程代码追求复用、安全、持久化与稳定接口。

## 2. 不可打乱的信息依赖

每章核心概念至少走完下面的有向路径：

```text
上一刻系统能力
→ 展示一个看似合理的错误版本
→ 写下运行预测
→ 运行并看见错误、错误状态或错误副作用
→ 从证据提炼设计问题
→ 引入恰好足够的概念
→ 从零实现最小修复
→ 修改一个变量并观察差异
→ 迁移到 Mini DeerFlow
→ 用决策表、练习和系统快照收尾
```

术语可以在路线图中提前出现，但不能在问题发生前作为可执行答案。工程迁移不能反过来充当概念的首次实现。

## 3. 单章结构

章节不要求使用完全相同的编号，但必须保持以下顺序。

### 3.1 上一刻系统还能做什么

写出学习者已经运行过的能力、本章继续使用的输入，以及当前系统唯一主要限制。不要用学习目标清单代替系统快照。

### 3.2 让问题真实发生

展示一个初学者可能自然写出的版本，先要求预测，再运行。失败可以是异常，也可以是静默覆盖、丢状态、重复副作用、错误轨迹或无法回答业务问题。

核心失败必须离线、确定、可重复。不能只写“假设会失败”，也不能故意写错一个与业务无关的断言来制造红灯。

### 3.3 从证据提炼设计问题

先让学习者回答所有权、生命周期、控制权、合并、恢复或副作用问题，再给术语。问题应能从刚才的输出中推导，不依赖作者权威。

### 3.4 引入最小概念

只解释解决当前失败所需的一个新机制，并说明它不解决什么。此时可以给一张局部图，不能先铺完整生产架构。

### 3.5 从零完成概念实验

使用框架原生 API 或标准 Python 写出 20–60 行透明代码。学习者能在当前页面看到 State、节点、边、事件、patch、checkpoint、tool call 或副作用怎样变化。

### 3.6 迁移到 Mini DeerFlow

完成概念实验后再导入 Mini DeerFlow。迁移必须列出工程封装比最小实现新增的边界，例如类型、权限、持久化、幂等、并发、可观测性和测试。

### 3.7 决策表、练习与下一刻系统

判断表放在推导之后。练习要求学习者预测、运行和修改；章节结尾记录新能力、仍未解决的问题，以及下一章将继承的真实工件。

## 4. 概念实验室契约

### 4.1 允许的依赖

概念实验可以导入：

- Python 标准库；
- 当前章节已经正式引入的 LangChain / LangGraph 公共 API；
- 为当前实验就地定义的短小 TypedDict、dataclass、Pydantic model、tool 或纯函数。

概念实验不得导入 `mini_deerflow`。需要脚本化模型时，直接使用当前章节已解释的 LangChain 公共 fake model，或就地定义最小 stub；课程 adapter 只能在工程迁移层出现。

### 4.2 代码边界

- 一个实验只增加一个主要机制；
- 主体建议 20–60 行，不用省略号隐藏核心逻辑；
- 不为复用而提前抽象 Repository、Provider、Manager、Registry 或 factory；
- 可以故意保留一个自然错误版本，但必须解释它为什么看似合理；
- 时间、UUID、随机数、网络和真实模型响应不能成为唯一证据。

### 4.3 失败与修复必须相邻

同一个问题的失败实验和最小修复使用同一 `pair`，在 Markdown 和 Notebook 中相邻出现。不能把所有成功实验集中在前面，再把失败统一移到末尾。

修复只能增加当前概念。若修复同时引入三个新抽象，应继续拆分实验。

### 4.4 先预测，再运行

每个核心实验在代码前提供一个可回答的预测问题，例如：

- 两个并行节点同时写 `results` 会覆盖、合并还是报错？
- 进程重启后，哪个节点会再次执行？
- `bind_tools` 返回 tool call 后，函数是否已经被调用？

预测不要求保存为评分数据，但 Notebook 必须给学习者留下作答位置。

## 5. 工程迁移契约

工程迁移可以并且应该导入 `mini_deerflow`。它不得简单重复概念实验，而要说明完整项目增加了什么。

每次迁移至少回答：

1. 概念实验中的哪段职责被哪个模块拥有？
2. 哪些字段、错误和副作用成为稳定协议？
3. 为什么需要抽象，直接代码在哪个规模开始失效？
4. 哪些安全、持久化、并发和测试边界是概念实验刻意省略的？
5. 这个模块怎样映射到 DeerFlow 的对应调用链？

工程迁移可以展示 factory 调用，但必须先链接到学习者已经完成的原生实验。不能用“源码中已经实现”代替机制解释。

## 6. Lab marker

新实验使用稳定的 HTML comment marker 包围。规范格式如下：

````markdown
<!-- lesson-lab:id=ch07-parallel-conflict layer=concept kind=failure concept=reducer pair=parallel-results -->
### 两个并行节点同时写 `results`

**运行前先预测**：两个 patch 会怎样进入最终 State？

```python sync=ch07-parallel-conflict
# 可直接执行的完整代码
```

**观察结果**：

```text output=ch07-parallel-conflict
InvalidUpdateError: ...
```

**发生了什么**：结合输入、patch 和合并边界解释原因。

**动手修改**：只改变一个字段或 reducer，再预测结果。
<!-- /lesson-lab -->
````

### 6.1 必填字段

| 字段 | 允许值 | 用途 |
| --- | --- | --- |
| `id` | 全书唯一短标识 | 连接 Markdown、Notebook、输出与测试 |
| `layer` | `concept` / `migration` | 区分首次解释与工程迁移 |
| `kind` | `baseline` / `failure` / `repair` / `contrast` / `exercise` | 保留实验在因果链中的职责 |
| `concept` | 领域术语 slug | 检查概念首次出现和章节归属 |
| `pair` | 问题 slug | 把 failure 与 repair/contrast 相邻配对；非配对实验可省略 |

### 6.2 实验内部必备元素

- 一个动作型标题；
- `运行前先预测`；
- 与 `id` 一致的 `sync` Python fence；
- 与 `id` 一致的 `output` text fence；
- `发生了什么`；
- 核心概念实验还需 `动手修改`。

`assert` 可以存在，但不能替代 `output`。没有学习者可读输出的实验不能标记完成。

### 6.3 Marker grammar

- 开始 marker 独占一行，字段固定按 `id layer kind concept pair` 排列；`pair` 可省略，其余必填；
- `id`、`concept`、`pair` 只使用小写字母、数字和连字符；
- lab 以独占一行的 `<!-- /lesson-lab -->` 结束；
- lesson lab 不允许嵌套；
- `sync` 与 `output` fence 各出现一次，标识必须等于 lab `id`；
- 外层文档需要展示 marker 示例时使用四反引号，避免嵌套 fence 提前闭合。

### 6.4 章节契约版本

完成迁移的 Markdown 在一级标题后加入：

```html
<!-- lesson-contract:v2 -->
```

迁移期间，lesson-lab validator 只对带该 marker 的章节启用新规则，避免把尚未改写的旧 sync fence 误报为缺少 lab。最终发布门禁要求全部正式课程章节带 v2 marker；附录和纯维护手册可以显式列入豁免清单。

## 7. 可观察输出格式

输出只保留支持当前结论的字段，使用稳定、可比较的文本或 JSON。

### 7.1 State 与节点更新

```text
[before]
results = []

[node:search_docs]
patch = {"results": ["docs"]}

[node:search_web]
patch = {"results": ["web"]}

[after]
results = ["docs", "web"]
```

### 7.2 异常

```text
InvalidUpdateError: results received multiple updates in one step
```

代码捕获预期异常并打印“异常类型 + 稳定摘要”，同时用断言检查真实异常类型。Notebook 不保存完整 traceback。

### 7.3 事件与协议

事件输出至少展示 `type`、`ns`、节点名和与结论相关的 payload。长消息正文、token 细节和 provider metadata 默认省略，并明确注明省略内容。

### 7.4 Checkpoint、SSE 与评测

- Checkpoint：打印 `thread_id`、`next`、`tasks`、关键 values 和恢复前后节点次数；
- SSE：打印 `id/event/data` frame 和重连游标；
- 评测：打印案例 ID、outcome、trajectory、budget 与解释，不只显示总分；
- 副作用：打印调用次数、idempotency key 和 ledger 状态。

## 8. Web、Notebook、测试与项目的职责

| 载体 | 主要职责 | 不能代替什么 |
| --- | --- | --- |
| Markdown / Web | 给出因果叙事、完整代码、稳定输出、图和边界 | 不能只链接 Notebook；不能用作者结论代替运行证据 |
| Jupyter Notebook | 按正文顺序执行、保存输出、允许预测和修改 | 不能重新按 success/failure 分组；不能只做回归测试 |
| 自动测试 | 验证确定性、不变量、失败类型和生成漂移 | 不能证明初学者理解；不能承担教学输出 |
| Mini DeerFlow | 展示工程归属、组合、复用和生产边界 | 不能首次解释基础概念 |
| DeerFlow 导读 | 验证迁移到大型真实系统的阅读能力 | 不能替代 Mini DeerFlow 实作 |

## 9. Notebook 生成契约

Notebook 必须保持 lesson lab 在 Markdown 中的原始顺序，不再根据 sync id 名称重新分为“成功/事件/失败”。

每个 lab 生成：

1. 标题与 layer/kind 标签；
2. 预测问题 Markdown cell；
3. 可执行代码 cell；
4. 已执行 stdout；
5. `发生了什么` Markdown cell；
6. `动手修改`的可编辑练习 cell或提示。

Notebook 先出现全部必要概念实验，再进入工程迁移。`mini_deerflow` 的环境探针不能出现在概念实验之前，避免让学习者误以为所有实验都必须依赖项目包。

输出 fence 是 Web 的稳定 transcript。Notebook 执行后捕获的标准化 stdout 必须与同 id 的 output fence 一致；换行、临时目录、时间和 UUID 必须在实验中主动稳定化，不能由 validator 猜测业务语义。

## 10. 自动检查规则

后续 validator 至少实现以下错误码：

| 错误码 | 触发条件 |
| --- | --- |
| `lesson-lab-marker-missing` | 带 `lesson-contract:v2` 的章节中，sync fence 不属于任何 lesson lab |
| `lesson-lab-id-duplicate` | `id` 不唯一，或 marker、sync、output id 不一致 |
| `concept-imports-mini-deerflow` | `layer=concept` 的 AST 导入 `mini_deerflow` |
| `lab-output-missing` | 核心实验没有可读 output fence |
| `assert-only-lab` | 代码只有断言，没有 stdout 或表达状态变化的输出 |
| `failure-repair-order` | 同 pair 的 failure 不在 repair/contrast 之前或不相邻 |
| `migration-before-concept` | 某 concept 的 migration 早于 concept lab |
| `notebook-order-drift` | Notebook lab 顺序与 Markdown 不一致 |
| `notebook-output-drift` | 执行 stdout 与 output fence 不一致 |
| `notebook-prose-missing` | Notebook 缺预测、解释或修改提示 |
| `lesson-contract-v2-incomplete` | 最终发布模式下，正式课程章节缺少 v2 marker 且不在显式豁免清单 |

不能完全自动判断的内容进入人工量规：失败是否自然、一次是否只引入一个概念、工程迁移是否说明了真实新增边界、未来概念是否执行过早。

## 11. 按改造强度验收

### P0 章节

- 至少一个中央 failure → repair 配对；
- 核心概念首次代码不导入 Mini DeerFlow；
- 章节主结构按因果重排；
- Notebook 保留预测、失败、修复和修改过程。

### P1 章节

- 至少补一个原生桥接实验；
- 工程 factory 前能看见关键框架 API 与数据形状；
- Web 显示关键输出，Notebook 可修改。

### P2 章节

- 保留现有结构；
- 为重要结论补稳定 transcript、命令或源码验证；
- 增加从工程封装返回原生概念实验的链接。

## 12. 第 07 章样章的最小验收集

第 07 章必须至少包含以下 lab，顺序固定：

1. `concept/baseline/state-node-patch`：单节点读取 State、返回 patch；
2. `concept/repair/serial-edge`：A → B 的 State 演进；
3. `concept/contrast/conditional-edge`：纯 router 只读 State；
4. `concept/failure/parallel-results`：并行同字段触发 `InvalidUpdateError`；
5. `concept/repair/parallel-results`：`operator.add` 合并两个 patch；
6. `concept/failure/task-list-duplicates`：`operator.add` 错用于可更新实体；
7. `concept/repair/task-list-duplicates`：按 ID 自定义 Reducer；
8. `concept/baseline/explicit-react`：从零搭 model/tool/conditional loop；
9. `concept/contrast/stream-modes`：展示 updates 与 values；
10. `concept/failure/recursion-limit`：显示异常前已发生的节点轨迹；
11. `migration/contrast/explicit-react`：迁移到 Mini DeerFlow factory 并列出新增边界。

这组实验既是样章目录，也是 Notebook 生成器和 validator 的首个真实验收 fixture。

## 13. 完成定义

一个章节只有同时满足下列条件，才算完成双层案例改造：

- 学习者在术语出现前已经看到需要它的证据；
- 概念实验透明、离线、可运行，并允许修改一个变量；
- Web 和 Notebook 都显示状态或事件怎样变化；
- 失败与修复相邻，且失败来自真实机制；
- Mini DeerFlow 只在工程迁移层首次出现；
- 决策表是实验结论，不是开场背诵材料；
- 自动测试通过，初学者盲读仍作为独立验收，不由测试替代。
