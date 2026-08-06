#!/usr/bin/env node
import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const SLIDE_SIZE = { width: 1280, height: 720 };

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith("--")) throw new Error(`Unexpected argument: ${key}`);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      args[key.slice(2)] = true;
      continue;
    }
    args[key.slice(2)] = value;
    index += 1;
  }
  return args;
}

function requireArg(args, key) {
  if (!args[key]) throw new Error(`Missing --${key}`);
  return args[key];
}

function runtimeNodeModules() {
  return path.join(
    process.env.HOME || process.cwd(),
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "node",
    "node_modules",
  );
}

function artifactEntrypoint() {
  const packageDir = path.join(runtimeNodeModules(), "@oai", "artifact-tool");
  const candidates = [
    path.join(packageDir, "dist", "node", "artifact_tool.mjs"),
    path.join(packageDir, "dist", "artifact_tool.mjs"),
  ];
  const entrypoint = candidates.find((candidate) => fsSync.existsSync(candidate));
  if (!entrypoint) throw new Error(`Cannot find @oai/artifact-tool in ${packageDir}`);
  return entrypoint;
}

function text(value) {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function factValue(value) {
  if (Array.isArray(value)) return value.map(text).join("；");
  return text(value);
}

function factIndex(factTable) {
  const index = {};
  for (const fact of factTable?.facts || []) {
    if (fact?.field) index[fact.field] = fact;
  }
  return index;
}

function factText(facts, field, fallback = "") {
  return factValue(facts[field]?.value) || fallback;
}

function truncate(value, max = 86) {
  const valueText = text(value).replace(/\s+/g, " ").trim();
  return valueText.length > max ? `${valueText.slice(0, max - 1)}…` : valueText;
}

function addShape(slide, options) {
  const { x, y, w, h, fill = "#FFFFFF", line = "#FFFFFF", radius = 0 } = options;
  return slide.shapes.add({
    geometry: "rect",
    position: { x, y, w, h },
    fill,
    line: { style: "solid", fill: line, width: radius ? 1 : 0 },
  });
}

function addText(slide, options) {
  const {
    text: content,
    x,
    y,
    w,
    h,
    fontSize = 28,
    color = "#111827",
    bold = false,
    fill = "rgba(0,0,0,0)",
    align = "left",
    valign = "top",
  } = options;
  const shape = addShape(slide, { x, y, w, h, fill, line: fill });
  shape.text = content;
  shape.text.fontSize = fontSize;
  shape.text.color = color;
  shape.text.bold = bold;
  shape.text.typeface = "Aptos";
  shape.text.alignment = align;
  shape.text.verticalAlignment = valign;
  shape.text.insets = { left: 10, right: 10, top: 6, bottom: 6 };
  return shape;
}

function addHeader(slide, kicker, title) {
  addText(slide, { text: kicker, x: 60, y: 36, w: 260, h: 30, fontSize: 16, color: "#64748B", bold: true });
  addText(slide, { text: title, x: 56, y: 72, w: 900, h: 54, fontSize: 30, color: "#0F172A", bold: true });
  addShape(slide, { x: 60, y: 140, w: 1160, h: 2, fill: "#CBD5E1", line: "#CBD5E1" });
}

function addBulletColumn(slide, title, items, x, y, w, h, accent = "#E0F2FE") {
  addShape(slide, { x, y, w, h, fill: "#F8FAFC", line: "#D8E0EA", radius: 1 });
  addShape(slide, { x, y, w: 8, h, fill: accent, line: accent });
  addText(slide, { text: title, x: x + 18, y: y + 16, w: w - 32, h: 30, fontSize: 18, bold: true });
  const visible = items.slice(0, 5);
  visible.forEach((item, index) => {
    addText(slide, {
      text: `• ${truncate(item, 72)}`,
      x: x + 18,
      y: y + 58 + index * 48,
      w: w - 32,
      h: 42,
      fontSize: 16,
      color: "#334155",
    });
  });
}

function addTitleSlide(presentation, data, facts) {
  const slide = presentation.slides.add();
  addShape(slide, { x: 0, y: 0, w: 1280, h: 720, fill: "#F8FAFC", line: "#F8FAFC" });
  addText(slide, { text: "成果汇报框架", x: 72, y: 86, w: 620, h: 56, fontSize: 42, color: "#0F172A", bold: true });
  addText(slide, {
    text: factText(facts, "project.title", "项目题目待确认"),
    x: 72,
    y: 156,
    w: 860,
    h: 58,
    fontSize: 24,
    color: "#334155",
  });
  addBulletColumn(
    slide,
    "事实约束",
    [
      `项目级别：${factText(facts, "project.level", "待确认")}`,
      `周期：${factText(facts, "timeline.cycle", "待确认")}`,
      `团队：${factText(facts, "team.memberCount", "待确认")}`,
      `质量状态：${data.qualityReport?.status || ""}`,
    ],
    72,
    278,
    500,
    300,
    "#BAE6FD",
  );
  addBulletColumn(
    slide,
    "交付边界",
    [
      "只使用 ProjectFactTable 中已有事实",
      "缺失和冲突字段需要人工确认",
      "预算与成果数值不得由模型补造",
      "本 PPTX 为可编辑汇报骨架",
    ],
    640,
    278,
    500,
    300,
    "#C7D2FE",
  );
  return slide;
}

function addTimelineSlide(presentation, support) {
  const slide = presentation.slides.add();
  addHeader(slide, "PROCESS", "项目过程时间线");
  const items = support.timelineItems || [];
  items.slice(0, 5).forEach((item, index) => {
    const x = 80 + index * 222;
    addShape(slide, { x, y: 270, w: 180, h: 6, fill: "#38BDF8", line: "#38BDF8" });
    addShape(slide, { x: x + 70, y: 238, w: 42, h: 42, fill: "#0EA5E9", line: "#0EA5E9" });
    addText(slide, { text: String(index + 1), x: x + 76, y: 244, w: 30, h: 28, fontSize: 18, color: "#FFFFFF", bold: true, align: "center" });
    addText(slide, { text: item.label || `阶段 ${index + 1}`, x, y: 308, w: 190, h: 34, fontSize: 18, bold: true });
    addText(slide, { text: truncate(item.description, 58), x, y: 346, w: 190, h: 76, fontSize: 15, color: "#475569" });
  });
  if (!items.length) {
    addText(slide, { text: "时间线事实待补充。", x: 80, y: 220, w: 780, h: 60, fontSize: 24, color: "#475569" });
  }
  return slide;
}

function addEvidenceSlide(presentation, support, facts) {
  const slide = presentation.slides.add();
  addHeader(slide, "EVIDENCE", "量化成果与图表建议");
  const chartItems = (support.chartSuggestions || []).map((item) => `${item.title || "图表"}：${item.chartType || ""}，${item.status || ""}`);
  const highlights = (support.achievementHighlights || []).map((item) => text(item.title || item.description || item));
  addBulletColumn(slide, "图表建议", chartItems.length ? chartItems : ["暂无可用数值事实，不能生成图表。"], 72, 186, 520, 360, "#BBF7D0");
  addBulletColumn(slide, "成果亮点", highlights.length ? highlights : [factText(facts, "outcomes.actual", "成果事实待确认")], 660, 186, 520, 360, "#FDE68A");
  return slide;
}

function addConsistencySlide(presentation, data) {
  const slide = presentation.slides.add();
  addHeader(slide, "CHECK", "跨文档一致性与下一步");
  const report = data.result?.crossDocumentConsistencyReport || {};
  addBulletColumn(
    slide,
    "一致性状态",
    [
      `检查状态：${report.status || "未提供"}`,
      `冲突数：${(report.conflicts || []).length}`,
      `缺失共享字段：${(report.missingSharedFields || []).length}`,
      "同一事实需回链同一组 factId",
    ],
    72,
    186,
    520,
    360,
    "#DDD6FE",
  );
  addBulletColumn(
    slide,
    "下一步",
    data.nextActions?.length ? data.nextActions : ["教师确认事实表后再进入正式排版。", "补齐缺失材料后重跑校验。"],
    660,
    186,
    520,
    360,
    "#FBCFE8",
  );
  return slide;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputPath = path.resolve(requireArg(args, "input"));
  const outputPath = path.resolve(requireArg(args, "out"));
  const data = JSON.parse(await fs.readFile(inputPath, "utf8"));
  if (data.skillId !== "project-proposal-skill") {
    throw new Error(`Expected project-proposal-skill output, got ${data.skillId}`);
  }
  const artifact = await import(pathToFileURL(artifactEntrypoint()).href);
  const { Presentation, PresentationFile } = artifact;
  const presentation = Presentation.create({ slideSize: SLIDE_SIZE });
  const factTable = data.result?.projectFactTable || {};
  const facts = factIndex(factTable);
  const support = data.result?.presentationSupport || {};
  addTitleSlide(presentation, data, facts);
  addTimelineSlide(presentation, support);
  addEvidenceSlide(presentation, support, facts);
  addConsistencySlide(presentation, data);

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  const stat = await fs.stat(outputPath);
  const payload = {
    status: "passed",
    output: outputPath,
    outputBytes: stat.size,
    slideCount: presentation.slides.count,
  };
  console.log(JSON.stringify(payload, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
