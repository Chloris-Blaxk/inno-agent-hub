"""程序化生成 riso(孔版印刷)风格的抽象图块。

每个 skill 用自己的 id 做种子 → 确定性产出一张独一无二的 SVG:
同一个 id 每次 build 出来的图恒等,新增 skill 自动有图,无需人工画。

riso 的观感来自三件事,这里都做了:
  1. 少量高饱和油墨色平涂(不是渐变)
  2. 套印不准 —— 第二层色块故意偏移 1~3px,叠色处用 multiply
  3. 纸张颗粒 —— 极淡的点状噪声
"""
from __future__ import annotations

import math

# 每个星系一组 riso 油墨(比页面底色饱和得多,否则星图会发灰)
INKS = {
    "备课": ["#2f7d52", "#8fc9a4", "#1b4d34", "#d8e8dc"],
    "讲课": ["#2f6f9e", "#8fbedd", "#17415f", "#d6e5f0"],
    "自学": ["#c25a2e", "#f0a878", "#8a3a17", "#f6ddc9"],
    "研究": ["#a58535", "#e0c583", "#6b5420", "#f0e5c8"],
    "创造": ["#6b4d9c", "#b199d6", "#432f66", "#e3daf1"],
}
PAPER = "#f7f4ed"

PATTERNS = ["grid", "halftone", "waves", "blocks", "arcs", "scatter", "stripes", "linework"]


class Rand:
    """mulberry32 —— 小巧、确定、跨语言可复现。"""

    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.s
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    def rng(self, a: float, b: float) -> float:
        return a + (b - a) * self.next()

    def int(self, a: int, b: int) -> int:
        return int(math.floor(self.rng(a, b + 1 - 1e-9)))

    def pick(self, xs):
        return xs[self.int(0, len(xs) - 1)]


def seed_of(text: str) -> int:
    """FNV-1a,稳定且分布好。"""
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _grid(r: Rand, w: int, h: int, ink: list[str]) -> str:
    n = r.int(4, 8)
    step = w / n
    lines = []
    for i in range(n + 1):
        x = round(i * step, 1)
        lines.append(f'<path d="M{x} 0V{h}"/>')
    m = max(1, int(h / step))
    for i in range(m + 1):
        y = round(i * step, 1)
        lines.append(f'<path d="M0 {y}H{w}"/>')
    sw = round(r.rng(1.1, 2.2), 1)
    return (f'<rect width="{w}" height="{h}" fill="{ink[3]}"/>'
            f'<g stroke="{ink[0]}" stroke-width="{sw}" fill="none">{"".join(lines)}</g>')


def _halftone(r: Rand, w: int, h: int, ink: list[str]) -> str:
    step = r.rng(7, 12)
    dots = []
    y = step / 2
    while y < h:
        x = step / 2
        while x < w:
            d = math.hypot(x - w * 0.35, y - h * 0.4) / max(w, h)
            rad = max(0.6, (1.05 - d * 1.5) * step * 0.42)
            dots.append(f'<circle cx="{round(x,1)}" cy="{round(y,1)}" r="{round(rad,1)}"/>')
            x += step
        y += step
    return (f'<rect width="{w}" height="{h}" fill="{ink[3]}"/>'
            f'<g fill="{ink[0]}">{"".join(dots)}</g>')


def _waves(r: Rand, w: int, h: int, ink: list[str]) -> str:
    n = r.int(4, 8)
    amp = r.rng(3, 7)
    paths = []
    for i in range(n):
        y = (i + 0.5) * h / n
        seg = w / 4
        d = f"M0 {round(y,1)}"
        for k in range(4):
            up = -amp if k % 2 == 0 else amp
            d += f" q{round(seg/2,1)} {round(up,1)} {round(seg,1)} 0"
        paths.append(f'<path d="{d}"/>')
    return (f'<rect width="{w}" height="{h}" fill="{ink[3]}"/>'
            f'<g stroke="{ink[0]}" stroke-width="{round(r.rng(1.4,2.6),1)}" fill="none" '
            f'stroke-linecap="round">{"".join(paths)}</g>')


def _blocks(r: Rand, w: int, h: int, ink: list[str]) -> str:
    cx = round(w * r.rng(0.36, 0.62), 1)
    cy = round(h * r.rng(0.36, 0.62), 1)
    quads = [
        (0, 0, cx, cy), (cx, 0, w - cx, cy),
        (0, cy, cx, h - cy), (cx, cy, w - cx, h - cy),
    ]
    cols = [ink[0], ink[1], ink[2], ink[3]]
    for i in range(len(cols) - 1, 0, -1):
        j = r.int(0, i)
        cols[i], cols[j] = cols[j], cols[i]
    out = []
    for (x, y, bw, bh), c in zip(quads, cols):
        out.append(f'<rect x="{x}" y="{y}" width="{round(bw,1)}" height="{round(bh,1)}" fill="{c}"/>')
    return "".join(out)


def _arcs(r: Rand, w: int, h: int, ink: list[str]) -> str:
    cx, cy = w * r.rng(0.1, 0.9), h * r.rng(0.1, 0.9)
    n = r.int(3, 6)
    step = max(w, h) / (n + 1)
    circles = [
        f'<circle cx="{round(cx,1)}" cy="{round(cy,1)}" r="{round((i+1)*step*0.62,1)}"/>'
        for i in range(n)
    ]
    return (f'<rect width="{w}" height="{h}" fill="{ink[3]}"/>'
            f'<g stroke="{ink[0]}" stroke-width="{round(r.rng(1.3,2.4),1)}" fill="none">'
            f'{"".join(circles)}</g>')


def _scatter(r: Rand, w: int, h: int, ink: list[str]) -> str:
    n = r.int(14, 30)
    out = []
    for _ in range(n):
        s = round(r.rng(2.5, 7), 1)
        x = round(r.rng(0, w - s), 1)
        y = round(r.rng(0, h - s), 1)
        c = ink[0] if r.next() > 0.32 else ink[2]
        out.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{c}"/>')
    return (f'<rect width="{w}" height="{h}" fill="{ink[3]}"/>{"".join(out)}')


def _stripes(r: Rand, w: int, h: int, ink: list[str]) -> str:
    sw = round(r.rng(3.5, 7), 1)
    gap = sw * 2
    diag = w + h
    paths = []
    x = -h
    while x < diag:
        paths.append(f'<path d="M{round(x,1)} {h}L{round(x+h,1)} 0"/>')
        x += gap
    return (f'<rect width="{w}" height="{h}" fill="{ink[3]}"/>'
            f'<g stroke="{ink[0]}" stroke-width="{sw}">{"".join(paths)}</g>')


def _linework(r: Rand, w: int, h: int, ink: list[str]) -> str:
    n = r.int(3, 6)
    paths = []
    for _ in range(n):
        x0, y0 = round(r.rng(0, w * .3), 1), round(r.rng(0, h), 1)
        x1, y1 = round(r.rng(w * .7, w), 1), round(r.rng(0, h), 1)
        cx1, cy1 = round(r.rng(0, w), 1), round(r.rng(-h * .2, h * 1.2), 1)
        cx2, cy2 = round(r.rng(0, w), 1), round(r.rng(-h * .2, h * 1.2), 1)
        paths.append(f'<path d="M{x0} {y0}C{cx1} {cy1} {cx2} {cy2} {x1} {y1}"/>')
    return (f'<rect width="{w}" height="{h}" fill="{ink[3]}"/>'
            f'<g stroke="{ink[0]}" stroke-width="{round(r.rng(1.2,2.2),1)}" fill="none" '
            f'stroke-linecap="round">{"".join(paths)}</g>')


_RENDER = {
    "grid": _grid, "halftone": _halftone, "waves": _waves, "blocks": _blocks,
    "arcs": _arcs, "scatter": _scatter, "stripes": _stripes, "linework": _linework,
}


def make_tile(skill_id: str, scenario: str) -> dict:
    """返回 {svg, w, h, pattern} —— 一张确定性的 riso 图块。"""
    r = Rand(seed_of(skill_id))
    ink = INKS.get(scenario, INKS["创造"])
    # 尺寸多样化(参考图里方的、横的、竖的都有)
    shape = r.next()
    if shape < 0.42:
        w = h = r.int(60, 80)
    elif shape < 0.74:
        w, h = r.int(74, 96), r.int(50, 66)
    else:
        w, h = r.int(50, 66), r.int(68, 90)

    pattern = r.pick(PATTERNS)
    body = _RENDER[pattern](r, w, h, ink)

    # 套印不准:第二层偏移色块,multiply 叠色
    ox, oy = round(r.rng(-3, 3), 1), round(r.rng(-3, 3), 1)
    bw, bh = round(w * r.rng(.3, .6), 1), round(h * r.rng(.3, .6), 1)
    bx, by = round(r.rng(0, w - bw), 1), round(r.rng(0, h - bh), 1)
    mis = (f'<g transform="translate({ox} {oy})" style="mix-blend-mode:multiply" opacity="0.55">'
           f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{ink[1]}"/></g>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'width="{w}" height="{h}" shape-rendering="crispEdges">'
           f'<rect width="{w}" height="{h}" fill="{PAPER}"/>'
           f'{body}{mis}'
           f'<rect width="{w}" height="{h}" fill="url(#grain)"/>'
           f'</svg>')
    return {"svg": svg, "w": w, "h": h, "pattern": pattern}
