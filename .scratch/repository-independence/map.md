# 仓库独立化整理地图

## 目的地

让 `Chengyunlai/langchain-logbook` 以独立维护项目的身份继续演进：本地只跟踪自己的远程仓库，公开页面不再沿用旧维护者身份，并为 PyCharm 用户提供可验证的首次运行入口。

## 执行原则

- 以当前验证通过的项目快照作为独立仓库的新根提交，不继续公开旧 fork 历史。
- 重写远程历史前在仓库外创建临时恢复包，避免误操作导致项目内容丢失。
- 不删除 `.scratch`、课程事实源、Notebook 或项目内容来制造“整洁”的假象；旧分支只在 bundle 备份后作为历史引用清理。
- 本地 Git 整理与 GitHub fork network 是两种不同状态，分别验证。
- GitHub 账号设置、永久退出 fork network 等操作由仓库管理员确认后执行。

## 已确认决策

- [01 本地仓库与项目身份整理](./issues/01-local-repository-cleanup.md)：本地仅保留 `origin`，发布身份改为当前维护者，并补齐 PyCharm 使用入口。
- [02 退出 GitHub fork network](./issues/02-leave-fork-network.md)：GitHub API 已确认仓库为独立仓库，`fork` 为 `false`。
- [03 项目导向的 About 与 README](./issues/03-project-facing-copy.md)：公开入口统一介绍项目定位、学习产物和工程原则。
- [04 重置 Git 提交历史](./issues/04-reset-git-history.md)：用当前项目快照创建单一根提交，并移除仍引用旧历史的远程分支。

## 当前前沿

- 本轮仓库独立化、历史重置与 GitHub Pages 恢复已全部完成。
