# 文档站、视觉质量与发布验证报告

> 完成日期：2026-07-14  
> 对应任务：[完成文档站、视觉质量与全量发布验证](../issues/17-docs-visual-release-qa.md)  
> 一键门禁：`make check`

## 1. 发布结论

本轮计划内的 17 个课程改造任务已经全部完成。本地发布候选满足以下条件：

- Markdown、离线 Notebook、Python 工程和 Astro 文档站仍由同一批课程源同步；
- 课程共构建 33 个静态页面，其中 21 个教学页面进入中文 Pagefind 索引；
- Mini DeerFlow 综合实战与 DeerFlow 源码导读均已进入文档站；
- Capstone 的 3 张 Mermaid 和 DeerFlow 导读的 7 张 Mermaid 在桌面与 390 px 窄屏均能查看，并且每张图都有文字替代与读图顺序；
- `make check` 完成锁文件、135 个通过测试、1 个显式外部依赖跳过项、教程/Notebook 契约、静态站构建和站内链接检查；
- 站内搜索、移动端菜单、文章日期、源码编辑链接和页脚仓库链接已由真实浏览器复验。

本报告说“本地发布候选通过”，不等同于已经部署到 GitHub Pages，也不把没有 API Key 的真实模型调用伪装为已验证。

## 2. 本轮修复

### 2.1 窄屏表格

Markdown 表格原先会把 390 px 页面撑到 648 px，导致整页出现水平滚动。现在表格本身使用 `display: block; max-width: 100%; overflow-x: auto`：页面宽度保持 390 px，只有内容确实较宽的表格容器横向滚动。

这个边界很重要：流程图和表格可能需要保留其内部最小宽度，但不应迫使标题、正文和导航一起横向移动。

### 2.2 搜索基路径

站点部署在 `/langchain-logbook` 子路径。Pagefind bundle 原先按根路径查找，搜索会停留在加载状态。搜索页现在从 `import.meta.env.BASE_URL` 构造 `/langchain-logbook/pagefind/`，本地预览能返回 `DeerFlow` 的 20 条结果，并能精确命中“从 Mini DeerFlow 进入真实 DeerFlow：源码调用链导读”。

### 2.3 日期与源码链接

- Capstone 与 DeerFlow 导读日期固定为实际完成日 `2026-07-14`；
- 同步脚本把每篇文章的事实源路径写入 `sourcePath` frontmatter；“在 GitHub 见证成长”据此生成 `https://github.com/HappyFrame/langchain-logbook/blob/main/<sourcePath>`，不再指向文档站生成副本；
- 页脚 GitHub 链接从 AstroPaper 模板仓库改为本项目仓库；
- 删除两个未使用图标 import，使 Astro 类型检查不再产生对应提示。

## 3. 自动化通过项

### 3.1 一键门禁

```text
make check
├── uv lock --check
├── offline pytest
├── tutorials / notebooks contract validation
├── Astro type check and static build
├── Mermaid transform
├── Pagefind index
└── internal link validation
```

有效结果：

- 锁文件与 `pyproject.toml` 同步；
- `135 passed, 1 skipped`；
- 跳过项是带显式 integration marker、需要供应商凭据的外部 smoke case；
- 教程验证：`0 new / 0 known / 0 stale`；
- Astro 类型检查：`0 errors / 0 warnings / 0 hints`；静态构建：33 pages；
- Pagefind：21 pages、4629 words；
- 站内链接：0 broken links。

### 3.2 专项 smoke

- `make mini-deerflow-eval`：outcome、trajectory、budget 全部通过，`pass_rate=1.0`；
- `make mini-deerflow-capstone`：两个 Subagent 完成，审批恢复成功，`effect_count=1`，Checkpointer 已重开，最终 `pass_rate=1.0`；
- FastAPI/SSE 两个精确节点：创建 Thread/Run、四种 stream mode、`Last-Event-ID` replay、用户隔离、interrupt 后新 Run resume，`2 passed`。

完整测试仍以 `make check` 为准；专项 smoke 的作用是让关键交付链有更易读的独立证据。

### 3.3 双轴复核

Standards 初审发现文章编辑链接仍指向生成副本的错误仓库路径，首页返回地址也没有部署 base path。引入 `sourcePath` 事实源元数据并让首页使用 `import.meta.env.BASE_URL` 后，构建产物和浏览器交互均复验通过。最终 Standards 与 Spec 两条独立复审均为 PASS。

## 4. 浏览器视觉与交互 QA

### 4.1 桌面视口 1280 × 720

- Capstone 文章的 3 张 Mermaid 均完成渲染；
- DeerFlow 导读的 7 张 Mermaid 均完成渲染；
- 文章正文、表格和代码块没有扩大页面宽度；
- 长代码块保留局部横向滚动，不裁掉命令；
- 文章日期显示为 `14 Jul, 2026`；
- 文章源码链接能生成正确的 GitHub `blob/main/` 地址。

### 4.2 移动视口 390 × 844

- Capstone 与 DeerFlow 导读的 `documentWidth`/`bodyWidth` 均保持 390 px；
- 宽表格只在自身容器中滚动；
- Mermaid 容器允许局部滚动，图后的文字替代和读图顺序可以在不操作图形的情况下说明同一关系；
- DeerFlow 三层架构图在窄屏仍能辨认主干，详细关系可结合文字替代阅读；
- 汉堡菜单能打开 Posts、Tags、About、Search；
- 首页写入的返回地址使用部署 base path，从文章执行“Go back”不会跳出 `/langchain-logbook`；
- 标题、面包屑、正文和页脚没有因图表而被横向截断。

### 4.3 搜索与导航

- 搜索输入框只有一个可交互实例；
- 查询 `DeerFlow` 返回 20 条结果；
- 查询 `源码调用链导读` 返回 11 条结果，第一条是目标导读；
- 目标链接为 `/langchain-logbook/posts/deerflow_guide/`；
- 页脚仓库链接为 `https://github.com/HappyFrame/langchain-logbook`。

## 5. 在线依赖项

以下内容没有被本地离线门禁冒充为“已通过”：

1. **真实模型供应商调用**：需要用户自行配置相应 API Key，再执行 `make test-integration`；默认离线课程不依赖它。
2. **GitHub / DeerFlow 外链实时可达性**：内部链接已验证，外部网络、仓库权限和上游提交是否仍在线属于发布时环境检查。
3. **GitHub Pages 部署**：本轮没有执行 push 或部署，因此线上 base path、CDN cache 和 Pages 权限仍要在实际发布后 smoke。

## 6. 仍需人工验证项

这些不是当前课程内容缺失，而是无法由单一桌面浏览器和本地静态构建完全证明的发布检查：

- macOS/Windows/Linux 不同字体栅格化下的极端中文换行；
- iOS Safari、Android Chrome 和真实触摸手势下的表格/图形局部滚动；
- 屏幕阅读器朗读顺序、键盘全路径和高对比度模式；
- GitHub Pages 实际 URL 上的缓存刷新、404 回退、RSS 和 sitemap 抓取；
- 使用真实供应商模型时的速率限制、成本和非确定性输出。

## 7. 已知非阻塞优化项

Mermaid 客户端包产生大于 500 kB 的 Vite chunk 提示。它不影响正确性或当前验收，但若文档站首屏性能成为目标，可把 Mermaid 改为按文章/视口延迟加载并测量真实 Web Vitals。课程当前优先保留可维护的源码图和跨主题渲染一致性，没有在发布收尾阶段引入新的加载架构。

## 8. 最终状态

任务 01–17 全部 `resolved`。项目已经具备完整中文学习主线、逐章演进的 Mini DeerFlow、长任务 Capstone、当前 DeerFlow 四条源码阅读路线，以及可重复的本地发布门禁。后续工作属于可选发布、真实供应商集成或性能/无障碍增强，不再是本轮课程改造的计划内缺口。
