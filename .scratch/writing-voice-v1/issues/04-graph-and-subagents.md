# 改写第 07–11 章

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 03

## Why

Graph、恢复、HITL 和 Subagent 是全书最抽象的一段。需要保留完整实验，同时减少连续定义和机械对照。

## Acceptance

- 每个新机制都能回指一个具体失败。
- 07–10 的恢复主线与第 11 章上下文问题连续。
- 复杂模式比较由控制权和运行结果说明，不靠术语堆叠。

## Answer

第 07–10 章现在沿“显式顺序、动态并行、跨进程恢复、可恢复审批与幂等副作用”连续推进；第 11 章从 Lead 上下文被原始材料淹没进入 Subagent。

Router、Handoff、Subgraph 与 Subagent-as-tool 通过控制权和运行结果比较。代码、输出、实验契约与 Mini DeerFlow 迁移均保留。
