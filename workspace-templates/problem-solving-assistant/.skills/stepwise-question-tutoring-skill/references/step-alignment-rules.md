# 步骤对齐规则

本文档定义学生步骤与标准步骤的对齐规则，用于诊断学生答案中的错误。

## 对齐目标

将学生的解题步骤与标准解题步骤进行一一对应，识别出：
1. 哪些步骤是正确的
2. 哪些步骤有偏差
3. 第一处明显错误在哪里
4. 错误的类型和严重程度

## 归一化规则

在对齐之前，需要对学生步骤和标准步骤进行归一化处理，消除格式差异。

### 1. 空格处理
- 去除前后空格：`"  1/2 + 1/3  "` → `"1/2 + 1/3"`
- 统一运算符周围空格：`"1/2+1/3"` → `"1/2 + 1/3"`
- 去除多余空格：`"1/2  +  1/3"` → `"1/2 + 1/3"`

### 2. 符号标准化
- 乘号统一：`"×"`, `"*"`, `"·"` → `"×"`
- 除号统一：`"÷"`, `"/"` → `"÷"`
- 等号统一：`"="`, `"＝"` → `"="`
- 分数线统一：`"1/2"`, `"½"` → `"1/2"`

### 3. 数字格式化
- 小数点统一：`"0.5"`, `".5"` → `"0.5"`
- 分数化简：`"2/4"` → `"1/2"`（可选，取决于题目要求）
- 百分数统一：`"50%"`, `"0.5"` → `"50%"`（根据上下文）

### 4. 中文表述标准化
- 运算动词：`"加上"`, `"加"`, `"相加"` → `"加"`
- 结果表述：`"答案是"`, `"结果是"`, `"等于"`, `"="` → `"="`
- 步骤标记：`"第一步："`, `"1."`, `"①"` → 去除，只保留内容

### 5. 大小写统一
- 英文字母：`"X"`, `"x"` → `"x"`（变量名统一小写）
- 单位：`"M"`, `"m"` → `"m"`（米）

## 语义等价模式

某些不同的表述在语义上是等价的，对齐时应视为相同。

### 数学运算等价

| 学生表述 | 标准表述 | 等价原因 |
|---------|---------|---------|
| "通分" | "化为同分母" | 同一操作的不同说法 |
| "找公倍数" | "找最小公倍数" | 简化表述 |
| "分子相加" | "分子加分子" | 同义表述 |
| "约分" | "化简" | 同一操作 |
| "移项" | "把...移到等号另一边" | 操作描述 |

### 物理概念等价

| 学生表述 | 标准表述 | 等价原因 |
|---------|---------|---------|
| "速度×时间" | "路程=速度×时间" | 省略了等号左边 |
| "F=ma" | "力=质量×加速度" | 公式与文字等价 |
| "串联" | "串联连接" | 简化表述 |

### 化学表述等价

| 学生表述 | 标准表述 | 等价原因 |
|---------|---------|---------|
| "H₂O" | "水" | 化学式与名称等价 |
| "点燃" | "加热" | 反应条件简化 |
| "生成" | "产生" | 同义词 |

## 对齐算法

### 1. 直接匹配
如果归一化后的学生步骤与标准步骤完全相同，则直接对齐。

```python
def direct_match(student_step: str, standard_step: str) -> bool:
    return normalize(student_step) == normalize(standard_step)
```

### 2. 语义等价匹配
如果学生步骤与标准步骤在语义等价表中有对应关系，则视为匹配。

```python
def semantic_match(student_step: str, standard_step: str) -> bool:
    student_normalized = normalize(student_step)
    standard_normalized = normalize(standard_step)
    
    # 检查是否在等价表中
    for equiv_pair in EQUIVALENCE_TABLE:
        if (student_normalized in equiv_pair and 
            standard_normalized in equiv_pair):
            return True
    return False
```

### 3. 关键词匹配
提取学生步骤和标准步骤的关键词，计算重叠度。

```python
def keyword_match(student_step: str, standard_step: str, threshold: float = 0.6) -> bool:
    student_keywords = extract_keywords(student_step)
    standard_keywords = extract_keywords(standard_step)
    
    overlap = len(student_keywords & standard_keywords)
    total = len(standard_keywords)
    
    return (overlap / total) >= threshold if total > 0 else False
```

**关键词提取规则：**
- 数学：运算符、数字、变量名、函数名
- 物理：物理量、单位、公式符号
- 化学：元素符号、化学式、反应条件

### 4. 模糊匹配（最后手段）
使用编辑距离或相似度算法进行模糊匹配。

```python
def fuzzy_match(student_step: str, standard_step: str, threshold: float = 0.7) -> bool:
    similarity = calculate_similarity(student_step, standard_step)
    return similarity >= threshold
```

## 对齐流程

### 步骤 1：预处理
```
学生步骤列表 → 归一化 → 归一化学生步骤列表
标准步骤列表 → 归一化 → 归一化标准步骤列表
```

### 步骤 2：逐一对齐
```
for i, standard_step in enumerate(standard_steps):
    matched = False
    for j, student_step in enumerate(student_steps):
        if already_matched[j]:
            continue
        
        if direct_match(student_step, standard_step):
            align(i, j, match_type="direct")
            matched = True
            break
        elif semantic_match(student_step, standard_step):
            align(i, j, match_type="semantic")
            matched = True
            break
        elif keyword_match(student_step, standard_step):
            align(i, j, match_type="keyword")
            matched = True
            break
    
    if not matched:
        # 标准步骤未找到对应的学生步骤
        mark_as_missing(i)
```

### 步骤 3：识别多余步骤
```
for j, student_step in enumerate(student_steps):
    if not already_matched[j]:
        mark_as_extra(j)
```

### 步骤 4：判断正确性
```
for alignment in alignments:
    if alignment.match_type == "direct":
        alignment.is_correct = True
    elif alignment.match_type == "semantic":
        alignment.is_correct = True
    elif alignment.match_type == "keyword":
        # 需要进一步检查数值是否正确
        alignment.is_correct = check_numerical_correctness(alignment)
    else:
        alignment.is_correct = False
```

## 第一错步检测逻辑

### 定义
第一错步是指学生首次偏离标准步骤的位置，包括：
1. 步骤内容错误（方法错、计算错）
2. 步骤缺失（跳过必要步骤）
3. 步骤多余（增加不必要步骤）

### 检测算法

```python
def find_first_error(alignments: List[Alignment]) -> Optional[FirstError]:
    for i, alignment in enumerate(alignments):
        # 情况1：步骤内容错误
        if alignment.is_matched and not alignment.is_correct:
            return FirstError(
                step_index=i,
                error_type="content_error",
                student_step=alignment.student_step,
                standard_step=alignment.standard_step
            )
        
        # 情况2：步骤缺失
        if not alignment.is_matched:
            return FirstError(
                step_index=i,
                error_type="missing_step",
                student_step=None,
                standard_step=alignment.standard_step
            )
    
    # 情况3：步骤多余（在所有标准步骤之后）
    extra_steps = [s for s in student_steps if s not in matched_student_steps]
    if extra_steps:
        return FirstError(
            step_index=len(alignments),
            error_type="extra_step",
            student_step=extra_steps[0],
            standard_step=None
        )
    
    return None  # 没有错误
```

### 错误类型分类

| 错误类型 | 描述 | 严重程度 | 示例 |
|---------|------|---------|------|
| `content_error` | 步骤内容错误 | 中-高 | 学生："分母相加"，标准："通分" |
| `missing_step` | 缺少必要步骤 | 中-高 | 学生跳过了"找最小公倍数"这一步 |
| `extra_step` | 多余步骤 | 低-中 | 学生多写了一步不必要的计算 |
| `calculation_error` | 计算结果错误 | 低-中 | 方法对但算错了：3+2=6 |
| `order_error` | 步骤顺序错误 | 中 | 先相加后通分（应该先通分后相加） |

## 偏离类型定义

### 1. 概念性错误 (`conceptual_error`)
- 对基本概念理解错误
- 示例：分母直接相加、面积周长混淆
- 严重程度：高

### 2. 方法性错误 (`method_error`)
- 选择了错误的解题方法
- 示例：用错公式、策略不当
- 严重程度：高

### 3. 计算性错误 (`calculation_error`)
- 计算过程出错，但方法正确
- 示例：7+8=16、6×7=48
- 严重程度：低

### 4. 步骤性错误 (`step_error`)
- 步骤缺失、多余或顺序错误
- 示例：跳过中间步骤、步骤颠倒
- 严重程度：中

### 5. 符号性错误 (`symbol_error`)
- 符号遗漏或错用
- 示例：忘记写单位、正负号错误
- 严重程度：低

## 对齐结果示例

### 示例 1：分数加法错误

**题目：** 计算 1/2 + 1/3 = ?

**学生步骤：**
```
1. 分母相加：2+3=5
2. 分子相加：1+1=2
3. 答案：2/5
```

**标准步骤：**
```
1. 找最小公倍数：2和3的最小公倍数是6
2. 通分：1/2=3/6，1/3=2/6
3. 分子相加：3+2=5
4. 答案：5/6
```

**对齐结果：**
```json
{
  "alignedSteps": [
    {
      "stepIndex": 0,
      "studentStep": "分母相加：2+3=5",
      "standardStep": "找最小公倍数：2和3的最小公倍数是6",
      "isCorrect": false,
      "matchType": "none",
      "divergenceType": "conceptual_error"
    },
    {
      "stepIndex": 1,
      "studentStep": "分子相加：1+1=2",
      "standardStep": "通分：1/2=3/6，1/3=2/6",
      "isCorrect": false,
      "matchType": "none",
      "divergenceType": "method_error"
    },
    {
      "stepIndex": 2,
      "studentStep": "答案：2/5",
      "standardStep": "分子相加：3+2=5",
      "isCorrect": false,
      "matchType": "semantic",
      "divergenceType": "calculation_error"
    }
  ],
  "firstError": {
    "stepIndex": 0,
    "studentStep": "分母相加：2+3=5",
    "correctStep": "找最小公倍数6，然后通分",
    "errorType": "conceptual_misunderstanding",
    "severity": "critical"
  }
}
```

### 示例 2：步骤跳跃

**题目：** 解方程 2x + 3 = 7

**学生步骤：**
```
1. x = 2
```

**标准步骤：**
```
1. 移项：2x = 7 - 3
2. 计算：2x = 4
3. 两边同除以2：x = 2
```

**对齐结果：**
```json
{
  "alignedSteps": [
    {
      "stepIndex": 0,
      "studentStep": null,
      "standardStep": "移项：2x = 7 - 3",
      "isCorrect": false,
      "matchType": "none",
      "divergenceType": "missing_step"
    },
    {
      "stepIndex": 1,
      "studentStep": null,
      "standardStep": "计算：2x = 4",
      "isCorrect": false,
      "matchType": "none",
      "divergenceType": "missing_step"
    },
    {
      "stepIndex": 2,
      "studentStep": "x = 2",
      "standardStep": "两边同除以2：x = 2",
      "isCorrect": true,
      "matchType": "semantic",
      "divergenceType": "none"
    }
  ],
  "firstError": {
    "stepIndex": 0,
    "studentStep": null,
    "correctStep": "移项：2x = 7 - 3",
    "errorType": "missing_step",
    "severity": "moderate"
  }
}
```

## 特殊情况处理

### 1. 学生步骤比标准步骤多
- 可能是学生写得更详细（好事）
- 也可能是走了弯路（需要指出更简洁的方法）

### 2. 学生步骤比标准步骤少
- 可能是跳步骤（需要补充）
- 也可能是学生用了更简洁的方法（需要验证正确性）

### 3. 学生步骤顺序与标准不同
- 如果逻辑正确，顺序不同也可以接受
- 如果顺序导致错误，需要指出

### 4. 多种正确解法
- 标准步骤只是一种参考
- 学生用其他正确方法也应认可
- 需要维护多套标准步骤模板

## 实施建议

1. **优先使用直接匹配和语义匹配**，这两种匹配准确度高
2. **关键词匹配需要设置合理的阈值**，避免误匹配
3. **模糊匹配作为最后手段**，且需要人工复核
4. **维护语义等价表**，不断补充新的等价模式
5. **记录对齐失败的案例**，用于改进算法
6. **考虑学科差异**，不同学科的对齐规则可能不同
