# 第一章 custom streaming 实验

## 目的地

让学习者在第一章的天气 Agent 中直接观察 `messages`、`updates` 与 `custom` 三条 streaming 通道，并能区分事件观测与 Agent 执行控制。

## 执行原则

- Markdown 是课程事实源，Notebook 与站点页面必须由同步脚本生成。
- 核心实验必须使用 offline profile，不能依赖 API Key 或外部网络。
- Fake Model 的能力边界必须显式解释，不能用不稳定行为伪装真实工具流。
- 实验必须提供断言和可读输出，让 PyCharm/Jupyter 能即时反馈。

## 已确认决策

- [01 在第一章加入天气 Tool custom streaming 实验](./issues/01-weather-tool-custom-stream.md)：通过 `ToolRuntime.stream_writer()` 发出业务事件，并将实验放在 Notebook 最后一个可执行位置。

## 当前前沿

- 本轮实验已完成，没有开放任务。

## 尚未明确

- 无。
