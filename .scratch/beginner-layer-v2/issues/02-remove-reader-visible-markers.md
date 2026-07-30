# 移除学习正文中的内部标记

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 01

## Why

真实审阅发现，第 01 章源文件出现面向维护工具的 HTML 注释。即使网页渲染会隐藏这些注释，直接阅读 Markdown 的学习者仍会看到与概念无关的实现细节。

## Work

- 从全部课程源文件移除章节契约、确定性替身模型（Fake Model）说明定位、可运行练习本（Notebook）阅读顺序定位、实验边界和图表 ID 等内部 HTML 注释；Fake Model 不调用外部供应商，只提供稳定输出，Notebook 则承载可执行实验；
- 让 Notebook 同步直接读取正文中的“Notebook 阅读顺序”，不把维护元数据当作学习内容；
- 把实验的层级、类型、概念和配对关系迁移到独立质量清单，正文只保留读者需要的标题、讲解、代码和输出；
- 让课程完整性和 Fake Model 检查验证可见中文内容，不再依赖隐藏注释；
- 同步文档站并运行现有门禁。

## Acceptance

- 读者可见 Markdown 和发布 HTML 中不再存在内部 HTML 注释；
- 第 01、06、11 章生成的 Notebook 开场内容不发生变化；
- 全部课程 Notebook 的实验顺序、代码、输出与质量元数据保持同步；
- Fake Model 首次说明和章节导航仍受自动检查保护；
- `make check` 全部通过。

## Answer

- 内部 HTML 注释已从全部课程 Markdown、Mini DeerFlow 文档和生成站点内容中移除。
- 实验元数据迁移到 `quality/lesson-labs.json`；Notebook 同步器按可见实验小节和 `sync` fence 提取正文，不再依赖 HTML 边界标记。
- Notebook 阅读顺序改为从可见中文栏目提取；三本受影响 Notebook 的开场内容与现有文件一致。
- 写作契约会扫描全部读者可见 Markdown，重新出现任意内部 HTML 注释都会失败；Fake Model 检查仍验证第一次可见提及所在行的解释。
- Notebook 同步、教程质量与写作专项回归通过；发布候选中第 02 章只删除内部标记，没有带入尚未人工审核的正文重写。
- `make check` 通过：186 passed、1 skipped；35 页构建成功；教程、链接、发布和 SEO 契约均为 0。
