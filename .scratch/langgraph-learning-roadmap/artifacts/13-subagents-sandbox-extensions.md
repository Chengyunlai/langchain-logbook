# Mini DeerFlow Subagent、Sandbox、MCP 与 Skills 扩展实现记录

> 完成日期：2026-07-13  
> 对应任务：[实现 Subagent、Sandbox、MCP 与 Skills 扩展](../issues/13-implement-subagents-sandbox-extensions.md)  
> 学习入口：[`mini_deerflow/SANDBOX_EXTENSIONS.md`](../../../mini_deerflow/SANDBOX_EXTENSIONS.md)  
> 架构入口：[`mini_deerflow/ARCHITECTURE.md`](../../../mini_deerflow/ARCHITECTURE.md)

## 1. 结论

Mini DeerFlow 已在不破坏离线核心的前提下，完成一条受控能力扩展纵切面：

```text
Application Runtime identity
→ SandboxProvider 按 user/thread acquire 工作区
→ workspace tools 只接受模型可选的相对路径与内容
→ 路径/symlink/字节预算校验、原子写入与有界审计
→ Command 把 ToolMessage + ArtifactRef 同时投影回 ThreadState
→ task tool 只向 allowlisted Subagent 传递 opaque sandbox_id
→ SubagentResult 返回有界 summary/artifacts
→ 可选 MCP tools 经本地 allowlist 后注入
→ Skill catalog 只暴露 metadata，正文经 load_skill 按需进入上下文
```

任务中的 `task` 调度、Subagent registry、并发/超时与结果预算已由任务 10/第 11 章交付。本任务复用并扩展这条经验证的路径，没有为 Sandbox 另写一套 executor。

## 2. Sandbox 与线程工作区

### 2.1 稳定 provider 契约

`SandboxProvider` 统一 `acquire(thread_id, user_id) / get(sandbox_id) / release(sandbox_id)` 生命周期；`SandboxSession` 统一文本读写、命令请求、工作区识别和审计事件。

`LocalSandboxProvider` 实现：

- 对 user/thread identity 做 digest，不把邮箱、斜杠或外部 ID 直接写入宿主路径；
- 同 user/thread 稳定获得同一 `sandbox_id`，不同 user 或 thread 得到不同工作区；
- release 释放会话对象，不隐式删除线程数据；重新 acquire 可恢复文件；
- 拒绝空路径、绝对路径、`..`、目标 symlink、父级 symlink、工作区/root 被 symlink 替换和越出 provider root 的解析；
- 单次文本读写有字节预算，写入用同目录临时文件 + `os.replace()`；
- 审计仅记录 action/path/outcome/字节大小，不复制文件正文；
- `execute()` 固定返回 exit code 126，不把宿主 shell 冒充为隔离执行。

这些保证仍然只是“受控本地线程工作区”。它不提供进程、网络、CPU/内存、恶意多租户或容器逃逸隔离。

### 2.2 工作区工具与 Artifact

`build_sandbox_workspace_tools()` 暴露 `read_workspace_file` 和 `write_workspace_file`：

- 模型 schema 只有 path/content/media type，没有 user/thread/provider/宿主 root；
- `ToolRuntime` 从应用 Context 和 configurable 取得 user/thread；
- metadata 分别要求 `workspace:read` 和 `workspace:write`；
- 写工具返回 `Command(update={messages, artifacts})`，继续经过任务 12 的 Artifact Middleware 与 reducer。

## 3. Subagent 能力继承

`build_task_tool(..., sandbox_provider=...)` 只在应用内部 acquire 会话，把 `sandbox_id` 加入 parent safe context。Executor 仍用 `SubagentSpec.allowed_context_fields` 取交集，因此 specialist 不会获得主 messages、auth token、workspace root 或 provider 对象。

测试中的 `report-writer` 只通过 handle 取得会话、写入 Artifact，再以 `SubagentResult` 返回有界结果。Delegation Ledger 只记录 `context_keys=("sandbox_id",)`，不保存 Secret 或主对话。

## 4. 可选 MCP 与 Skills

### 4.1 MCP

`MCPToolAdapter` 在 `enabled=False` 时不创建 client、不 import optional package、不连 server。启用后：

- 通过官方 `MultiServerMCPClient.get_tools()` 的最小异步接口发现工具；
- 仅保留应用 `allowed_tool_names` 中的名称；
- 拒绝重名并标记 `source=mcp` / `optional_extension=True`；
- 可选包未安装时只在真正 load 处失败，并给出明确安装命令；
- 组合根二次检查所有 built-in/extension tool name，不允许覆盖。

`mcp` 是 `pyproject.toml` 的显式 optional extra。默认 locked/dev 环境不安装 adapter，离线核心测试不受影响。缺包测试主动 mock import failure，即使开发者安装了 extra 也不会误启不存在的外部 server。

### 4.2 Skills

`SkillCatalog` 扫描 `*/SKILL.md`，用 `yaml.safe_load()` 校验 `name/description`，并只缓存 metadata/path。`render_index()` 不含正文；`load_skill(name)` 被模型显式调用后才返回 instructions。

Catalog 在 discovery 和 load 两阶段都重新校验 root/symlink/256000-byte 限制；load 还拒绝 metadata 在发现后被悄然替换。随 wheel 分发的 `research-report` 教学 Skill 提供中文引用核验工作流。

## 5. 教学与 DeerFlow 映射

`mini_deerflow/SANDBOX_EXTENSIONS.md` 以四个 TDD 纵切面组织，包含：

1. 路径护栏、本地 provider 与容器 Sandbox 的边界；
2. provider lifecycle 和 thread/user ownership；
3. `ToolRuntime → Session → Command → Artifact State` 时序；
4. Subagent 能力句柄而非全 Context 继承；
5. MCP discovery/authorization 分层；
6. Skill metadata/body 渐进披露；
7. 失败矩阵、反例、工程权衡、练习和延迟回忆题；
8. 3 张 Mermaid 图及文本替代。

对照 DeerFlow `807c3c521832526c6205ffee23e5f05231eaea5b`，学习路径从 `sandbox_provider.py` 依次进入 local provider、sandbox middleware/tools/security、task/executor、MCP tool assembly、skills catalog，最后回到 `make_lead_agent` 组合根。

## 6. TDD 与审查证据

- Sandbox 红灯：缺少 `LocalSandboxProvider`；绿灯后又用工作区/root symlink 替换测试补强 provider root 安全。
- Workspace tool 红灯：缺少 `build_sandbox_workspace_tools`；绿灯证明真实 Agent loop 产生 Artifact State。
- Subagent 红灯：`task` 不接受 provider；绿灯证明 specialist 只获得 `sandbox_id`。
- MCP/Skills 红灯：模块不存在；绿灯覆盖 lazy/allowlist 和 metadata/on-demand body。
- Standards 初审发现 4 项：MCP 缺包测试会受已安装 extra 影响、provider root symlink 过早 resolve、Skill load 未重验文件预算、Lead 教程一处未来时。全部修复后复核为 0 个开放项。
- Spec 审查通过，无缺失、范围漂移或错误实现发现。

## 7. 验证结果

- 全量离线测试：`107 passed, 1 skipped`；跳过项是显式外部 integration case。
- 唯一 pytest warning 来自 LangSmith 依赖使用 Python 3.14 将弃用的 `ast.Str`，不来自本任务代码。
- 教程契约：`0 new / 0 known / 0 stale`；第 02/11 章 Notebook 已由更新后的 Markdown 重新生成并离线执行。
- CLI smoke：offline profile 正常，注册 6 个工具（包含 workspace read/write 和 task），Middleware events 正常。
- Lock：`uv lock --check` 通过，解析 215 个 package；默认 dev 运行中 optional MCP adapter 未安装。
- Wheel：Sandbox/MCP/Skills/workspace tools 与 `research-report/SKILL.md` 均进入 package。
- 文档站：27 页可构建，Sandbox 专题的 3 张 Mermaid 均完成转换，链接检查为 `0 broken links`。
- Astro 保留 2 个既有未使用 icon hints；Vite 保留 Mermaid 大 chunk 提示，均不是本任务引入的功能错误。

## 8. 有意延后的范围与下一前沿

- 不可信代码执行、进程/容器、网络和资源 quota，必须由更强生产 Sandbox provider 实现。
- MCP 外部 server 真实 transport/session/interceptor 集成不进入默认离线测试；本任务固定的是 adapter 与授权接缝。
- Skill references/assets/scripts、allowed-tools、来源签名与 Secret policy 只作为练习/生产延伸，当前不自动执行。
- 任务 14 下一步实现 thread/run repository、完整 SSE、取消、interrupt 恢复和 API 适配。
- 任务 15 在 13/14 都解决后，再统一扩展评测、观测和安全回归矩阵。
