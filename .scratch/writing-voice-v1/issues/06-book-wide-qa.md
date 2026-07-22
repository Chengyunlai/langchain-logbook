# 全书同步、阅读与发布验收

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 05

## Why

文字自然不能以 Notebook 漂移、链接失效或概念缺失为代价。全书完成后必须重新验证三端事实和阅读体验。

## Acceptance

- 01–11 Notebook 原样执行通过。
- Web、Markdown、Notebook 的代码和顺序一致。
- 全量测试、站点、链接、SEO 和发布契约通过。
- 新的初学者审阅能复述业务主线，同时指出仍像模板的段落。

## Answer

全书 Markdown、Web 与 11 本 Notebook 已完成同步验收。最终门禁结果为 179 passed、1 skipped；教程校验无新增、已知或过期问题，站点链接、发布契约与 SEO 均为 0 失败，Astro 为 0 errors、0 warnings、0 hints。

一个不继承项目历史的初学者 Agent 只按线上顺序阅读课程，并下载执行 11 本 Notebook。149 个代码单元全部通过、0 error；它能独立复述 01–11 的章节因果链、核心概念边界、Mini DeerFlow 组合根，以及 DeerFlow 的状态/恢复、工具/沙箱、委派/上下文、运行时/流式协议四条责任链。

首次盲读发现三项明显摩擦：第 11 章未解释 Supervisor、06/11 Notebook 缺少分层路线、05/06/09 历史源文件名与公开下载名缺少说明；另有一项页内导航润色。提交 `4839e21` 已全部修复。发布后定点复核五项均为 PASS，未引入新理解问题。

发布证据：提交 `4839e21`；Quality run `29888383233`；Pages run `29888383239`。完整盲读与发布后复核见 `../artifacts/final-beginner-reaudit.md`。浏览器运行时当时没有可用实例，因此下载名以线上 HTML 的 `href`/`download` 属性和实际下载响应核验；该限制已在报告中明确记录。
