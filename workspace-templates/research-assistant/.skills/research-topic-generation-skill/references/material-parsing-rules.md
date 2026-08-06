# 材料解析规则

本文件用于把教师上传的论文、课例、教学反思、课题成果等材料解析为 `MaterialDigest`。当前为 mock 规则，供 pipeline 跑通；真实上线前应由科研专家补充字段和样例。

## 支持材料类型

| materialType | 说明 | 重点抽取 |
|---|---|---|
| `teaching_case` | 教学案例、课堂实录摘要、课例说明 | 教学对象、问题情境、教学策略、学生表现、可研究问题 |
| `reflection` | 教学反思、磨课记录、听评课记录 | 问题意识、改进动作、观察证据、后续设想 |
| `paper` | 已发表或待投稿论文 | 研究主题、方法、结论、已有基础、可延展方向 |
| `project_outcome` | 已完成课题、成果报告、获奖材料 | 项目主题、成果数量、应用范围、可申报基础 |
| `data_record` | 调查数据、课堂观察、问卷结果 | 样本范围、指标、主要发现、限制 |

## MaterialDigest 生成规则

每份材料至少生成：

- `digestId`
- `materialId`
- `materialType`
- `title`
- `keyFacts`
- `topicSignals`
- `usableFor`
- `limitations`

## keyFacts 规则

- 只能抽取材料中明确出现的事实。
- 事实应尽量短句化，例如“已完成 3 节错因诊断课例”。
- 如果材料只有想法没有证据，`confidence` 标为 `low`。
- 不得把愿望、计划、推测写成已完成事实。

## topicSignals 规则

从材料中抽取可形成选题的关键词，例如：

- 教学对象：小学数学、高年级、城区普通小学
- 问题类型：错因诊断、即时反馈、小组合作
- 方法策略：课堂投票、错因分类、观察记录
- 成果形态：教学案例、课堂观察、反思记录

## usableFor 规则

| usableFor | 含义 |
|---|---|
| `research_topic` | 可作为研究选题依据 |
| `project_basis` | 可作为项目申报研究基础 |
| `paper_background` | 可作为论文背景素材 |
| `needs_more_evidence` | 材料不足，只能提示补证据 |

## 降级规则

- 缺少材料标题：用 `未命名材料-{index}`。
- 缺少材料内容：写入 `limitations`，不生成 keyFacts。
- 同一事实冲突：保留多个候选事实，交由后续 `qualityReport` 标记。

## 向教师展示时的材料引用规则

- ✅ 回链材料时用**材料标题**（如「你的《异分母分数加减法错因分析课例》」），`materialId`（如 `mat-001`）只能出现在括号或脚注中。
- ✅ 用材料类型 + 一句话概括代替技术字段。例如：不要写「`mat-001 materialType=teaching_case`」，而是写「📋 课例：《异分母分数加减法错因分析》——记录了你在分数运算单元的课堂诊断实操」。
- ❌ 禁止在面向教师的正文中裸写 `materialId`、`digestId` 作为材料主标签。

