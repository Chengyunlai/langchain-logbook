# 第一批初学者解释层调整

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by:

## Why

真实读者反馈指出：课程仍缺少独立的零基础坐标页，第 01 章同时出现 Runnable、工具意图、Fake Model 和 v2 stream，首读认知负担过高。

## Work

- 新增第 00 章；
- 首页与序章导向第 00 章；
- 第 01 章区分真实调用主线与工程深入；
- 为主线与工程专题补齐本章导航；
- 统一 Fake Model 首次说明；
- 同步课程清单、文档站、Notebook 与自动检查。

## Acceptance

- 首页只有一个初学者主入口，指向第 00 章；
- 第 00 章能独立解释模型、Chain、Agent 与 LangGraph 的关系；
- 第 01 章前 90 秒能看出首读只需掌握模型调用和 Message；
- Fake Model 第一次出现时不会被误认为真实模型调用；
- `make check` 全部通过。

## Answer

- 新增 `ORIENTATION.md`，用一次调用、固定 Chain、Agent 循环和显式 Graph 建立零基础坐标，并保留 Mermaid 文本替代、自检题和下一步。
- 首页唯一主入口已改为第 00 章，并增加初学者、已有 LangChain 经验者和 Agent 系统开发者三个可点击入口。
- 第 01 章先展示真实模型调用，再展示确定性 Fake Model；首读完成第 2 节即可进入第 02 章，Runnable、工具意图与 v2 stream 保留为工程深入。
- 第 02～11 章和七篇 Mini DeerFlow/DeerFlow 工程主线均增加当前系统、遇到的问题、暂时不讲、学习结果和预计时间。
- Fake Model 首次出现位置已统一说明其不调用真实供应商，只用于确定性协议、状态或轨迹证据。
- 写作检查新增初学者导航卡与 Fake Model 首次说明契约；首页发布契约固定到 `/posts/orientation/`。
- `make check` 通过：181 passed、1 skipped；Tutorial validation 为 0；35 页构建成功；链接、发布和 SEO 契约均为 0。
- 浏览器复核通过：第 00 章和第 01 章首屏信息正确；首页 1280 px 与 390 px 均无横向溢出，三类入口可点击。
