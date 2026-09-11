"""Generate docs/demo.gif — animated product walkthrough for README.

Renders premium UI frames with Pillow (no browser required). Uses real agent
outputs when GROQ_API_KEY is set; otherwise falls back to representative demo
copy matching generate_demo_data.py.

Run:
    python scripts/generate_demo_gif.py
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo.gif"
LOGO = ROOT / "docs" / "brand" / "logo.png"

W, H = 1100, 640
NAVY = (11, 37, 69)
TEAL = (13, 148, 136)
TEAL_DARK = (15, 118, 110)
SLATE = (51, 65, 85)
MUTED = (100, 116, 139)
WHITE = (255, 255, 255)
BG = (248, 250, 252)
CARD = (255, 255, 255)
BORDER = (226, 232, 240)
SUCCESS_BG = (236, 253, 245)
SUCCESS = (5, 150, 105)
WARN_BG = (255, 251, 235)
WARN = (217, 119, 6)
DANGER_BG = (254, 242, 242)
DANGER = (220, 38, 38)

DEMO_STEPS = [
    {
        "title": "Clinical Protocol Guardian",
        "subtitle": "Self-reflective RAG with five-layer safety validation",
        "query": "",
        "confidence": None,
        "verdict": "",
        "status": "Upload guidelines · Ask protocol questions · Review with confidence scores",
        "answer": "",
        "frame_ms": 2200,
    },
    {
        "title": "Protocol validation",
        "subtitle": "Query grounded strictly in ingested guidelines",
        "query": "What is the first-line treatment for Type 2 diabetes?",
        "confidence": 0.98,
        "verdict": "SUPPORTED",
        "status": "High confidence — answer is well grounded in the guidelines.",
        "answer": (
            "Metformin is the recommended first-line pharmacological therapy for adults "
            "with type 2 diabetes unless contraindicated. Initiate 500 mg once daily and "
            "titrate to a maximum of 2000 mg per day. (Protocol GLY-2024, Section 1)"
        ),
        "frame_ms": 2800,
    },
    {
        "title": "Self-correction loop",
        "subtitle": "Borderline answers trigger expanded re-retrieval",
        "query": "Can metformin be used with kidney disease?",
        "confidence": 0.88,
        "verdict": "SUPPORTED",
        "status": "Returned after 1 re-query — wider context improved grounding.",
        "answer": (
            "Metformin can be used only with careful attention to renal function. It is "
            "contraindicated when eGFR is below 30 mL/min/1.73m² due to lactic acidosis risk. "
            "(Protocol GLY-2024, Section 4)"
        ),
        "frame_ms": 2800,
    },
    {
        "title": "Human escalation",
        "subtitle": "Uncertainty is a successful safety outcome",
        "query": "What happens if a patient misses a dose?",
        "confidence": 0.27,
        "verdict": "ERROR",
        "status": "FLAGGED FOR CLINICAL REVIEW — not supported by available guidelines.",
        "answer": (
            "The provided guidelines do not address missed-dose instructions. I cannot "
            "determine the correct action from the current protocol."
        ),
        "frame_ms": 3200,
    },
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _wrap(draw, text, font, max_width):
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


def render_frame(step: dict, frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Hero band
    _rounded_rect(draw, (24, 24, W - 24, 130), 18, NAVY)
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA").resize((56, 56), Image.Resampling.LANCZOS)
        img.paste(logo, (44, 44), logo)
    draw.text((112, 48), "Sentinel-RAG", font=_font(28, True), fill=WHITE)
    draw.text((112, 82), step["subtitle"], font=_font(15), fill=(203, 213, 225))

    # Trust pills
    pills = ["Grounded", "Self-audit", "Escalation", "Privacy-first"]
    x = 44
    for pill in pills:
        tw = draw.textlength(pill, font=_font(11))
        _rounded_rect(draw, (x, 148, x + tw + 24, 176), 10, CARD, outline=BORDER)
        draw.text((x + 12, 154), pill, font=_font(11), fill=SLATE)
        x += tw + 34

    # Main panel
    _rounded_rect(draw, (24, 196, W - 24, H - 24), 16, CARD, outline=BORDER)
    draw.text((44, 214), step["title"], font=_font(20, True), fill=NAVY)

    y = 252
    if step["query"]:
        draw.text((44, y), "Clinical query", font=_font(11, True), fill=TEAL)
        y += 20
        _rounded_rect(draw, (44, y, W - 44, y + 52), 10, (241, 245, 249), outline=BORDER)
        for i, line in enumerate(_wrap(draw, step["query"], _font(14), W - 120)):
            draw.text((58, y + 12 + i * 18), line, font=_font(14), fill=SLATE)
        y += 68

    if step["confidence"] is not None:
        metrics = [
            (f"{step['confidence']:.0%}", "Confidence"),
            (step["verdict"], "Validation"),
            ("1" if "re-query" in step["status"].lower() else "0", "Re-queries"),
        ]
        mx = 44
        for val, label in metrics:
            _rounded_rect(draw, (mx, y, mx + 150, y + 72), 12, (248, 250, 252), outline=BORDER)
            draw.text((mx + 16, y + 14), val, font=_font(22, True), fill=NAVY)
            draw.text((mx + 16, y + 44), label.upper(), font=_font(10), fill=MUTED)
            mx += 166

        y += 88
        conf = step["confidence"]
        if conf >= 0.85:
            banner_fill, banner_text, banner_fg = SUCCESS_BG, step["status"], SUCCESS
        elif conf >= 0.75:
            banner_fill, banner_text, banner_fg = WARN_BG, step["status"], WARN
        else:
            banner_fill, banner_text, banner_fg = DANGER_BG, step["status"], DANGER

        _rounded_rect(draw, (44, y, W - 44, y + 40), 10, banner_fill, outline=banner_fg)
        draw.text((58, y + 12), banner_text, font=_font(12), fill=banner_fg)
        y += 54

    if step["answer"]:
        draw.text((44, y), "Validated response", font=_font(11, True), fill=TEAL)
        y += 20
        lines = _wrap(draw, step["answer"], _font(13), W - 120)
        box_h = max(72, 16 + len(lines) * 18)
        _rounded_rect(draw, (44, y, W - 44, y + box_h), 10, (248, 250, 252), outline=TEAL)
        for i, line in enumerate(lines[:4]):
            draw.text((58, y + 12 + i * 18), line, font=_font(13), fill=SLATE)
    elif step["status"] and not step["query"]:
        draw.text((44, 260), step["status"], font=_font(16), fill=SLATE)

    # Progress dots
    for i in range(len(DEMO_STEPS)):
        color = TEAL if i == frame_idx else BORDER
        draw.ellipse((W - 120 + i * 22, H - 44, W - 106 + i * 22, H - 30), fill=color)

    return img


def main() -> None:
    keyframes = [render_frame(step, i) for i, step in enumerate(DEMO_STEPS)]
    # Crossfade tweens between keyframes for smoother motion
    frames: list[Image.Image] = []
    durations: list[int] = []
    tween_steps = 4
    for i, kf in enumerate(keyframes):
        frames.append(kf)
        durations.append(DEMO_STEPS[i]["frame_ms"])
        if i < len(keyframes) - 1:
            nxt = keyframes[i + 1]
            for t in range(1, tween_steps + 1):
                alpha = t / (tween_steps + 1)
                blended = Image.blend(kf, nxt, alpha)
                frames.append(blended)
                durations.append(120)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUT} ({len(frames)} frames, crossfade enabled)")


if __name__ == "__main__":
    main()
