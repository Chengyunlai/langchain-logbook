# CI、GitHub Pages 与发布手册对齐记录

> 完成日期：2026-07-14  
> 对应任务：[对齐本地门禁、CI 与 GitHub Pages 发布产物](../issues/19-align-ci-pages-release.md)  
> 发布手册：[`docs/release.md`](../../../docs/release.md)

## 1. 审计结论

改造前有两条互相漂移的自动化路径：

- Quality workflow 把 Python 与 docs 拆成两个 job，docs 只执行旧的内部链接检查，不包含任务 18 的发布契约；
- Pages workflow 使用 `withastro/action` 独立构建并上传，既没有运行 `make check`，也无法证明上传产物与本地验证产物相同。

对旧 workflow 运行新契约校验，得到四类真实失败：

```text
quality-gate
deploy-gate
deploy-artifact
deploy-safety
```

## 2. 统一后的发布数据流

```text
Pull Request / push
→ Quality workflow
→ make check
→ 只产生发布候选结论，不具备 Pages 写权限

main/master push / workflow_dispatch
→ Pages build job
→ make check
→ 同一次 docs-site/dist
→ upload-pages-artifact
→ deploy job needs build
→ github-pages environment
→ deploy-pages
```

Pages 不再调用第二套隐式 builder。`build` job 既拥有完整门禁，也拥有 artifact 上传；`deploy` job 没有源码构建职责，只消费该 artifact。

## 3. Workflow 契约

`scripts/check_workflows.py` 通过本地 YAML 检查：

- `quality.yml` 全部 job 中恰好有一个有效 `make check` gate；
- gate 必须是独立且精确的 `run: make check`，step 与承载 job 都不能带 `if`，也不能忽略失败；
- `deploy.yml` 的 `build` job 同样只有一个有效 gate，且不使用 `withastro/action`；
- build 恰好上传一次 `docs-site/dist`，上传 step 无条件且紧邻 gate，验证后不能插入二次构建；
- deploy 必须 `needs: build`、使用 `github-pages` environment，并恰好调用一次 deploy action；
- 保留 `workflow_dispatch`、精确最小权限和 Pages 并发保护；
- Pages action major 固定为当前校准的 `configure-pages@v6`、`upload-pages-artifact@v5`、`deploy-pages@v5`。

该检查作为 `check-workflows` 接入 `make check`，因此 workflow 不能通过修改自己来绕过本地门禁而不触发失败。

## 4. Red → Green

按纵切面逐项加入测试：

1. Quality 只运行 `make test`：先失败，再增加 `quality-gate`；
2. Pages 使用 `withastro/action`：先失败，再增加 `deploy-gate`；
3. build 上传 `docs-site/public`：先失败，再增加 `deploy-artifact`；
4. deploy 不依赖 build：先失败，再增加 `deploy-wiring`；
5. 缺手动入口、权限过宽、无并发保护：先失败，再增加 `deploy-safety`；
6. Pages artifact action 回退到旧 major：先失败，再增加 `pages-action-version`；
7. 正确 Quality + Pages fixture 作为正向契约；
8. step 级 `if: false` / `continue-on-error: true` 不能伪装成有效 gate；
9. gate 之后插入 `npm run build` 会触发 `deploy-artifact-flow`；
10. job 级 `if: false` / `continue-on-error: true` 同样不能绕过 gate。
11. 不存在的 `setup-uv@v8` 浮动 tag 会触发 `setup-uv-version`，Quality 与 Pages 必须使用已校准的不可变 tag。
12. Quality 重复两次 setup-uv、Pages build 完全缺失时仍失败，证明两个 gate job 各自恰好安装一次。

专项最终为 `14 passed`。其中验证后重建、Quality job 条件跳过、Pages build 容错、无效 setup-uv tag 与跨 workflow 归属五个反例都先得到预期失败，再完成最小实现。

## 5. 当前性校准

2026-07-14 依据官方资料校准：

- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)：build/upload/deploy、`needs`、environment、`pages: write` 与 `id-token: write`；
- [actions/checkout](https://github.com/actions/checkout)：当前 v6；
- [actions/setup-python releases](https://github.com/actions/setup-python/releases)：当前 v6；
- [actions/setup-node](https://github.com/actions/setup-node)：当前 v6；
- [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv)：当前使用不可变 tag `v8.3.2`；v8 起不再发布 `v8` 浮动 tag；
- Pages actions：`configure-pages@v6`、`upload-pages-artifact@v5`、`deploy-pages@v5`；首次线上 run 暴露旧 major 的 Node 20 弃用警告后，以官方 release 页重新校准到 Node 24 版本。

workflow action major 与课程运行时分开：action 更新到当前 major，但仍明确安装 Python 3.12、Node 22 与 uv 0.7.6，不借 CI 改造静默升级课程依赖。

## 6. 中文交接手册

`docs/release.md` 解释：

- 本地候选、PR Quality 和 Pages 部署各自的权限与终态；
- 首次 Pages 设置；
- 发布前清单与部署后 smoke；
- build、artifact、OIDC/environment、线上 smoke 的故障定位；
- artifact 重跑与 `git revert` 两类可审计回滚；
- 为什么不能 `reset --hard` 共享主分支或手改线上生成文件；
- 静态文档部署与 Mini DeerFlow 后端生产部署的明确边界。

手册通过 `copy-docs.mjs` 同步到文档站，README 也提供入口。

## 7. 原任务边界与后续授权

任务 19 完成本地实现时，以下操作明确不在原始任务授权内：

- 不 push 工作区；
- 不触发 `workflow_dispatch`；
- 不修改 GitHub Pages Source 或 environment protection；
- 不写入 Secret 或长期 token；
- 不把静态 Pages 部署当成 Gateway/worker/数据库部署。

这些外部状态只在用户明确授权后执行。2026-07-14 用户随后明确表示可以登录 GitHub 并要求协助配置，因此后续首次 Pages 配置、push 和线上 workflow 属于新的显式授权，不改变原任务验收边界。

## 8. 双重审查与最终验证

首轮 Standards / Spec 审查发现两类契约漏洞：检查器只按 run 文本识别 gate，允许 step 条件跳过或忽略失败；同时 gate 与 artifact upload 分开检查，不能证明二者顺序。修复为“唯一、精确、无条件 gate + 紧邻唯一上传”后，第二轮又发现承载 gate 的整个 job 仍可能条件跳过或容错。加入 job 级反例并把同一无条件规则提升到 job 后，两路最终复审均 PASS。

最终本地证据：

- workflow 契约专项：`14 passed`；
- 真实 workflow：`Workflow contracts: 0 failure(s)`；
- 完整 `make check`：`154 passed, 1 skipped`；
- 教程同步：`0 new / 0 known / 0 stale`；
- Astro：`0 errors / 0 warnings / 0 hints`，34 pages；
- Pagefind：22 pages、4689 words；
- 内部链接：`0 broken link(s)`；
- 站点发布契约：`0 failure(s)`。

Astro/Vite 仍报告超过 500 kB 的 Mermaid 客户端 chunk 提示，但 Astro diagnostics 为零，且该提示不影响本任务的发布正确性；它可作为后续性能优化观察项，不冒充本次阻塞。
