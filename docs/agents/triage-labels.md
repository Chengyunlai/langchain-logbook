# 任务分流标签

这些标签描述“任务现在需要谁做什么”，不是实现进度。Wayfinder 的 `open / claimed / resolved` 负责表示执行进度，两者不要混用。

| 标准标签 | 本项目标签 | 中文含义 | 何时使用 |
| --- | --- | --- | --- |
| `needs-triage` | `needs-triage` | 待评估 | 任务刚提出，范围、价值或优先级尚未确认。 |
| `needs-info` | `needs-info` | 等待补充信息 | 缺少用户选择、外部资料、凭证或无法从仓库推断的事实。 |
| `ready-for-agent` | `ready-for-agent` | Agent 可独立执行 | 问题、边界、依赖和验收标准已经明确，无需用户实时参与。 |
| `ready-for-human` | `ready-for-human` | 需要人工参与 | 需要主观取舍、账号操作、视觉确认或真实业务决策。 |
| `wontfix` | `wontfix` | 本轮不处理 | 与当前目的地无关、收益不足，或已被其他方案替代。 |

## 转换规则

- 新发现但尚未分析的任务从 `needs-triage` 开始。
- 缺少必要信息时转为 `needs-info`，信息补齐后重新评估。
- 任务具备清晰输入和验收标准后转为 `ready-for-agent`。
- 只有确实需要用户判断时才使用 `ready-for-human`，不要把普通困难推给用户。
- 确认超出本轮课程改造目标时使用 `wontfix`，并记录原因。
