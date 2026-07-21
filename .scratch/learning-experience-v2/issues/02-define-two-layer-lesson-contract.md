# 定义双层案例章节契约与可观察反馈格式

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 01

## Why

“概念实验室 + Mini DeerFlow 工程迁移”需要成为可验证的章节契约，否则不同章节仍会退回定义、封装和断言的旧顺序。

## Work

- 定义七步章节结构：当前能力、真实失败、设计问题、最小概念、从零代码、工程迁移、决策表与练习。
- 定义概念实验室的代码长度、导入边界、错误输出和观察记录格式。
- 定义 Web 文章、Notebook 和测试各自承担的反馈职责。
- 给出可以被自动检查的 marker、输出和反模式规则。

## Acceptance

- 新契约能判断一个示例是在教授概念还是只验证封装。
- `assert` 保留为回归证据，同时必须有学习者可读的状态或事件输出。
- 说明什么时候允许提前使用 Mini DeerFlow，什么时候必须先写透明实现。
- 契约可以直接用于第 07 章样章验收。

## Answer

已建立[双层案例章节契约与可观察反馈格式](../artifacts/02-two-layer-lesson-contract.md)，并在原中文写作与视觉标准中声明新版教学顺序优先。

契约固定“上一刻能力 → 真实失败 → 设计问题 → 最小概念 → 从零修复 → 修改观察 → Mini DeerFlow 迁移 → 决策表与练习”的信息依赖。

概念实验不得导入 `mini_deerflow`；工程迁移必须说明完整项目新增的安全、持久化、抽象和测试边界。

契约定义了 `lesson-lab` marker、`sync`/`output` 对应关系、failure/repair 配对和稳定 transcript，并划分 Markdown、Notebook、测试与 Mini DeerFlow 的职责。

概念层不得导入 Mini DeerFlow；Notebook 必须保留正文实验顺序，不能再按成功、事件、失败重新分组。

自动检查规则已明确，包括概念层误导入 Mini DeerFlow、缺少输出、只含断言、失败修复倒序、迁移早于概念、Notebook 顺序和输出漂移。第 07 章所需 12 个实验已作为首个验收集固定。
