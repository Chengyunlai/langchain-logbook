---
title: "版本、依赖与验证策略"
description: "理解兼容范围、锁定版本与依赖升级门禁。"
pubDatetime: 2025-01-01T00:00:00Z
featured: false
tags: ["tutorial"]
sourcePath: "docs/version-policy.md"
learningOrder: 21
learningStage: "reference"
learningStageTitle: "维护与协议资料"
learningGoal: "理解兼容范围、锁定版本与依赖升级门禁。"
contentType: "reference"
---

> 最近校准：2026-07-13

本项目是一套需要长期维护的教程。版本策略的目标不是追逐每次发布，而是同时保证“当前能力可学”和“任意提交可复现”。

## 三层版本事实

| 层次 | 事实源 | 含义 |
|---|---|---|
| 课程兼容范围 | `pyproject.toml` | 本轮课程允许的 minor 版本窗口，例如 LangChain 1.3.x |
| 精确复现环境 | `uv.lock` | CI、维护者和学习者安装的完整传递依赖版本 |
| 实际运行环境 | `uv run --locked ...` | 必须与 lock 一致；全局 Python 和手工 `pip install` 不算课程验证环境 |

`pyproject.toml` 中的范围不表示所有未来 patch 都天然兼容。只有 lock 更新后完成离线测试、Notebook 检查和文档构建，新的 patch 才成为课程已验证版本。

## 为什么显式声明直接依赖

课程直接导入 `langgraph`、`langchain-core` 和 `langsmith`，因此它们必须是直接依赖，不能只依靠 `langchain` 暂时带入。这样做可以：

- 让课程使用的运行时边界在 `pyproject.toml` 中可见；
- 避免上游调整传递依赖后突然无法导入；
- 为 LangChain、LangGraph、Core 和 LangSmith 设置彼此兼容的 minor 窗口；
- 让升级评审能够看到真正改变的核心包。

Notebook、pytest 和交互式 shell 位于 `dev` dependency group。它们是课程开发工具，不是未来 Mini DeerFlow 的运行时依赖。

## 当前课程窗口

| 包 | 兼容窗口 | 选择理由 |
|---|---|---|
| `langchain` | `>=1.3.13,<1.4` | 当前稳定 `create_agent`、middleware 与 model/tool 入口 |
| `langchain-core` | `>=1.4.9,<1.5` | 消息、Runnable、tool 与模型协议 |
| `langgraph` | `>=1.2.9,<1.3` | Graph、durable execution、v2 stream 与 interrupt |
| `langsmith` | `>=0.10.2,<0.11` | 当前 tracing/evaluation 客户端 |

精确 patch 版本必须读取 `uv.lock`，README 不重复手写，以免出现第四套版本事实。

## API 状态

- **current**：课程主线，必须有离线测试或 integration test。
- **compatibility**：仍支持但不是新代码首选，正文解释迁移边界。
- **legacy**：只在迁移附录出现，例如 `langchain.smith` 与 LangServe。
- **preview**：实验性能力，不作为核心验收唯一依赖，例如尚未稳定的 streaming preview。

教程验证器会把已发现的 legacy import、v2 错误解包、错误 Notebook 输出等记录在 `quality/tutorial-baseline.json`。新增问题会立即失败；已知问题修复后，旧 baseline 会变成 stale 并要求维护者显式删除。这让课程可以在不覆盖用户现有章节修改的情况下先建立质量门禁，再逐章清偿债务。

## 离线与集成测试

核心质量门禁永远不需要付费 API：

```bash
make test
```

它验证：

- LangChain/LangGraph 公共导入；
- v2 stream event envelope；
- Agent 的标准 `messages` 输入；
- Markdown 代码导入、Notebook 语法与二者代码契约同步；
- 已知教程债务没有新增、漂移或被静默隐藏。

pytest 会收集外部实验，但在默认 `offline` profile 下将它们明确显示为
`SKIPPED`。这既证明测试确实存在，也避免“用 deselect 假装通过”。需要真实
DeepSeek 冒烟测试时，显式提供 Key 后运行：

```bash
DEEPSEEK_API_KEY=... make test-integration
```

完整本地门禁还会干净构建文档站并检查生成链接：

```bash
make check
```

真实 DeepSeek、OpenAI-compatible、百炼、LangSmith 或 Langfuse 调用属于 integration profile。只有 profile 与对应 Key 同时存在才允许发出请求；缺少任一条件时必须显示 `SKIPPED`，不能把认证失败或没有收集到测试当成成功。

## 升级流程

1. 阅读官方 release notes 和 breaking changes；
2. 调整 `pyproject.toml` 的版本窗口；
3. 运行 `uv lock --upgrade-package <package>`；
4. 查看 lock diff，确认核心包和集成包的联动升级；
5. 运行 `make test`；
6. 顺序执行核心 Notebook 或后续自动 Notebook runner；
7. 运行 `make check`；
8. 对真实 provider 执行有标记的 integration tests；
9. 更新本文件的校准日期与官方能力基线。

不要在 Notebook 中临时 `pip install -U`，也不要为了让一个单元通过而放宽到无上限版本范围。这两种做法都会让课程离开可复现环境。