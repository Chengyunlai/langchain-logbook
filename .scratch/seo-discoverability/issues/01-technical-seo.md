# 01 建立技术 SEO 与收录闭环

- Status: resolved
- Triage: ready-for-agent
- Type: task
- Blocked by:

## Why

站点已有 sitemap（可索引网址清单）、robots（抓取与索引指令）和基础 meta tag，但所有页面都被标记为 `BlogPosting`（文章结构化类型），非文章页会输出无效日期；搜索与 404 页面也没有明确禁止索引。缺少 canonical（规范网址）、Open Graph/Twitter Card（分享元数据）和 JSON-LD（机器可读结构化数据）自动化契约时，这些问题容易在主题升级或页面扩展后重新出现。

## Work

- 为普通页面与课程文章输出正确的 WebPage/BlogPosting JSON-LD。
- 补齐 canonical、robots、Open Graph、Twitter Card、关键词和站点搜索结构化数据。
- 为 Google、Bing 和百度提供可选验证变量。
- 发布 SEO 操作指南和 `llms.txt`。
- 新增构建后 SEO 检查并接入 `make check-docs`。

## Acceptance

- 首页 JSON-LD 包含 `WebSite`、`WebPage` 和 `SearchAction`。
- 课程文章包含合法 `BlogPosting`，且没有 `undefined` 日期。
- 搜索和 404 页面为 `noindex, follow`。
- robots 指向正确 sitemap；canonical、OG 与 Twitter 元数据完整。
- SEO 单元测试、完整测试、Astro 类型检查、构建与发布契约通过。

## Answer

已完成页面类型化 JSON-LD、绝对 canonical、robots、Open Graph、Twitter Card、站点关键词、SearchAction、搜索引擎验证变量、`llms.txt` 和收录操作指南。新增 `check_site_seo.py` 并接入 `make check-docs`；契约测试从缺少检查器的失败开始，覆盖 sitemap 与 `noindex` 一致性、`llms.txt` 存在性和核心元数据。完整验收结果：162 个测试通过、1 个外部集成测试跳过；教程校验无漂移；Astro 类型检查、静态页面构建、Pagefind、站内链接、发布契约和 SEO 契约全部通过。动态 OG 与 Astro 字体已改为仓库内静态分享图和系统字体栈，构建不再依赖 Google Fonts 网络。

遗留风险：Google、Bing 和百度验证变量仍需站点管理员在 GitHub 设置中配置并提交 sitemap；技术 SEO 只能改善发现与理解，不能保证收录时间、富媒体展示或搜索排名。
