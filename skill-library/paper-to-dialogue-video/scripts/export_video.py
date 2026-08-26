#!/usr/bin/env python3
"""Render a paper-podcast episode folder to a portable H.264 MP4."""

import argparse
import json
import os
import shutil
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


def find_font(bold=False):
    env_name = "PAPER2SHARE_FONT_BOLD" if bold else "PAPER2SHARE_FONT_REGULAR"
    candidates = [
        os.environ.get(env_name),
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError(
        f"No CJK font found. Set {env_name} to a Chinese TrueType/OpenType font path."
    )


FONT_REGULAR = find_font(False)
FONT_BOLD = find_font(True)


def font(path, size):
    return ImageFont.truetype(str(path), size=size)


def wrap_text(draw, text, text_font, max_width):
    lines, current = [], ""
    for char in text:
        candidate = current + char
        if current and draw.textbbox((0, 0), candidate, font=text_font)[2] > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def render_frame(scene, episode, index, total, target, width=1080, height=1440):
    source = Path(scene["visual"])
    base = Image.open(source).convert("RGB")
    base = ImageOps.fit(base, (width, height), method=Image.Resampling.LANCZOS)
    base = base.convert("RGBA")

    overlay_top = 1000
    blurred = base.crop((0, overlay_top, width, height)).filter(ImageFilter.GaussianBlur(10))
    base.paste(blurred, (0, overlay_top), Image.new("L", blurred.size, 82))

    glass = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glass_px = glass.load()
    for y in range(overlay_top, height):
        t = (y - overlay_top) / max(1, height - overlay_top - 1)
        alpha = round(64 + 76 * t)
        for x in range(width):
            glass_px[x, y] = (8, 44, 45, alpha)
    base = Image.alpha_composite(base, glass)
    draw = ImageDraw.Draw(base)

    utility = font(FONT_BOLD, 22)
    small = font(FONT_REGULAR, 19)
    role_font = font(FONT_REGULAR, 18)
    name_font = font(FONT_BOLD, 27)
    badge_font = font(FONT_BOLD, 36)
    label_font = font(FONT_BOLD, 23)

    rounded(draw, (56, 42, 1024, 104), 31, (18, 63, 64, 92), (255, 255, 255, 80), 2)
    draw.text((80, 61), episode["meta"].get("episode_label", "柚子论文电台"), font=utility, fill=(255, 255, 255, 238))
    count = f"{index:02d} / {total:02d}"
    count_w = draw.textbbox((0, 0), count, font=utility)[2]
    draw.text((995 - count_w, 61), count, font=utility, fill=(255, 255, 255, 230))

    host = episode["speakers"]["host"]
    expert = episode["speakers"]["expert"]
    active = scene["speaker"]
    accent = (245, 201, 106, 255)
    inactive = (255, 255, 255, 105)

    def speaker_badge(cx, person, initial, is_active, warm=False, right=False):
        cy, radius = 1090, 47
        fill = (255, 239, 191, 205) if warm else (223, 247, 240, 205)
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=fill,
                     outline=accent if is_active else inactive, width=7 if is_active else 3)
        bbox = draw.textbbox((0, 0), initial, font=badge_font)
        draw.text((cx-(bbox[2]-bbox[0])/2, cy-(bbox[3]-bbox[1])/2-4), initial,
                  font=badge_font, fill=(23, 74, 75, 255))
        name = person["name"]
        role = person["role"]
        if right:
            name_w = draw.textbbox((0, 0), name, font=name_font)[2]
            role_w = draw.textbbox((0, 0), role, font=role_font)[2]
            draw.text((cx-radius-18-name_w, cy-30), name, font=name_font, fill=(255,255,255,245 if is_active else 165))
            draw.text((cx-radius-18-role_w, cy+8), role, font=role_font, fill=(255,255,255,175 if is_active else 110))
        else:
            draw.text((cx+radius+18, cy-30), name, font=name_font, fill=(255,255,255,245 if is_active else 165))
            draw.text((cx+radius+18, cy+8), role, font=role_font, fill=(255,255,255,175 if is_active else 110))

    speaker_badge(105, host, "鲸", active == "host")
    speaker_badge(975, expert, "柚", active == "expert", warm=True, right=True)
    draw.rounded_rectangle((385, 1087, 695, 1095), radius=4, fill=(255,255,255,48))
    if active == "host":
        draw.rounded_rectangle((385, 1087, 525, 1095), radius=4, fill=(85,184,173,235))
    else:
        draw.rounded_rectangle((555, 1087, 695, 1095), radius=4, fill=(245,201,106,235))

    person = episode["speakers"][active]
    label = f"{scene['section']} · {person['name']} · {person['role']}"
    draw.text((66, 1162), label, font=label_font, fill=(255, 190, 178, 255))
    for subtitle_size in (40, 38, 36, 34, 32):
        subtitle_font = font(FONT_BOLD, subtitle_size)
        lines = wrap_text(draw, scene["text"], subtitle_font, width - 132)
        if len(lines) <= 3:
            break
    if len(lines) > 4:
        subtitle_font = font(FONT_BOLD, 30)
        lines = wrap_text(draw, scene["text"], subtitle_font, width - 132)
    y = 1205
    for line in lines:
        draw.text((66, y), line, font=subtitle_font, fill=(255,255,255,255), stroke_width=1, stroke_fill=(10,38,39,120))
        y += subtitle_font.size + 14
    source_text = f"证据：{scene['source']}"
    draw.text((66, 1403), source_text, font=small, fill=(255,255,255,160))
    base.convert("RGB").save(target, quality=95)


def find_ffmpeg(explicit=None):
    if explicit:
        return explicit
    command = shutil.which("ffmpeg")
    if command:
        return command
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as error:
        raise RuntimeError("ffmpeg is required; install ffmpeg or imageio-ffmpeg") from error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-folder", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ffmpeg-bin")
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    folder = Path(args.episode_folder).resolve()
    episode = json.loads((folder / "episode.json").read_text(encoding="utf-8"))
    timeline = json.loads((folder / "timing.json").read_text(encoding="utf-8"))
    frames_dir = folder / "video-frames"
    frames_dir.mkdir(exist_ok=True)
    with wave.open(str(folder / "podcast.wav"), "rb") as audio_file:
        total_duration = audio_file.getnframes() / audio_file.getframerate()

    frame_paths = []
    for index, scene in enumerate(timeline, 1):
        frame_path = frames_dir / f"scene-{index:02d}.png"
        render_frame(scene, episode, index, len(timeline), frame_path)
        frame_paths.append(frame_path)
        print(f"[{index:02d}/{len(timeline):02d}] rendered", flush=True)

    manifest = folder / "frames.ffconcat"
    lines = ["ffconcat version 1.0"]
    for index, frame_path in enumerate(frame_paths):
        start = timeline[index]["start"]
        end = timeline[index + 1]["start"] if index + 1 < len(timeline) else total_duration
        duration = max(0.04, end - start)
        safe_path = str(frame_path).replace("'", "'\\''")
        lines.extend([f"file '{safe_path}'", f"duration {duration:.6f}"])
    lines.append(f"file '{str(frame_paths[-1]).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ffmpeg = find_ffmpeg(args.ffmpeg_bin)
    output = Path(args.output).resolve()
    subprocess.run([
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-i", str(folder / "podcast.wav"),
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", f"fps={args.fps}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_duration:.6f}", "-shortest", str(output),
    ], check=True)
    print(f"Exported {output}")


if __name__ == "__main__":
    main()
