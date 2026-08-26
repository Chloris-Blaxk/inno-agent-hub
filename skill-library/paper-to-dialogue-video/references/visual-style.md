# Visual style

## Direction

Use a warm “seaside paper radio” identity: show one finished Xiaohongshu card as the full stage background, with two small character anchors floating above it. Let motion explain speaker changes and evidence progression.

## Tokens

- Deep tide: `#174A4B`
- Ocean teal: `#2F7E80`
- Sea foam: `#DDF4EE`
- Warm paper: `#FFF8E8`
- Coral emphasis: `#F49F8E`
- Citrus yellow: `#F5C96A`
- Ink: `#203738`

Use `Yuanti SC` or `STYuanti-SC` for restrained display text, `PingFang SC` for body copy, and `Menlo` for source labels and timings. Do not fetch remote fonts.

## Layout

- Default to the Xiaohongshu card's native 3:4 stage. Use 9:16 only when the source cards were intentionally designed for that ratio.
- Use the finished Xiaohongshu card—not its embedded paper screenshot—as the full stage background. Never replace it with a paper crop unless `use_visual_overrides` is explicitly true.
- Preserve the complete card. Match the stage ratio to the card instead of cropping or nesting it inside another frame.
- Keep only the episode label, section, play button, speakers, subtitles, and source anchor above the card. Do not repeat a large episode headline when the card already carries its own title.
- Keep subtitles and speakers together in a stable sea-glass overlay: visibly translucent, lightly blurred, and limited to two or three subtitle lines.
- Place the host and explainer on opposite sides; highlight only the active speaker.
- Provide source anchors inside the stage, not only in a separate document.
- Omit a progress bar by default. Keep only an unobtrusive play/pause control because browsers require a user gesture to start audio.

## Motion

- Use one signature movement: a tide line flows toward the active speaker.
- Crossfade evidence cards; use subtle vertical movement under 20 px.
- Pulse the active avatar once at the start of a segment.
- Avoid continuous bobbing, confetti, spinning icons, and unrelated particles.
- Respect `prefers-reduced-motion`.

## Interaction and QA

- Support play/pause, seeking, previous/next scene, Space, and arrow keys.
- Show current time and total duration.
- Keep visible keyboard focus and usable contrast.
- Verify at desktop and narrow mobile widths.
- Ensure local relative assets work without a server.
