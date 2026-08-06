#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const pptxgen = require('pptxgenjs');

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error('Usage: node scripts/export_lesson_deck_pptx.mjs <deck.json> <output.pptx>');
  process.exit(2);
}

const deck = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const meta = deck.deckMeta || {};
const context = deck.curriculumContext || {};
const slides = Array.isArray(deck.slides) ? deck.slides : [];

if (meta.visualSystem !== 'edu-deck-v1') {
  console.error('Only edu-deck-v1 decks are supported.');
  process.exit(1);
}

const THEMES = {
  'chalk-grid': { bg: '1F2D25', paper: '26382F', ink: 'F4F0DC', muted: 'B9C1AE', line: '526353', accent: 'F1C94A', accent2: '8BD3C7', warn: 'EF9A83', good: '8ED9A8' },
  daylight: { bg: 'F6F2E8', paper: 'FFFDF7', ink: '17201C', muted: '68706B', line: 'D9D3C4', accent: 'D95F43', accent2: '0C7C72', warn: 'B6463A', good: '16745E' },
  'science-lab': { bg: 'EEF5F6', paper: 'FBFEFF', ink: '13242E', muted: '5E6D76', line: 'CAD9DF', accent: '007C89', accent2: '6B7FDA', warn: 'B6463A', good: '16745E' },
  'humanities-ink': { bg: 'F3EEE3', paper: 'FFFAF0', ink: '2A1F19', muted: '78685D', line: 'DCCFC0', accent: '9F2F2F', accent2: '2F665B', warn: '9F2F2F', good: '2F665B' }
};

const theme = THEMES[meta.stylePreset] || THEMES.daylight;
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'lesson-deck-generation-skill';
pptx.company = 'AgentDesign';
pptx.subject = `${meta.grade || ''}${meta.subject || ''} ${meta.lessonType || ''}`.trim();
pptx.title = meta.title || '课堂课件';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Microsoft YaHei UI',
  bodyFontFace: 'Microsoft YaHei UI',
  lang: 'zh-CN'
};
pptx.defineLayout({ name: 'LAYOUT_WIDE', width: 13.333, height: 7.5 });

const W = 13.333;
const H = 7.5;
const RAIL = 0.9;
const FONT = 'Microsoft YaHei UI';

function asList(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(String(text || ''), {
    x, y, w, h,
    fontFace: FONT,
    fontSize: opts.fontSize || 18,
    color: opts.color || theme.ink,
    bold: Boolean(opts.bold),
    valign: opts.valign || 'top',
    align: opts.align || 'left',
    fit: 'shrink',
    margin: opts.margin ?? 0.04,
    breakLine: false,
    ...opts
  });
}

function addBox(slide, x, y, w, h, fill = theme.paper, line = theme.line) {
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: fill }, line: { color: line, width: 1 } });
}

function addRail(slide, item, index, total) {
  slide.background = { color: theme.bg };
  addBox(slide, 0, 0, RAIL, H, theme.paper, theme.line);
  addText(slide, String(index + 1).padStart(2, '0'), 0.16, 0.32, 0.58, 0.42, { fontSize: 22, bold: true, color: theme.accent, align: 'center', margin: 0 });
  addText(slide, `${item.layoutId || ''}`, 0.17, 1.2, 0.55, 2.4, { fontSize: 9, color: theme.muted, rotate: 270, margin: 0 });
  addText(slide, `${item.timing?.minutes || '-'} min`, 0.12, H - 0.55, 0.66, 0.25, { fontSize: 8, color: theme.muted, align: 'center', margin: 0 });
  addText(slide, `${index + 1} / ${total}`, W - 1.15, H - 0.38, 0.78, 0.18, { fontSize: 8, color: theme.muted, align: 'right', margin: 0 });
}

function addHeader(slide, item) {
  const screen = item.screen || {};
  addText(slide, screen.eyebrow || item.stage || 'LESSON', 1.25, 0.38, 2.4, 0.22, { fontSize: 9, bold: true, color: theme.accent, margin: 0 });
  slide.addShape(pptx.ShapeType.line, { x: 1.25, y: 0.72, w: W - 1.65, h: 0, line: { color: theme.line, width: 1 } });
  addText(slide, item.teachingIntent || '', W - 5.2, 0.35, 4.7, 0.28, { fontSize: 8.5, color: theme.muted, align: 'right', margin: 0 });
}

function addFooter(slide, item) {
  slide.addShape(pptx.ShapeType.line, { x: 1.25, y: H - 0.65, w: W - 1.65, h: 0, line: { color: theme.line, width: 1 } });
  addText(slide, item.title || '', 1.25, H - 0.45, 4.8, 0.2, { fontSize: 8.5, color: theme.muted, margin: 0 });
  addText(slide, asList(item.notes).join('；'), W - 5.7, H - 0.45, 5.2, 0.2, { fontSize: 8.5, color: theme.muted, align: 'right', margin: 0 });
}

function addVisualSlot(slide, item, x, y, w, h) {
  const slot = asList(item.visualSlots)[0] || {};
  addBox(slide, x, y, w, h, theme.paper, theme.line);
  addText(slide, slot.id || 'visual_slot', x + 0.25, y + 0.22, w - 0.5, 0.25, { fontSize: 9, bold: true, color: theme.accent, margin: 0 });
  addText(slide, slot.description || '', x + 0.25, y + 0.68, w - 0.5, h - 1.0, { fontSize: 17, color: theme.muted, margin: 0 });
}

function addBullets(slide, items, x, y, w, h, fontSize = 21) {
  const rows = asList(items).slice(0, 5);
  const rowH = Math.min(0.62, h / Math.max(rows.length, 1));
  rows.forEach((item, idx) => {
    const yy = y + idx * rowH;
    slide.addShape(pptx.ShapeType.rect, { x, y: yy + 0.12, w: 0.08, h: 0.08, fill: { color: theme.accent }, line: { color: theme.accent } });
    addText(slide, item, x + 0.22, yy, w - 0.22, rowH, { fontSize, bold: true, margin: 0 });
  });
}

function addNumberRows(slide, rows, x, y, w, h, fontSize = 18) {
  const items = asList(rows).slice(0, 5);
  const rowH = Math.min(0.78, h / Math.max(items.length, 1));
  items.forEach((item, idx) => {
    const yy = y + idx * rowH;
    const label = item?.label || String(idx + 1);
    const content = item?.content || String(item || '');
    addBox(slide, x, yy + 0.05, 0.42, 0.42, theme.accent, theme.accent);
    addText(slide, label, x, yy + 0.11, 0.42, 0.2, { fontSize: 11, bold: true, color: theme.paper, align: 'center', margin: 0 });
    addText(slide, content, x + 0.6, yy, w - 0.6, rowH, { fontSize, bold: true, margin: 0 });
  });
}

function addNotes(slide, item) {
  const ts = item.teacherScript || {};
  const lines = [
    `教学意图：${item.teachingIntent || ''}`,
    `教师说：${ts.say || ''}`,
    ...(asList(ts.ask).length ? [`追问：${asList(ts.ask).join(' / ')}`] : []),
    ...(asList(ts.expectedResponses).length ? [`预设回应：${asList(ts.expectedResponses).join(' / ')}`] : []),
    ...(item.feedbackEvidence ? [`反馈证据：${item.feedbackEvidence}`] : []),
    ...(ts.transition ? [`过渡语：${ts.transition}`] : []),
    ...(asList(item.notes).length ? [`备注：${asList(item.notes).join('；')}`] : [])
  ];
  if (typeof slide.addNotes === 'function') slide.addNotes(lines.join('\n'));
}

function renderSlide(slide, item, index, total) {
  const screen = item.screen || {};
  addRail(slide, item, index, total);
  addHeader(slide, item);
  addFooter(slide, item);
  const lx = 1.25;
  const ly = 1.1;
  const lw = 5.0;
  const rx = 6.65;
  const rw = W - rx - 0.55;
  const bodyH = 5.55;

  if (item.layoutId === 'ED01') {
    addText(slide, screen.headline || item.title, lx, 1.55, 6.3, 1.18, { fontSize: 38, bold: true, margin: 0 });
    addText(slide, screen.subtitle || '', lx, 2.82, 5.8, 0.42, { fontSize: 18, color: theme.muted, margin: 0 });
    addBox(slide, lx, 3.62, 5.6, 0.62, theme.paper, theme.line);
    addText(slide, screen.outcome || '', lx + 0.18, 3.78, 5.2, 0.28, { fontSize: 13, color: theme.ink, margin: 0 });
    addVisualSlot(slide, item, rx, 1.32, rw, 4.8);
    return;
  }

  addText(slide, screen.headline || item.title, lx, ly, lw, 0.78, { fontSize: 30, bold: true, margin: 0 });

  if (item.layoutId === 'ED02') {
    addText(slide, '先知道要去哪里，课堂才不会迷路。', lx, 2.05, lw, 0.48, { fontSize: 15, color: theme.muted, margin: 0 });
    addNumberRows(slide, asList(screen.route).map((content, i) => ({ label: String(i + 1), content })), rx, 1.18, rw, 4.8, 20);
  } else if (item.layoutId === 'ED03') {
    addText(slide, screen.question || '', lx, 2.0, lw, 1.35, { fontSize: 24, bold: true, color: theme.accent, margin: 0 });
    addVisualSlot(slide, item, rx, 1.18, rw, 4.8);
  } else if (item.layoutId === 'ED04') {
    addText(slide, screen.prompt || '', lx, 2.0, lw, 1.2, { fontSize: 18, color: theme.muted, margin: 0 });
    const points = asList(screen.comparePoints).map((content, i) => ({ label: String(i + 1), content }));
    addNumberRows(slide, points, rx, 1.35, rw, 3.5, 21);
  } else if (item.layoutId === 'ED05') {
    addText(slide, screen.keyIdea || '', lx, 1.98, lw, 0.8, { fontSize: 22, bold: true, color: theme.accent2, margin: 0 });
    addBullets(slide, screen.bullets || [], lx, 3.0, lw, 2.8, 18);
    addVisualSlot(slide, item, rx, 1.18, rw, 4.8);
  } else if (item.layoutId === 'ED06') {
    addText(slide, '把方法留在黑板上，后面的练习都回到这里。', lx, 2.0, lw, 0.62, { fontSize: 15, color: theme.muted, margin: 0 });
    addBullets(slide, screen.modelSteps || [], rx, 1.35, rw, 4.3, 22);
  } else if (item.layoutId === 'ED07') {
    addText(slide, screen.example || '', lx, 2.0, lw, 1.0, { fontSize: 17, color: theme.muted, margin: 0 });
    addNumberRows(slide, screen.steps || [], rx, 1.25, rw, 4.8, 17);
  } else if (item.layoutId === 'ED08') {
    addText(slide, '先说方法，再开始动笔。', lx, 2.0, lw, 0.5, { fontSize: 15, color: theme.muted, margin: 0 });
    addNumberRows(slide, screen.tasks || [], rx, 1.55, rw, 3.8, 22);
  } else if (item.layoutId === 'ED09') {
    addText(slide, '错误不是终点，是看清方法边界的入口。', lx, 2.0, lw, 0.72, { fontSize: 15, color: theme.muted, margin: 0 });
    addBox(slide, rx, 1.22, rw, 1.25, theme.paper, theme.warn);
    addText(slide, screen.misconception || '', rx + 0.25, 1.48, rw - 0.5, 0.55, { fontSize: 18, bold: true, margin: 0 });
    addBox(slide, rx, 2.82, rw, 1.45, theme.paper, theme.good);
    addText(slide, screen.correction || '', rx + 0.25, 3.05, rw - 0.5, 0.82, { fontSize: 16, margin: 0 });
    addBox(slide, rx, 4.62, rw, 0.92, theme.paper, theme.accent);
    addText(slide, screen.checkQuestion || '', rx + 0.25, 4.83, rw - 0.5, 0.3, { fontSize: 14, color: theme.muted, margin: 0 });
  } else if (item.layoutId === 'ED10') {
    const activity = screen.activity || {};
    addText(slide, '让学生留下可观察的课堂证据。', lx, 2.0, lw, 0.5, { fontSize: 15, color: theme.muted, margin: 0 });
    addText(slide, activity.studentAction || '', rx, 1.45, rw, 1.35, { fontSize: 22, bold: true, color: theme.accent, margin: 0 });
    addText(slide, activity.materials || '', rx, 3.05, rw, 0.7, { fontSize: 15, color: theme.muted, margin: 0 });
  } else if (item.layoutId === 'ED11') {
    addText(slide, '把今天的方法压缩成可带走的句子。', lx, 2.0, lw, 0.5, { fontSize: 15, color: theme.muted, margin: 0 });
    addBullets(slide, screen.summary || [], rx, 1.35, rw, 4.3, 22);
  } else if (item.layoutId === 'ED12') {
    addText(slide, '用短测决定下一步教学。', lx, 2.0, lw, 0.5, { fontSize: 15, color: theme.muted, margin: 0 });
    addNumberRows(slide, screen.tickets || [], rx, 1.7, rw, 3.1, 22);
  } else {
    addVisualSlot(slide, item, rx, 1.18, rw, bodyH);
  }
}

slides.forEach((item, index) => {
  const slide = pptx.addSlide();
  renderSlide(slide, item, index, slides.length);
  addNotes(slide, item);
});

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
await pptx.writeFile({ fileName: outputPath });
console.log(outputPath);
