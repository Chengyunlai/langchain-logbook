# 评审第 07 章双层案例样章

Status: resolved
Triage: ready-for-human
Type: prototype
Blocked by: 03

## Why

全书已经确定采用双层案例，但扩展前仍需真实阅读反馈，校准失败顺序、代码粒度和工程迁移是否真的降低了初学者的认知负担。

## Question

阅读第 07 章样章后，学习者能否在不依赖 Mini DeerFlow 封装的情况下解释 State、Node、Edge、并行冲突和 Reducer，并能说明它们如何迁移到完整 Agent？

## Acceptance

- 用户完成一次 Web 样章阅读并指出仍然跳跃、冗余或不透明的位置。
- 反馈被整理为可执行修改，不由 Agent 代替用户作答。
- 把反馈整理成第 05、06 章和其余章节共同遵守的粒度修正，不再把“是否改全书”作为待决问题。

## Answer

用户在 Web 样章中发现 `lesson-lab` 内部 marker 被显示，这是发布层泄漏教学元数据，而不是正文内容。

问题已在提交 `ee341e7` 中修复：教程源保留 marker，Web 发布副本删除 marker，发布门禁禁止内部标记进入最终 HTML。

用户随后明确要求“其它所有课程和 Jupyter 都修改”。这确认第 07 章的双层案例方向可以扩展到全书，不再把是否只做样章或少数章节作为待决问题。

后续统一粒度如下：每个核心概念必须先有可预测、可运行、可观察、可修改的概念实验，再进入 Mini DeerFlow。

Web 与 Notebook 同序，工程深度不删减；内部同步 marker 不属于学习内容，Web 必须隐藏。

第 05、06 章先分别校准 Context Engineering 与 Middleware 的章节粒度。两章完成后，第 01–04、08–11 章、工程专题、Capstone 与 DeerFlow 导读全部进入同一改造流程。
