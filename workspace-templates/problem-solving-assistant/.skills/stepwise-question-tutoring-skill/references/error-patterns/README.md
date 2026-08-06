# 错误模式库索引

本文件夹包含各学科的错误模式库，用于诊断学生作答中的常见错误。

## 文件列表

### 核心学科（完全适配 ⭐⭐⭐⭐⭐）
- [error-patterns-math.json](error-patterns-math.json) - **数学学科错误模式库**（待创建）
  - 计算错误、概念理解错误、应用题建模错误

### 高度适配学科（⭐⭐⭐⭐）
- [error-patterns-physics.json](error-patterns-physics.json) - **物理学科错误模式库**
  - 受力分析、单位量纲、公式误用、方向正负号
  
- [error-patterns-chemistry.json](error-patterns-chemistry.json) - **化学学科错误模式库**
  - 化学方程式、化学计量、化合价与化学键
  
- [error-patterns-ai.json](error-patterns-ai.json) - **人工智能教育学科错误模式库**
  - 数据泄露、过拟合、模型选择、评估指标、算法理解

### 部分适配学科（⭐⭐⭐）
- [error-patterns-english.json](error-patterns-english.json) - **英语学科错误模式库**（客观题）
  - 语法错误（时态、主谓一致、非谓语）、词汇选择、句子结构
  
- [error-patterns-biology.json](error-patterns-biology.json) - **生物学科错误模式库**（计算与推理题）
  - 遗传计算、实验步骤、概念推理
  
- [error-patterns-it.json](error-patterns-it.json) - **信息技术学科错误模式库**（编程题）
  - 编程逻辑、算法理解、语法错误

### 少量适配学科（⭐⭐）
- [error-patterns-chinese.json](error-patterns-chinese.json) - **语文学科错误模式库**（限定题型）
  - 文言文翻译、病句修改
  
- [error-patterns-geography.json](error-patterns-geography.json) - **地理学科错误模式库**（计算题）
  - 时区时差、比例尺
  
- [error-patterns-history.json](error-patterns-history.json) - **历史学科错误模式库**（材料分析）
  - 要点提取、过度解读、归纳概括

### 极少适用学科（⭐）
- [error-patterns-ethics.json](error-patterns-ethics.json) - **道德与法治学科错误模式库**（概念题）
  - 概念辨析、概念范围
  
- [error-patterns-labor.json](error-patterns-labor.json) - **劳动教育学科错误模式库**（理论题）
  - 安全知识、劳动理论

## 错误模式库结构

每个错误模式库包含以下结构：

```json
{
  "version": "1.0",
  "description": "学科名称错误模式库",
  "errorCategories": [
    {
      "categoryId": "唯一标识",
      "categoryName": "错误类别名称",
      "description": "类别描述",
      "patterns": [
        {
          "id": "错误模式唯一ID",
          "name": "错误模式名称",
          "knowledgePointIds": ["相关知识点ID"],
          "symptom": "症状描述",
          "likelyCause": "可能原因",
          "diagnosisSignals": ["诊断信号列表"],
          "hintTemplate": "提示模板",
          "remediationSteps": ["补救步骤"]
        }
      ]
    }
  ]
}
```

## 使用说明

1. **智能体调用方式**：在 `SKILL.md` 中通过 `references/error-patterns/{学科}.json` 引用
2. **诊断流程**：
   - 根据学科加载对应错误模式库
   - 匹配学生错误与错误模式
   - 使用 `hintTemplate` 和 `remediationSteps` 生成反馈
3. **扩展方式**：
   - 新增学科：创建 `error-patterns-{subject}.json`
   - 新增错误类型：在 `errorCategories` 中添加
   - 新增错误模式：在对应类别的 `patterns` 中添加

## 适用范围说明

- **完全适配**：所有题型都适用步骤诊断
- **高度适配**：大部分题型适用，需补充学科特定错误
- **部分适配**：仅客观题、计算题、推理题适用
- **少量适配**：仅特定题型适用（如翻译、改错、计算）
- **极少适用**：仅概念辨析等极少题型可用

不适用的题型包括：主观开放题（作文、论述）、技能型题目（需视频/音频分析）、综合实践活动等。
