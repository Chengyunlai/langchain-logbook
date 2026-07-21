# 完成全书学习体验验收与发布

Status: open
Triage: ready-for-agent
Type: task
Blocked by: 09

## Why

两轮初学者盲读通过后，还需要完成工程门禁、跨端视觉检查和线上发布，避免教学内容正确但 Notebook、站点或链接不可用。

## Work

- 检查概念首次出现顺序、双层案例职责和 Mini DeerFlow 迁移边界。
- 执行全部 Notebook、测试、教程漂移、站点构建、链接、SEO 与发布契约。
- 完成桌面和窄屏阅读 QA，重点检查长代码、状态记录和并行图。
- 发布 GitHub Pages 并验证线上全书路线、Notebook 下载与关键样章。

## Acceptance

- 两个互不共享上下文的初学者 Agent 已分别完成首轮盲读和修复后复验。
- 学习者不提前阅读 Mini DeerFlow 源码也能完成核心概念实验。
- 学习者能把实验中的机制定位到 Mini DeerFlow 和 DeerFlow 架构。
- 自动门禁、可访问性、搜索和发布全部通过。
- 形成仍需真实人类读者反馈的清单，不把 Agent 验收等同于真实教学成效。

## Progress

- 本地 `make check` 通过：175 passed、1 skipped；Tutorial 0 new/known/stale；Astro 0 errors/warnings/hints；links、release、SEO 均 0 failure。
- 真实 In-app Browser 已完成 1440px 桌面与 390px 窄屏 QA，首页、学习路线、第 11 章和 DeerFlow Guide 无页面级横向溢出或 console error；详见 [`web-ui-qa.md`](../artifacts/web-ui-qa.md)。
- `main` 已推送至 GitHub；Quality run `29828880095` 与 Pages run `29828880117` 均成功。
- 线上首页、学习路线、更新后的 14 文件 DeerFlow Guide、第 11 章顶层 `await` 均已核验；第 06/11 章 Notebook 下载返回 `200 application/x-ipynb+json`。
- 尚未满足的是 Issue 08 的真实初学者 Web 首页独立阅读。子 Agent 无 Browser backend，根任务 QA 不冒充该主体；因此本项继续保持 open，并等待 `ready-for-human` 反馈。
