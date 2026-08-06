---
name: research-topic-generation-skill
description: 基于教师已有材料和最小教师画像生成总结性、规划性教育研究选题，并评估已有基础、差异化、创新点、可行性风险和下一步资料清单。支持 DKG（动态知识图谱）图计算管线发现研究缺口与 LLM 理解材料两种执行轨道。
entryName: 研究选题生成
entryToken: "@研究选题生成"
displayName: 研究选题生成
status: runnable_prototype
execution_protocol:
  model_required: true
  model_role: education_content_generator
  model_id: innospark-235b
  model_name: InnoSpark-235B
  model_base_url_env: INNOSPARK_AIECNU_BASE_URL
  model_api_key_env:
    - INNOSPARK_AIECNU_API_KEY
    - INNOSPARK_API_KEY
---

# 研究选题生成智能体 Skill

## 场景定位

面向教师评职称、论文和课题申报前的选题困难。核心矛盾不是"缺题"，而是**不知道自己的已有积累能往哪个方向走**——上过的课、写过的案例、发过的文章，这些东西汇总起来能形成什么研究选题？也不知道未来应该往哪个方向深耕才既有创新又在自己能力范围内。

本 Skill 把教师已有积累和未来规划约束转化为可申报、可深耕的教育科研选题，并为每个候选方向输出可追溯证据链。**只给出"值得探索的方向 + 证据 + 风险"，不承诺完整研究空白检测或中标概率预测。**

## 何时使用

- 用户说"帮我生成课题/论文选题""不知道已有材料能往哪个方向走""评职称需要选题""未来 1-3 年深耕方向""判断选题是否重复/差异化"
- 用户上传论文、案例、教学反思、课题成果，希望归纳个人研究轨迹
- 用户已有初步主题，需要结合政策、立项题、学校问题、教师条件做候选方向排序

不要用于纯文献检索、论文润色、引用格式校验、项目申报书/结题报告生成。文献阅读下游使用 `@文献阅读助手`。

## 固定入口与独立性

- 当用户显式使用 `@研究选题生成` 时，优先进入本 Skill；不要因为需要文献或项目申报信息就改派其他 Skill。
- 本 Skill 只需要 `teacherProfile` 和 `input.materials` 即可独立运行；政策热点、历年立项题、文献元数据都是增强输入。
- 可接收论文、课例、教学反思、课题成果、获奖材料等作为 `SourceMaterial`；已有成果必须来自材料或用户明确输入。
- 真实交互中只能使用当前用户输入、附件、会话上下文或显式传入的 `sourceFiles`；不得默认读取 `../research-line-test-data/`、旧 `examples/test-data/` 或任意测试材料包。
- 需要联动时，只在 `handoff.topicCandidates`、`handoff.keywords`、`handoff.readingQuestions` 中输出给下游使用，不把下游结果作为本 Skill 的必需前置。
- `result` 保留完整对象；`handoff` 使用压缩对象（题目、关键词、证据状态、风险级别、下一步阅读问题），不得只传 ID。
- 跨 Skill 汇总使用 `researchWorkspace`，公共契约见 `../research-line-common/schemas/research_workspace.schema.json`。

## 数据资源优先级

选题的可靠程度取决于可用的数据资源，按优先级排列：

1. **用户材料解析规范**：论文、案例、反思、成果 — 最直接的研究基础证据
2. **最小教师画像 schema**：学科、学段、学校条件、能力基础、可投入周期 — 约束可行性判断
3. **政策热点与资助方向标签** — 对齐政策趋势
4. **历年立项题目样本** — 重复度与差异化判断
5. **学校/区域实践问题库** — 创新性-可行性双维量规
6. **文献元数据索引** — 可通过 `RESEARCH_LITERATURE_BACKEND=pedascope|hybrid` 接入 PedaScope KB，作为题录密度、代表文献和差异化阅读问题的增强信号

数据不足时做保守判断，不硬生成。缺省字段记录 `fallback_flags`，不静默补全。

## 双轨执行架构

本 Skill 支持两种执行轨道，系统根据条件自动选择或降级：

```
用户请求
    │
    ├── input.enableDKG = true 且 DKG 已构建？
    │   │
    │   ├── 是 →【DKG 轨】图计算管线
    │   │   S1 构建/维护 DKG           → 多源实体、关系、时间戳、动态权重
    │   │   S2 请求解析                → ReqParam、回退标记、输出约束
    │   │   S3 锚点与子图              → 锚点集合、K 跳局部子图、递进裁剪
    │   │   S4 拓扑分析                → 密度、连通性、聚类、核心层级、社团、中心性、结构约束
    │   │   S5 缺口识别                → 稀疏区域型 / 结构洞型缺口与成因
    │   │   S6 趋势预测                → 时间序列热度、关系演化或回退趋势证据
    │   │   S7 评分排序                → 匹配/缺口/趋势/可行性评分 + 多样性约束
    │   │   S8 证据链                  → 8 字段结构化证据链
    │   │   S9 反馈闭环               → 用户选择/否定反馈更新 DKG 权重
    │   │   LLM 包装                    → 将图证据转化为语言化选题描述
    │   │
    │   └── 否 →【LLM 轨】材料理解管线（原有流程）
    │       材料解析 → MaterialClusters → ResearchTrajectory
    │       → LLM 生成选题 → 对比立项题样本 → 评估 → 输出
    │
    └── 输出选题报告 + 证据链 + 质量报告
```

### DKG 轨快速运行

```bash
# 构建知识图谱
python3 scripts/dkg.py build \
    --sources examples/sample_sources.json \
    --out examples/sample_dkg.json

# 运行选题发现
python3 scripts/discover.py run \
    --dkg examples/sample_dkg.json \
    --request examples/sample_request.json \
    --config assets/agent_config.json \
    --out examples/sample_result.json

# 用户反馈更新权重
python3 scripts/discover.py feedback \
    --dkg examples/sample_dkg.json \
    --result examples/sample_result.json \
    --feedback examples/sample_feedback.json \
    --out examples/sample_dkg_after_feedback.json
```

## 任务模式

- `summative_topic`：从已有材料中提炼当前阶段可申报或可写作的选题。"基于你已做的 X，可围绕 Y 申报 Z 类课题"。
- `planning_topic`：面向未来 1-3 年，结合教师条件、政策热点和实践问题推荐 3-5 个深耕方向。
- `mixed_topic`：同时输出总结性和规划性选题，并明确两者依据不同。
- `topic_refine`：对用户已有题目做聚焦、降重、范围收窄和可行性调整。

## 执行流程

### LLM 轨流程

1. 读取 `references/input-output-schema.md`，确认请求和输出信封；公共信封见 `../research-line-common/schemas/research_line.schema.json`。
2. 用 `references/teacher-profile-schema.json` 检查教师画像；缺字段时写入 warnings 或 nextActions，不自行补造。
3. 用 `references/material-parsing-rules.md` 将材料转成 `MaterialDigest`，只抽取材料中明确出现的事实。
4. 先生成 `materialClusters` 和 `researchTrajectory`：
   - `materialClusters` 将课例、反思、论文、成果等按共同主题聚合，并回链 `materialId`。
   - `researchTrajectory` 归纳教师已有积累阶段（`insufficient_material` / `material_accumulation` / `theme_consolidation` / `evidence_building`）、主导主题、未来深耕路径和风险。
5. 根据 taskIntent 生成选题：
   - 总结性选题必须引用 `materialId`，说明"已有 X 基础，距离 Y 选题还差 Z"。
   - 总结性选题优先基于主题簇生成，而不是只复述单份材料。
   - 规划性选题可引用 `references/policy-hotspot-tags.json`、`references/grant-title-samples.json` 和 `references/practice-problem-bank.json`，但必须说明风险和补资料清单。
6. 用 `references/topic-evaluation-rubric.json` 评估已有基础、创新性、可行性和差异化。
7. 每个选题必须补齐 `basisGap` 和 `differentiation`：说明已有基础、目标申报要求、差距、升级路径、最近似立项题和差异化策略。
8. 当 `RESEARCH_LITERATURE_BACKEND=pedascope|hybrid` 或请求显式开启 `enableLiteratureSignals` 时，通过 `../research-line-common/literature_adapter.py` 生成 `literatureSignals`；它只表示题录相关性和重复风险信号，不证明完整研究空白，也不生成 EvidenceCard。
9. 输出 `topicEvaluationReport`、`qualityReport`、`provenanceReport`，并运行 `scripts/validate_research_topic.py` 校验。
10. 若产物来自模型生成，render、handoff 或交付前还必须通过 `../research-line-common/model_output_guard.py`；`warn` 只能带警告进入人工复核，`rejected` 不得交付。

### DKG 轨流程

1. 先确认是否已有 DKG。若只有原始材料，先按 `references/workflow.md` 的源记录格式建图；若完全没有数据，只能演示示例，不得编造真实政策或立项题。
2. 运行 `scripts/discover.py run` 执行 S2-S8 管线。
3. 将 DKG 输出的 `rank_list` + `evidence_chains` 经 LLM 包装为语言化选题描述：
   - `gap_type` → "研究缺口类型"
   - `gap_cause` → "为什么这里存在缺口"
   - `topo_evidence` → "图结构证据"
   - `trend_evidence` → "趋势判断"
   - `score_breakdown` → "综合评分解释"
4. 每个 DKG 选题仍需与历年立项题样本做差异化对比（`references/grant-title-samples.json`），补充 `basisGap` 和 `differentiation`。
5. 输出 `topicEvaluationReport`、`qualityReport`（含 DKG 指标）、`provenanceReport`。
6. 若产物来自模型生成，必须通过 `../research-line-common/model_output_guard.py`。

### 反馈闭环（DKG 轨专属）

用户对选题结果的反馈（选择/收藏/否定）通过 `scripts/discover.py feedback` 写回 DKG 权重：
- 正向反馈（选择、收藏）→ 增强相关实体/关系权重
- 负向反馈（否定）→ 衰减相关实体/关系权重
- 所有反馈写入演化记录 `evolog`

## 关键输出字段

### dkgEvidence（DKG 轨专属）

当 DKG 轨启用时，每个 `ResearchTopicCandidate` 附带 `dkgEvidence` 对象：

| 字段 | 说明 |
|------|------|
| `enabled` | 是否由 DKG 轨生成 |
| `gapType` | `sparse_region`（稀疏区域型）或 `structural_hole`（结构洞型） |
| `gapCause` | 成因描述：触发依据、缺口两侧实体、与请求关系 |
| `topoEvidence` | 拓扑指标摘要（指标类型、阈值策略、结论） |
| `trendEvidence` | 趋势方法、时间窗、结论、置信度、回退状态 |
| `sourceCoverage` | 来源覆盖度（0-1），<0.5 提示可靠性受限 |
| `graphPath` | 锚点到缺口的图路径 |
| `scoreBreakdown` | 四项分项分 + 综合分 + 合成方式 |
| `uncertaintyNote` | 趋势回退、来源不足、争议对象、外围弱关联等风险提示 |

完整 schema 见 `references/input-output-schema.md` 的 `ResearchTopicCandidate.dkgEvidence`。

## 边界

- 首批不承诺完整研究空白检测。
- 文献元数据索引作为增强依赖，未接入时只做保守判断；接入 PedaScope 时只能输出 `literatureSignals`、代表题录和下一步阅读问题。
- PedaScope 题录和系统生成摘要不得写成研究结论、原文摘要、EvidenceCard 或支撑性引用。
- 不替用户虚构已有成果。
- 材料不足时，不硬生成总结性选题；可以降级为规划性选题或补资料清单。
- 不承诺课题立项、论文发表或职称评审结果。
- DKG 轨的图计算管线依赖 DKG 数据就绪；DKG 未构建时自动降级为 LLM 轨。
- 趋势回退、来源覆盖不足、争议对象、外围弱关联都必须原样保留在不确定性提示中。
- 不输出"保证创新""一定中标""已完整证明空白"之类结论。

## 教师可读性规则

本 Skill 的目标用户是「中小学教师（科研能力初级~中级）」。以下规则**对 Markdown/文本输出强制执行**：

### 选题展示规则

- ✅ 选题以序号 + 标题为主标识，如「选题 1：《小学数学课堂即时反馈支持错因诊断的实践研究》」。**不要**用 `topic-001` 之类内部 ID 做主标签。
- ✅ 用 🔵 标记总结性选题、🟢 标记规划性选题，让教师一眼区分。
- ✅ 评分用 ⭐ 星级（1-5 星）展示，配一句话通俗解释（如「⭐⭐⭐⭐☆ — 材料匹配度很高，可以直接申报」），**不要**裸写 `{"score": 4, "weight": 0.3}` 之类 JSON。
- ✅ 差异化检查用自然语言描述（如「这个题目跟某区 2023 年立项的《XXX》有点像，但你的创新点在于……所以建议在申报书中重点突出……方面」）。
- ✅ 可行性风险用人话（如「需要其他年级老师的配合」「你可能需要一个现成的元认知测量问卷」），**不要**用 `feasibility.risks: ["teacher_cooperation"]` 之类的技术表述。

### 材料展示规则

- ✅ 材料回链用材料标题（如「你的《异分母分数加减法错因分析课例》」），**不要**用 `mat-001` 做主标签。
- ✅ 材料聚类用主题名 + 一句通俗解释（如「这两份材料都是围绕『错因诊断』做的——课例是课堂实操，结题报告是系统总结」）。
- ✅ 研究轨迹阶段用中文描述：`insufficient_material` →「📭 材料还比较少，暂时看不出完整轨迹」、`material_accumulation` →「📚 材料在积累中，已经有了初步方向」、`theme_consolidation` →「🎯 研究方向已经成形，可以准备申报课题了」、`evidence_building` →「✅ 证据链比较完整，可以写论文或申报了」。

### 整体语言原则

- ✅ 用「你（李老师）」「你的课题」「你的已有积累」称呼教师，不用「用户」。
- ✅ 用「建议首选这个方向」「这个题目可以先储备」代替 `recommended: true/false`。
- ✅ 数据来源声明必须写成人话（如「目前只对比了 3 条 mock 立项题样本，真实立项题的数量远多于此，申报前建议去区教研网查最近 3 年的立项公示」）。
- ❌ 禁止在面向教师的正文中出现 JSON 字段路径（如 `topicCandidates[0].dkgEvidence.gapType`）、裸写内部枚举值。
- ⚠️ `dkgEvidence` 和 `scoreBreakdown` 是机器内部字段，**不要**直接照搬进教师可读输出——如果要用，必须转成自然语言（如「图谱分析发现这个方向的研究密度较低，说明可探索空间较大」）。

## 质量标准

### 教师可读性（P0 — 交付前必查）

- 选题以「序号 + 标题」为主标识，topicId 仅出现在脚注或括号中。
- 评分用 ⭐ 星级 + 通俗解释，不裸写 JSON 数值。
- 材料回链用材料标题、不用 mat-XXX ID。
- 研究轨迹阶段用中文描述 + emoji 标记。
- 数据来源声明写成人话，说明 mock 数据的局限性。
- 全文用「你」称呼教师，不用「用户」。
- dkgEvidence 和 scoreBreakdown 不直接照搬进教师可读输出，必须转成自然语言。

### 学术诚信（P0 — 交付前必查）

- 选题必须引用用户已有材料或画像条件作为依据。
- 材料聚类必须回链真实材料，并说明主题缺口与可转化选题角度。
- 研究轨迹必须区分材料不足、材料积累、主题成形和证据链建设阶段。
- 明确区分总结性选题和规划性选题。
- 每个选题必须说明”已有 X 基础，距离 Y 选题还差 Z”。
- 每个选题必须给出与历年立项题样本的重复度/差异化检查。
- 若输出 `literatureSignals`，必须声明题录级边界，并把相关文献数解释为”文献分布信号”而不是”研究空白证明”。
- 每个选题包含可行性风险和补充资料清单。
- 避免宏大空泛、无法落地的题目。
- DKG 轨：每个候选方向必须带 8 字段证据链，且拓扑/缺口/趋势/评分优先运行脚本，不手算替代。
- `generated-outputs/sample-valid.json`、`sample-evidence-missing.json`、`sample-invalid.json` 是本 Skill 的输出边界样例。

## 参考数据索引

| 文件 | 用途 | 轨道 |
|---|---|---|
| `references/input-output-schema.md` | 请求与输出结构约定（含 dkgEvidence schema） | LLM + DKG |
| `references/requirements.md` | 需求摘录：核心痛点、需求边界、研发方向 | LLM |
| `references/teacher-profile-schema.json` | 最小教师画像 schema | LLM |
| `references/material-parsing-rules.md` | 材料解析规范 | LLM |
| `references/policy-hotspot-tags.json` | 政策热点与资助方向标签 | LLM + DKG |
| `references/grant-title-samples.json` | 历年立项题目样本（重复度与差异化判断） | LLM + DKG |
| `references/practice-problem-bank.json` | 学校/区域实践问题库 | LLM |
| `references/topic-evaluation-rubric.json` | 创新性-可行性双维量规 | LLM |
| `references/workflow.md` | DKG 建图与九步工作流详细文档 | DKG |
| `references/scoring_and_evidence.md` | DKG 评分公式与证据链字段规范 | DKG |
| `references/quality-checklist.md` | 质量检查清单 | LLM + DKG |

## 组件地图

### Agents
- `agents/openai.yaml`：UI 元数据（`display_name`、`short_description`、`default_prompt`），与 frontmatter 和入口表保持同一展示语义。

### Scripts（LLM 轨）
- `scripts/render_research_topic.py`：LLM 轨渲染入口（材料解析 → 聚类 → 选题生成 → 差异化对比 → JSON + Markdown 输出）
- `scripts/validate_research_topic.py`：本地质量校验

### Scripts（DKG 轨）
- `scripts/dkg.py`：S1 动态知识图谱构建/维护（多源融合、对齐消歧、动态权重、演化记录）
- `scripts/discover.py`：S2/S3/S9 请求解析、锚点子图、选题发现运行、反馈更新
- `scripts/topology.py`：S4/S5 拓扑特征分析 + 稀疏区域/结构洞缺口识别
- `scripts/trend.py`：S6 趋势预测（时间序列热度 + 关系演化 + 回退策略）
- `scripts/scoring.py`：S7 综合评分与排序（匹配/缺口/趋势/可行性 + 多样性约束）
- `scripts/evidence.py`：S8 证据链生成（8 字段结构化 + 方向标题渲染）
- `scripts/graphlib.py`：纯 Python 图算法库（密度、聚类、k-core、社团、介数、结构约束）

### Shared（科研线公共）
- `../research-line-common/model_output_guard.py`：模型输出安全门禁
- `../research-line-common/docx_export.py`：DOCX 导出
