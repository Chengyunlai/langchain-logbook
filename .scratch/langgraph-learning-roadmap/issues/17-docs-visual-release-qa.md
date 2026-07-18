# 完成文档站、视觉质量与全量发布验证

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 16

## Why

课程只有在 Markdown、Notebook、代码项目和在线文档站一致时才算完成。大量图示和代码块还需要视觉与链接验证。

## Work

- 同步全部章节、附录、流程图和实战项目文档到 Astro 站点。
- 检查 Mermaid、必要的 imagegen 资产、代码块、表格和移动端阅读效果。
- 执行 Notebook、测试、评测样例、API smoke test 和文档构建。
- 校验内部链接、章节顺序、版本日期、源码链接和下载/运行说明。

## Acceptance

- 一条发布验证命令可以完成主要检查。
- 文档站包含所有章节和最终实战，不遗漏后期内容。
- 关键流程图在桌面和窄屏均可理解，并有文字解释。
- 最终验收报告列出通过项、在线依赖项和仍需人工验证项。

## Answer

已完成本地发布候选的自动化与浏览器双重验收。`make check` 通过：`135 passed, 1 skipped`、教程/Notebook 漂移 `0/0/0`、33 个静态页面、21 个中文搜索页面、0 个站内断链；评测与 Capstone 均为 `pass_rate=1.0`，FastAPI/SSE 两个专项节点通过。

浏览器已覆盖 1280×720 桌面和 390×844 窄屏：Capstone 3 张、DeerFlow 导读 7 张 Mermaid 均可读且有文字替代/读图顺序；表格改为局部横向滚动；移动菜单、Pagefind 搜索、发布日期、源码编辑链接和页脚仓库链接均已复验。真实模型、GitHub Pages 部署、外链实时性以及真实设备/屏幕阅读器检查被明确列为线上或人工项，没有混入离线通过结论。

完整证据、修复说明和发布后检查表见[任务 17 发布验证报告](../artifacts/17-docs-visual-release-qa.md)。
