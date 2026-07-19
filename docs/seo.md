# SEO 与搜索引擎收录

本项目的技术 SEO 由 Astro 构建和发布契约共同维护。每次 `make check` 都会验证 canonical URL、robots 指令、Open Graph、Twitter Card、JSON-LD 结构化数据和 sitemap 入口，避免页面能打开但无法被正确索引。

## 术语与边界

| 术语 | 中文含义与作用 | 不应混淆 |
| --- | --- | --- |
| canonical URL | 规范网址；告诉搜索引擎多个可访问地址中哪个是主版本 | 不是跳转，也不能代替正确内部链接 |
| robots meta | 页面级抓取/索引指令；本项目用 `noindex, follow` 排除搜索页和 404，同时允许继续发现链接 | 不等于 `robots.txt`；后者是站点级爬取规则 |
| Open Graph / Twitter Card | 社交平台分享标题、摘要和图片协议 | 通常不直接提升搜索排名 |
| JSON-LD | 机器可读的结构化数据；帮助搜索引擎理解 WebSite、WebPage 和 BlogPosting | 不保证富媒体结果或排名 |
| sitemap | 可索引 URL 清单；帮助搜索引擎发现页面 | 不应包含 `noindex` 页面，也不能保证收录 |
| SearchAction | 描述站内搜索入口的 Schema.org 动作 | 不等于 Pagefind 搜索索引本身 |

## 已自动生成的搜索信号

- 每个可索引页面只有一个绝对 canonical URL。
- 普通页面使用 `WebPage`，课程文章使用 `BlogPosting` JSON-LD。
- 全站 `WebSite` 数据提供指向 Pagefind 的 `SearchAction`。
- 文章输出发布时间、修改时间、作者、关键词和仓库内静态分享图片。
- 搜索结果页与 404 页面使用 `noindex, follow`，避免低价值或重复页面进入索引。
- `robots.txt` 指向 `sitemap-index.xml`，Astro 自动生成 sitemap。
- `/llms.txt` 为 AI 搜索和文档型爬虫提供项目摘要与主要入口。

## Google Search Console

1. 在 [Google Search Console](https://search.google.com/search-console/) 添加网址前缀资源：`https://chengyunlai.github.io/langchain-logbook/`。
2. 选择 HTML meta tag 验证，将 token 保存为 GitHub Actions Variable：`PUBLIC_GOOGLE_SITE_VERIFICATION`。
3. 重新运行 Pages workflow。
4. 提交 sitemap：`https://chengyunlai.github.io/langchain-logbook/sitemap-index.xml`。
5. 使用 URL Inspection 请求首页、序章和核心章节建立索引。

## Bing Webmaster Tools

1. 在 [Bing Webmaster Tools](https://www.bing.com/webmasters/) 添加站点。
2. 将验证 token 保存为 GitHub Actions Variable：`PUBLIC_BING_SITE_VERIFICATION`。
3. 提交与 Google 相同的 sitemap URL。

Bing 可以向部分合作搜索产品同步索引数据，但具体覆盖范围由平台当前策略决定。

## 百度搜索资源平台

1. 在[百度搜索资源平台](https://ziyuan.baidu.com/)添加站点。
2. 将 HTML 标签验证 token 保存为 GitHub Actions Variable：`PUBLIC_BAIDU_SITE_VERIFICATION`。
3. 提交 sitemap URL；GitHub Pages 无法提供服务器级主动推送时，以 sitemap 和自然抓取为主。

## GitHub Actions Variable

进入仓库 **Settings → Secrets and variables → Actions → Variables**，按需创建：

```text
PUBLIC_GOOGLE_SITE_VERIFICATION
PUBLIC_BING_SITE_VERIFICATION
PUBLIC_BAIDU_SITE_VERIFICATION
```

这些值是公开站点验证 token，不是模型 API Key。真实模型密钥仍只能放在 Secret 或本地 `.env` 中。

## 本地验证

运行完整门禁：

```bash
make check
```

只检查已经构建的 SEO 产物：

```bash
uv run --locked --group dev python scripts/check_site_seo.py \
  --site docs-site/dist \
  --site-url https://chengyunlai.github.io/langchain-logbook/
```

SEO 改善不会保证排名。稳定收录还依赖高质量原创内容、外部链接、持续更新以及搜索引擎自身的抓取节奏。
