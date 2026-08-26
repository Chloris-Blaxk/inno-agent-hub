#!/usr/bin/env python3
"""Build a source-grounded two-speaker HTML paper podcast with free TTS."""

import argparse
import audioop
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BG = SKILL_DIR / "assets" / "ocean-fruit-background.png"
TEMPLATE = SKILL_DIR / "assets" / "player-template.html"


def load_episode(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("meta", "speakers", "scenes"):
        if key not in data:
            raise ValueError(f"episode.json missing '{key}'")
    for key in ("host", "expert"):
        if key not in data["speakers"]:
            raise ValueError(f"speakers missing '{key}'")
    if not data["scenes"]:
        raise ValueError("scenes must not be empty")
    seen = set()
    for index, scene in enumerate(data["scenes"], 1):
        for key in ("id", "section", "speaker", "text", "source", "key_point", "visual"):
            if not scene.get(key):
                raise ValueError(f"scene {index} missing '{key}'")
        if scene["id"] in seen:
            raise ValueError(f"duplicate scene id: {scene['id']}")
        seen.add(scene["id"])
        if scene["speaker"] not in data["speakers"]:
            raise ValueError(f"unknown speaker in {scene['id']}: {scene['speaker']}")
        if not Path(scene["visual"]).is_file():
            raise FileNotFoundError(f"visual not found: {scene['visual']}")
    return data


def format_srt_time(seconds):
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def synthesize_local_segment(text, voice, rate, output_wav, workdir):
    raw_aiff = workdir / "speech.aiff"
    output_wav.unlink(missing_ok=True)
    subprocess.run(
        ["say", "-v", voice, "-r", str(rate), "-o", str(raw_aiff), text],
        check=True,
    )
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", str(raw_aiff), str(output_wav)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def synthesize_edge_segment(text, speaker, output_wav, workdir, edge_tts_bin, ffmpeg_bin):
    """Generate a neural-voice MP3 with edge-tts, then normalize it to WAV."""
    raw_mp3 = workdir / "speech.mp3"
    output_wav.unlink(missing_ok=True)
    command = [
        str(edge_tts_bin),
        "--voice", speaker.get("edge_voice", speaker.get("voice", "zh-CN-XiaoxiaoNeural")),
        f"--rate={speaker.get('edge_rate', '+0%')}",
        f"--pitch={speaker.get('edge_pitch', '+0Hz')}",
        "--text", text,
        "--write-media", str(raw_mp3),
    ]
    last_error = None
    for attempt in range(5):
        try:
            subprocess.run(
                command, check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            last_error = None
            break
        except subprocess.CalledProcessError as error:
            last_error = error
            raw_mp3.unlink(missing_ok=True)
            if attempt < 4:
                time.sleep(2 ** attempt)
    if last_error:
        raise last_error
    subprocess.run(
        [
            str(ffmpeg_bin), "-y", "-loglevel", "error", "-i", str(raw_mp3),
            "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", str(output_wav),
        ],
        check=True,
    )


def normalize_wav(path, target_rate=22050, target_channels=1, target_width=2):
    with wave.open(str(path), "rb") as src:
        channels = src.getnchannels()
        width = src.getsampwidth()
        rate = src.getframerate()
        frames = src.readframes(src.getnframes())
    if width != target_width:
        frames = audioop.lin2lin(frames, width, target_width)
        width = target_width
    if channels == 2 and target_channels == 1:
        frames = audioop.tomono(frames, width, 0.5, 0.5)
        channels = 1
    elif channels != target_channels:
        raise ValueError(f"unsupported channel conversion: {channels} -> {target_channels}")
    if rate != target_rate:
        frames, _ = audioop.ratecv(frames, width, channels, rate, target_rate, None)
    return frames


def valid_wav(path):
    try:
        with wave.open(str(path), "rb") as src:
            return src.getnframes() > 0 and src.getframerate() > 0
    except (FileNotFoundError, wave.Error, EOFError):
        return False


def build_audio(
    episode, output, backend="local", pause_seconds=0.24,
    edge_tts_bin=None, ffmpeg_bin=None,
):
    segments_dir = output / "audio-segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    sample_rate, sample_width, channels = 22050, 2, 1
    silence = struct.pack("<h", 0) * round(sample_rate * pause_seconds)
    timeline = []
    cursor_frames = 0
    combined = output / "podcast.wav"
    prepared = []
    for index, scene in enumerate(episode["scenes"], 1):
        speaker = episode["speakers"][scene["speaker"]]
        signature = json.dumps(
            {"backend": backend, "text": scene["text"], "speaker": speaker},
            ensure_ascii=False, sort_keys=True,
        ).encode("utf-8")
        digest = hashlib.sha1(signature).hexdigest()[:10]
        segment_path = segments_dir / f"{index:02d}-{scene['id']}-{digest}.wav"
        cached = valid_wav(segment_path)
        print(
            f"[{index:02d}/{len(episode['scenes']):02d}] "
            f"{scene['id']} · {'cached' if cached else 'synthesizing'}",
            flush=True,
        )
        if not cached:
            with tempfile.TemporaryDirectory(prefix="paper-podcast-") as tmp:
                if backend == "edge":
                    synthesize_edge_segment(
                        scene["text"], speaker, segment_path, Path(tmp),
                        edge_tts_bin, ffmpeg_bin,
                    )
                    time.sleep(2.0)
                else:
                    synthesize_local_segment(
                        scene["text"], speaker["voice"], speaker.get("rate", 185),
                        segment_path, Path(tmp)
                    )
        prepared.append((scene, segment_path))

    temporary_combined = output / "podcast.building.wav"
    with wave.open(str(temporary_combined), "wb") as dst:
        dst.setnchannels(channels)
        dst.setsampwidth(sample_width)
        dst.setframerate(sample_rate)
        for scene, segment_path in prepared:
            frames = normalize_wav(segment_path, sample_rate, channels, sample_width)
            start = cursor_frames / sample_rate
            dst.writeframes(frames)
            speech_frames = len(frames) // (sample_width * channels)
            cursor_frames += speech_frames
            end = cursor_frames / sample_rate
            dst.writeframes(silence)
            cursor_frames += len(silence) // (sample_width * channels)
            timeline.append({**scene, "start": round(start, 3), "end": round(end, 3)})
    temporary_combined.replace(combined)

    (output / "timing.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    srt = []
    for index, item in enumerate(timeline, 1):
        speaker_name = episode["speakers"][item["speaker"]]["name"]
        srt.extend([
            str(index),
            f"{format_srt_time(item['start'])} --> {format_srt_time(item['end'])}",
            f"{speaker_name}：{item['text']}",
            "",
        ])
    (output / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")
    return timeline


def estimated_timeline(episode):
    cursor = 0.0
    timeline = []
    for scene in episode["scenes"]:
        duration = max(2.4, len(scene["text"]) / 4.6)
        timeline.append({**scene, "start": round(cursor, 3), "end": round(cursor + duration, 3)})
        cursor += duration + 0.24
    return timeline


def copy_assets(episode, timeline, output):
    asset_dir = output / "media"
    asset_dir.mkdir(parents=True, exist_ok=True)
    copied = {}
    overrides = (
        episode["meta"].get("visual_overrides", {})
        if episode["meta"].get("use_visual_overrides", False)
        else {}
    )
    for item in timeline:
        visual = item["visual"]
        override = overrides.get(visual, {})
        source = Path(override.get("path", visual)).resolve()
        crop = override.get("crop", item.get("visual_crop"))
        key = (source, tuple(crop) if crop else None)
        if key not in copied:
            signature = f"{source}:{source.stat().st_mtime_ns}:{crop}".encode("utf-8")
            digest = hashlib.sha1(signature).hexdigest()[:8]
            target = asset_dir / f"visual-{len(copied) + 1:02d}-{digest}{source.suffix.lower()}"
            if crop:
                if Image is None:
                    raise RuntimeError("Pillow is required for visual crops: pip install pillow")
                with Image.open(source) as image:
                    image.crop(tuple(crop)).save(target)
            else:
                shutil.copy2(source, target)
            copied[key] = target.relative_to(output).as_posix()
        item["visual"] = copied[key]
        item.pop("visual_crop", None)
    bg_source = Path(episode["meta"].get("background", DEFAULT_BG)).resolve()
    if not bg_source.is_file():
        raise FileNotFoundError(f"background not found: {bg_source}")
    bg_target = asset_dir / f"background{bg_source.suffix.lower()}"
    shutil.copy2(bg_source, bg_target)
    return bg_target.relative_to(output).as_posix()


def render_html(episode, timeline, output, has_audio):
    background = copy_assets(episode, timeline, output)
    payload = {
        "meta": episode["meta"],
        "speakers": episode["speakers"],
        "scenes": timeline,
        "background": background,
        "audio": "podcast.wav" if has_audio else None,
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    html = template.replace("__EPISODE_JSON__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / "episode.json").write_text(
        json.dumps(episode, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_support_docs(episode, output):
    lines = [
        f"# {episode['meta']['title']}", "",
        f"论文：{episode['meta'].get('paper_title', '')}",
        f"出处：{episode['meta'].get('venue', '')}", "",
    ]
    source_lines = [
        "# Source map", "",
        "| 段落 | 说话人 | 证据位置 | 本段要点 |",
        "|---|---|---|---|",
    ]
    for scene in episode["scenes"]:
        person = episode["speakers"][scene["speaker"]]
        lines.extend([f"**{person['name']}｜{scene['section']}**", "", scene["text"], ""])
        clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
        source_lines.append(
            f"| {clean(scene['id'])} | {clean(person['name'])} | "
            f"{clean(scene['source'])} | {clean(scene['key_point'])} |"
        )
    (output / "双人讲稿.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "source-map.md").write_text("\n".join(source_lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--tts", choices=("auto", "edge", "local"), default="auto")
    parser.add_argument("--edge-tts-bin", help="Path to the edge-tts executable")
    parser.add_argument("--ffmpeg-bin", help="Path to ffmpeg for Edge MP3 conversion")
    parser.add_argument("--max-scenes", type=int, help="Build only the first N scenes for review")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    episode = load_episode(args.episode)
    if args.max_scenes:
        if args.max_scenes < 1:
            parser.error("--max-scenes must be at least 1")
        episode["scenes"] = episode["scenes"][:args.max_scenes]

    edge_tts_bin = args.edge_tts_bin or shutil.which("edge-tts")
    ffmpeg_bin = args.ffmpeg_bin or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    can_edge = bool(edge_tts_bin and ffmpeg_bin)
    can_local = bool(shutil.which("say") and shutil.which("afconvert"))
    if args.tts == "edge":
        if not can_edge:
            parser.error("Edge TTS needs both edge-tts and ffmpeg; provide their paths or install them")
        backend = "edge"
    elif args.tts == "local":
        if not can_local:
            parser.error("Local TTS needs macOS say and afconvert")
        backend = "local"
    else:
        backend = "edge" if can_edge else "local"
    can_tts = can_edge or can_local
    if args.no_audio or not can_tts:
        timeline = estimated_timeline(episode)
        (output / "timing.json").write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        has_audio = False
        if not args.no_audio:
            print("Local TTS unavailable; built a visual-only preview.", file=sys.stderr)
    else:
        timeline = build_audio(
            episode, output, backend=backend,
            edge_tts_bin=edge_tts_bin, ffmpeg_bin=ffmpeg_bin,
        )
        has_audio = True
    render_html(episode, timeline, output, has_audio)
    write_support_docs(episode, output)
    total = timeline[-1]["end"] if timeline else 0
    mode = "visual only" if not has_audio else f"{backend} TTS"
    print(f"Built {len(timeline)} scenes ({total:.1f}s, {mode}) in {output}")


if __name__ == "__main__":
    main()
