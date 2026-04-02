import fs from 'fs';
import path from 'path';

const SRC_DIR = path.resolve('../');
const DEST_DIR = path.resolve('./src/content/docs');

// Ensure destination exists
if (!fs.existsSync(DEST_DIR)) {
  fs.mkdirSync(DEST_DIR, { recursive: true });
}

// 1. Copy tutorials directory
const tutorialsSrc = path.join(SRC_DIR, 'tutorials');
const tutorialsDest = path.join(DEST_DIR, 'tutorials');
if (fs.existsSync(tutorialsDest)) {
  fs.rmSync(tutorialsDest, { recursive: true, force: true });
}
if (fs.existsSync(tutorialsSrc)) {
  fs.cpSync(tutorialsSrc, tutorialsDest, { recursive: true });
}

// 2. Copy APPENDIX.md
const appendixSrc = path.join(SRC_DIR, 'APPENDIX.md');
const appendixDest = path.join(DEST_DIR, 'APPENDIX.md');
if (fs.existsSync(appendixSrc)) {
  fs.copyFileSync(appendixSrc, appendixDest);
}

// 3. Copy README.md as index.md
const readmeSrc = path.join(SRC_DIR, 'README.md');
const indexDestMdx = path.join(DEST_DIR, 'index.mdx');
const indexDestMd = path.join(DEST_DIR, 'index.md');

if (fs.existsSync(indexDestMdx)) {
  fs.rmSync(indexDestMdx);
}

if (fs.existsSync(readmeSrc)) {
  let readmeContent = fs.readFileSync(readmeSrc, 'utf8');
  if (!readmeContent.startsWith('---')) {
    const heroFrontmatter = `---
title: LangChain Logbook
description: The ultimate learning path for LangChain and AI Agents.
template: splash
hero:
  tagline: 从底层重新认识大语言模型应用架构，构建工业级 Agent
  image:
    file: ../../assets/houston.webp
  actions:
    - text: 开始阅读教程
      link: /langchain-logbook/tutorials/01_getting_started/
      icon: right-arrow
      variant: primary
    - text: 在 GitHub 查看源码
      link: https://github.com/HappyFrame/langchain-logbook
      icon: external
---

`;
    readmeContent = heroFrontmatter + readmeContent;
  }
  fs.writeFileSync(indexDestMd, readmeContent);
}

// 4. Inject frontmatter into all markdown files
function injectFrontmatter(dir) {
  const files = fs.readdirSync(dir, { withFileTypes: true });
  for (const file of files) {
    const fullPath = path.join(dir, file.name);
    if (file.isDirectory()) {
      injectFrontmatter(fullPath);
    } else if (file.isFile() && fullPath.endsWith('.md')) {
      let content = fs.readFileSync(fullPath, 'utf8');
      
      // Fast bypass for existing frontmatter
      if (content.startsWith('---')) continue;

      let title = file.name.replace('.md', '');
      
      // If it's the index, give it a home title
      if (file.name === 'index.md') {
        title = 'Home';
      } else {
        // Try to extract H1
        const h1Match = content.match(/^#\s+(.+)$/m);
        if (h1Match) {
          title = h1Match[1].trim();
        }
      }

      const frontmatter = `---\ntitle: "${title.replace(/"/g, '\\"')}"\n---\n\n`;
      fs.writeFileSync(fullPath, frontmatter + content);
    }
  }
}

injectFrontmatter(DEST_DIR);

console.log('Successfully copied docs and injected Astro frontmatter');
