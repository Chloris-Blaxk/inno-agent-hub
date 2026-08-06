# 输入输出模式定义

本文档定义拍题答疑辅导技能的请求/响应数据契约。

## 请求模式 (Request Modes)

### 1. 未作答提示模式 (`unanswered_hint`)

用于学生未作答或卡住时，提供分级提示。

```json
{
  "mode": "unanswered_hint",
  "subject": "数学",
  "grade": "五年级",
  "question": "计算：1/2 + 1/3 = ?",
  "questionImage": "base64_encoded_image_data...",  // 可选，拍照题目
  "hintLevel": 1,  // 1-4，提示级别
  "hintLevels": [1, 2, 3, 4],  // 可选，批量生成多个提示层级，测试/演示用
  "knowledgePointIds": ["math-g5-fraction-add"],  // 可选，已知知识点
  "requirements": "不要直接给答案，引导学生思考"
}
```

**字段说明：**
- `mode`: 固定值 `"unanswered_hint"`
- `subject`: 学科（数学、物理、化学等）
- `grade`: 年级（一年级～高三）
- `question`: 题目文本（如果有 `questionImage` 则可选）
- `questionImage`: 可选，题目图片的 base64 编码
- `hintLevel`: 提示级别 1-4
  - 1: 知识回忆（最轻度）
  - 2: 关键洞察
  - 3: 第一步
  - 4: 完整解析
- `hintLevels`: 可选，批量提示层级列表。正式产品流程建议逐级请求；该字段主要用于测试和演示。
- `knowledgePointIds`: 可选，已知的知识点 ID 列表
- `requirements`: 可选，额外要求

---

### 2. 诊断答案模式 (`diagnose_answer`)

用于学生已作答，需要诊断错误并给出补救建议。

**支持 5 种输入方式（按优先级排序）：**

#### 方式 1a：完全结构化输入（最高优先级）

```json
{
  "mode": "diagnose_answer",
  "subject": "数学",
  "grade": "五年级",
  "question": "计算：1/2 + 1/3 = ?",
  "studentAnswer": {
    "steps": [
      "分母相加：2+3=5",
      "分子相加：1+1=2"
    ],
    "finalAnswer": "2/5"
  },
  "knowledgePointIds": ["math-g5-fraction-add"],
  "requirements": "指出第一处错误并说明原因"
}
```

**适用场景：** 在线作业系统、API 集成、教师已整理好的数据

---

#### 方式 1b：手动输入连续文本（新增）

```json
{
  "mode": "diagnose_answer",
  "subject": "数学",
  "grade": "五年级",
  "question": "计算：1/2 + 1/3 = ?",
  "studentAnswer": {
    "answerText": "分母相加2+3=5 分子相加1+1=2 答案2/5"
  },
  "knowledgePointIds": ["math-g5-fraction-add"],
  "requirements": "从连续文本中解析学生步骤，并诊断错误"
}
```

**适用场景：** 用户手动输入学生的完整答案文本（从纸质作业抄录）

**处理方式：** 系统使用 LLM 自动解析 `answerText` 为结构化的 `steps` 和 `finalAnswer`

---

#### 方式 2：题目文本 + 答案图片

```json
{
  "mode": "diagnose_answer",
  "subject": "数学",
  "grade": "五年级",
  "question": "计算：1/2 + 1/3 = ?",
  "studentAnswer": {
    "workImage": "base64_encoded_answer_image..."
  },
  "knowledgePointIds": ["math-g5-fraction-add"],
  "requirements": "识别答案图片并诊断错误"
}
```

**适用场景：** 题目是打印的或已知的，只需要识别学生手写答案

**处理方式：** OCR 识别答案图片 → LLM 解析步骤

---

#### 方式 3：分别上传题目和答案图片

```json
{
  "mode": "diagnose_answer",
  "subject": "数学",
  "grade": "五年级",
  "questionImage": "base64_encoded_question_image...",
  "studentAnswer": {
    "workImage": "base64_encoded_answer_image..."
  },
  "knowledgePointIds": ["math-g5-fraction-add"],
  "requirements": "分别识别题目和答案图片，并诊断错误"
}
```

**适用场景：** 题目和答案在不同位置，用户分别拍照

**处理方式：** 两张图片分别 OCR 识别

---

#### 方式 4：一张完整作业图片（自动分离）

```json
{
  "mode": "diagnose_answer",
  "subject": "数学",
  "grade": "五年级",
  "combinedImage": "base64_encoded_full_homework_image...",
  "splitRatio": 0.4,
  "knowledgePointIds": ["math-g5-fraction-add"],
  "requirements": "从完整作业图片中自动分离题目和答案，并诊断错误"
}
```

**适用场景：** 拍摄整张作业纸，最方便的方式

**处理方式：** 图片区域分割（上 40% = 题目，下 60% = 答案）→ 分别 OCR 识别 → LLM 解析步骤

**降级策略：** 如果分割失败 → 整图 OCR → LLM 文本分离

---

**字段说明：**
- `mode`: 固定值 `"diagnose_answer"`
- `question`: 题目文本（可选，如果提供了 `questionImage` 或 `combinedImage`）
- `questionImage`: 可选，题目图片的 base64 编码
- `combinedImage`: 可选，完整作业图片的 base64 编码（包含题目和答案）
- `splitRatio`: 可选，分割比例（0.0-1.0），默认 0.4（题目占 40%）
- `studentAnswer`: 学生答案对象，支持以下字段：
  - `steps`: 学生的解题步骤数组（结构化输入）
  - `finalAnswer`: 学生的最终答案（结构化输入）
  - `answerText`: 学生答案的连续文本（手动输入）
  - `workImage`: 学生手写作业的照片（图片输入）
- `knowledgePointIds`: 可选，已知的知识点 ID 列表
- `requirements`: 可选，额外要求

---

### 3. 请求相似题模式 (`request_similar`)

用于推荐相似练习题，验证掌握度。

```json
{
  "mode": "request_similar",
  "subject": "数学",
  "grade": "五年级",
  "knowledgePointIds": ["math-g5-fraction-add"],
  "difficulty": 2,  // 1-5
  "count": 3,  // 推荐题目数量
  "excludeQuestionIds": ["seed-frac-a-001"]  // 可选，排除已做过的题
}
```

**字段说明：**
- `mode`: 固定值 `"request_similar"`
- `knowledgePointIds`: 知识点 ID 列表
- `difficulty`: 难度级别 1-5
- `count`: 推荐题目数量（默认 2-3 道）
- `excludeQuestionIds`: 可选，排除的题目 ID 列表

---

## 响应模式 (Response Schemas)

### 1. 提示阶梯响应 (Hint Ladder Response)

用于 `unanswered_hint` 模式的响应。

```json
{
  "mode": "unanswered_hint",
  "question": "计算：1/2 + 1/3 = ?",
  "knowledgePoints": [
    {
      "id": "math-g5-fraction-add",
      "name": "异分母分数加减法",
      "prerequisites": ["分数的意义", "通分"]
    }
  ],
  "hint": {
    "level": 1,
    "content": "这道题涉及异分母分数加法。你还记得当两个分数的分母不同时，应该怎么做吗？",
    "revealedInfo": ["知识点：异分母分数加法"],
    "nextLevelAvailable": true
  },
  "hints": [
    {
      "level": 1,
      "content": "这道题涉及异分母分数加法。你还记得当两个分数的分母不同时，应该怎么做吗？",
      "revealedInfo": ["知识点：异分母分数加法"],
      "nextLevelAvailable": true
    },
    {
      "level": 2,
      "content": "可以先想一想：两个分数单位不同，怎样把它们变成相同单位？",
      "revealedInfo": ["关键思路：通分"],
      "nextLevelAvailable": true
    }
  ],
  "similarQuestions": [
    {
      "questionId": "seed-frac-a-002",
      "stem": "计算：1/3 + 1/4 = ?",
      "difficulty": 2,
      "methodTag": "异分母先通分再加减"
    }
  ],
  "qualityReport": {
    "hintRestraint": "pass",  // pass/warn/fail
    "gradeAppropriate": "pass",
    "warnings": []
  }
}
```

**字段说明：**
- `hint`: 提示对象
  - `level`: 当前提示级别 1-4
  - `content`: 提示内容文本
  - `revealedInfo`: 该提示透露的信息列表
  - `nextLevelAvailable`: 是否还有下一级提示
- `hints`: 可选，批量提示数组。仅当请求中提供 `hintLevels` 且生成多个层级时返回；`hint` 始终保留为第一个层级，兼容旧调用。
- `similarQuestions`: 相似题推荐列表
- `qualityReport`: 质量检查报告

---

### 2. 诊断报告响应 (Diagnostic Report Response)

用于 `diagnose_answer` 模式的响应。

```json
{
  "mode": "diagnose_answer",
  "question": "计算：1/2 + 1/3 = ?",
  "studentAnswer": {
    "steps": ["分母相加：2+3=5", "分子相加：1+1=2", "答案：2/5"],
    "finalAnswer": "2/5"
  },
  "correctAnswer": "5/6",
  "isCorrect": false,
  "diagnosis": {
    "alignedSteps": [
      {
        "stepIndex": 0,
        "studentStep": "分母相加：2+3=5",
        "standardStep": "找最小公倍数：2和3的最小公倍数是6",
        "isCorrect": false,
        "divergenceType": "conceptual_error"
      },
      {
        "stepIndex": 1,
        "studentStep": "分子相加：1+1=2",
        "standardStep": "通分：1/2=3/6，1/3=2/6",
        "isCorrect": false,
        "divergenceType": "method_error"
      }
    ],
    "firstError": {
      "stepIndex": 0,
      "studentStep": "分母相加：2+3=5",
      "correctStep": "找最小公倍数6，然后通分",
      "errorType": "conceptual_misunderstanding",
      "severity": "critical"
    },
    "errorPattern": {
      "patternId": "err-denominator-add",
      "patternName": "分母直接相加",
      "frequency": "high",
      "rootCause": "没有理解分母表示分数单位，单位不同不能直接合并",
      "typicalSymptom": "把1/2+1/3算成2/5"
    },
    "remediation": "分母表示分数单位，单位不同不能直接合并。建议先复习'分数的意义'和'通分'两个知识点。可以用图示法理解为什么分母不能直接相加：1/2表示2份中的1份，1/3表示3份中的1份，它们的'份'大小不同，不能直接合并。"
  },
  "similarQuestions": [
    {
      "questionId": "seed-frac-a-003",
      "stem": "计算：1/4 + 1/6 = ?",
      "difficulty": 2,
      "methodTag": "异分母先通分再加减",
      "purpose": "巩固通分概念"
    }
  ],
  "qualityReport": {
    "errorEvidence": "pass",
    "remediationClarity": "pass",
    "gradeAppropriate": "pass",
    "warnings": []
  }
}
```

**字段说明：**
- `diagnosis`: 诊断对象
  - `alignedSteps`: 步骤对齐结果数组
  - `firstError`: 第一处错误详情
  - `errorPattern`: 匹配的错误模式
  - `remediation`: 补救建议文本

---

### 3. 相似题推荐响应 (Similar Questions Response)

用于 `request_similar` 模式的响应。

```json
{
  "mode": "request_similar",
  "knowledgePointIds": ["math-g5-fraction-add"],
  "difficulty": 2,
  "similarQuestions": [
    {
      "questionId": "seed-frac-a-004",
      "stem": "计算：2/3 + 1/4 = ?",
      "answer": "11/12",
      "difficulty": 2,
      "layer": "B",
      "methodTag": "异分母先通分再加减",
      "knowledgePointIds": ["math-g5-fraction-add"],
      "estimatedTimeSec": 180
    },
    {
      "questionId": "seed-frac-a-005",
      "stem": "小明吃了一个披萨的1/3，小红吃了1/4，他们一共吃了多少？",
      "answer": "7/12",
      "difficulty": 2,
      "layer": "B",
      "methodTag": "异分母先通分再加减",
      "knowledgePointIds": ["math-g5-fraction-add"],
      "estimatedTimeSec": 240
    }
  ],
  "qualityReport": {
    "knowledgePointMatch": "pass",
    "difficultyMatch": "pass",
    "diversity": "pass",
    "warnings": []
  }
}
```

---

## 数据类型定义

### 学生答案对象 (StudentAnswer)

```typescript
interface StudentAnswer {
  steps: string[];           // 学生的解题步骤
  finalAnswer: string;       // 最终答案
  workImage?: string;        // 可选，作业照片 base64
}
```

### 提示对象 (Hint)

```typescript
interface Hint {
  level: 1 | 2 | 3 | 4;      // 提示级别
  content: string;           // 提示内容
  revealedInfo: string[];    // 透露的信息列表
  nextLevelAvailable: boolean; // 是否有下一级
}
```

### 步骤对齐对象 (AlignedStep)

```typescript
interface AlignedStep {
  stepIndex: number;         // 步骤索引
  studentStep: string;       // 学生步骤
  standardStep: string;      // 标准步骤
  isCorrect: boolean;        // 是否正确
  divergenceType: string;    // 偏离类型
}
```

### 错误对象 (Error)

```typescript
interface FirstError {
  stepIndex: number;         // 错误步骤索引
  studentStep: string;       // 学生的错误步骤
  correctStep: string;       // 正确步骤
  errorType: string;         // 错误类型
  severity: "minor" | "moderate" | "critical"; // 严重程度
}
```

### 错误模式对象 (ErrorPattern)

```typescript
interface ErrorPattern {
  patternId: string;         // 错误模式 ID
  patternName: string;       // 错误模式名称
  frequency: "low" | "medium" | "high"; // 频率
  rootCause: string;         // 根本原因
  typicalSymptom: string;    // 典型症状
}
```

### 相似题对象 (SimilarQuestion)

```typescript
interface SimilarQuestion {
  questionId: string;        // 题目 ID
  stem: string;              // 题干
  answer?: string;           // 答案（可选）
  difficulty: number;        // 难度 1-5
  layer?: "A" | "B" | "C";   // 层级（可选）
  methodTag: string;         // 方法标签
  knowledgePointIds: string[]; // 知识点 ID 列表
  estimatedTimeSec?: number; // 预计用时（秒）
  purpose?: string;          // 推荐目的（可选）
}
```

---

## 质量报告字段

### 提示质量检查

- `hintRestraint`: 提示克制性（1-3级不得泄露答案）
  - `pass`: 通过
  - `warn`: 警告（轻微泄露）
  - `fail`: 失败（直接给出答案）

- `gradeAppropriate`: 年级适配性（语言符合年级水平）
  - `pass`: 通过
  - `warn`: 警告（个别术语超纲）
  - `fail`: 失败（大量超纲术语）

### 诊断质量检查

- `errorEvidence`: 错误证据（必须引用具体学生步骤）
  - `pass`: 通过
  - `fail`: 失败（未引用具体步骤）

- `remediationClarity`: 补救建议清晰度
  - `pass`: 通过
  - `warn`: 警告（建议过于笼统）
  - `fail`: 失败（无具体建议）

### 相似题质量检查

- `knowledgePointMatch`: 知识点匹配度
  - `pass`: 完全匹配
  - `warn`: 部分匹配
  - `fail`: 不匹配

- `difficultyMatch`: 难度匹配度（± 1 级）
  - `pass`: 在范围内
  - `warn`: 超出 1 级
  - `fail`: 超出 2 级以上

- `diversity`: 题目多样性（避免重复题型）
  - `pass`: 题型多样
  - `warn`: 题型单一
