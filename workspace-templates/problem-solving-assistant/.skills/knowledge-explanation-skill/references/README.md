# References

本目录是 `knowledge-explanation-skill` 的流程、风格和质检规则源。当前默认没有可用知识库、题库、教材库或学生画像；Claude Code 触发 Skill 后主要依赖用户输入、对话上下文和 AI 的通用学科知识，再结合本目录规则判断知识类型、学生状态、语气和教学行为。

## 核心文件

- `knowledge-graph.json`：可选模拟资料；未来有知识库时可用于标准知识点定位、前置关系和后续关系。
- `knowledge-details.json`：可选模拟资料；未来有详解库时可用于分层目标、讲解抓手、例题、易错点和检验题。
- `teaching-style-guide.md`：讲解语言风格与教学策略指南，辅助判断语气、密度和策略。
- `style-layer-cards.md`：风格层与风格卡规范，负责用户指定风格时的语气选项和安全边界。
- `knowledge-explanation-process-design.md`：引用版知识点讲解过程设计说明，定义知识点讲解的本体要求、理论依据和综合流程。
- `skill-design-doc-v0.2.md`：当前原型的研发思路与闭环设计说明。
- `current-skill-flow.md`：当前 Skill 的流程总览，说明每轮入口检查、知识类型判断、教学动作、风格层和质量边界。

## 运行契约

- `input-output-schema.md`：自然语言交互输入输出约定。
- `workflow-routing.md`：学生状态、语气和教学行为判断规则。
- `quality-checklist.md`：结构、来源、风格合规和教学闭环检查。
- `classic-example-index.md`：典型例题选择原则和来源约束。
- `misconception-notes.md`：易错点写法和修复建议模板。
- `retrieval-fallback-policy.md`：命中失败或数据缺失时的保守处理策略。

## 当前状态

- 运行方式：Claude Code 直接基于对话、AI 通用学科知识和本目录规则生成答案。
- 确定性渲染脚本：已移除。
- 主数据源：当前无外部知识库；用户输入和 AI 通用学科知识是默认内容依据。
- 可选增强：`knowledge-graph.json` + `knowledge-details.json` 仅作为模拟资料或未来知识库接入位置。
- 表达控制：`teaching-style-guide.md` + `style-layer-cards.md`

## 维护原则

- 若后续补充更完整题库或术语词典，应优先扩充 `knowledge-details.json` 和 `knowledge-graph.json`。
- 无知识库运行时，不得声称已检索知识图谱、题库、教材库或课标；生成微例不能伪装成真实来源。
- 风格层选项应收敛到 `style-layer-cards.md`；通用表达规则、分层和质检规则继续收敛到 `teaching-style-guide.md`、`workflow-routing.md` 和 `quality-checklist.md`。
- 不新增运行时确定性讲解脚本；如确需工具脚本，只能用于离线检查资料完整性。
- 新增逻辑必须优先满足“实现功能时越简单越好”。
