#!/usr/bin/env python3
"""Compose screenshot-led Xiaohongshu pages from a JSON configuration."""

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


W, H = 1242, 1660
DEEP, INK = "#2F6F73", "#263B3C"
MINT, CORAL = "#DDF4EE", "#F4A79A"
WHITE, LINE = "#FFFFFF", "#B7DCD5"
DEFAULT_BG = Path(__file__).resolve().parents[1] / "assets/ocean-fruit-background.png"


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
            return candidate
    raise RuntimeError(
        f"No CJK font found. Set {env_name} to a Chinese TrueType/OpenType font path."
    )


def fnt(size, bold=False):
    return ImageFont.truetype(find_font(bold), size)


F_LABEL, F_TITLE, F_SUB = fnt(27, True), fnt(58, True), fnt(31)
F_BODY, F_BODY_BOLD, F_SMALL, F_TINY = fnt(30), fnt(30, True), fnt(23), fnt(19)


def wrap(draw, text, font, width):
    lines = []
    for paragraph in str(text).split("\n"):
        current = ""
        for ch in paragraph:
            trial = current + ch
            if not current or draw.textlength(trial, font=font) <= width:
                current = trial
            else:
                lines.append(current)
                current = ch
        lines.append(current)
    return lines


def text_block(draw, x, y, text, font, fill, width, spacing=10):
    for line in wrap(draw, text, font, width):
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + spacing
    return y


def fit(img, size, contain=True, fill=WHITE):
    w, h = size
    ratio = min(w / img.width, h / img.height) if contain else max(w / img.width, h / img.height)
    img = img.resize((round(img.width * ratio), round(img.height * ratio)), Image.Resampling.LANCZOS)
    if contain:
        plate = Image.new("RGB", size, fill)
        plate.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
        return plate
    return img.crop(((img.width - w) // 2, (img.height - h) // 2, (img.width + w) // 2, (img.height + h) // 2))


def paste_card(canvas, image, box, radius=26):
    x, y, w, h = box
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x + 8, y + 10, x + w + 8, y + h + 10), radius, fill=(47, 111, 115, 32))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    image = fit(image, (w, h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius, fill=255)
    canvas.paste(image, (x, y), mask)
    ImageDraw.Draw(canvas).rounded_rectangle((x, y, x + w, y + h), radius, outline=LINE, width=3)


def load_crop(spec):
    img = Image.open(spec["image"]).convert("RGB")
    if spec.get("crop"):
        img = img.crop(tuple(spec["crop"]))
    return img


def background(path):
    img = Image.open(path).convert("RGB")
    img = fit(img, (W, H), contain=False)
    veil = Image.new("RGBA", (W, H), (255, 248, 232, 34))
    out = img.convert("RGBA")
    out.alpha_composite(veil)
    return out


def header(canvas, page, index, total, label):
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((58, 52, 320, 102), 25, fill=(221, 244, 238, 224), outline="#78CFC0", width=2)
    draw.text((80, 63), label, font=F_LABEL, fill=DEEP)
    draw.text((1110, 66), f"{index}/{total}", font=F_SMALL, fill=DEEP)
    y = text_block(draw, 62, 142, page["title"], F_TITLE, INK, 1110, 12)
    if page.get("subtitle"):
        y = text_block(draw, 64, y + 12, page["subtitle"], F_SUB, DEEP, 1100, 8)
    return draw, y


def footer(draw, page):
    draw.line((62, 1578, 1180, 1578), fill=LINE, width=2)
    draw.text((64, 1595), page.get("source", ""), font=F_TINY, fill=DEEP)
    note = page.get("footer_note", "")
    draw.text((1178 - draw.textlength(note, font=F_TINY), 1595), note, font=F_TINY, fill=DEEP)


def render_page(bg_path, page, index, total, label):
    canvas = background(bg_path)
    draw, y = header(canvas, page, index, total, label)
    layout = page.get("layout", "evidence")
    image = load_crop(page) if page.get("image") else None

    if layout in {"hero", "paper", "evidence"}:
        img_h = int(page.get("image_height", 790 if layout == "hero" else 920))
        paste_card(canvas, image, (62, y + 24, 1118, img_h))
        content_y = y + img_h + 56
        badges = page.get("badges", [])
        if badges:
            gap = 18
            width = (1118 - gap * (len(badges) - 1)) // len(badges)
            for i, badge in enumerate(badges):
                x = 62 + i * (width + gap)
                fill = "#FFF1EC" if i == len(badges) - 1 and page.get("warn_last") else (221, 244, 238, 232)
                draw.rounded_rectangle((x, content_y, x + width, content_y + 62), 24, fill=fill, outline="#78CFC0", width=2)
                draw.text((x + width / 2, content_y + 31), badge, font=F_SMALL, fill=DEEP, anchor="mm")
                content_y += 0
        if page.get("callout"):
            cy = int(page.get("callout_y", content_y + (90 if badges else 0)))
            draw.rounded_rectangle((74, cy, 1168, cy + 142), 24, fill=(255, 241, 236, 238), outline=CORAL, width=2)
            text_block(draw, 104, cy + 26, page["callout"], F_BODY, INK, 1035, 8)

    elif layout == "technical":
        img_h = int(page.get("image_height", 500))
        paste_card(canvas, image, (62, y + 24, 1118, img_h))
        details = page.get("details", [])[:5]
        content_y = y + img_h + 52
        gap = 14
        available = 1538 - content_y - gap * max(0, len(details) - 1)
        card_h = min(164, available // max(1, len(details)))
        for i, detail in enumerate(details):
            yy = content_y + i * (card_h + gap)
            draw.rounded_rectangle(
                (62, yy, 1180, yy + card_h), 24,
                fill=(255, 255, 255, 238), outline=LINE, width=3
            )
            draw.rounded_rectangle(
                (84, yy + 22, 142, yy + 80), 20,
                fill=(221, 244, 238, 242), outline="#78CFC0", width=2
            )
            draw.text((113, yy + 51), f"{i + 1}", font=F_BODY_BOLD, fill=DEEP, anchor="mm")
            text_block(draw, 166, yy + 24, detail, F_BODY, INK, 970, 7)

    elif layout == "limits":
        paste_card(canvas, image, (660, y + 24, 520, 850))
        for i, bullet in enumerate(page.get("bullets", [])[:3]):
            yy = y + 28 + i * 245
            draw.rounded_rectangle((62, yy, 610, yy + 205), 26, fill=(255, 255, 255, 236), outline=LINE, width=3)
            draw.text((94, yy + 28), f"{i + 1:02d}", font=fnt(48), fill="#78CFC0")
            text_block(draw, 190, yy + 38, bullet, F_BODY, INK, 385, 8)
        if page.get("callout"):
            draw.rounded_rectangle((62, y + 925, 1180, y + 1085), 26, fill=(255, 241, 236, 238), outline=CORAL, width=2)
            text_block(draw, 94, y + 950, page["callout"], F_BODY, INK, 1050, 8)

    footer(draw, page)
    return canvas.convert("RGB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    out = Path(cfg["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    bg = Path(cfg.get("background", DEFAULT_BG))
    pages = cfg["pages"]
    for i, page in enumerate(pages, 1):
        image = render_page(bg, page, i, len(pages), cfg.get("label", "柚子读论文"))
        image.save(out / f"{i:02d}-{page.get('slug', 'page')}.png", quality=95)
    print(f"Generated {len(pages)} pages in {out}")


if __name__ == "__main__":
    main()
