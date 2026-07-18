# 实现 Subagent、Sandbox、MCP 与 Skills 扩展

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 10, 12

## Why

DeerFlow 的长任务能力来自受控工具环境和子代理，而不是无限增加主 Agent 工具。此任务把协作、权限和扩展机制落到真实代码。

## Work

- 实现 `task` 调度工具、子代理注册表、并发限制和结果摘要。
- 定义 Sandbox 接口，并提供安全的本地实现或模拟实现。
- 演示线程工作区、文件工具、路径验证和副作用审计。
- 提供 MCP 工具适配与 Skills 元数据/按需加载的最小实现。

## Acceptance

- 子代理上下文与主 Agent 上下文隔离，结果通过明确契约回传。
- Sandbox 生命周期、线程隔离和路径安全有测试。
- MCP/Skills 是可选扩展，不影响离线核心测试。
- 学习者能够把这些模块映射到 DeerFlow 对应源码目录。

## Answer

已完成 Subagent、Sandbox、MCP 与 Skills 扩展纵切面，详细实现、边界与验证证据见 [任务 13 实现记录](../artifacts/13-subagents-sandbox-extensions.md)，学习者入口见 [`mini_deerflow/SANDBOX_EXTENSIONS.md`](../../../mini_deerflow/SANDBOX_EXTENSIONS.md)。

核心结果：

- 复用第 11 章已验证的 task/registry/executor/并发/超时/结果预算，只向 allowlisted Subagent 继承 opaque `sandbox_id`，结果仍通过 `SubagentResult` 回传；
- `LocalSandboxProvider` 提供 user/thread 分区、durable workspace、release/reacquire、路径与 symlink 防护、原子文本写入和无正文审计，并明确拒绝宿主命令；
- workspace tools 从 `ToolRuntime` 取得应用控制的 user/thread，写入产生 `ToolMessage + ArtifactRef` 并继续经过 State/Middleware 安全边界；
- MCP adapter 默认关闭、延迟 import/client creation，启用后再按应用 allowlist 筛选工具；Skill catalog 只发现 metadata，正文通过 `load_skill` 按需返回；
- 中文专题以 4 条 TDD 纵切面、3 张 Mermaid、失败矩阵、权衡、练习和固定提交源码路径映射当前 DeerFlow。

验证：`107 passed, 1 skipped`；教程契约 `0 new / 0 known / 0 stale`；lock、CLI smoke 和 wheel 通过；文档站 27 页与 0 断链；Standards 初审 4 项已全部关闭，Spec 审查无发现。

有意延后：本地 provider 不是生产容器隔离；MCP 真实外部 transport 不进入默认离线 profile；Skill scripts/assets/allowed-tools 继续作为可审查扩展。下一前沿是任务 14 Runtime/API/SSE。
