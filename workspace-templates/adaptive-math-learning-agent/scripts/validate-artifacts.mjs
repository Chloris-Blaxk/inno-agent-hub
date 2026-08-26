import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const errors = [];
const allowedStatuses = new Set([
  "observation", "suspected", "inconclusive", "confirmed",
  "improving", "resolved", "dismissed", "reopened"
]);
const allowedEvaluators = new Set(["deterministic", "rubric", "model", "teacher", "self"]);

function fail(file, message) {
  errors.push(`${file}: ${message}`);
}

function jsonFiles(directory) {
  const absolute = path.join(root, directory);
  if (!fs.existsSync(absolute)) return [];
  return fs.readdirSync(absolute)
    .filter((name) => name.endsWith(".json"))
    .map((name) => ({ name, absolute: path.join(absolute, name) }));
}

function parse(file) {
  try {
    return JSON.parse(fs.readFileSync(file.absolute, "utf8"));
  } catch (error) {
    fail(file.name, `JSON 无效：${error.message}`);
    return null;
  }
}

function validConceptId(value) {
  return typeof value === "string" && /^math\.(primary|junior|senior)\.[a-z0-9-]+$/.test(value);
}

for (const file of jsonFiles("attempts")) {
  const value = parse(file);
  if (!value) continue;
  if (value.attempt_id !== path.basename(file.name, ".json")) fail(file.name, "attempt_id 必须与文件名一致");
  if (!value.task || typeof value.task !== "object") fail(file.name, "缺少 task");
  const concepts = value.task?.concept_ids;
  if (!Array.isArray(concepts) || concepts.length === 0 || concepts.some((id) => !validConceptId(id))) {
    fail(file.name, "concept_ids 必须是非空且带学段命名空间的稳定 ID");
  }
  if (!allowedStatuses.has(value.analysis?.diagnosis_status)) fail(file.name, "diagnosis_status 不在允许列表");
  if (!allowedEvaluators.has(value.analysis?.evaluator)) fail(file.name, "evaluator 不在允许列表");
  if (!Array.isArray(value.evidence_ids) || value.evidence_ids.some((id) => typeof id !== "string")) {
    fail(file.name, "evidence_ids 必须是字符串数组");
  }
}

for (const file of jsonFiles("practice")) {
  const value = parse(file);
  if (!value) continue;
  if (value.practice_id !== path.basename(file.name, ".json")) fail(file.name, "practice_id 必须与文件名一致");
  if (!validConceptId(value.target_concept_id)) fail(file.name, "target_concept_id 必须是带学段命名空间的稳定 ID");
  if (typeof value.prompt !== "string" || value.prompt.trim() === "") fail(file.name, "prompt 不能为空");
  if (typeof value.expected_answer !== "string" || value.expected_answer.trim() === "") fail(file.name, "expected_answer 不能为空");
  if (!Array.isArray(value.solution_outline) || value.solution_outline.length === 0) fail(file.name, "solution_outline 不能为空");
  const checks = value.quality_checks;
  for (const key of ["conditions_complete", "answer_verified", "target_isolated", "grade_appropriate", "no_ambiguity"]) {
    if (checks?.[key] !== true) fail(file.name, `quality_checks.${key} 必须为 true`);
  }
}

const ledgerPath = path.join(root, "misconception-ledger.md");
if (fs.existsSync(ledgerPath)) {
  const ledger = fs.readFileSync(ledgerPath, "utf8");
  const ids = [...ledger.matchAll(/^## 条目：(MIS-[A-Za-z0-9-]+)$/gm)].map((match) => match[1]);
  const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
  if (duplicates.length) fail("misconception-ledger.md", `MIS 编号重复：${[...new Set(duplicates)].join(", ")}`);
}

if (errors.length) {
  console.error("运行产物校验失败：");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("运行产物校验通过");
console.log(`- attempts: ${jsonFiles("attempts").length}`);
console.log(`- practice: ${jsonFiles("practice").length}`);
console.log("- concept ID、状态、评价方式、质量门与账本编号有效");
