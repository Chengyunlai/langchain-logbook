# LangGraph Agent 工程学习体系

本项目是一套从 LangChain 高层开发入口逐步进入 LangGraph Agent 工程的中文学习体系。课程最终通过一个可运行、可测试、可部署的类 DeerFlow 实战项目，验证学习者能否构建自己的核心 Agent 业务并阅读大型 Agent Harness。

## Language

**学习主线**：
从增强模型层、Agent 封装层、Graph 编排层到 Agent 工程层的连续能力路径；每一层都以前一层的可运行产物为输入。
_Avoid_: API 清单、知识点拼盘

**增强模型层**：
围绕模型、消息、Prompt、结构化输出、检索和工具 Schema 建立确定性输入输出的课程阶段，尚不负责完整 Agent 循环。
_Avoid_: LangChain 基础杂项、Agent Runtime

**Agent 封装层**：
围绕 `create_agent`、工具循环、流式事件、Runtime Context 和 Agent Middleware 建立 Agent 运行时直觉的课程阶段。
_Avoid_: 黑盒 Agent、普通 Chain

**Graph 编排层**：
围绕 State、Reducer、Node、Edge、Command、Send、Checkpoint、Interrupt 和 Subgraph 显式设计控制流的课程阶段。
_Avoid_: 画图阶段、底层 API 阶段

**Agent 工程层**：
把 Agent 作为长期运行的业务系统来设计，覆盖上下文治理、权限、安全、持久化、子代理、沙箱、协议接入、测试、评测、观测和部署。
_Avoid_: 生产技巧、部署附录

**核心 Agent 业务**：
产品中由 Agent 驱动的主要业务闭环，包含状态、控制流、工具副作用、安全边界、恢复策略和可验证结果，而不只是一次模型调用。
_Avoid_: 聊天机器人、LLM 包装器

**Runtime Context**：
由应用在运行时提供、模型不可自行决定的会话或调用配置，例如用户身份、权限、依赖连接和模型选择。
_Avoid_: Memory、State、隐藏 Prompt

**Graph State**：
由图节点共同读写、通过 Reducer 合并并可被 Checkpointer 保存的线程内事实，例如消息、计划、产物和执行进度。
_Avoid_: Runtime Context、长期记忆、全局变量

**Store**：
独立于单一线程状态、用于跨线程保存应用定义数据的长期存储边界。
_Avoid_: Checkpointer、对话历史、业务数据库的统称

**产品 Thread**：
由应用运行时拥有、绑定认证用户和业务元数据的会话资源；可以与 LangGraph checkpoint 共用 `thread_id`，但不等于 checkpoint 本身。
_Avoid_: Checkpoint、聊天消息副本

**Run**：
同一产品 Thread 上的一次可查询执行，具有独立 ID、输入类型、状态、取消策略和事件序列；interrupt 恢复会创建新 Run 并继续原 Thread。
_Avoid_: Thread、Graph Node、HTTP Request

**Runtime Event Journal**：
先持久化后投递的产品运行事件日志，以 `run_id + sequence` 建立可重放游标；它保存客户端可见事实，不是 Graph State 的第二份真相。
_Avoid_: Checkpointer、Trace、消息历史

**Evaluation Dataset**：
可版本化的代表性 Agent 任务集合；每个案例保存输入以及可确定验证的结果、轨迹、预算或安全参考契约，用于重复实验和回归比较。
_Avoid_: 生产日志全集、唯一黄金答案列表、Trace 项目

**Agent Observation**：
从一次 Agent 执行投影出的稳定评测事实，包括最终输出、工具/节点轨迹、模型与工具调用次数和 token usage；它隔离 provider 与 tracing 平台对象。
_Avoid_: Graph State 全量副本、LangSmith RunTree、Evaluator 分数

**Trajectory Evaluation**：
验证 Agent 执行步骤的顺序、禁止步骤和调用结构，补足“最终文本正确但过程越权、循环或浪费”的结果评测盲区。
_Avoid_: Chain-of-thought 采集、只比较最终答案、Trace 可视化

**Trace / Span**：
用于诊断一次真实执行的父子调用树；一次请求只由 Graph 或 Gateway 中的一个 instrumentation owner 创建 root，模型、工具和 Subagent 继承为 child span。
_Avoid_: Runtime Event Journal、Evaluation Report、多个 provider 重复 root

**Evaluation Report**：
对版本化 Dataset 运行 outcome、trajectory、budget 等 evaluator 后得到的逐案例解释与聚合通过率；可与已批准 baseline 比较并作为 CI 门禁。
_Avoid_: Trace、用户端运行状态、只保留一个不透明总分

**Gateway**：
位于客户端和 Agent Harness 之间的应用适配层，负责认证身份、Thread/Run 用例、HTTP/SSE 投影与错误边界；不负责定义工具权限或 Graph 业务拓扑。
_Avoid_: Agent Harness、Agent Server 的同义词、通用反向代理

**章节闭环**：
一个章节从问题建模开始，经过概念解释、最小示例、工程示例、失败实验和验收练习，最终产出可被后续章节复用的工件。
_Avoid_: Notebook 演示、代码片段集合

**Mini DeerFlow**：
贯穿课程逐步构建的类 DeerFlow 实战项目，用较小规模保留 Lead Agent、状态、Middleware、工具、Subagent、Sandbox、持久化、流式 API、测试与评测等核心架构关系。
_Avoid_: DeerFlow 复刻、最终大作业、翻译小组示例

**研究交付任务**：
贯穿全书的业务情境。学习者负责把一个只能回答问题的助手，逐章升级为能够解析研究请求、检索可信资料、规划与委派任务、生成带引用草稿、等待人工审批、失败恢复并交付报告的 Mini DeerFlow。
_Avoid_: 每章重新发明业务示例、虚构人物故事、只在综合实战出现的临时场景

**系统快照**：
每章开始和结束时对当前 Mini DeerFlow 能力、可运行工件、已知限制和下一项约束的简明记录，用于维持跨章节连续性。
_Avoid_: 学习目标清单、章末内容摘要、脱离实际代码的路线口号

**Capstone Assembly（综合实战装配）**：
把课程已经验证的 Lead、Subagent、Sandbox、Checkpoint、审批、副作用和评测接口组织成一个长任务纵切面；它只编排已有公共接缝，不建立第二套平行 Agent 框架。
_Avoid_: 最终版框架、复制粘贴式大作业、简单 Demo

**源码阅读路线**：
从可执行入口沿调用关系依次追踪组合根、数据边界、能力边界和产品交付，而不是按目录逐文件摘要；每条结论使用固定 commit 链接并能由故障问题验证。
_Avoid_: 目录漫游、文件清单、永远指向 main 的链接
