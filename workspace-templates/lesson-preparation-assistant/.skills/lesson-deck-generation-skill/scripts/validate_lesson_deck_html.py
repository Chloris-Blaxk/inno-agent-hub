#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VALID_LAYOUTS = {f"ED{i:02d}" for i in range(1, 13)}
REQUIRED_SECTION_ATTRS = {"data-layout", "data-stage", "data-slot", "data-slot-ratio", "data-asset-status"}
REQUIRED_RUNTIME_IDS = {"deck", "speaker", "hud", "dots", "deck-json", "overview-toggle", "power-toggle", "speaker-toggle"}
TEACHER_ONLY_MARKERS = ("教师说：", "预设回应：", "反馈证据：", "教学意图：")


class LessonDeckHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[dict[str, str]] = []
        self.ids: set[str] = set()
        self.data_animate_count = 0
        self.deck_json_chunks: list[str] = []
        self.visible_text_chunks: list[str] = []
        self.in_script = False
        self.in_style = False
        self.deck_json_script = False
        self.svg_depth = 0
        self.svg_text_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        if tag == "section":
            classes = set(attr_map.get("class", "").split())
            if "slide" in classes:
                self.sections.append(attr_map)
        if "id" in attr_map:
            self.ids.add(attr_map["id"])
        if "data-animate" in attr_map:
            self.data_animate_count += 1
        if tag == "script":
            self.in_script = True
            self.deck_json_script = attr_map.get("id") == "deck-json"
        if tag == "style":
            self.in_style = True
        if tag == "svg":
            self.svg_depth += 1
        if tag == "text" and self.svg_depth:
            self.svg_text_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_script = False
            self.deck_json_script = False
        if tag == "style":
            self.in_style = False
        if tag == "svg" and self.svg_depth:
            self.svg_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_script:
            if self.deck_json_script:
                self.deck_json_chunks.append(data)
            return
        if self.in_style:
            return
        if data.strip():
            self.visible_text_chunks.append(data.strip())


def parse_html(path: Path) -> LessonDeckHTMLParser:
    parser = LessonDeckHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def load_embedded_deck(parser: LessonDeckHTMLParser) -> dict[str, Any]:
    raw = "".join(parser.deck_json_chunks).strip()
    if not raw:
        raise ValueError("缺少 id=\"deck-json\" 的内嵌 JSON。")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"deck-json 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("deck-json 根对象必须是 object。")
    return data


def validate(path: Path, strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    parser = parse_html(path)

    missing_runtime = sorted(REQUIRED_RUNTIME_IDS - parser.ids)
    if missing_runtime:
        errors.append(f"HTML runtime 缺少元素 id: {', '.join(missing_runtime)}。")

    try:
        deck = load_embedded_deck(parser)
    except ValueError as exc:
        errors.append(str(exc))
        deck = {}

    slides = deck.get("slides", []) if isinstance(deck, dict) else []
    expected_layouts = [slide.get("layoutId") for slide in slides if isinstance(slide, dict)]
    html_layouts = [section.get("data-layout") for section in parser.sections]

    if not parser.sections:
        errors.append("HTML 中没有找到 <section class=\"slide\">。")
    if expected_layouts and len(parser.sections) != len(expected_layouts):
        errors.append(f"HTML slide 数量 {len(parser.sections)} 与 JSON slides 数量 {len(expected_layouts)} 不一致。")
    if expected_layouts and html_layouts != expected_layouts:
        errors.append(f"HTML data-layout 顺序与 JSON 不一致: HTML={html_layouts}, JSON={expected_layouts}。")

    for index, section in enumerate(parser.sections, start=1):
        layout = section.get("data-layout", "")
        if layout not in VALID_LAYOUTS:
            errors.append(f"Slide {index}: 未登记 data-layout={layout!r}。")
        missing_attrs = [attr for attr in sorted(REQUIRED_SECTION_ATTRS) if not section.get(attr)]
        if missing_attrs:
            errors.append(f"Slide {index}: section 缺少属性 {', '.join(missing_attrs)}。")
        classes = set(section.get("class", "").split())
        if layout and f"layout-{layout.lower()}" not in classes:
            errors.append(f"Slide {index}: 缺少 layout-{layout.lower()} CSS class。")

    if parser.svg_text_count:
        errors.append(f"SVG 内发现 {parser.svg_text_count} 个 <text>，可见文字应使用 HTML/PPTX 可编辑文本。")

    visible_text = "\n".join(parser.visible_text_chunks)
    for marker in TEACHER_ONLY_MARKERS:
        if marker in visible_text:
            errors.append(f"学生屏幕疑似泄漏教师信息: {marker}")

    if parser.data_animate_count < max(1, len(parser.sections)):
        warnings.append("HTML 中 data-animate 数量偏少，入场动效可能未覆盖主要内容。")

    html_text = path.read_text(encoding="utf-8")
    for token in ("touchstart", "touchend", "low-power", "overview"):
        if token not in html_text:
            errors.append(f"HTML runtime 缺少 {token} 支持。")
    if re.search(r'data-layout="(?!ED\d{2})[^"]+"', html_text):
        errors.append("HTML 中存在非 EDxx data-layout。")

    if strict and warnings:
        errors.extend([f"strict warning: {warning}" for warning in warnings])
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 edu-deck-v1 HTML 课件。")
    parser.add_argument("deck_html")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    errors, warnings = validate(Path(args.deck_html), strict=args.strict)
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print("Lesson deck HTML validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Lesson deck HTML validation passed: {len(parse_html(Path(args.deck_html)).sections)} slide(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
