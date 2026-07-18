export const REPOSITORY_URL =
  process.env.REPOSITORY_URL ??
  "https://github.com/Chengyunlai/langchain-logbook";

export const SITE = {
  website:
    process.env.SITE_URL ?? "https://chengyunlai.github.io/langchain-logbook/",
  author: "Cyrus",
  profile: "https://github.com/Chengyunlai",
  desc: "从底层重新认识大语言模型应用架构，构建工业级 Agent",
  title: "LangChain Logbook",
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
  dynamicOgImage: true,
  dir: "ltr",
  lang: "zh",
  timezone: "Asia/Shanghai",
} as const;
