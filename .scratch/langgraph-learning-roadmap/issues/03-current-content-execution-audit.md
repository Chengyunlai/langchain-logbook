# 审计现有教程、Notebook 与文档站的可执行性

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by:

## Why

课程目前存在版本声明、依赖、Notebook 示例、流式返回形状、持久化语义和评测导入不一致的问题。必须先建立完整缺陷清单，后续重构才能保留有效内容而不是盲目重写。

## Work

- 逐章检查 Markdown 与 Notebook 是否同步。
- 对代码单元做语法、导入、最小离线执行和必要的集成验证。
- 检查 README、pyproject、uv.lock、Makefile、文档站同步脚本和 CI。
- 把问题分为：事实错误、过期 API、不可运行、概念缺口、教学顺序问题、工程缺口、视觉问题。
- 标记用户当前未提交修改，后续实施不得覆盖。

## Acceptance

- 形成逐章中文审计表，并给每项问题标注严重度、证据和建议处理方式。
- 能通过命令复现的错误必须给出复现命令。
- 明确保留、修正、迁移、删除四类内容，不以笼统“重写”代替判断。
- 形成可供版本与 CI 任务直接消费的验收清单。

## Answer

已完成详细中文审计，工件见[现有教程、Notebook 与文档站可执行性审计](../artifacts/03-current-content-execution-audit.md)。

主要结论：

- 43 个 Markdown Python 代码块和全部 Notebook code cell 均能通过 AST 解析，但存在多项 P1 运行与语义错误；语法完整不能代表课程可执行。
- 已复现 v2 stream 错误解包、listener 错误签名、Agent `input` 被静默忽略、两套 LangSmith 评测导入失效，以及 LangServe/FastAPI 不可用。
- 第 03 章保存了供应商认证错误；第 07 章没有可运行图；第 08、09 章从未执行；README 的全量完成状态不成立。
- 已对 README、附录和 01–09 章逐一给出严重度、证据以及“保留 / 修正 / 迁移 / 删除”判断。
- 已验证 Astro 干净构建成功，同时发现生成站点 8 个内部断链、错误 EditPost URL、模板 GitHub 链接和若干发布维护问题。
- 已形成版本、Markdown、Notebook、Agent/Graph、测试和文档站六类 CI-ready 验收清单。

本任务只新增审计工件和更新任务状态，没有改写用户现有教程文件。
