# 改写工程专题与 DeerFlow Guide

Status: resolved
Triage: ready-for-agent
Type: task
Blocked by: 04

## Why

工程专题证据充分，但表格、问题单和验收单密度过高。需要先带读者追调用链，再展开完整参考资料。

## Acceptance

- Architecture 从一次真实装配失败进入组合根。
- Lead、Sandbox、Runtime、Evaluation、Capstone 保持一条业务链。
- DeerFlow Guide 的四条证据路线和固定 commit 标准完整保留。

## Answer

Architecture 以一次离线调用进入组合根；Lead 沿两轮跨重建恢复受压；Sandbox 从 `ArtifactRef` 没有文件落点进入能力链；Runtime 沿一次浏览器长任务展开；Evaluation 从 success 但不可交付进入质量系统。

Capstone 只装配前文公共接缝。DeerFlow Guide 以伪造身份、Workspace 串写、SSE 断线和 Trace/EventStore 分叉四个故障组织源码路线；固定 commit、14 文件证据切片、全部链接、命令、图和验收均保留。
