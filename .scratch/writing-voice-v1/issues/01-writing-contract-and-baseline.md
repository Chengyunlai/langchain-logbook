# 建立写作契约与自动度量

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by:

## Why

没有共同标尺时，“去 AI 化”很容易退化为换同义词，甚至误删教学证据。先固定什么要保留、什么要减少、什么只能由读者判断。

## Work

- 记录重复句式、标题形态、实验标签和主线篇幅基线。
- 定义自然中文技术写作契约。
- 为段落长度、模板短语和显式 Notebook 入口增加可重复检查。

## Acceptance

- 契约明确区分正文叙事层与实验契约层。
- 指标不会要求删除预测、输出、解释和修改实验。
- 全书范围和分批顺序写入地图。

## Answer

已建立中文技术书写契约，区分正文叙事与 lesson lab 实验契约。全书范围、分批依赖和基线指标均已写入地图。

新增 `scripts/check_writing_contract.py`：正文段落超过 240 字即失败，同时报告校准句式数量；`make test` 会运行该门禁。首页唯一主起点和 01–11 Notebook 下载入口由站点发布契约检查。
