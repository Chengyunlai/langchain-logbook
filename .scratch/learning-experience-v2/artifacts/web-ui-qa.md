# 本地 Web 阅读与响应式 QA

## 结论

根任务使用真实 Codex In-app Browser 访问本地 Astro preview，桌面与窄屏检查均通过。没有发现页面级横向溢出、学习路线错序、关键内容未渲染或浏览器控制台错误。

这份证据用于发布门禁，不冒充“初学者子 Agent 亲自点击 Web”。第二位初学者 Agent 的独立浏览器环境没有可用 backend；该环境限制已在 `beginner-audit-2.md` 中如实保留。

## 环境

- 构建：`make check` 生成的 `docs-site/dist`
- 服务：`astro preview --host 127.0.0.1 --port 4321`
- 浏览器：Codex In-app Browser
- 桌面 viewport：`1440 × 1000`
- 窄屏 viewport：`390 × 844`
- 日期：2026-07-21

## 桌面检查

### 首页

- H1、课程一句话定位、Introduction 入口、课程总览和“从第 01 章开始”按顺序出现。
- 顶部“学习路线”链接进入 `/posts/`，不是发布日期归档。
- 第 01–03 章卡片同时给出章节标题和学习目标。

### 学习路线页

- 页面明确声明“不是按发布日期排列的文章列表”。
- 序章、第一部、第二部、第三部、第四部依次出现。
- 01–11 与工程专题编号连续；每个卡片都有“先回答”和“学完你能”。
- 附录、版本、发布、PyCharm、SEO 位于“按需参考”，没有混入主线。

## 390px 窄屏检查

### 学习路线页

- `documentElement.scrollWidth = 390`，无页面级横向溢出。
- H1、主线说明与五段阶段导航完整可见；阶段 chip 自动换行，没有遮挡。

### 第 11 章

- `documentElement.scrollWidth = 390`，无页面级横向溢出。
- 共 53 个 `pre`；其中 43 个长代码块在自己的容器内溢出，`overflow-x: auto`，没有撑宽正文。
- Mermaid/SVG 最大渲染宽度为 390px。
- H1、课程位置、本章工件和正文层级可读。

### DeerFlow Guide

- `documentElement.scrollWidth = 390`，无页面级横向溢出。
- “证据切片”标题和 `gateway/services.py` 补充说明均在渲染 DOM 中。
- 固定 commit、前置课程和学习目标在首屏可见。

## 运行时检查

- 浏览器 console error：0。
- `make check`：175 passed、1 skipped；Tutorial、Astro、links、release、SEO 全绿。

## 仍需真实人类反馈

- 长篇章节的疲劳度、练习节奏和术语记忆负担仍需真实学习者反馈。
- 本次浏览器检查证明布局和导航可用，不等同于真实读者完成课程。
