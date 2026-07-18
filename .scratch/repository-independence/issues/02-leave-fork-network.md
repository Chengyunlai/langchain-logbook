# 02 退出 GitHub fork network

- Status: resolved
- Triage: ready-for-human
- Type: task
- Blocked by: 01

## Why

删除本地 `upstream` 只改变 Git 配置，不会取消 GitHub 仓库页面上的 Fork 标记。用户要求仓库成为真正的独立项目，因此还需要修改 GitHub 托管状态。

## Work

仓库管理员登录 GitHub，进入 `Chengyunlai/langchain-logbook` 的 **Settings → General → Danger Zone**，使用 **Leave fork network**。如果该入口不可用，再按 GitHub 官方文档采用删除并重建独立仓库的人工流程。

## Acceptance

- GitHub 仓库首页不再显示 fork 来源。
- 仓库 URL 仍为 `https://github.com/Chengyunlai/langchain-logbook`。
- 默认分支、完整 Git 提交历史和本地 `origin` 推送地址保持可用。
- 管理员理解退出 fork network 是永久操作，并确认 Issues、Pull Requests、Stars、Watchers、Wikis、评论、子 fork 等仓库元数据可能不会保留。

## Answer

仓库管理员已在 GitHub 完成 **Leave fork network**。2026-07-19 通过 GitHub 公共 API 核验：`fork` 为 `false`、`network_count` 为 `0`，响应不再包含 `parent` 或 `source`；仓库 URL、默认分支 `main` 和 Pages 地址均保持不变。
