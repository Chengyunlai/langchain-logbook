import fs from "fs";
import path from "path";

const SRC_DIR = path.resolve("../");
const DEST_DIR = path.resolve("./src/data/blog");
const NOTEBOOK_DEST_DIR = path.resolve("./public/notebooks");
const BASE_PATH = process.env.SITE_BASE_PATH ?? "/langchain-logbook";
const REPOSITORY_URL =
  process.env.REPOSITORY_URL ??
  "https://github.com/Chengyunlai/langchain-logbook";
const CURRICULUM = JSON.parse(
  fs.readFileSync(path.resolve("./curriculum.json"), "utf8")
);
const CURRICULUM_ENTRIES = new Map();
const PROCESSED_SOURCES = new Set();

let learningOrder = 0;
for (const stage of CURRICULUM.stages) {
  for (const entry of stage.entries) {
    if (CURRICULUM_ENTRIES.has(entry.sourcePath)) {
      throw new Error(`Duplicate curriculum sourcePath: ${entry.sourcePath}`);
    }
    CURRICULUM_ENTRIES.set(entry.sourcePath, {
      ...entry,
      learningOrder,
      learningStage: stage.id,
      learningStageTitle: stage.title,
      contentType: stage.kind,
    });
    learningOrder += 1;
  }
}

// Slugify function to match AstroPaper's behavior (kebab-case)
function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^\w-]+/g, "")
    .replace(/--+/g, "-")
    .replace(/^-+/, "")
    .replace(/-+$/, "");
}

// Helper to determine publication date for sorting (01 < 02 < 03 ... Appendix)
function getPubDate(filename) {
  if (filename.toLowerCase() === "introduction") return "2026-04-03T12:00:00Z";
  if (filename.toLowerCase() === "orientation") return "2026-04-03T13:00:00Z";
  const engineeringDates = {
    ARCHITECTURE: "2026-07-14T00:00:00Z",
    LEAD_AGENT_CORE: "2026-07-13T00:00:00Z",
    SANDBOX_EXTENSIONS: "2026-07-13T00:00:00Z",
    RUNTIME_GATEWAY: "2026-07-13T00:00:00Z",
    EVALUATION_OBSERVABILITY: "2026-07-13T00:00:00Z",
    CAPSTONE: "2026-07-14T00:00:00Z",
    DEERFLOW_GUIDE: "2026-07-14T00:00:00Z",
    RELEASE: "2026-07-14T00:00:00Z",
  };
  const engineeringDate = engineeringDates[filename.toUpperCase()];
  if (engineeringDate) return engineeringDate;
  const match = filename.match(/^(\d+)_/);
  if (match) {
    const chapterNum = parseInt(match[1]);
    const date = new Date("2026-04-03T00:00:00Z");
    date.setDate(date.getDate() - chapterNum);
    return date.toISOString();
  }
  return "2025-01-01T00:00:00Z"; // Appendix or others (Oldest)
}

if (!fs.existsSync(DEST_DIR)) {
  fs.mkdirSync(DEST_DIR, { recursive: true });
}

// Clear destination
if (fs.existsSync(DEST_DIR)) {
  const existingFiles = fs
    .readdirSync(DEST_DIR)
    .filter(f => !f.startsWith("."));
  for (const file of existingFiles) {
    fs.rmSync(path.join(DEST_DIR, file), { recursive: true, force: true });
  }
}

// Rewrite local Markdown pages and publish Notebook links under public/notebooks.
function rewriteLinks(content) {
  const sourceFiles = content
    .replace(
      /\[([^\]]+)\]\(\.\/(mini_deerflow\/[^)]+\.py)\)/g,
      (_match, text, relativePath) =>
        `[${text}](${REPOSITORY_URL}/blob/main/${relativePath})`
    )
    .replace(
      /\[([^\]]+)\]\(\.\/app\.py\)/g,
      (_match, text) =>
        `[${text}](${REPOSITORY_URL}/blob/main/mini_deerflow/app.py)`
    )
    .replace(
      /\[([^\]]+)\]\(\.\.\/langgraph\.json\)/g,
      (_match, text) => `[${text}](${REPOSITORY_URL}/blob/main/langgraph.json)`
    );
  const localDocuments = sourceFiles.replace(
    /\[([^\]]+)\]\(((?:\.{1,2}\/)[^)]+?\.(?:md|ipynb)(?:#[^)]+)?)\)/g,
    (_match, text, target) => {
      const [relativePath, fragment] = target.split("#", 2);
      const extension = path.extname(relativePath).toLowerCase();
      const filename = path.basename(relativePath, extension);
      const hash = fragment ? `#${fragment}` : "";

      if (extension === ".ipynb") {
        return `[${text}](${BASE_PATH}/notebooks/${path.basename(relativePath)}${hash})`;
      }
      if (filename.toLowerCase() === "readme")
        return `[${text}](${BASE_PATH}/${hash})`;
      const slug = slugify(
        filename.toLowerCase() === "appendix" ? "appendix" : filename
      );
      return `[${text}](${BASE_PATH}/posts/${slug}/${hash})`;
    }
  );
  return localDocuments.replace(
    /\[([^\]]+)\]\(\.\/(pyproject\.toml|uv\.lock)\)/g,
    (_match, text, filename) =>
      `[${text}](${REPOSITORY_URL}/blob/main/${filename})`
  );
}

function stripInternalLessonMarkers(content) {
  return content
    .replace(/^> \[!NOTE\]$/gm, "> **本章导航**")
    .replace(/^[ \t]*<!-- lesson-lab:[^\r\n]*-->[ \t]*$/gm, "")
    .replace(/^[ \t]*<!-- \/lesson-lab -->[ \t]*$/gm, "");
}

function processFile(srcPath, destFilename) {
  if (!fs.existsSync(srcPath)) return;
  let content = fs.readFileSync(srcPath, "utf8");
  let name = destFilename.replace(".md", "");
  let title = name;
  const h1Match = content.match(/^#\s+(.+)$/m);
  if (h1Match) {
    title = h1Match[1].trim();
    content = content.replace(/^#\s+.+$/m, "").trim();
  }
  content = rewriteLinks(stripInternalLessonMarkers(content));
  const pubDate = getPubDate(name);
  const sourcePath = path.relative(SRC_DIR, srcPath).split(path.sep).join("/");
  const curriculumEntry = CURRICULUM_ENTRIES.get(sourcePath);
  if (!curriculumEntry) {
    throw new Error(`Missing curriculum entry for ${sourcePath}`);
  }
  PROCESSED_SOURCES.add(sourcePath);
  const notebookMetadata = curriculumEntry.notebookFilename
    ? `notebookFilename: "${curriculumEntry.notebookFilename}"\n`
    : "";
  const frontmatter = `---
title: "${title.replace(/"/g, '\\"')}"
description: "${curriculumEntry.goal.replace(/"/g, '\\"')}"
pubDatetime: ${pubDate}
featured: ${name === "introduction"}
tags: ["tutorial"]
sourcePath: "${sourcePath}"
${notebookMetadata}learningOrder: ${curriculumEntry.learningOrder}
learningStage: "${curriculumEntry.learningStage}"
learningStageTitle: "${curriculumEntry.learningStageTitle.replace(/"/g, '\\"')}"
learningGoal: "${curriculumEntry.goal.replace(/"/g, '\\"')}"
contentType: "${curriculumEntry.contentType}"
---

`;
  fs.writeFileSync(path.join(DEST_DIR, destFilename), frontmatter + content);
}

const tutorialsDir = path.join(SRC_DIR, "tutorials");
if (fs.existsSync(tutorialsDir)) {
  fs.mkdirSync(NOTEBOOK_DEST_DIR, { recursive: true });
  for (const file of fs.readdirSync(NOTEBOOK_DEST_DIR)) {
    if (file.endsWith(".ipynb")) fs.rmSync(path.join(NOTEBOOK_DEST_DIR, file));
  }
  const tutFiles = fs.readdirSync(tutorialsDir);
  for (const file of tutFiles) {
    if (file.endsWith(".md")) processFile(path.join(tutorialsDir, file), file);
    if (file.endsWith(".ipynb")) {
      const tutorialSourcePath = `tutorials/${file.replace(/\.ipynb$/, ".md")}`;
      const publishedFilename =
        CURRICULUM_ENTRIES.get(tutorialSourcePath)?.notebookFilename ?? file;
      fs.copyFileSync(
        path.join(tutorialsDir, file),
        path.join(NOTEBOOK_DEST_DIR, publishedFilename)
      );
      if (publishedFilename !== file) {
        fs.copyFileSync(
          path.join(tutorialsDir, file),
          path.join(NOTEBOOK_DEST_DIR, file)
        );
      }
    }
  }
}
processFile(path.join(SRC_DIR, "APPENDIX.md"), "APPENDIX.md");
processFile(
  path.join(SRC_DIR, "docs/getting-started-pycharm.md"),
  "getting-started-pycharm.md"
);
processFile(path.join(SRC_DIR, "docs/seo.md"), "seo.md");
processFile(path.join(SRC_DIR, "docs/version-policy.md"), "version-policy.md");
processFile(path.join(SRC_DIR, "docs/release.md"), "release.md");
processFile(path.join(SRC_DIR, "ORIENTATION.md"), "orientation.md");

const miniDeerFlowDir = path.join(SRC_DIR, "mini_deerflow");
for (const file of fs.readdirSync(miniDeerFlowDir)) {
  if (file.endsWith(".md") && file !== "README.md") {
    processFile(path.join(miniDeerFlowDir, file), file);
  }
}

processFile(path.join(SRC_DIR, "README.md"), "introduction.md");

const unprocessedCurriculumSources = [...CURRICULUM_ENTRIES.keys()].filter(
  sourcePath => !PROCESSED_SOURCES.has(sourcePath)
);
if (unprocessedCurriculumSources.length > 0) {
  throw new Error(
    `Curriculum sources were not published: ${unprocessedCurriculumSources.join(", ")}`
  );
}

process.stdout.write("Successfully synchronized docs for AstroPaper\n");
