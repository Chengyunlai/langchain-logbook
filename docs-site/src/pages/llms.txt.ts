import type { APIRoute } from "astro";
import { SITE } from "@/config";

const lines = [
  `# ${SITE.title}`,
  "",
  `> ${SITE.desc}`,
  "",
  "LangChain Logbook 是一套中文 Agent 工程课程，通过连续演进的 Mini DeerFlow 展示 LangChain、LangGraph、Subagent、Sandbox、持久化、Gateway 与评测。",
  "",
  "## 主要入口",
  "",
  `- [课程首页](${SITE.website})`,
  `- [课程序章](${new URL("posts/introduction/", SITE.website)})`,
  `- [完整学习路线](${new URL("posts/", SITE.website)})`,
  `- [Mini DeerFlow 架构](${new URL("posts/architecture/", SITE.website)})`,
  `- [综合实战](${new URL("posts/capstone/", SITE.website)})`,
  `- [DeerFlow 源码导读](${new URL("posts/deerflow_guide/", SITE.website)})`,
  `- [站内搜索](${new URL("search/", SITE.website)})`,
  `- [RSS](${new URL("rss.xml", SITE.website)})`,
  `- [Sitemap](${new URL("sitemap-index.xml", SITE.website)})`,
  "",
  "课程正文为中文；代码标识符、官方 API 名称和协议术语保留英文。",
  "",
].join("\n");

export const GET: APIRoute = () =>
  new Response(lines, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
