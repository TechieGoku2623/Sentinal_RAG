"""Pillow frame renderers for the 7-clip Sentinel-RAG walkthrough storyboard."""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "docs" / "brand" / "logo.png"

W, H = 1920, 1080
FPS = 24

# Sentinel-RAG dark clinical palette
BG = (6, 13, 20)
SURFACE = (12, 24, 37)
ELEVATED = (19, 34, 51)
TEAL = (14, 199, 136)
TEAL_DIM = (10, 122, 85)
TEXT = (232, 240, 248)
MUTED = (122, 154, 184)
BORDER = (255, 255, 255, 23)
RED = (232, 64, 64)
AMBER = (240, 165, 0)
WHITE = (255, 255, 255)


def _font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if mono:
        candidates = [
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/cour.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    elif bold:
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _base() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    # Subtle vignette
    for i in range(80):
        alpha = int(i * 1.2)
        draw.rectangle([0, i, W, i + 1], fill=(0, 0, 0))
        draw.rectangle([0, H - i - 1, W, H - i], fill=(0, 0, 0))
    return img


def _caption(img: Image.Image, text: str, progress: float = 1.0) -> None:
    if progress <= 0:
        return
    draw = ImageDraw.Draw(img)
    font = _font(28)
    tw = draw.textlength(text, font=font)
    pad_x, pad_y = 18, 10
    box_w = tw + pad_x * 2
    box_h = 46
    x = (W - box_w) // 2
    y = H - 120
    alpha = int(153 * min(1.0, progress))
    draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=8, fill=(6, 13, 20))
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=TEXT)


def _monitor_frame(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    glow: tuple[int, int, int] = TEAL,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1 - 8, y1 - 8, x2 + 8, y2 + 8], radius=16, fill=(4, 8, 14))
    draw.rounded_rectangle([x1, y1, x2, y2], radius=10, fill=SURFACE, outline=glow, width=2)
    return x1 + 24, y1 + 24, x2 - 24, y2 - 24


def _typewriter(text: str, t: float, cps: float = 38.0) -> str:
    n = int(len(text) * min(1.0, t * cps / max(len(text), 1)))
    return text[: max(0, min(len(text), n))]


def _draw_arc(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    progress: float,
    color: tuple[int, int, int],
    label: str,
) -> None:
    progress = max(0.0, min(1.0, progress))
    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(bbox, start=135, end=405, fill=(40, 55, 70), width=10)
    if progress > 0:
        end = 135 + 270 * progress
        draw.arc(bbox, start=135, end=end, fill=color, width=10)
    draw.text((cx - 22, cy - 16), label, font=_font(22, bold=True), fill=color)


def _draw_pipeline(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    active: int,
    node_colors: list[tuple[int, int, int]] | None = None,
    loop_back: float = 0.0,
) -> None:
    labels = ["RETRIEVE", "GENERATE", "REFLECT", "OUTPUT"]
    spacing = 280
    start_x = cx - spacing * 1.5
    colors = node_colors or [TEAL_DIM] * 4
    for i, label in enumerate(labels):
        x = start_x + i * spacing
        col = colors[i] if i < len(colors) else TEAL_DIM
        lit = i <= active
        fill = col if lit else (25, 40, 55)
        outline = col if lit else (50, 65, 80)
        draw.ellipse([x - 28, cy - 28, x + 28, cy + 28], fill=fill, outline=outline, width=2)
        draw.text((x - draw.textlength(label, font=_font(14, mono=True)) / 2, cy + 38), label, font=_font(14, mono=True), fill=MUTED if not lit else TEXT)
        if i < len(labels) - 1:
            nx = x + spacing
            draw.line([x + 30, cy, nx - 30, cy], fill=TEAL if lit else (40, 55, 70), width=3)
    if loop_back > 0:
        lb = int(180 * loop_back)
        draw.arc([cx - 420, cy - 120, cx + 420, cy + 100], start=200, end=200 + lb, fill=AMBER, width=4)


def render_clip_01(t: float) -> Image.Image:
    """Hook — confident wrong answer on tablet."""
    img = _base()
    draw = ImageDraw.Draw(img)
    scale = _lerp(1.15, 1.0, _ease(max(0, (t - 0.35) / 0.45)))
    mw, mh = int(900 * scale), int(620 * scale)
    mx, my = (W - mw) // 2, (H - mh) // 2 + 40
    inner = _monitor_frame(draw, (mx, my, mx + mw, my + mh), glow=RED if t > 0.75 else (80, 100, 120))
    x1, y1, x2, y2 = inner

    q = "What is the correct metformin dose for this patient?"
    a = "The standard dose is 1000mg twice daily."
    qt = _typewriter(q, min(1.0, t / 0.25))
    at = _typewriter(a, max(0.0, min(1.0, (t - 0.25) / 0.2)))

    draw.text((x1, y1), "Clinical AI chat", font=_font(16, mono=True), fill=MUTED)
    for i, line in enumerate(_wrap(draw, qt, _font(26), x2 - x1)):
        draw.text((x1, y1 + 40 + i * 34), line, font=_font(26), fill=TEXT)
    ay = y1 + 140
    draw.rounded_rectangle([x1, ay, x2, ay + 120], radius=8, fill=ELEVATED)
    for i, line in enumerate(_wrap(draw, at, _font(24), x2 - x1 - 32)):
        draw.text((x1 + 16, ay + 16 + i * 30), line, font=_font(24), fill=MUTED)

    if t > 0.75:
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 6)
        w = int(4 + 6 * pulse)
        draw.rounded_rectangle([mx - w, my - w, mx + mw + w, my + mh + w], radius=14, outline=RED, width=w)

    _caption(img, "Healthcare AI can't afford to hallucinate.", _ease(max(0, (t - 0.5) / 0.3)))
    return img


def render_clip_02(t: float) -> Image.Image:
    """Problem — doctor compares screen to printed guideline."""
    img = _base()
    draw = ImageDraw.Draw(img)
    # Silhouette
    sx, sy = 320, 280
    draw.ellipse([sx - 55, sy - 80, sx + 55, sy + 30], fill=(30, 45, 60))
    draw.rounded_rectangle([sx - 90, sy + 20, sx + 90, sy + 320], radius=40, fill=(35, 50, 65))
    draw.text((sx - 70, sy + 360), "Skeptical review", font=_font(20), fill=MUTED)

    mx, my, mw, mh = 980, 180, 760, 620
    inner = _monitor_frame(draw, (mx, my, mx + mw, my + mh), glow=(100, 130, 160))
    x1, y1, x2, y2 = inner
    draw.text((x1, y1), "Generic clinical AI", font=_font(16, mono=True), fill=MUTED)
    draw.text((x1, y1 + 40), "Metformin dosing recommendation", font=_font(28, bold=True), fill=WHITE)
    draw.rounded_rectangle([x1, y1 + 100, x2, y2 - 40], radius=8, fill=ELEVATED)
    ans = "1000mg twice daily — high confidence response"
    for i, line in enumerate(_wrap(draw, ans, _font(24), x2 - x1 - 40)):
        draw.text((x1 + 20, y1 + 120 + i * 32), line, font=_font(24), fill=TEXT)

    # Paper prop
    px = 420 + int(30 * _ease(min(1.0, t * 1.5)))
    py = 520 + int(10 * math.sin(t * math.pi * 2))
    draw.rounded_rectangle([px, py, px + 200, py + 260], radius=6, fill=(220, 225, 230))
    draw.text((px + 16, py + 16), "Printed\nGuideline", font=_font(18), fill=(60, 70, 80))
    for i in range(6):
        draw.line([px + 16, py + 70 + i * 22, px + 180, py + 70 + i * 22], fill=(180, 185, 190), width=2)

    _caption(img, "Standard AI fails silently.", _ease(max(0, (t - 0.3) / 0.4)))
    return img


def render_clip_03(t: float) -> Image.Image:
    """Sentinel-RAG pipeline activates."""
    zoom = _lerp(1.0, 1.08, _ease(t))
    img = _base()
    draw = ImageDraw.Draw(img)
    mw, mh = int(1400 * zoom), int(780 * zoom)
    mx, my = (W - mw) // 2, (H - mh) // 2
    inner = _monitor_frame(draw, (mx, my, mx + mw, my + mh))
    x1, y1, x2, y2 = inner

    title = _typewriter("SENTINEL-RAG · CLINICAL PROTOCOL GUARDIAN", min(1.0, t / 0.35))
    draw.text((x1, y1), title, font=_font(32, bold=True, mono=True), fill=TEXT)

    active = min(3, int(max(0, (t - 0.35) / 0.15) * 4))
    _draw_pipeline(draw, W // 2, (y1 + y2) // 2 + 40, active)

    _caption(img, "Sentinel-RAG self-audits every answer.", _ease(max(0, (t - 0.55) / 0.35)))
    return img


def render_clip_04(t: float) -> Image.Image:
    """High confidence 98%."""
    img = _base()
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    cw, ch = 1200, 680
    x1, y1, x2, y2 = cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2
    draw.rounded_rectangle([x1, y1, x2, y2], radius=14, fill=SURFACE, outline=TEAL, width=2)

    q = "What is the first-line treatment for Type 2 diabetes?"
    qt = _typewriter(q, min(1.0, t / 0.2))
    draw.text((x1 + 32, y1 + 32), "Clinical query", font=_font(14, mono=True), fill=TEAL)
    for i, line in enumerate(_wrap(draw, qt, _font(28), cw - 200)):
        draw.text((x1 + 32, y1 + 64 + i * 36), line, font=_font(28), fill=TEXT)

    if t > 0.25:
        ay = y1 + 180
        draw.rounded_rectangle([x1 + 32, ay, x2 - 32, y2 - 100], radius=10, fill=ELEVATED)
        ans = (
            "Metformin is the recommended first-line pharmacological therapy for adults "
            "with type 2 diabetes unless contraindicated."
        )
        at = _typewriter(ans, max(0, min(1.0, (t - 0.25) / 0.25)))
        for i, line in enumerate(_wrap(draw, at, _font(22), cw - 120)):
            draw.text((x1 + 48, ay + 20 + i * 30), line, font=_font(22), fill=MUTED)

    conf_t = max(0, min(1, (t - 0.35) / 0.25))
    _draw_arc(draw, x2 - 100, y1 + 110, 56, conf_t, TEAL, f"{int(98 * conf_t)}%")

    pills = [("RETURNED", TEAL), ("Retries: 0", MUTED), ("Sources: 3", MUTED)]
    if t > 0.55:
        px = x1 + 32
        for i, (label, col) in enumerate(pills):
            show = max(0, min(1, (t - 0.55 - i * 0.08) / 0.1))
            if show <= 0:
                continue
            tw = draw.textlength(label, font=_font(16, mono=True)) + 24
            draw.rounded_rectangle([px, y2 - 72, px + tw, y2 - 36], radius=6, fill=ELEVATED, outline=col)
            draw.text((px + 12, y2 - 64), label, font=_font(16, mono=True), fill=col)
            px += tw + 16

    zoom = _lerp(1.0, 0.92, _ease(max(0, (t - 0.75) / 0.25)))
    if zoom < 1.0:
        cropped = img.crop([int(W * (1 - zoom) / 2), int(H * (1 - zoom) / 2), int(W * (1 + zoom) / 2), int(H * (1 + zoom) / 2)])
        img = cropped.resize((W, H), Image.Resampling.LANCZOS)

    _caption(img, "High confidence → instant return.", _ease(max(0, (t - 0.4) / 0.3)))
    return img


def render_clip_05(t: float) -> Image.Image:
    """Self-correction / retry loop."""
    img = _base()
    draw = ImageDraw.Draw(img)
    colors = [TEAL, TEAL, AMBER, TEAL_DIM]
    loop = 0.0
    conf = 0.74
    active = 2
    if t < 0.25:
        active = 2
        conf = 0.74
    elif t < 0.55:
        loop = _ease((t - 0.25) / 0.3)
        active = 0 if loop > 0.6 else 2
        colors = [TEAL if loop > 0.6 else TEAL_DIM, TEAL_DIM, AMBER, TEAL_DIM]
    else:
        active = 3
        conf = _lerp(0.74, 0.88, _ease((t - 0.55) / 0.35))
        colors = [TEAL, TEAL, TEAL, TEAL]

    _draw_pipeline(draw, W // 2, H // 2 - 40, active, colors, loop_back=loop)
    _draw_arc(draw, W - 180, 180, 50, conf, AMBER if conf < 0.85 else TEAL, f"{int(conf * 100)}%")

    if 0.25 < t < 0.55:
        draw.text((W // 2 - 80, 160), "Re-query 1 of 3", font=_font(18, mono=True), fill=AMBER)

    _caption(img, "Borderline → automatic re-query.", _ease(max(0, (t - 0.2) / 0.35)))
    return img


def render_clip_06(t: float) -> Image.Image:
    """Flagged for clinical review."""
    img = _base()
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    cw, ch = 1200, 680
    x1, y1, x2, y2 = cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2

    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2)
    bw = int(3 + 4 * pulse)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=14, fill=(40, 18, 22), outline=RED, width=bw)

    draw.text((x1 + 32, y1 + 32), "What happens if a patient misses a dose?", font=_font(28), fill=TEXT)
    draw.text((x1 + 32, y1 + 100), "FLAGGED FOR CLINICAL REVIEW", font=_font(20, bold=True, mono=True), fill=RED)

    body = "The provided guidelines do not address this scenario. Escalating for human review."
    for i, line in enumerate(_wrap(draw, body, _font(22), cw - 80)):
        draw.text((x1 + 32, y1 + 150 + i * 32), line, font=_font(22), fill=MUTED)

    conf_t = min(0.27, 0.27 * min(1.0, t / 0.4))
    _draw_arc(draw, x2 - 100, y1 + 110, 56, conf_t / 0.27, RED, "27%")

    draw.rounded_rectangle([x1 + 32, y2 - 72, x1 + 160, y2 - 36], radius=6, fill=(60, 20, 24), outline=RED)
    draw.text((x1 + 44, y2 - 64), "FLAGGED", font=_font(16, mono=True), fill=RED)
    draw.text((x1 + 180, y2 - 64), "Retries: 0", font=_font(16, mono=True), fill=MUTED)

    zoom = _lerp(1.0, 0.9, _ease(max(0, (t - 0.6) / 0.4)))
    if zoom < 1.0:
        cropped = img.crop([int(W * (1 - zoom) / 2), int(H * (1 - zoom) / 2), int(W * (1 + zoom) / 2), int(H * (1 + zoom) / 2)])
        img = cropped.resize((W, H), Image.Resampling.LANCZOS)

    _caption(img, "Uncertain → flagged for human review.", _ease(max(0, (t - 0.35) / 0.4)))
    return img


def render_clip_07(t: float) -> Image.Image:
    """Close — trust earned."""
    img = _base()
    draw = ImageDraw.Draw(img)
    sx = 420
    draw.ellipse([sx - 50, 260, sx + 50, 360], fill=(35, 50, 65))
    draw.rounded_rectangle([sx - 80, 350, sx + 80, 620], radius=35, fill=(40, 55, 70))
    nod = int(8 * math.sin(min(1.0, t / 0.6) * math.pi))
    draw.ellipse([sx - 50, 260 + nod, sx + 50, 360 + nod], fill=(35, 50, 65))

    mx, my, mw, mh = 720, 160, 980, 560
    inner = _monitor_frame(draw, (mx, my, mx + mw, my + mh))
    x1, y1, x2, y2 = inner
    _draw_pipeline(draw, (x1 + x2) // 2, (y1 + y2) // 2, 3, [TEAL] * 4)
    draw.text((x1, y2 - 48), "4 answered · 1 escalated for review", font=_font(18, mono=True), fill=TEAL)

    fade = max(0.0, (t - 0.75) / 0.25)
    if fade > 0:
        overlay = Image.new("RGB", (W, H), BG)
        img = Image.blend(img, overlay, fade)

    _caption(img, "Safe AI that knows its limits.", _ease(max(0, (t - 0.2) / 0.35)) * (1 - fade))
    return img


def render_title_card(t: float) -> Image.Image:
    """4-second title card."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA").resize((72, 72), Image.Resampling.LANCZOS)
        img.paste(logo, (W // 2 - 36, H // 2 - 160), logo)
        draw = ImageDraw.Draw(img)

    fade_in = _ease(min(1.0, t / 0.2))
    fade_out = 1.0 - _ease(max(0.0, (t - 0.8) / 0.2))
    alpha = fade_in * fade_out

    def col(c: tuple[int, int, int]) -> tuple[int, int, int]:
        return tuple(int(v * alpha) for v in c)

    t1 = "SENTINEL-RAG"
    t2 = "Clinical Protocol Guardian"
    t3 = "github.com/TechieGoku2623/Sentinal_RAG"
    f1, f2, f3 = _font(56, bold=True), _font(24), _font(18, mono=True)
    draw.text((W // 2 - draw.textlength(t1, font=f1) / 2, H // 2 - 40), t1, font=f1, fill=col(TEXT))
    draw.text((W // 2 - draw.textlength(t2, font=f2) / 2, H // 2 + 30), t2, font=f2, fill=col(MUTED))
    draw.text((W // 2 - draw.textlength(t3, font=f3) / 2, H // 2 + 80), t3, font=f3, fill=col(TEAL))
    return img


CLIP_RENDERERS = [
    ("clip_01", render_clip_01, 8.0),
    ("clip_02", render_clip_02, 8.0),
    ("clip_03", render_clip_03, 8.0),
    ("clip_04", render_clip_04, 8.0),
    ("clip_05", render_clip_05, 8.0),
    ("clip_06", render_clip_06, 8.0),
    ("clip_07", render_clip_07, 8.0),
]


def render_frames(fn, duration: float, fps: int = FPS) -> list:
    import numpy as np

    n = max(1, int(duration * fps))
    frames = []
    for i in range(n):
        t = i / max(n - 1, 1)
        frames.append(np.array(fn(t).convert("RGB")))
    return frames
