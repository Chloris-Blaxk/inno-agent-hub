# 配图生成工作流

本工作流对应 `visualSlots`。默认先生成可编辑占位和提示词；只有用户明确需要图片，或课件必须依赖实验现象/实物/场景图时，才生成位图素材。

## 决策顺序

1. `editable_diagram`、`board_model`、`step_flow`：优先用 HTML/PPTX 可编辑形状，不生成位图。
2. `situation_image`、`experiment_visual`、`historical_scene`、`object_photo`：可以生成或检索位图。
3. `practice_grid`、`exit_ticket`：不生成图片，保持题目可编辑。

## 生成前检查

- 必须使用 `visualSlots[].ratio`。
- 图片里不烘焙标题、公式、步骤、页码、logo 和长文字。
- 需要标签时在 HTML/PPTX 文本框中叠加。
- 每张图只服务一个课堂动作：情境、证据、现象、作品、实物或过程。

## Prompt 模板

```text
{ratio} classroom teaching visual for {topic};
single clear subject; projection-friendly contrast;
clean editable composition; no title, no footer, no logo;
leave space for editable labels outside the image;
style follows {stylePreset}; suitable for {grade} {subject}.
```

## 回写字段

生成后更新对应 slot：

```json
{
  "assetStatus": "generated",
  "assetPath": "assets/generated/s05-concept-diagram.png",
  "source": "imagegen",
  "prompt": "..."
}
```

当前原型不强制生成图片；没有真实素材时保留 `assetStatus: "placeholder"`，并让 PPTX 导出保持可编辑占位框。
