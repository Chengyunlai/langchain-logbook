# 把文档站浏览器发现固化为发布契约

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 17

## Why

任务 17 的浏览器 QA 发现三类问题无法被原有站内链接检查覆盖：GitHub 编辑链接虽然是外链但可能指向仓库中不存在的文件；首页返回地址可能丢失 GitHub Pages base path；Pagefind bundle 可能按域名根路径加载。只依赖发布前人工观察会让同类回归再次出现。

## Work

- 为静态构建产物增加独立的发布契约校验器。
- 校验仓库 `blob/<branch>/<path>` 链接映射到真实本地事实源。
- 校验首页返回地址和 Pagefind bundle 地址都包含部署 base path。
- 以最小静态站 fixture 完成 red → green 测试，并接入 `make check-docs` / `make check`。
- 用中文说明自动门禁与仍需浏览器验证的边界。

## Acceptance

- 错误 GitHub 事实源、错误首页返回地址、错误 Pagefind bundle path 各有一个先失败后通过的 CLI 测试。
- 正确构建产物通过发布契约校验。
- `make check` 仍是一条完整的发布验证命令。
- 校验器只读取本地构建产物和仓库，不依赖网络。

## Answer

已新增 `scripts/check_site_contracts.py` 并接入 `make check-docs`。静态发布门禁现在独立验证首页 `data-home-url`、搜索 `data-bundle-path`，以及本项目 GitHub `blob/<branch>/<path>` 是否映射到仓库内真实文件；缺失、空值、重复属性、错误 base、路径穿越和不存在文件都会失败，全程不访问网络。

测试按 red → green 完成：初始 4 个行为测试因脚本不存在全部失败，实现后通过；Standards 审查发现重复 HTML 属性的浏览器首值语义风险后，新增反例先失败，再改为保留全部属性并要求唯一契约，专项最终 `5 passed`。完整质量 CLI `19 passed`，最终 `make check` 为 `140 passed, 1 skipped`、教程漂移 `0/0/0`、33 页构建、21 页搜索索引、0 断链、0 发布契约失败；本地浏览器也复验了搜索、文章返回和 Capstone 事实源链接。Standards/Spec 复审均 PASS。

自动门禁与浏览器、视觉、线上部署及无障碍验证的边界详见[任务 18 实现记录](../artifacts/18-site-release-contracts.md)。
