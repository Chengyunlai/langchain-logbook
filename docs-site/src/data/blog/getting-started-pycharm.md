---
title: "在 PyCharm 中使用 LangChain Logbook"
description: "在 PyCharm 中复用 uv 环境，运行离线示例、测试与 Notebook，并找到课程入口。"
pubDatetime: 2025-01-01T00:00:00Z
featured: false
tags: ["tutorial"]
sourcePath: "docs/getting-started-pycharm.md"
learningOrder: 22
learningStage: "reference"
learningStageTitle: "维护与协议资料"
learningGoal: "在 PyCharm 中复用 uv 环境，运行离线示例、测试与 Notebook，并找到课程入口。"
contentType: "reference"
---

这份指南只解决第一次打开项目时最容易卡住的环境、运行和阅读入口。项目的 Python 依赖由 `uv.lock` 锁定，不建议在 PyCharm 中逐个手工安装包。

## 1. 准备 Python 和 uv

项目要求 Python 3.12 或更高版本。在 PyCharm 底部打开 **Terminal**，运行：

```bash
python3 --version
make install-uv
make setup
```

`make setup` 会创建项目根目录下的 `.venv`、按 `uv.lock` 安装依赖，并在缺失时从 `.env.example` 创建 `.env`。

如果 `make install-uv` 刚完成但终端仍然找不到 `uv`，关闭并重新打开 PyCharm Terminal，再运行 `make setup`。

## 2. 配置 PyCharm 解释器

打开 **Settings → Project → Python Interpreter**，选择已有环境中的解释器：

```text
<项目目录>/.venv/bin/python
```

不要再创建第二个 `venv`，否则 PyCharm 解释器和 `uv run` 可能使用两套不同依赖。

## 3. 先运行离线示例

在 Terminal 中执行：

```bash
make mini-deerflow
```

这个入口运行真实的 LangChain `create_agent` 与 LangGraph 工具循环，但使用可预测的 fake model，因此不需要 API Key。随后可以继续运行：

```bash
make mini-deerflow-eval
make mini-deerflow-capstone
```

三个命令分别验证基础对话、结果/轨迹/预算评测，以及包含检索、委派、审批、恢复和幂等发布的长任务闭环。

## 4. 在 PyCharm 中创建 Run Configuration

如果希望使用右上角的运行按钮，可创建以下配置。

### Mini DeerFlow

- 配置类型：**Python**
- Run：**Module name**
- Module name：`mini_deerflow`
- Working directory：项目根目录
- Python interpreter：项目的 `.venv`

### 测试

- 配置类型：**pytest**
- Target：`tests`
- Working directory：项目根目录
- Environment variables：`LANGCHAIN_LOGBOOK_PROFILE=offline`

命令行中的等价入口是：

```bash
make test
```

## 5. 阅读和运行 Notebook

推荐从 `tutorials/01_Getting_Started.ipynb` 开始。也可以在 Terminal 中启动 Jupyter：

```bash
make lab
```

如果直接在 PyCharm 中打开 Notebook，请把 Kernel（内核）选择为项目 `.venv`。Markdown 是课程事实源，Notebook 是可执行实验；修改课程内容后不要只更新其中一个。

## 6. 使用真实模型

离线示例和核心测试不需要密钥。需要运行真实供应商示例时，编辑根目录 `.env`，按需填写：

```dotenv
OPENAI_API_KEY=...
DEEPSEEK_API_KEY=...
BAILIAN_API_KEY=...
```

`.env` 已被 Git 忽略，不要把真实密钥写进 Notebook、测试或提交记录。

## 7. 常用命令

| 命令 | 用途 |
| --- | --- |
| `make help` | 查看全部项目命令 |
| `make setup` | 创建环境并安装锁定依赖 |
| `make mini-deerflow` | 运行离线 Agent 示例 |
| `make lab` | 启动教程 Notebook |
| `make test` | 运行离线测试与教程校验 |
| `make check` | 运行测试、Notebook、文档站和发布契约的完整门禁 |

## 8. 推荐学习顺序

1. 阅读根目录 `README.md`，理解课程的四部结构。
2. 完成 `tutorials/01` 到 `tutorials/03`，掌握模型、结构化输出和检索。
3. 完成 `tutorials/04` 到 `tutorials/06`，理解 Agent 工具循环、Context 与 Middleware。
4. 完成 `tutorials/07` 到 `tutorials/10`，学习 StateGraph、Checkpoint 和人工审批。
5. 阅读 `tutorials/11` 与 `mini_deerflow/`，把前面的能力装配成完整系统。

遇到问题时，先运行 `make test` 获取可复现的失败，再根据第一个失败定位环境或代码问题。