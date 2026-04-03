import fs from 'fs';
import path from 'path';

const SRC_DIR = path.resolve('../');
const DEST_DIR = path.resolve('./src/data/blog');
const BASE_PATH = '/langchain-logbook';
const BASE_DATE = new Date('2026-04-01T00:00:00Z');

// Slugify function to match AstroPaper's behavior (kebab-case)
function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')     
    .replace(/[^\w-]+/g, '')   
    .replace(/--+/g, '-')       
    .replace(/^-+/, '')         
    .replace(/-+$/, '');        
}

// Helper to determine publication date for sorting (01 < 02 < 03 ... Appendix)
function getPubDate(filename) {
  if (filename.toLowerCase() === 'introduction') return '2026-04-03T12:00:00Z';
  const match = filename.match(/^(\d+)_/);
  if (match) {
    const chapterNum = parseInt(match[1]);
    const date = new Date('2026-04-03T00:00:00Z');
    date.setDate(date.getDate() - chapterNum);
    return date.toISOString();
  }
  return '2025-01-01T00:00:00Z'; // Appendix or others (Oldest)
}

if (!fs.existsSync(DEST_DIR)) {
  fs.mkdirSync(DEST_DIR, { recursive: true });
}

// Clear destination
if (fs.existsSync(DEST_DIR)) {
  const existingFiles = fs.readdirSync(DEST_DIR).filter(f => !f.startsWith('.'));
  for (const file of existingFiles) {
    fs.rmSync(path.join(DEST_DIR, file), { recursive: true, force: true });
  }
}

// Helper to rewrite links to /posts/[slug]/
function rewriteLinks(content) {
  return content.replace(/\[([^\]]+)\]\(\.\/([^)]+)\.md\)/g, (match, text, relPath) => {
    const filename = path.basename(relPath);
    if (filename.toLowerCase() === 'readme') return `[${text}](${BASE_PATH}/)`;
    const slug = slugify(filename === 'APPENDIX' ? 'appendix' : filename);
    return `[${text}](${BASE_PATH}/posts/${slug}/)`;
  });
}

function processFile(srcPath, destFilename) {
  if (!fs.existsSync(srcPath)) return;
  let content = fs.readFileSync(srcPath, 'utf8');
  let name = destFilename.replace('.md', '');
  let title = name;
  const h1Match = content.match(/^#\s+(.+)$/m);
  if (h1Match) {
    title = h1Match[1].trim();
    content = content.replace(/^#\s+.+$/m, '').trim();
  }
  content = rewriteLinks(content);
  const pubDate = getPubDate(name);
  const frontmatter = `---
title: "${title.replace(/"/g, '\\"')}"
description: "LangChain Logbook content: ${title}"
pubDatetime: ${pubDate}
featured: ${name === 'introduction'}
tags: ["tutorial"]
---

`;
  fs.writeFileSync(path.join(DEST_DIR, destFilename), frontmatter + content);
}

const tutorialsDir = path.join(SRC_DIR, 'tutorials');
if (fs.existsSync(tutorialsDir)) {
  const tutFiles = fs.readdirSync(tutorialsDir);
  for (const file of tutFiles) {
    if (file.endsWith('.md')) processFile(path.join(tutorialsDir, file), file);
  }
}
processFile(path.join(SRC_DIR, 'APPENDIX.md'), 'APPENDIX.md');
processFile(path.join(SRC_DIR, 'README.md'), 'introduction.md');

console.log('Successfully synchronized docs for AstroPaper');
