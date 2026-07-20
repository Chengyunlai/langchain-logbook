# 01 在第一章加入天气 Tool custom streaming 实验

- Status: resolved
- Triage: ready-for-agent
- Type: task
- Blocked by:

## Why

第一章已经解释 `messages`、`updates` 与 `custom` 的概念，但缺少一个可断点调试的天气 Tool 实验，学习者难以看清自动事件与主动业务事件分别在哪里产生，也容易误把 `stream_mode` 当成 Agent 决策控制开关。

## Work

- 在第一章 Markdown 中增加 `ToolRuntime.stream_writer()` 天气进度实验。
- 生成并离线执行同名 Notebook，使该单元成为最后一个可执行实验。
- 同步文档站页面，并把新增 sync id 纳入章节契约。
- 解释锁定版本 Fake Model 的工具调用 streaming 边界。

## Acceptance

- Notebook 输出至少包含 `messages`、`updates` 与 `custom` 三类观测结果。
- custom 事件明确包含天气查询开始与完成。
- 新实验位于第一章 Notebook 的最后一个可执行位置。
- Markdown、Notebook、站点副本与 lesson contract 无漂移。
- Notebook 同步测试、完整测试、Astro 构建与站点契约通过。

## Answer

已在第一章增加 `ch01-custom-stream-boundary` 实验：天气 Tool 通过 `ToolRuntime.stream_writer()` 发出查询开始与完成事件，`create_agent` 的内部节点自动产生 updates，纯文本离线 Agent 产生 messages。实验显式解释 `GenericFakeChatModel` 在 tool-call token streaming 上的限制，避免把 Fake Model 行为误认为真实供应商协议；真实模型仍可在同一次调用订阅三种模式。

Notebook 已从 Markdown 重新生成并离线顺序执行，新单元是最后一个可执行实验，输出依次展示 model update、两条 custom 事件、tools/model update 和 message。验证结果：Notebook/质量 CLI 定向测试 30 个通过；完整测试 162 个通过、1 个外部集成测试跳过；教程校验无新增、已知或陈旧问题；Astro 类型检查与 34 页构建通过；站内链接、发布契约和 SEO 契约均为 0 个失败。

遗留风险：离线 Fake Model 为保持确定性，把 messages 与天气工具循环拆成两个调用；使用真实供应商模型时需要单独验证同一工具循环中的 token、tool call chunk 和 custom 事件顺序。用户原有 Notebook 执行元数据已备份到 `/tmp/langchain-logbook-notebook-backup-20260720/01_Getting_Started.ipynb`。
