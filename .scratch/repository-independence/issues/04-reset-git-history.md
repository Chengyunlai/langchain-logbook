# 04 重置 Git 提交历史

- Status: resolved
- Triage: ready-for-agent
- Type: task
- Blocked by: 03

## Why

仓库已经脱离 GitHub fork network，但 `main` 仍保留从早期仓库继承的提交链。用户明确要求清空 Git 提交记录，让当前验证通过的完整项目成为独立仓库的新起点。

## Work

- 在仓库外创建包含重写前全部引用的临时 Git bundle。
- 将当前工作区完整快照写入一个新的根提交 `Initial commit`。
- 使用带预期远程 SHA 的强制推送更新 `main`，避免覆盖并发远程修改。
- 删除仍引用旧提交历史的远程功能分支和标签。
- 核验本地与 GitHub 的 `main` 只包含一个提交。

## Acceptance

- `git rev-list --count main` 返回 `1`。
- `git log main` 只显示新的 `Initial commit`。
- 本地工作区与重写前验证通过的项目快照一致。
- GitHub `main` 指向新的根提交，且没有其他远程分支或标签保留旧提交链。

## Answer

已在 `/tmp/langchain-logbook-before-history-reset-20260719.bundle` 创建并验证完整恢复包。当前项目快照被写入单一根提交 `Initial commit`，GitHub `main` 已使用带预期 SHA 的 `--force-with-lease` 更新；两个本地与远程功能分支以及内部旧历史引用均已清理。最终核验要求为：本地与远程 `main` 提交数均为 1，且不存在其他远程分支或标签。
