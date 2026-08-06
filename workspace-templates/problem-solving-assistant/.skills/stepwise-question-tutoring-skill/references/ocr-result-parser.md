# OCR 结果解析规则

## 输入格式
OCR API 返回 JSON：
```json
{
  "result": "原始文本（题目+学生作答+参考答案混合）",
  "status": "success"
}
```

## 解析目标
从 `result` 字符串中提取三个字段：
1. **question_text**：题目正文（包括选项）
2. **student_answer**：学生的推理过程和作答（若有）
3. **reference_solution**：参考答案或标准解析（若有）

---

## 解析逻辑

### 步骤 1：定位分隔标志
按以下优先级查找分隔符：

| 标志词 | 含义 | 正则匹配 |
|--------|------|----------|
| `解：`、`答：`、`解答：` | 学生作答开始 | `r'(解|答|解答)[:：]'` |
| `∵`、`∴`、`∴` | 数学推理符号（学生作答） | `r'[∵∴]'` |
| `【答案】`、`答案：`、`正确答案：` | 参考答案开始 | `r'(【答案】|答案[:：]|正确答案[:：])'` |
| `解析：`、`【解析】` | 参考解析开始 | `r'(解析[:：]|【解析】)'` |

### 步骤 2：三段切分
```python
import re

def parse_ocr_result(ocr_text: str) -> dict:
    # 找到第一个"学生作答"标志
    student_match = re.search(r'(解|答|解答)[:：]|[∵∴]', ocr_text)
    
    # 找到第一个"参考答案"标志
    reference_match = re.search(r'(【答案】|答案[:：]|正确答案[:：]|解析[:：]|【解析】)', ocr_text)
    
    if student_match and reference_match:
        # 三段式：题目 | 学生作答 | 参考答案
        question = ocr_text[:student_match.start()].strip()
        student_answer = ocr_text[student_match.start():reference_match.start()].strip()
        reference = ocr_text[reference_match.start():].strip()
    elif student_match:
        # 两段式：题目 | 学生作答
        question = ocr_text[:student_match.start()].strip()
        student_answer = ocr_text[student_match.start():].strip()
        reference = None
    elif reference_match:
        # 两段式：题目 | 参考答案
        question = ocr_text[:reference_match.start()].strip()
        student_answer = None
        reference = ocr_text[reference_match.start():].strip()
    else:
        # 纯题目
        question = ocr_text.strip()
        student_answer = None
        reference = None
    
    return {
        "question_text": question,
        "student_answer": student_answer,
        "reference_solution": reference
    }
```

### 步骤 3：清洗文本
- 移除题号前缀（`1.`、`(1)`、`【1】` 等）
- 保留所有 LaTeX 公式（`$...$`、`$$...$$`）
- 保留推理符号（`∵`、`∴`、`→`、`⇒` 等）

---

## 示例

### 示例 1：完整三段式

**OCR 输入**：
```
1. 已知直线$y = mx + n$，其中$m,n$是常数，且满足$mn<0$，那么该直线必经过？
A. 第二、三象限  B. 第一、四象限  C. 第一、二象限  D. 第二、四象限

解：∵ $mn<0$ ∴ $m$和$n$异号
∴ 当 $m>0$，$n<0$时，$y = mx + n$ 经过一、三、四象限；
当 $m<0$，$n>0$时，$y = mx + n$ 经过一、二、四象限；
综上所述，该直线必经过一、四象限。

【答案】B
```

**解析输出**：
```json
{
  "question_text": "已知直线$y = mx + n$，其中$m,n$是常数，且满足$mn<0$，那么该直线必经过？\nA. 第二、三象限  B. 第一、四象限  C. 第一、二象限  D. 第二、四象限",
  "student_answer": "解：∵ $mn<0$ ∴ $m$和$n$异号\n∴ 当 $m>0$，$n<0$时，$y = mx + n$ 经过一、三、四象限；\n当 $m<0$，$n>0$时，$y = mx + n$ 经过一、二、四象限；\n综上所述，该直线必经过一、四象限。",
  "reference_solution": "【答案】B"
}
```

### 示例 2：仅题目（学生未作答）

**OCR 输入**：
```
计算：$\frac{2}{3} + \frac{1}{4} = $ ______
```

**解析输出**：
```json
{
  "question_text": "计算：$\\frac{2}{3} + \\frac{1}{4} = $ ______",
  "student_answer": null,
  "reference_solution": null
}
```

### 示例 3：题目 + 学生作答（无参考答案）

**OCR 输入**：
```
计算：$\frac{1}{2} + \frac{1}{3} = $ ______

解：分母相加2+3=5，分子相加1+1=2，答案2/5
```

**解析输出**：
```json
{
  "question_text": "计算：$\\frac{1}{2} + \\frac{1}{3} = $ ______",
  "student_answer": "解：分母相加2+3=5，分子相加1+1=2，答案2/5",
  "reference_solution": null
}
```

---

## ⚠️ 关键原则
1. **保留学生作答原文**：不改写、不总结、不纠正错别字
2. **优先识别学生作答**：数学符号（`∵`、`∴`）出现即视为学生推理
3. **题目和学生作答的分界线**：第一个"解："或数学推理符号
4. **当无法明确分割时**：优先保证题目完整性，将模糊部分归入学生作答

---

## 边界情况处理

### 情况 1：多个"解："标志
```
1. 题目文本……

解：学生作答……

正确解法：……
```
**策略**：第一个"解："作为学生作答起点，"正确解法："作为参考答案起点

### 情况 2：只有推理符号，无"解："
```
1. 题目文本……

∵ 条件A
∴ 结论B
```
**策略**：第一个 `∵` 作为学生作答起点

### 情况 3：学生作答和参考答案混在一起
```
1. 题目文本……

学生答案：B（错误）  正确答案：A
```
**策略**：
- 如果能明确识别"学生答案"和"正确答案"标志，分别提取
- 如果无法区分，将整段归入 `student_answer`，在后续诊断中由 LLM 进一步解析

### 情况 4：OCR 识别错误导致分隔符错位
```
1. 题目文本……解方程……（"解"是题目的一部分，不是"解："）

答案：x=3
```
**策略**：
- 检查"解"后是否紧跟冒号或换行
- 如果"解"是题目内容的一部分（如"解方程"、"解不等式"），不视为分隔符
- 正则匹配时使用边界检测：`r'解[:：]\s'` 而非 `r'解'`
