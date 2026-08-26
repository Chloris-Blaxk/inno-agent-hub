# Episode JSON schema

Use UTF-8 JSON with this structure:

```json
{
  "meta": {
    "title": "Chinese episode title",
    "paper_title": "Original paper title",
    "authors": "Author list",
    "venue": "Venue and year",
    "doi": "DOI or source URL",
    "episode_label": "柚子论文电台 · 001",
    "background": "/absolute/path/to/background.png",
    "visual_overrides": {
      "/path/to/reused-card.png": {
        "path": "/path/to/original-paper-page.png",
        "crop": [70, 60, 690, 920]
      }
    },
    "use_visual_overrides": false
  },
  "speakers": {
    "host": {
      "name": "小鲸", "role": "提问", "emoji": "🐳",
      "edge_voice": "zh-CN-YunxiNeural", "edge_rate": "+8%", "edge_pitch": "+2Hz",
      "voice": "Tingting", "rate": 190
    },
    "expert": {
      "name": "小柚", "role": "讲解", "emoji": "🍊",
      "edge_voice": "zh-CN-XiaoxiaoNeural", "edge_rate": "-3%", "edge_pitch": "-1Hz",
      "voice": "Eddy (中文（中国大陆）)", "rate": 185
    }
  },
  "scenes": [
    {
      "id": "s01",
      "section": "研究问题",
      "speaker": "host",
      "text": "这篇论文具体研究了什么？",
      "source": "Abstract, page 1",
      "key_point": "连接数量与极化之间可能存在临界转变",
      "visual": "/absolute/path/to/image.png"
    }
  ]
}
```

Requirements:

- Use only `host` and `expert` speaker keys in version 1.
- Keep scene IDs unique and ordered.
- Require nonempty `text`, `source`, and `key_point` for every scene.
- Use absolute input asset paths; the builder copies them into the portable output folder.
- Add `visual_crop: [left, top, right, bottom]` to an individual scene when the source page needs cropping.
- Use `meta.visual_overrides` when many scenes reuse an existing visual key but the rendered episode should substitute an original paper crop. This avoids editing every dialogue scene.
- Use PNG or JPEG visuals. Reuse a visual across adjacent scenes when the explanation remains on the same evidence.
- Keep the background optional; the bundled ocean background is used when omitted.
- Keep `use_visual_overrides` false when scenes already point to finished Xiaohongshu cards. Set it true only when the user explicitly wants original paper crops instead.
- Use the bundled Edge defaults for the character identities: Yunxi for lively male host 小鲸 and Xiaoxiao for gentle, rigorous female explainer 小柚. Keep the macOS `voice` and `rate` fields as offline fallbacks.
