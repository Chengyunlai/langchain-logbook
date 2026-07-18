# 建立版本、依赖与自动验证基线

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 01, 03

## Why

教程如果不能持续执行，详细内容越多，过期和互相矛盾的风险越高。版本策略与 CI 必须先于大规模内容重写落地。

## Work

- 明确直接依赖与传递依赖，决定兼容版本范围和锁文件更新策略。
- 修复 `make test`，加入 Markdown 代码导入检查、Notebook 结构检查和可离线执行测试。
- 为需要真实模型或外部服务的实验设计可跳过标记与 mock/fake 模型。
- 在 CI 中构建 Astro 文档站并检查内部链接。

## Acceptance

- README、pyproject、uv.lock 和实际环境版本语义一致。
- 一条本地命令可以完成主要静态与离线验证。
- CI 能捕获过期导入、错误流式解包、Notebook 不同步和文档站构建失败。
- 外部 API 缺失时，核心测试仍能稳定运行。

## Answer

已完成[版本、依赖与自动验证基线](../artifacts/06-version-dependency-ci-baseline.md)。

关键结果：

- 课程核心依赖采用有上界的 minor 窗口，`uv.lock` 作为唯一精确环境，所有命令通过 `uv run --locked` 执行。
- `make check` 现在串联 lock、offline pytest、教程验证、Astro 干净构建和最终静态站内部链接检查。
- 教程验证器会实际检查导入，识别 v2 stream 错误解包、Agent 输入错误、Notebook error/未执行状态，以及 Markdown/Notebook 的归一化 AST 代码漂移。
- 现有 23 项教程问题进入带内容指纹的显式 baseline；新增问题和已修复但未清理的 stale 问题都会失败。
- 新增真实 DeepSeek integration 冒烟测试。默认 offline profile 会收集并明确显示 `SKIPPED`；只有 integration profile 与 Key 同时存在才允许联网。
- 修复文档站 GitHub Pages base path 与 69 处生成断链，部署前缀集中配置；越出 `dist` 的相对链接即使命中仓库文件也会失败。
- 完整 `make check` 结果为 14 passed、1 skipped、0 new、23 known、0 stale、22 pages、0 broken links。

该基线已解锁 07–11：基础/Agent、Context/Middleware、Graph/Persistence/HITL、多 Agent，以及 Mini DeerFlow 工程骨架可开始实施。
