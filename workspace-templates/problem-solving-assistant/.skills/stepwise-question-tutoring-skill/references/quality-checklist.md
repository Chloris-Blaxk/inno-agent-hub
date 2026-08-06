# 质量检查清单

本文档定义拍题答疑辅导技能输出的质量验证标准。

## 验证维度

### 1. 提示克制性 (Hint Restraint)

**适用场景：** 未作答提示模式 (Level 1-3)

**验证目标：** 确保提示不直接泄露答案，保持适当的引导性。

#### Level 1 (知识回忆) 检查项

- ✅ **必须包含：**
  - 知识点名称
  - 引导性问题（"你还记得..."、"你对...掌握得怎么样"）
  - 前置知识提示

- ❌ **不得包含：**
  - 最终答案
  - 具体解题步骤
  - 关键操作名称（如"通分"、"找公倍数"）
  - 具体数值计算

**示例：**
```
✅ 通过："这道题涉及异分母分数加法。你还记得分数加法的规则吗？"
❌ 失败："这道题需要先通分，找到2和3的最小公倍数6。"（泄露了关键步骤）
```

#### Level 2 (关键洞察) 检查项

- ✅ **必须包含：**
  - 关键概念或障碍点
  - 方法方向提示
  - 引导性问题

- ❌ **不得包含：**
  - 最终答案
  - 第一步的具体做法
  - 具体数值计算结果

**示例：**
```
✅ 通过："解决这类问题的关键是什么？提示：注意两个分数的分母是否相同。"
❌ 失败："第一步应该找最小公倍数6。"（泄露了第一步）
```

#### Level 3 (第一步引导) 检查项

- ✅ **必须包含：**
  - 第一步的操作名称
  - 中间目标
  - 引导性任务

- ❌ **不得包含：**
  - 最终答案
  - 完整的计算过程
  - 后续步骤

**示例：**
```
✅ 通过："第一步应该通分。你能找到2和3的最小公倍数吗？"
❌ 失败："第一步通分：1/2=3/6，1/3=2/6，然后相加得5/6。"（泄露了完整过程）
```

#### Level 4 (完整解析) 检查项

- ✅ **必须包含：**
  - 完整的解题步骤
  - 每步的原因说明
  - 最终答案

**验证方法：**
```python
def validate_hint_restraint(hint: dict) -> str:
    level = hint["level"]
    content = hint["content"]
    
    if level in [1, 2, 3]:
        # 检查是否包含答案关键词
        answer_keywords = ["答案是", "结果是", "等于", "="]
        for keyword in answer_keywords:
            if keyword in content:
                return "fail"
        
        # Level 1 特殊检查
        if level == 1:
            method_keywords = ["通分", "公倍数", "第一步", "先"]
            for keyword in method_keywords:
                if keyword in content:
                    return "warn"
        
        # Level 2 特殊检查
        if level == 2:
            step_keywords = ["第一步", "应该", "需要做"]
            for keyword in step_keywords:
                if keyword in content:
                    return "warn"
    
    return "pass"
```

---

### 2. 错误证据性 (Error Evidence)

**适用场景：** 诊断答案模式

**验证目标：** 确保错误诊断必须引用具体的学生步骤，不能凭空判断。

#### 检查项

- ✅ **必须满足：**
  - `firstError.studentStep` 字段非空
  - 诊断报告中引用了具体的学生步骤内容
  - 错误位置明确（stepIndex）

- ❌ **不得出现：**
  - 模糊的错误描述（"你做错了"、"方法不对"）
  - 未引用具体步骤的诊断
  - 错误位置不明确

**示例：**
```json
✅ 通过：
{
  "firstError": {
    "stepIndex": 0,
    "studentStep": "分母相加：2+3=5",
    "correctStep": "找最小公倍数6，然后通分",
    "errorType": "conceptual_misunderstanding"
  }
}

❌ 失败：
{
  "firstError": {
    "stepIndex": 0,
    "studentStep": null,  // 未引用具体步骤
    "correctStep": "方法不对",
    "errorType": "unknown"
  }
}
```

**验证方法：**
```python
def validate_error_evidence(diagnosis: dict) -> str:
    first_error = diagnosis.get("firstError")
    
    if not first_error:
        return "fail"
    
    # 检查是否引用了具体学生步骤
    if not first_error.get("studentStep"):
        return "fail"
    
    # 检查错误位置是否明确
    if first_error.get("stepIndex") is None:
        return "fail"
    
    # 检查是否有具体的错误类型
    if not first_error.get("errorType") or first_error["errorType"] == "unknown":
        return "warn"
    
    return "pass"
```

---

### 3. 年级适配语言 (Grade-Appropriate Language)

**适用场景：** 所有模式

**验证目标：** 确保语言符合学生的年级水平，不使用超纲术语。

#### 年级术语表

**小学低年级（1-3年级）：**
- ✅ 允许：加、减、乘、除、份数、一样的、变成
- ❌ 禁止：公倍数、通分、单位换算、方程、函数

**小学高年级（4-6年级）：**
- ✅ 允许：公倍数、通分、分数单位、小数、百分数
- ❌ 禁止：代数式、方程、函数、导数、向量

**初中（7-9年级）：**
- ✅ 允许：方程、函数、几何证明、代数式、不等式
- ❌ 禁止：导数、极限、向量、矩阵、微积分

**高中（10-12年级）：**
- ✅ 允许：导数、向量、概率分布、三角函数、立体几何
- ❌ 禁止：大学数学术语（如拓扑、泛函、群论）

#### 检查项

- ✅ **必须满足：**
  - 使用年级允许的术语
  - 语言简洁清晰
  - 避免过于专业的表述

- ⚠️ **警告情况：**
  - 个别术语略超纲但可理解
  - 表述过于复杂

- ❌ **失败情况：**
  - 大量使用超纲术语
  - 学生完全无法理解

**验证方法：**
```python
def validate_grade_appropriate(content: str, grade: str) -> str:
    # 加载年级术语表
    forbidden_terms = load_forbidden_terms(grade)
    
    # 检查是否包含禁用术语
    violations = []
    for term in forbidden_terms:
        if term in content:
            violations.append(term)
    
    if len(violations) == 0:
        return "pass"
    elif len(violations) <= 2:
        return "warn"
    else:
        return "fail"
```

---

### 4. 补救建议清晰度 (Remediation Clarity)

**适用场景：** 诊断答案模式

**验证目标：** 确保补救建议具体可操作，不能过于笼统。

#### 检查项

- ✅ **优秀建议：**
  - 指出具体需要复习的知识点
  - 给出具体的学习方法或练习方向
  - 提供类比或图示建议

- ⚠️ **一般建议：**
  - 只指出知识点，未给出具体方法
  - 建议过于笼统

- ❌ **不合格建议：**
  - "多练习"、"再看看书"等无实质内容
  - 未指出具体知识点
  - 建议与错误无关

**示例：**
```
✅ 优秀："分母表示分数单位，单位不同不能直接合并。建议先复习'分数的意义'和'通分'两个知识点。可以用图示法理解为什么分母不能直接相加：1/2表示2份中的1份，1/3表示3份中的1份，它们的'份'大小不同，不能直接合并。"

⚠️ 一般："需要复习分数加法的知识。"

❌ 不合格："多做几道题就会了。"
```

**验证方法：**
```python
def validate_remediation_clarity(remediation: str) -> str:
    # 检查是否包含具体知识点
    has_knowledge_point = any(kp in remediation for kp in ["知识点", "概念", "定义", "规则"])
    
    # 检查是否包含具体方法
    has_method = any(method in remediation for method in ["复习", "练习", "图示", "类比", "对比"])
    
    # 检查长度（过短可能不够具体）
    is_detailed = len(remediation) >= 30
    
    if has_knowledge_point and has_method and is_detailed:
        return "pass"
    elif has_knowledge_point or has_method:
        return "warn"
    else:
        return "fail"
```

---

### 5. 相似题质量 (Similar Question Quality)

**适用场景：** 所有模式（推荐相似题时）

**验证目标：** 确保推荐的相似题匹配知识点和难度约束。

#### 知识点匹配度

- ✅ **完全匹配：** 相似题的知识点与原题完全相同
- ⚠️ **部分匹配：** 相似题的知识点与原题有重叠
- ❌ **不匹配：** 相似题的知识点与原题无关

**验证方法：**
```python
def validate_knowledge_point_match(original_kps: list, similar_kps: list) -> str:
    overlap = set(original_kps) & set(similar_kps)
    
    if overlap == set(original_kps):
        return "pass"
    elif len(overlap) > 0:
        return "warn"
    else:
        return "fail"
```

#### 难度匹配度

- ✅ **在范围内：** 相似题难度 = 原题难度 ± 1
- ⚠️ **略超范围：** 相似题难度 = 原题难度 ± 2
- ❌ **严重偏离：** 相似题难度偏离超过 2 级

**验证方法：**
```python
def validate_difficulty_match(original_difficulty: int, similar_difficulty: int) -> str:
    diff = abs(original_difficulty - similar_difficulty)
    
    if diff <= 1:
        return "pass"
    elif diff == 2:
        return "warn"
    else:
        return "fail"
```

#### 题目多样性

- ✅ **题型多样：** 推荐的题目包含不同题型（计算题、应用题等）
- ⚠️ **题型单一：** 推荐的题目都是同一题型
- ❌ **题目重复：** 推荐的题目与原题完全相同

**验证方法：**
```python
def validate_diversity(similar_questions: list) -> str:
    question_types = [q["questionType"] for q in similar_questions]
    unique_types = set(question_types)
    
    if len(unique_types) >= 2:
        return "pass"
    elif len(unique_types) == 1:
        return "warn"
    else:
        return "fail"
```

---

## 综合质量报告

每次输出都应包含质量报告，格式如下：

```json
{
  "qualityReport": {
    "hintRestraint": "pass",           // 提示克制性
    "errorEvidence": "pass",           // 错误证据性
    "remediationClarity": "pass",      // 补救建议清晰度
    "gradeAppropriate": "pass",        // 年级适配语言
    "knowledgePointMatch": "pass",     // 知识点匹配度
    "difficultyMatch": "pass",         // 难度匹配度
    "diversity": "pass",               // 题目多样性
    "overallStatus": "pass",           // 总体状态
    "warnings": [],                    // 警告列表
    "failures": []                     // 失败列表
  }
}
```

### 总体状态判定

- **pass**: 所有检查项都通过，或只有轻微警告
- **warn**: 有多个警告项，但无失败项
- **fail**: 有任何失败项

```python
def determine_overall_status(report: dict) -> str:
    failures = [k for k, v in report.items() if v == "fail"]
    warnings = [k for k, v in report.items() if v == "warn"]
    
    if len(failures) > 0:
        return "fail"
    elif len(warnings) > 2:
        return "warn"
    else:
        return "pass"
```

---

## 验证流程

### 1. 输入验证
- 检查必填字段是否完整
- 检查字段类型是否正确
- 检查数值范围是否合理

### 2. 输出验证
- 根据模式选择对应的验证规则
- 逐项检查质量标准
- 生成质量报告

### 3. 报告生成
- 汇总所有检查结果
- 列出警告和失败项
- 给出改进建议

### 4. 人工复核（可选）
- 对于失败的输出，建议人工复核
- 记录复核结果，用于改进验证规则

---

## 实施建议

1. **自动化验证优先**：大部分检查项可以自动化
2. **人工抽查补充**：定期抽查验证结果，确保准确性
3. **持续改进规则**：根据实际使用情况，不断完善验证规则
4. **记录失败案例**：建立失败案例库，用于训练和改进
5. **用户反馈闭环**：收集用户反馈，调整质量标准

---

## 附录：常见问题

### Q1: 如何判断提示是否泄露答案？
A: 检查提示中是否包含最终答案的关键信息。对于 Level 1-3，不应包含具体数值计算结果或最终答案。

### Q2: 如何处理多种正确解法？
A: 如果学生使用了与标准步骤不同但正确的方法，应该认可。验证时需要维护多套标准步骤模板。

### Q3: 如何平衡提示的引导性和克制性？
A: Level 1-2 应更克制，只提示方向；Level 3 可以更具体，但不给完整过程；Level 4 才给完整解析。

### Q4: 相似题推荐数量多少合适？
A: 建议 2-3 道。太少不足以验证掌握度，太多会增加学生负担。

### Q5: 如何处理跨学科题目？
A: 识别主要学科，使用该学科的验证规则。如果涉及多学科，需要综合考虑各学科的术语表。
