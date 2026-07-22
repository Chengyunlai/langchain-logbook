# 初学者线上学习体验验收（content-only）

- 验收日期：2026-07-21（Asia/Shanghai）
- 唯一入口：<https://chengyunlai.github.io/langchain-logbook/>
- 读者画像：只具备基础 Python；不预先掌握 LangChain、LangGraph、Mini DeerFlow 或 DeerFlow
- 总评：**BLOCKED（真实 UI / 响应式验收被阻塞）；线上内容与顺序核对 PASS**

## 验收方式与证据边界

本轮先按要求连接真实 Browser，并以首页 URL 请求浏览器后端；连接结果为 `No browser is available`，进一步列举可用后端得到空列表 `[]`。因此没有可声明的真实点击、截图或 viewport 证据。

随后仅用只读 HTTP 从公开首页抓取可见链接，再沿这些链接读取线上页面。没有读取本地仓库、Notebook、源码、构建产物、测试、既有报告或改写讨论。以下“看到的事实”均来自线上公开 HTML；凡涉及视觉呈现、点击交互、390px 布局和页面级溢出，均判 **BLOCKED**，不以静态 HTML 推断冒充 UI 验收。

## 结论摘要

| 验收面 | 结论 | 摘要 |
|---|---|---|
| 首页定位与起点 | PASS（有轻微摩擦） | 首页清楚说明这是中文 Agent 工程课程与 Mini DeerFlow 实战，并直链 Introduction；但同页又出现“从第 01 章开始”，对首次读者形成两个起点。 |
| 导航与顺序 | PASS | 学习路线明确给出序章、四部、01→11、Mini DeerFlow 12→17、DeerFlow Guide 18；阶段进入条件、先回答、学完你能都可建立期待。 |
| 01–11 阅读连贯性 | PASS | 章节持续使用“上一刻系统/真实失败 → 预测 → 观察结果 → 发生了什么 → 动手修改 → 下一刻系统”，过渡可追踪。 |
| 概念 → Mini DeerFlow → DeerFlow | PASS | 每章先做原生概念实验，再迁入 Mini DeerFlow；工程专题沿同一组合根推进；最终 Guide 固定 commit 并给出四条调用链。 |
| 桌面/390px、代码与图表视觉 | BLOCKED | Browser 后端不可用，无法做真实 viewport、滚动、图表渲染、页面级横向溢出验证。 |
| 关键链接 | PASS（抽查） | 所有主线公开页均返回可读内容；01/06/11 的 GitHub 教程源链接与 DeerFlow 固定 commit 关键链接抽查为 HTTP 200。 |
| Notebook 下载入口 | BLOCKED / 缺入口 | 线上文章声明 Markdown、Notebook 等共同验证，但已读页面只发现 GitHub Markdown 源链接，未发现显式 `.ipynb` 或“下载 Notebook”入口，因此无法从 UI 访问或验证下载。 |

## 导航 / 顺序

### PASS：首页能回答“项目是什么、从哪里开始”

- URL：<https://chengyunlai.github.io/langchain-logbook/>
- 看到的事实：首页首屏文案是“从 LangChain 模型调用到 LangGraph 可恢复工作流：中文 Agent 工程课程与可运行的 Mini DeerFlow 实战”；“关于本项目”进一步说明课程连续演进、离线可运行、由契约验证。首页明确写“直接点击下方的课程看板 (Introduction) 开始”，链接指向公开序章。
- 结论：只具备基础 Python 的读者能知道这是 Agent 工程课程，不会误以为是零散 API 博客。

### 轻微摩擦：首页出现两个“开始”信号

- URL：<https://chengyunlai.github.io/langchain-logbook/>
- 看到的事实：上方要求从 Introduction 开始，下方又用标题“从第 01 章开始”。学习路线页则明确说“第一次阅读请从序章开始”。
- 影响：第一次到站的读者可能跳过序章，错失“同一个研究交付任务”和四次能力升级的上下文。
- 最小修复：把首页下方标题改成“读完序章后，从第 01 章开始”，并让 Introduction 保持唯一主 CTA。

### PASS：学习路线顺序、进入条件和期待管理完整

- URL：<https://chengyunlai.github.io/langchain-logbook/posts/>
- 看到的事实：页面不是按发布日期排序，而是显示固定主线：
  - 序章：00 Introduction；进入条件是会读基础 Python，不要求 LangChain/LangGraph。
  - 第一部：01–03，模型/消息/事件 → Schema → 带来源检索。
  - 第二部：04–06，工具循环 → Context 所有权 → Middleware 治理。
  - 第三部：07–10，StateGraph → 动态并行/子图 → 持久化 → 可恢复审批。
  - 第四部：11、Mini DeerFlow 12–16、Capstone 17、DeerFlow Guide 18。
- 每一部都有“适合谁”和“进入条件”；每一个条目都有“先回答”和“学完你能”。例如第 06 章先问权限、PII、调用上限与失败如何统一进入生命周期，预期产出是用 AgentMiddleware 统一治理；第 11 章先问多 Agent 的控制权、共享上下文和并行，预期产出是能选择 Router/Handoff/Supervisor/Subagent-as-tool 并隔离上下文。
- 结论：“先回答”给出问题张力，“学完你能”给出可验证能力，能建立合理期待。

## 阅读连贯性

### PASS：序章建立同一个长期任务，而非 API 清单

- URL：<https://chengyunlai.github.io/langchain-logbook/posts/introduction/>
- 看到的事实：序章把读者设为研究交付 Agent 的实现者，最终链路是“研究请求 → 结构化计划 → 检索可信资料 → 委派/草稿 → 人工审批 → 幂等发布 → 结果/轨迹/预算评测”，Checkpoint 负责跨重启恢复。正文解释四部顺序由依赖决定，并逐章列出“当前问题 / 本章交付”。
- 结论：对新手足够具体，后续术语有业务落点。

### PASS：01–11 形成连续故障链

逐页 HTTP 阅读结果如下，均可访问并有正文：

| 页 | 线上事实与章末过渡 |
|---|---|
| [01](https://chengyunlai.github.io/langchain-logbook/posts/01_getting_started/) | 从字符串回答不足开始，区分 `model.invoke`、Runnable、`bind_tools` 与 `create_agent`；解释 v2 envelope；迁入模型工厂和 stream adapter；结尾指出结果仍是自然语言，进入 02。 |
| [02](https://chengyunlai.github.io/langchain-logbook/posts/02_structured_output/) | 先让字符串解析、默认值、路径和失败协议逐一出错，再引入 Pydantic/结构化输出；结尾指出计划可消费但事实无来源。 |
| [03](https://chengyunlai.github.io/langchain-logbook/posts/03_rag_20/) | 从上下文预算、Document metadata、切分、引用、空召回和 recall@k 建立检索契约；结尾指出系统仍不会自主行动。 |
| [04](https://chengyunlai.github.io/langchain-logbook/posts/04_smart_tooling/) | 从 tool schema、`ToolMessage` 配对到完整 model→tool→model；再加入 Runtime Context、registry 与 recursion limit；结尾暴露事实所有权混乱。 |
| [05](https://chengyunlai.github.io/langchain-logbook/posts/05_agent_middleware/) | 用万能 State 的安全/生命周期失败区分 Context、State、Store、业务库和 Secret；结尾指出治理逻辑仍散落。 |
| [06](https://chengyunlai.github.io/langchain-logbook/posts/06_observability_persistence/) | 先真实执行一次漏检权限的发布副作用，再用 `wrap_tool_call`、`wrap_model_call`、before/after、异步取消、摘要与 HITL 收敛治理；结尾指出业务拓扑仍藏在 Prompt。 |
| [07](https://chengyunlai.github.io/langchain-logbook/posts/07_stategraph/) | 把阶段、router、并行 reducer 和 ReAct 循环写成显式 StateGraph；结尾指出动态并行尚未解决。 |
| [08](https://chengyunlai.github.io/langchain-logbook/posts/08_engineering_defense/) | 通过 Command、Send、Subgraph、循环进度和 Functional task 建动态研究拓扑；结尾指出进程退出仍清空现场。 |
| [09](https://chengyunlai.github.io/langchain-logbook/posts/09_multi_agent_eval/) | 从无 checkpointer、无 `thread_id`、内存 saver 跨重建失败，到 SQLite、history/time travel、schema migration；结尾指出高风险动作仍直接发生。 |
| [10](https://chengyunlai.github.io/langchain-logbook/posts/10_human_in_the_loop/) | 从阻塞等待进入 interrupt/resume，验证 resume payload、重放副作用、幂等 operation ID 和多 interrupt 顺序；结尾指出 Lead 上下文膨胀。 |
| [11](https://chengyunlai.github.io/langchain-logbook/posts/11_multi_agent_patterns/) | 从 Lead 历史包含 2600 字符原始 specialist 输出和 Secret 的可见失败出发，建立请求/结果协议、输入投影、四种控制权模式、并发/timeout/部分失败/输出预算/ledger；结尾进入 Mini DeerFlow 架构。 |

### 重点页实验解释

- 01：每个实验都有“运行前先预测 / 观察结果 / 发生了什么 / 动手修改”。尤其先展示 `AIMessage.content == ''` 但 `tool_calls` 有效，再解释 `bind_tools` 只表达意图、不执行函数；随后把 v2 event 错当旧二元组，修正为先读取 `type/ns/data`。这对零基础读者有效拆除了两个高频误解。
- 06：开头承接 05 的事实所有权，先执行未授权发布并看到副作用列表已被写入，再解释“横切关注点”，而不是先背 hook 名称。随后分别验证权限短路、hook 顺序、模型请求投影、异常归一化、异步取消和默认治理链；章末自然导向显式 Graph。
- 11：开头承接 10 的可恢复 Agent，先让原始材料和 Secret 进入 Lead 长期历史，再用 Pydantic 请求/结果协议切断；模式比较以“谁拥有下一步控制权”为轴，最后迁入 Registry → Executor → task tool → ToolMessage → bounded ledger。对“多 Agent 不是多画节点”的解释清楚。

### 摩擦：第 11 章体量很大，在线长读风险高

- URL：<https://chengyunlai.github.io/langchain-logbook/posts/11_multi_agent_patterns/>
- 看到的事实：公开 HTML 约 465 KB，含约 53 个 `<pre>` 区块、4 个 Mermaid 图和 2 个表；内容虽分节清楚，但手机或首次阅读可能难以保持位置。
- 最小修复：增加页内目录与章节进度/“本节最小必读”提示；把完整代码默认折叠但保留预测、关键 diff、观察结果和复制按钮。是否需要此修复仍需真实 UI 验收确认。

## 概念 → Mini DeerFlow → DeerFlow 迁移

### PASS：概念先失败，Mini DeerFlow 后装配

- 01–11 的公开页均不是从项目封装开场；它们先用 LangChain/LangGraph 原生对象制造可观察失败，再出现“工程迁移：Mini DeerFlow”或等价段落。
- 06 把原生 Middleware 机制映射到默认治理链；11 把输入投影、Semaphore、失败状态和输出预算映射到 Registry/Executor/task/Ledger。读者能分清“框架原语”和“项目工程接缝”。

### PASS：Mini DeerFlow 工程专题沿同一组合根递进

| 顺序 | URL | 看到的事实 |
|---|---|---|
| 12 架构 | <https://chengyunlai.github.io/langchain-logbook/posts/architecture/> | 明确前 11 章已有零件，当前任务是避免 CLI/Notebook/API 各装一套；固定 `build_application → _assemble_graph → create_lead_agent → graph.invoke`，区分 State、Runtime Context、Store、产品数据库。 |
| 13 Lead | <https://chengyunlai.github.io/langchain-logbook/posts/lead_agent_core/> | 用跨应用重建、Artifact reducer、Middleware 顺序、JSON-safe streaming 与 Mermaid 拓扑共同验证核心纵切面。 |
| 14 Sandbox/扩展 | <https://chengyunlai.github.io/langchain-logbook/posts/sandbox_extensions/> | 明确路径护栏不等于生产 Sandbox；通过 provider handle、权限、MCP allowlist 与 Skills 渐进披露扩展能力。 |
| 15 Runtime/Gateway | <https://chengyunlai.github.io/langchain-logbook/posts/runtime_gateway/> | 分开产品 Thread/Run/Event 与 Graph checkpoint；沿 Repository → RunManager → Graph → journal → SSE 建立取消、恢复与重放。 |
| 16 Eval/Obs | <https://chengyunlai.github.io/langchain-logbook/posts/evaluation_observability/> | 分离 outcome、trajectory、budget、安全硬门禁、trace 和 runtime journal；明确没有发现 DeerFlow 固定版本中正式的 Dataset/evaluate 回归层，不夸大映射。 |
| 17 Capstone | <https://chengyunlai.github.io/langchain-logbook/posts/capstone/> | 明确“只允许装配，不再发明第二套框架”，组合检索、并行委派、草稿、审批、重建恢复、幂等发布和评测；给出故障注入与评分量规。 |

### PASS：DeerFlow Guide 使用统一固定 commit 和四条路线

- URL：<https://chengyunlai.github.io/langchain-logbook/posts/deerflow_guide/>
- 看到的事实：Guide 固定到 `4af617835805dd7cd78162ebed02fd6b782ea8bf`（页面标注 2026-07-14），要求留下“入口、调用关系、跨边界数据、缺少边界时的失败”四类证据。
- 四条路线清楚且与 Mini DeerFlow 一一对应：
  1. `langgraph.json → make_lead_agent → model/tools/middleware/prompt/state → create_agent`；
  2. `ThreadState → Runtime Context → Middleware`，并与产品 Thread/Run record 分离；
  3. `task tool → policy/config → SubagentExecutor → 隔离 Agent → ToolMessage/Command`；
  4. `Gateway router → service → RunManager → worker → graph → journal/event store → StreamBridge/SSE`。
- Guide 最后还让读者静态追踪“一次研究委派如何回到 SSE”，并用反事实问题检查 timeout、断线、tracing 失败和 worker 重启的所有权。

### 轻微摩擦：专题历史 commit 与最终统一 commit 并存

- URLs：
  - <https://chengyunlai.github.io/langchain-logbook/posts/lead_agent_core/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/sandbox_extensions/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/runtime_gateway/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/evaluation_observability/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/deerflow_guide/>
- 看到的事实：部分专题保留 `807c3c...` 或 `3e7baba...` 的历史局部对照；每处都明确说明全书最后四条路线以 Guide 的 `4af6178...` 为统一验收版本。
- 影响：不是内容冲突，但初学者可能暂时不知道该复制哪个 commit。
- 最小修复：把提示统一为醒目的固定组件：“本篇历史证据锚点 / 全书最终验收锚点”，并在复制按钮旁标明用途。

## 响应式 / 代码 / 图表

### BLOCKED：无法完成桌面和约 390px 的真实视觉验收

- 涉及 URL：
  - <https://chengyunlai.github.io/langchain-logbook/posts/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/11_multi_agent_patterns/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/deerflow_guide/>
- 阻塞事实：Browser 后端列表为空，无法设置 viewport、展开移动菜单、水平滚动代码、检查 Mermaid 渲染尺寸、表格滚动容器或 `documentElement.scrollWidth`。
- 静态事实（不能替代 UI 结论）：第 11 章代码 `<pre>` 带 `overflow-x: auto` 和 `tabindex="0"`；第 11 章有 4 个 Mermaid 图，Guide 有 7 个 Mermaid 图和 4 个表；图后普遍提供“图的文本替代”。这些是良好实现信号，但不能证明 390px 下没有页面级横向溢出。
- 最小修复/后续验收：Browser 可用后至少执行 1440×900 与 390×844 两档；分别检查路线卡片、移动菜单、第 11 章最长 Python 代码、Guide 四路线 Mermaid 和映射表，并记录 `scrollWidth <= clientWidth`；代码/表格可内部横滚，但正文页面不得整体横滚。

## 链接与 Notebook 入口

### PASS：主线站内链接均可读取

从首页和学习路线可见链接进入后，Introduction、01–11、Architecture、Lead Agent Core、Sandbox Extensions、Runtime Gateway、Evaluation Observability、Capstone、DeerFlow Guide 均返回可读公开正文。01→02、06→07、10→11、11→Architecture，以及工程专题之间的“继续阅读”目标均存在。

### PASS：关键外链抽查

- 01/06/11 页的“在 GitHub 见证成长”分别链接公开 Markdown 教程源，HTTP 抽查均为 200：
  - <https://github.com/Chengyunlai/langchain-logbook/blob/main/tutorials/01_Getting_Started.md>
  - <https://github.com/Chengyunlai/langchain-logbook/blob/main/tutorials/06_Observability_Persistence.md>
  - <https://github.com/Chengyunlai/langchain-logbook/blob/main/tutorials/11_Multi_Agent_Patterns.md>
- Guide 中 `4af6178...` 的 manifest、Lead、task、Gateway router、worker、journal、Subagent executor 等关键固定源码链接抽查可达；个别请求发生短暂连接超时，重试后为 200。

### 问题：没有可见 Notebook 下载入口

- 相关 URL：
  - <https://chengyunlai.github.io/langchain-logbook/posts/introduction/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/01_getting_started/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/06_observability_persistence/>
  - <https://chengyunlai.github.io/langchain-logbook/posts/11_multi_agent_patterns/>
- 看到的事实：序章说明 Markdown、Notebook、测试和文档站共同验证，并给出本地启动 Notebook 的命令；文章顶部/底部的源码入口却只指向 `tutorials/*.md`。已读线上 HTML 中没有显式 `.ipynb` 链接或“下载 Notebook”按钮。
- 影响：只在网页学习的新手无法确认 Notebook 在哪里，也无法直接下载与当前章匹配的可运行版本。
- 最小修复：每章标题附近增加“查看 Markdown / 下载 Notebook (.ipynb)”并列入口；下载应使用版本稳定、可验证的 URL，并显示与当前网页同步的章节名/commit。若 Notebook 不打算公开下载，则把文案改为“本地仓库生成 Notebook”，并链接明确说明页。

## 阻塞或摩擦清单

1. **BLOCKED — 无真实 Browser 后端**
   - 事实：连接线上入口后无可用浏览器，后端列表 `[]`。
   - 影响：无法声明实际点击、桌面/390px、菜单、代码/表格横滚、Mermaid 视觉和页面级溢出结果。
   - 最小处置：恢复 Browser 后补跑 viewport 验收；本报告 UI 项保持 BLOCKED。

2. **摩擦 — 首页两个起点**
   - URL：<https://chengyunlai.github.io/langchain-logbook/>
   - 最小修复：把“从第 01 章开始”改为“读完序章后，从第 01 章开始”。

3. **摩擦 — 第 11 章在线体量大**
   - URL：<https://chengyunlai.github.io/langchain-logbook/posts/11_multi_agent_patterns/>
   - 最小修复：页内目录、阅读进度和可折叠完整代码；保留预测与观察结果常显。

4. **摩擦 — 多个历史源码锚点**
   - URL：<https://chengyunlai.github.io/langchain-logbook/posts/deerflow_guide/>
   - 最小修复：统一组件区分“专题历史锚点”和“最终验收锚点 4af6178...”。

5. **问题 — Notebook 无显式线上入口**
   - URL：<https://chengyunlai.github.io/langchain-logbook/posts/>
   - 最小修复：每章增加版本稳定的 `.ipynb` 下载；或清楚说明只能在本地生成。

6. **环境摩擦 — GitHub Pages / GitHub 偶发连接超时**
   - 事实：少数只读 HTTP 请求出现 SSL/连接超时，重试后页面或固定源码链接可读。
   - 影响：未形成永久 404，但弱网新手可能误以为章节损坏。
   - 最小修复：站内无需为一次性网络错误改内容；可以给源码/Notebook 下载按钮增加明确失败提示与重试建议，部署后链接检查继续覆盖永久错误。

## 最终判定

- **线上内容事实：PASS。** 课程定位、唯一项目、四部路线、01–11 连续故障链、Mini DeerFlow 工程纵切面、Capstone 装配，以及固定 commit 的 DeerFlow 四条调用链均完整且对初学者可解释。
- **真实导航交互、桌面/390px 响应式、长代码/图表视觉：BLOCKED。** 本轮没有可用 Browser，不能冒充真实 UI 验收。
- **链接：PASS（主线与关键外链抽查）；Notebook 入口：BLOCKED / 缺入口。**
