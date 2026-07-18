# 05 恢复独立仓库的 GitHub Pages

- Status: resolved
- Triage: ready-for-agent
- Type: task
- Blocked by: 04

## Why

仓库退出 fork network 后，用户访问 `/posts/introduction/` 得到 404。GitHub Actions 显示最后一次 Pages 部署成功于退出 fork network 之前，说明静态产物本身已通过门禁，但独立仓库需要一次新的 Pages 配置与部署。

## Work

- 使用当前新根提交触发 `.github/workflows/deploy.yml`。
- 等待 `configure-pages`、构建、artifact 上传和 `deploy-pages` 完成。
- 通过 GitHub Actions 与 deployment API 核验新根提交的部署状态。
- 确认 `/posts/introduction/` 路由包含在构建产物中。

## Acceptance

- 新根提交对应的 Deploy workflow 结论为 `success`。
- GitHub Pages deployment 指向新根提交并处于成功状态。
- 本地构建包含 `dist/posts/introduction/index.html`，站内链接与发布契约为 0 个失败。

## Answer

根因是退出 fork network 后 GitHub Pages Source 需要重新设置为 **GitHub Actions**；旧部署虽然成功，但发生在仓库独立化之前。重新启用 Source 后，新根提交对应的 Deploy workflow 已完成 `configure-pages`、完整门禁、artifact 上传与 `deploy-pages`，结论为 `success`；deployment API 同时返回 `state: success`，环境地址为 `https://chengyunlai.github.io/langchain-logbook/`。本地构建确认 `posts/introduction/index.html` 存在，站内链接与发布契约均为 0 个失败。执行环境访问 `github.io` 会被网络重置，因此最终线上 HTTP 状态由 GitHub deployment 状态与用户浏览器确认共同覆盖。
