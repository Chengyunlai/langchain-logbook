export const REPOSITORY_URL =
  process.env.REPOSITORY_URL ??
  "https://github.com/Chengyunlai/langchain-logbook";

export const SITE = {
  website:
    process.env.SITE_URL ?? "https://chengyunlai.github.io/langchain-logbook/",
  author: "Cyrus",
  profile: "https://github.com/Chengyunlai",
  desc: "从 LangChain 模型调用到 LangGraph 可恢复工作流：中文 Agent 工程课程与可运行的 Mini DeerFlow 实战。",
  title: "LangChain Logbook",
  keywords: [
    "LangChain",
    "LangGraph",
    "AI Agent",
    "智能体工程",
    "Mini DeerFlow",
    "Agent Middleware",
    "RAG",
    "Python",
  ],
  locale: "zh_CN",
  ogImage: "astropaper-og.jpg",
  lightAndDarkMode: true,
  postPerIndex: 4,
  postPerPage: 10,
  scheduledPostMargin: 15 * 60 * 1000,
  showArchives: false,
  showBackButton: true,
  editPost: {
    enabled: true,
    text: "在 GitHub 见证成长",
    url: `${REPOSITORY_URL}/blob/main/`,
  },
  dynamicOgImage: false,
  dir: "ltr",
  lang: "zh",
  timezone: "Asia/Shanghai",
} as const;
