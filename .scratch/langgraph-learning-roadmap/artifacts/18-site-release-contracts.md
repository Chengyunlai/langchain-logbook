# 文档站发布契约自动化记录

> 完成日期：2026-07-14  
> 对应任务：[把文档站浏览器发现固化为发布契约](../issues/18-automate-site-release-contracts.md)  
> 公共入口：`make check`

## 1. 为什么站内断链检查还不够

原有 `check_site_links.py` 负责验证构建目录中的内部页面和静态资源。它有意忽略 HTTP(S) 外链，因此无法发现下面三类问题：

1. GitHub 编辑链接格式合法，但 `blob/main/<path>` 在本仓库中不存在；
2. 首页脚本把返回地址写成 `/`，在 GitHub Pages 子路径部署时跳出项目；
3. Pagefind bundle 从 `/pagefind/` 加载，而真实部署位置是 `/langchain-logbook/pagefind/`。

这些不是普通内部断链，而是“本地事实源 + 部署 base path”的发布契约。因此新增独立的 `scripts/check_site_contracts.py`，不把不同职责继续塞进站内链接解析器。

## 2. 自动门禁的数据流

```text
make check
└── make check-docs
    ├── Astro build + Pagefind index
    ├── check_site_links.py
    │   └── 内部页面与资源是否存在
    └── check_site_contracts.py
        ├── data-home-url == deployment base
        ├── data-bundle-path == <base>/pagefind/
        └── repository/blob/<branch>/<path> 映射到本地真实文件
```

首页与搜索页不要求校验器猜测压缩后的 JavaScript。它们分别把运行契约暴露为 `data-home-url` 与 `data-bundle-path`，浏览器脚本也消费同一个值。这样构建产物是公共测试接缝，组件内部实现仍可调整。

## 3. Red → Green 证据

第一轮先加入四个 CLI 测试；在脚本不存在时得到 `4 failed`。实现最小校验器后得到 `4 passed`：

- 正确本地发布契约通过；
- 不存在的 `src/data/blog/CAPSTONE.md` 仓库事实源失败；
- 首页 `data-home-url="/"` 失败；
- 搜索 `data-bundle-path="/pagefind/"` 失败。

Standards 审查随后发现重复 HTML 属性可能被 `dict(attrs)` 折叠为最后一个值，而浏览器采用第一个值。新增重复 `data-home-url` 反例后先得到 `1 failed`，解析器改为保留全部属性值并要求唯一契约后，发布契约测试为 `5 passed`。

## 4. 自动门禁覆盖什么

- 构建目录、仓库目录不存在时失败；
- 首页或搜索页缺失时失败；
- 契约属性缺失、为空、重复或值错误时失败；
- 本项目 GitHub `blob` 链接没有分支/文件路径、越出仓库根目录、指向目录或不存在文件时失败；
- 所有检查只读取本地 HTML 与文件系统，不访问 GitHub 或模型供应商。

## 5. 自动门禁不覆盖什么

静态契约通过只说明“页面向运行时提供了正确地址，事实源在本地存在”，不证明以下行为：

- Pagefind JavaScript 已在某个真实浏览器成功加载、完成索引查询并渲染结果；
- 首页点击、Astro 页面切换和 `sessionStorage` 在所有浏览器中行为一致；
- Mermaid、表格、代码块、移动菜单和字体布局在真实设备上视觉正确；
- GitHub Pages、CDN、外部 GitHub/DeerFlow 链接与模型供应商当前在线；
- 键盘、屏幕阅读器、高对比度和触摸手势全部通过。

这些仍属于浏览器、真实设备或线上部署 smoke。任务 18 额外用本地浏览器复验了搜索命中、首页进入文章后的 `/langchain-logbook` 返回链接，以及 Capstone 的 `mini_deerflow/CAPSTONE.md` 事实源链接；它们是本次实现证据，不会被描述成跨浏览器保证。

## 6. 验证结果

- 发布契约专项：`5 passed`；
- 整个质量 CLI 文件：`19 passed`；
- 完整 `make check`：`140 passed, 1 skipped`，教程契约 `0 new / 0 known / 0 stale`；
- 真实文档构建：33 pages、21 Pagefind pages；
- 内部链接：`0 broken link(s)`；
- 发布契约：`0 failure(s)`；
- 浏览器：`源码调用链导读` 搜索命中 1 条，返回地址与 Capstone 事实源链接正确。

Standards 与 Spec 修复后复审均为 PASS。
