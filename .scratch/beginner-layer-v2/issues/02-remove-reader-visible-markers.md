# 移除学习正文中的内部标记

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 01

## Why

真实审阅发现，第 01 章源文件出现面向维护工具的 HTML 注释。即使网页渲染会隐藏这些注释，直接阅读 Markdown 的学习者仍会看到与概念无关的实现细节。

## Work

- 从全部课程源文件移除章节契约、确定性替身模型（Fake Model）说明定位和可运行练习本（Notebook）阅读顺序定位标记；Fake Model 不调用外部供应商，只提供稳定输出，Notebook 则承载可执行实验；
- 让 Notebook 同步直接读取正文中的“Notebook 阅读顺序”，不把维护元数据当作学习内容；
- 让课程完整性和 Fake Model 检查验证可见中文内容，不再依赖隐藏注释；
- 同步文档站并运行现有门禁。

## Acceptance

- 用户指出的四类 HTML 注释不再存在于仓库课程内容中；
- 第 01、06、11 章生成的 Notebook 开场内容不发生变化；
- Fake Model 首次说明和章节导航仍受自动检查保护；
- `make check` 全部通过。

## Answer

- 四类内部标记已从全部课程 Markdown 和生成站点内容中移除。
- Notebook 阅读顺序改为从可见中文栏目提取；三本受影响 Notebook 的开场内容与现有文件一致。
- 发布范围改为检查面向学习者的章节导航字段；Fake Model 检查改为检查第一次可见提及所在行的解释。
- 专项回归通过：48 passed；写作契约与教程验证均为 0。
- `make check` 通过：183 passed、1 skipped；35 页构建成功；链接、发布和 SEO 契约均为 0。
