# 确定课程信息架构与章节契约

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 01, 02, 03

## Why

当前章节按主题排列，但后半程没有足够深度，也没有持续产物。需要先确定每章解决的问题、前置能力和输出工件，之后才能重写而不再次变成知识点拼盘。

## Work

- 确定增强模型层、Agent 封装层、Graph 编排层、Agent 工程层的章节边界。
- 为每章写学习目标、前置知识、核心问题、失败实验、练习和验收。
- 决定现有 01–09 的保留、拆分、合并和新增关系。
- 让每章都向 Mini DeerFlow 交付一个可复用模块。

## Acceptance

- 产出完整课程目录和章节依赖图。
- 每章说明“为什么此时学习”“学完能做什么”“向实战项目贡献什么”。
- RAG、结构化输出等辅助能力不会挤占 LangGraph 核心路径。
- 从第一章到 DeerFlow 阅读章不存在需要突然补学的大块概念。

## Answer

已形成[LangGraph Agent 工程课程信息架构与章节契约](../artifacts/04-curriculum-information-architecture.md)。

关键决策：

- 将现有 9 个主题章重组为“1 个导学章 + 16 个能力章 + 4 组附录”，按增强模型层、Agent 封装层、Graph 编排层、Agent Harness 层、验证交付层、综合迁移阅读六阶段递进。
- 每章都明确为什么此时学习、学完能力、核心内容、最小实验、工程实验、失败实验、练习验收、Mini DeerFlow 增量和 DeerFlow 映射。
- `create_agent` 作为 Lead Agent 的贯穿入口，StateGraph 用于理解和实现显式业务控制流，两者不再被描述为替代关系。
- RAG 与结构化输出保留详细工程内容，但定位为进入 Lead Agent 的能力，不占据 LangGraph 控制流主轴。
- Context/State/Store、AgentMiddleware、Graph、Persistence、HITL、Multi-Agent、Sandbox、Quality、Runtime 各有独立执行闭环。
- 关键代码以可导入 Python package 与测试为事实源；Markdown 负责解释，Notebook 负责实验，避免继续手工维护两套互相漂移的实现。
- Mini DeerFlow 从第 00 章开始逐章演进，最终场景覆盖研究、文件、审批、委派、恢复、评测和 SSE，而非简单翻译/天气 Demo。
- 已给出现有 README、01–09、附录内容的保留、修正、拆分迁移和主线删除位置，后续实施不得覆盖用户现有修改。

该决策解锁“建立详细教学内容与视觉表达标准”；版本、依赖与自动验证基线仍可并行推进。
