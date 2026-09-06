---
name: learner-question-loop
category: 教学辅导
description: 运行由学习者主动发问的概念学习循环：先直接回答问题，识别错误前提，累计 2–3 个问题后用复述、边界或迁移任务检验理解，并分开记录问题深度与掌握证据。用于学习者选择概念、提出或追问概念问题、表示已经理解、请求自测或恢复既有学习时。
---

# 学习者追问循环

坚持以下主循环：

```text
学习者选择概念并提问
→ 先回答实际问题
→ 记录问题但不冒充掌握
→ 每 2–3 问进行一次单项检验
→ 根据学习者的作答更新掌握证据
→ 把发问权交还学习者
```

## 进入一轮

1. 先读取 `learning-state.json`。文件不存在或当前主题没有概念时，转用 `concept-seeder`；不要凭空制造历史。
2. 识别问题对应的概念，将其设为 `active_concept_id`。学习者可提出种子之外的相关概念；按 `concept-seeder` 的跨工作区语义 ID 规则将它追加到当前主题后再继续，禁止生成顺序 ID。
3. 若消息含多个可分离问题，先回答第一个并简短列出其余待问项，让学习者决定下一问。不要用一篇长文一次消耗掉全部追问空间。
4. 若已有待完成检验而学习者改问了新的概念问题，仍先回答新问题；随后只重申一个检验任务。学习者明确要求跳过时允许继续，但不得把该概念标为已掌握。

## 先回答，再引导

对每个实质性概念问题依次执行：

1. **直接结论**：先用 1–2 句回答用户实际问的内容，不用“你觉得呢？”把问题退回。
2. **前提检查**：问题含错误前提时，明确写出“这个前提需要修正：……”，给出正确前提，再回答最接近的有效问题。
3. **必要展开**：按“直觉 → 机制 → 例子或边界”解释到足以支撑下一次追问；只展开本问需要的部分。
4. **交还发问权**：未到检验点时，用一句“继续由你提出下一问”结束。除非学习者说不会提问，不替其生成下一道完整问题。

把定义、事实或机制相关的问题都视为实质性问题。致谢、寒暄、文件操作和单独一句“懂了”不计入问题数。

## 分开判断两类信号

给每个学习者问题标记深度，并写入状态与日志：

- `D1`：定义、事实、例子或基本澄清；
- `D2`：机制、因果、比较或概念关系；
- `D3`：假设、边界、反例、反事实、综合或迁移；
- `D0`：尚无问题。

问题深度只描述探索方式。即使问题达到 `D3`，也不得据此提高 `mastery_evidence` 或 `mastery_delta`。

掌握证据只能来自学习者完成的检验：

- `E0`：未检验，或作答无法体现核心理解；
- `E1`：能回忆部分要点，但有关键缺口；
- `E2`：能准确复述核心机制并说明适用条件；
- `E3`：能在新情境中应用，或正确处理边界与反例。

## 安排检验

在回答当前问题后按以下规则触发：

- `questions_since_check >= 3`：必须检验；
- `questions_since_check == 2` 且学习者准备切换/结束、仍有明显误区，或主动表示“懂了”：立即检验；
- 学习者在任意时点说“懂了 / 明白了 / 会了”或要求检查理解：不把自我报告当证据，立即检验。

每次只给一个任务，并在任务后停止输出、等待作答。轮换使用：

- **复述**：要求不回看，用自己的话说明核心机制及条件；
- **边界**：给一个最小案例，要求判断概念是否适用并说明原因；
- **迁移**：给一个未讲过的新情境，要求应用概念并解释步骤。

不要同时给答案、提示、评分标准或第二道题。发出任务时将 `status` 设为 `checking`，并把 `pending_verification` 写成包含 `type`、`prompt`、`issued_at` 的对象；此时先不要清零问题计数。

## 评估检验

收到检验作答后：

1. 引用学习者答案中的具体证据，分别指出“已经体现的理解”和“仍需修正之处”，不要笼统表扬。
2. 按 `E0–E3` 赋值。只有 `E2` 或 `E3` 可将状态设为 `verified`；`E0` 或 `E1` 设为 `needs-review`。
3. 对关键错误给出简短纠正；需要重试时只给一个变式任务并停止。学习者明确跳过则保留原证据，不制造一次作答。
4. 完成一次实际评估后，将 `questions_since_check` 清零、清除 `pending_verification`、写入 `last_verified_at`。若发出重试，保留待检验状态直到重试结束。
5. 把发问权交还学习者，让其继续追问或选择下一个概念。

## 文件记录

每回答一个实质性问题，同一轮更新 `learning-state.json`：

- `questions_since_check += 1`，`total_questions += 1`；
- `status` 从 `seeded` 改为 `exploring`；
- `highest_question_depth` 只升不降；
- 仅在有直接证据时增删 `misconceptions`，不要从提问措辞臆测掌握。

同时向 `question-journal.md` **追加**一段，不覆盖旧内容：

```markdown
## <ISO 8601 时间> — <主题> / <概念>
- 类型：学习者问题 | 掌握检验
- 学习者输入：<原问题或检验作答>
- 回答要点 / 检验任务：<简要摘要>
- 问题深度：D0 | D1 | D2 | D3
- 掌握证据：未检验 | E0 | E1 | E2 | E3
- 前提或误区：无 | <具体内容>
```

普通问题的“掌握证据”必须写“未检验”，即使问题很深入。检验记录写实际证据等级和判断理由。所有写入完成后更新状态顶层 `updated_at`；写入失败时告知用户，不声称已经保存。

## L1 学习事件

向某个概念写入本轮第一个 L1 事件前，先调用 `patch_learner_profile` 建立或校正可读标签；无法确定概念是否已存在时可以安全地重复调用：

```yaml
concept_id: statistics.bayes.posterior-probability
concept_name: 后验概率
domain: statistics.bayes
```

不要在这一步传入 `mastery` 或 `mastery_delta`。它只负责把跨工作区语义 ID 映射到真实概念名称和领域；掌握度仍由后续检验证据决定。

回答实质性问题后调用 `record_learning_event`：

```yaml
event_type: concept_explained
context:
  concept_ids: [statistics.bayes.posterior-probability]
payload:
  mode: learner-question
  topic_id: statistics.bayes
  concept_id: statistics.bayes.posterior-probability
  concept: 后验概率
  question_depth: D1 | D2 | D3
derived_signals:
  mastery_delta: 0
  misconception_candidates: [<仅记录有证据的误区>]
```

解释、追问数量、问题深度以及学习者说“懂了”都不能改变 `mastery_delta`。

仅在学习者实际提交检验答案后记录 `exercise_attempt`：

```yaml
event_type: exercise_attempt
context:
  concept_ids: [statistics.bayes.posterior-probability]
payload:
  mode: verification
  topic_id: statistics.bayes
  concept_id: statistics.bayes.posterior-probability
  concept: 后验概率
  verification_type: teach-back | boundary | transfer
  evidence_level: E0 | E1 | E2 | E3
derived_signals:
  mastery_delta: <按下表取值>
  misconception_candidates: [<本次作答直接暴露的误区>]
```

使用一致的增量：

- 实际作答错误或无关（`E0`）：`-0.02`；
- 部分正确但有关键缺口（`E1`）：`0`；
- 正确复述并说明条件（`E2`）：`+0.03`；
- 成功迁移或处理边界（`E3`）：`+0.05`。

跳过或未回答检验时不要记录 `exercise_attempt`。若 `patch_learner_profile` 或 `record_learning_event` 不可用，仍维护工作区文件并明确说明哪些 L1 更新未同步。
