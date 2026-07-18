# 项目协作约定

## Agent skills

### Issue tracker

本项目使用仓库内的本地 Markdown 文件跟踪课程改造与工程任务，不使用远程 Issue。详细约定见 `docs/agents/issue-tracker.md`。

### Triage labels

任务使用 `needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix` 五类分流标签；文档中提供对应的中文解释和转换条件。详见 `docs/agents/triage-labels.md`。

### Domain docs

本项目采用单上下文结构：根目录 `CONTEXT.md` 维护统一术语和领域模型，`docs/adr/` 记录重要架构决策。详见 `docs/agents/domain.md`。
