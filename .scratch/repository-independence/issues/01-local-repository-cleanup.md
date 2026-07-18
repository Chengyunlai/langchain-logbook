# 01 本地仓库与项目身份整理

- Status: resolved
- Triage: ready-for-agent
- Type: task
- Blocked by:

## Why

当前本地仓库仍配置原项目 `upstream`，文档站也混有旧维护者身份；第一次从 PyCharm 打开项目时，环境、解释器和运行入口不够集中。这些问题会让独立维护状态和使用方式都不清晰。

## Work

- 移除本地 `upstream`，只保留自己的 `origin`。
- 统一 README、Python 包元数据和文档站的当前维护者身份。
- 保留完整 Git 历史，并避免把“当前维护者”误写成对历史贡献的覆盖。
- 新增 PyCharm 环境、运行、测试、Notebook 和真实模型配置指南。
- 让站点与仓库地址可以通过构建变量覆盖。

## Acceptance

- `git remote -v` 只显示 `origin`。
- README 和站点不再把旧维护者显示为当前维护者。
- PyCharm 指南可从 README 进入，也能作为文档站页面构建。
- Python 测试、教程校验、Astro 构建、链接检查和发布契约通过。

## Answer

已完成本地远程、项目身份、PyCharm 使用入口与构建配置整理。验证结果：154 个测试通过、1 个外部集成测试跳过；教程校验无漂移；Astro 类型检查与静态构建通过；站内链接和发布契约均为 0 个失败。构建时 Google Fonts 元数据连接超时，项目按既有回退策略继续完成构建。
