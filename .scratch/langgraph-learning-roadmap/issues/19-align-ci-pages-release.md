# 对齐本地门禁、CI 与 GitHub Pages 发布产物

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 18

## Why

本地 `make check` 已包含测试、教程契约、文档构建、断链和发布契约，但现有 Quality workflow 仍手工拆分旧步骤，Pages workflow 又通过独立 action 重新构建并直接上传。这样无法证明部署产物就是通过本地门禁的同一份 `docs-site/dist`。

## Work

- 让 PR/主分支 Quality workflow 调用唯一公共入口 `make check`。
- 让 Pages build job 运行同一门禁，再上传这次门禁生成的 `docs-site/dist`。
- 保留手动发布入口、最小权限、并发保护和部署 environment。
- 增加无需 GitHub 网络的 workflow 静态契约校验及 red → green 测试。
- 编写中文发布、验证、回滚和故障定位手册；不在本任务执行真实部署。

## Acceptance

- Quality 与 Pages build 都无法绕过 `make check`。
- Pages 上传路径严格为已验证的 `docs-site/dist`，不会再次隐式构建。
- `make check` 本地验证 workflow 契约，错误 gate 或 artifact path 会失败。
- 中文手册区分 PR 验证、实际部署、部署后 smoke 与回滚边界。
- 不写入凭据、不 push、不触发线上部署。

## Answer

已把本地、PR 与 Pages 收敛到唯一发布门禁 `make check`。Quality workflow 只有只读权限；Pages build 运行同一门禁，并立即上传这次门禁生成的唯一 `docs-site/dist`；deploy job 只依赖 build artifact，经 `github-pages` environment 调用 Pages deployment，不再使用 `withastro/action` 二次构建。

新增 `scripts/check_workflows.py` 并接入 `make check`。检查器不仅验证 action、权限、触发器、并发、environment、依赖与路径，还要求 Quality 和 Pages build 各自只有一个精确 `make check`：step 和承载 job 都不能带条件或忽略失败；无条件 artifact upload 必须唯一且紧邻门禁，因此验证后插入重建或替换产物会失败。首次线上运行进一步证明 `setup-uv` v8 不发布浮动 major tag；对应反例及“两条 gate job 各恰好一次”的归属反例已加入契约，专项按 red → green 扩展到 `14 passed`。

中文 [`docs/release.md`](../../../docs/release.md) 已覆盖三类运行边界、首次 Pages 配置、发布前后清单、故障定位、artifact 重跑与 `git revert` 回滚，并明确静态文档发布不等于部署 Mini DeerFlow 后端。修正不可用 action tag 与跨 workflow 归属漏洞后，最终 `make check` 为 `154 passed, 1 skipped`、教程漂移 `0/0/0`、34 页构建、22 页中文搜索索引、0 断链、0 发布契约失败、0 workflow 契约失败；Standards 与 Spec 在两轮绕过修复后均 PASS。

本任务最初按 Acceptance 未 push、未触发线上部署、未修改 GitHub 外部设置；任务关闭后，用户在后续对话中另行明确授权 GitHub 登录与配置。后续 Pages 配置和首次线上验证属于该新增授权，而不是对原任务边界的追溯扩大。

完整设计、TDD 与审查记录见[任务 19 实现记录](../artifacts/19-ci-pages-release.md)。
