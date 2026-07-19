# SEO 与搜索收录地图

## 目的地

让搜索引擎能够抓取、理解并持续收录 LangChain Logbook，同时用本地发布门禁防止 canonical、robots、分享元数据和结构化数据回归。

## 执行原则

- 搜索信号必须与页面意图一致：`noindex` 页面不得进入 sitemap。
- SEO 元数据服务于准确理解，不做关键词堆砌或排名保证。
- 搜索引擎验证 token 通过公开的 Actions Variable 注入，不与模型 Secret 混用。
- 所有发布信号必须由静态构建产物和自动化契约验证。

## 已确认决策

- [01 建立技术 SEO 与收录闭环](./issues/01-technical-seo.md)：结构化数据区分页面与文章，搜索/404 不进入索引，验证 token 通过 GitHub Actions Variable 注入，并用构建后契约验收。

## 当前前沿

- 本轮技术 SEO 与搜索收录改造已完成。

## 尚未明确

- 无遗留实现问题；Google、Bing 和百度的账号验证与 sitemap 提交仍属于站点管理员操作。
