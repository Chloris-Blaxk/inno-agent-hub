---
name: paper-to-dialogue-video
category: 内容创作
subject: 跨学科
kind: 内容创作
description: Turn a research-paper PDF into a source-grounded Chinese two-host podcast with a checked dialogue script, distinct voices, synchronized subtitles, paper figures, and a warm vertical HTML animation. Use when the user asks for 论文播客、双人讲论文、论文音频、论文视频、小红书论文动画、带字幕配音的论文解读, or wants an academic PDF converted into a conversational audiovisual episode.
---

# Paper to Dialogue Video

Create a complete, inspectable episode rather than generating audio directly from an unchecked summary.

## Workflow

1. **Read the paper.** Extract metadata, research question, method, essential variables, main results, author-stated limitations, and figure/table locations. Render and inspect the PDF pages when layout or figures matter.
2. **Build an evidence sheet.** Record every publishable number and claim with a page, section, figure, or table anchor. Separate model results, empirical observations, author interpretations, and later criticism. Read [references/evidence-rules.md](references/evidence-rules.md).
3. **Plan the episode.** Default to a 3–6 minute Chinese dialogue. Give the host concrete beginner questions and the explainer direct technical answers. Read [references/dialogue-style.md](references/dialogue-style.md).
4. **Create `episode.json`.** Follow [references/episode-schema.md](references/episode-schema.md). Attach a source anchor, visual, and key point to every spoken segment.
5. **Audit before speech.** Check names, numbers, equations, causal wording, pronunciations, and whether each visual supports the current line. Do not synthesize an unverified draft.
6. **Synthesize and assemble.** Run:

   ```bash
   python3 scripts/build_episode.py \
     --episode /absolute/path/to/episode.json \
     --output /absolute/path/to/output-folder
   ```

   Prefer the free Edge neural backend for finished previews. Install it once with `python3 -m pip install edge-tts imageio-ffmpeg`, then run with `--tts edge`. It needs internet but no API key. Use `--max-scenes 4` for a short voice check before synthesizing the full episode. The `auto` mode chooses Edge when both commands are available, otherwise it falls back to macOS `say` and `afconvert`. Use `--no-audio` only when neither backend is available.
7. **Inspect the HTML.** Open `index.html`; check voice identity, subtitle timing, image crops, text wrapping, mobile layout, keyboard playback, and reduced-motion behavior. Read [references/visual-style.md](references/visual-style.md).
8. **Export the approved video.** After approving the HTML and voices, run:

   ```bash
   python3 scripts/export_video.py \
     --episode-folder /absolute/path/to/output-folder \
     --output /absolute/path/to/output-folder/podcast.mp4
   ```

   Export a 1080×1440 H.264 MP4 with the complete 3:4 card background, translucent subtitle glass, active-speaker badges, evidence anchors, and synchronized audio.
9. **Deliver the package.** Include `index.html`, `podcast.wav`, `podcast.mp4`, `subtitles.srt`, `timing.json`, `episode.json`, `双人讲稿.md`, and `source-map.md`.

## Non-negotiable quality rules

- Keep the explanation plain, reliable, and technically sufficient. Shorten repetition, not the causal chain.
- Avoid opening with “不是……而是……”, decorative metaphors, manufactured surprise, and excessive banter.
- Let the host surface likely beginner confusion; let the explainer answer before adding nuance.
- State when a result is simulated, correlational, qualitative, or causally identified.
- Never invent a quote, number, experiment, figure, or limitation.
- Use the finished Xiaohongshu card as the full 3:4 scene background by default. Preserve it completely and place only translucent character, subtitle, section, and source layers above it.
- Use original paper crops only when explicitly requested; keep source and license notes.
- Keep one speaker per segment. Split long sentences before TTS.
- Keep stable character voices: 小鲸 uses `zh-CN-YunxiNeural` at about `+8%` rate and `+2Hz` pitch; 小柚 uses `zh-CN-XiaoxiaoNeural` at about `-3%` rate and `-1Hz` pitch. Adjust dialogue phrasing before making large pitch changes.
- Generate a 3–6 scene voice check before a full episode. Listen for role identity, unnatural numbers, English terms, and repeated mechanical pauses.
- Audit English terms, author names, symbols, and polyphonic Chinese characters separately.

## Bundled resources

- `scripts/build_episode.py`: validate the episode, synthesize free Edge neural voices or local fallback voices, assemble WAV/SRT/timing, and render the HTML player.
- `scripts/export_video.py`: render the approved episode folder to a portable 3:4 H.264 MP4.
- `assets/player-template.html`: responsive vertical animated player.
- `assets/ocean-fruit-background.png`: default warm ocean-and-fruit background.
- `references/`: dialogue, evidence, schema, and visual rules loaded only when needed.
