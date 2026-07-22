# LangChain Logbook 全书作者声音改造地图

## Destination

保留全部 LangChain/LangGraph 实验、Notebook 输出、Mini DeerFlow 工程深度和 DeerFlow 固定源码证据，把主线改写成自然、具体、克制的中文技术书。

读者应感到一位工程师正在带他处理同一个系统，而不是一套模板在逐项满足课程 rubric。

## Scope

- 序章与线上首页；
- 第 01–11 章全部正文；
- Mini DeerFlow 的 Architecture、Lead、Sandbox、Runtime、Evaluation、Capstone；
- DeerFlow Guide；
- Web/Notebook 的入口与顺序一致性。

附录、版本策略、IDE、SEO 和发布手册只检查术语、链接与主线入口，不强行改造成故事章节。

## Non-negotiables

- 不删除 lesson lab、代码、稳定输出、失败/修复配对或“动手修改”。
- 不用轻松口吻掩盖 State、Reducer、Checkpoint、interrupt、Subagent、Sandbox、Runtime 或评测边界。
- 不逐句模仿任何在世作者，只采用短句、具体观察、克制判断和问题驱动等通用技术写作原则。
- 每个正文段落最多 240 个字符；代码、表格、输出和链接不计入。
- Markdown 继续作为 Notebook 与 Web 的事实源。

## Baseline

- 01–11 共 149 处“运行前先预测”、149 处“发生了什么”、122 处“动手修改”。这些是教学契约，不作为删减对象。
- 主线粗略扫描有 68 处“不是……而是…… / 不等于 / 这意味着 / 换句话说”等校准句式。
- 17 个标题使用“从 A 到 B”或破折号式双标题。
- 工程专题常连续出现阅读问题、映射表、验收表和反例表；证据完整，但叙事呼吸不足。
- 首页同时提示从 Introduction 和第 01 章开始；线上文章缺少显式 Notebook 下载入口。

## Decisions

- 实验层保持统一；正文层允许不同章节使用不同节奏。
- 每节先给现场、输出或反例，再命名概念；避免先声明“本节将回答三个问题”。
- 表格只承载精确映射，不能代替因果解释。
- “下一章”只在真正存在未解决限制时出现一次，不在每个小节重复导航。
- 工程专题先追一条调用链，再给完整目录和检查表。
- [写作契约与自动度量](./issues/01-writing-contract-and-baseline.md) 已建立：正文段落上限进入 `make test`，实验标签不参与去模板化删减。
- [序章与第 01–03 章](./issues/02-orientation-and-foundations.md) 已改写：首页只有一个主起点，每章提供 Notebook 下载入口。
- [第 04–06 章](./issues/03-agent-runtime.md) 已改写：工具循环、事实所有权和 Middleware 从同一研究助手的故障推导。
- [第 07–11 章](./issues/04-graph-and-subagents.md) 已改写：Graph、恢复、审批与 Subagent 形成连续能力链。
- [工程专题与 DeerFlow Guide](./issues/05-engineering-book.md) 已改写：同一业务链从组合根延伸到 Sandbox、Runtime、评测、Capstone 和四条固定源码路线。

## Frontier

- [全书同步、阅读与发布验收](./issues/06-book-wide-qa.md) — claimed

## Later

- 暂无。若最终初学者盲读发现新阻塞，再创建可验收任务。

## Human boundary

自动指标只能发现模板化倾向，不能证明文章“像人写”。最终仍要保留真实读者对节奏、信任感和作者声音的反馈。
