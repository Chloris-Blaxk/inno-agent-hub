# Assets

本目录放置提示词模板和输出版式素材。

| 文件 / 目录 | 用途 |
|------|------|
| `prompts/review_report_prompt.md` | 课堂点评的 LLM 系统提示词（Agent 角色、规则、输出结构） |
| `prompts/lesson_rewrite_prompt.md` | 教案重构的 LLM 系统提示词（要求先查核心素养映射再写目标） |
| `prompts/teacher_transcript_prompt.md` | 基于优化教案生成教师上课逐字稿的 LLM 系统提示词 |
| `rubric/rubric-map.json` | 学科评价量规索引；按学科别名匹配具体公开课评价量规，未命中时回退到通用量规 |
| `rubric/*.md` | 统一格式的学科公开课评价量规，均为定性评价量规 |
| `output-templates/report_template.md` | 课堂点评报告 Markdown 输出模板 |
| `output-templates/lesson_plan_template.md` | 优化版公开课教案 Markdown 输出模板（核心素养导向目标） |
| `output-templates/teacher_transcript_template.md` | 教师上课逐字稿 Markdown 输出模板 |
