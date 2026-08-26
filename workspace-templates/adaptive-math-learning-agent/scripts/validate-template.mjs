import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const errors = [];
const expectedSkills = [
  "adaptive-math-practice",
  "math-learning-progress-reporter",
  "math-misconception-verifier",
  "math-reasoning-trace-analyzer",
  "math-task-structurer",
  "multi-representation-repair"
];

function fail(message) {
  errors.push(message);
}

function read(relativePath) {
  const absolutePath = path.join(root, relativePath);
  if (!fs.existsSync(absolutePath)) {
    fail(`缺少文件：${relativePath}`);
    return "";
  }
  return fs.readFileSync(absolutePath, "utf8");
}

const requiredFiles = [
  "agent.md",
  "README.md",
  "preset.json",
  "docs/design_notes.md",
  "references/diagnosis-state-model.md",
  "references/math-error-taxonomy.md",
  "references/problem-schema.md",
  "references/practice-generation-rules.md",
  "references/problem-quality-checklist.md",
  "references/curriculum/primary-math.md",
  "references/curriculum/junior-math.md",
  "references/curriculum/senior-math.md",
  "references/domains/arithmetic.md",
  "references/domains/algebra.md",
  "references/domains/functions.md",
  "references/domains/geometry.md",
  "references/domains/modeling.md",
  "references/domains/probability-statistics.md",
  "templates/attempt-record-template.json",
  "templates/practice-item-template.json",
  "templates/misconception-ledger-template.md",
  "templates/review-plan-template.md",
  "templates/report-template.md",
  "examples/evaluation-cases.md",
  "examples/browser-test-guide.md",
  "scripts/validate-artifacts.mjs"
];

for (const file of requiredFiles) read(file);

let preset;
try {
  preset = JSON.parse(read("preset.json"));
} catch (error) {
  fail(`preset.json 不是有效 JSON：${error.message}`);
}

if (preset) {
  const folderName = path.basename(root);
  if (preset.id !== folderName) fail(`preset.json.id 必须与目录名一致：${folderName}`);
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(preset.id ?? "")) fail("preset.json.id 必须使用 kebab-case");
  if (preset.category !== "教学") fail("preset.json.category 必须为“教学”");
  for (const key of ["name", "description", "icon"]) {
    if (typeof preset[key] !== "string" || preset[key].trim() === "") fail(`preset.json.${key} 不能为空`);
  }
}

const skillsRoot = path.join(root, ".skills");
if (!fs.existsSync(skillsRoot)) {
  fail("缺少 .skills 目录");
} else {
  const actualSkills = fs.readdirSync(skillsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
  if (JSON.stringify(actualSkills) !== JSON.stringify([...expectedSkills].sort())) {
    fail(`Skill 列表不正确：${actualSkills.join(", ")}`);
  }
  for (const directory of actualSkills) {
    const relativePath = path.join(".skills", directory, "SKILL.md");
    const source = read(relativePath);
    const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!match) {
      fail(`${relativePath} 缺少 YAML frontmatter`);
      continue;
    }
    const frontmatter = match[1];
    const name = frontmatter.match(/^name:\s*([^\r\n]+)$/m)?.[1]?.trim();
    const category = frontmatter.match(/^category:\s*([^\r\n]+)$/m)?.[1]?.trim();
    if (name !== directory) fail(`${relativePath} 的 name 必须与目录名一致`);
    if (category !== "教学辅导") fail(`${relativePath} 的 category 必须为“教学辅导”`);
    if (!/^description:/m.test(frontmatter)) fail(`${relativePath} 缺少 description`);
  }
}

for (const jsonFile of [
  "preset.json",
  "templates/attempt-record-template.json",
  "templates/practice-item-template.json"
]) {
  try {
    JSON.parse(read(jsonFile));
  } catch (error) {
    fail(`${jsonFile} 不是有效 JSON：${error.message}`);
  }
}

function inspect(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if ([".git", "node_modules"].includes(entry.name)) continue;
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      inspect(absolutePath);
      continue;
    }
    const relativePath = path.relative(root, absolutePath);
    if (/\.DS_Store$|\.mov$/i.test(entry.name)) fail(`不应提交本地或视频文件：${relativePath}`);
    if (/\.(md|json)$/i.test(entry.name)) {
      const source = fs.readFileSync(absolutePath, "utf8");
      if (/\b(?:TODO|TBD)\b|待补充/.test(source)) fail(`发现未完成占位内容：${relativePath}`);
      if (/adaptive-equation-learning-agent|solution-trace-analyzer|equation-concept-taxonomy/.test(source)) {
        fail(`发现旧模板命名：${relativePath}`);
      }
    }
  }
}

inspect(root);

if (errors.length) {
  console.error("模板校验失败：");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log(`模板校验通过：${path.basename(root)}`);
console.log(`- ${expectedSkills.length} 个 Skill 的 name、category 与目录一致`);
console.log("- 三学段、六领域参考和题目质量门齐全");
console.log("- JSON 模板有效，未发现旧命名、占位或不应提交文件");
