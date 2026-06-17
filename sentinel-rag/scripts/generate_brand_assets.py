"""Generate Sentinel-RAG brand assets (logo PNG, favicon, apple touch icon).

Outputs to docs/brand/ and copies to docs/screenshots/ and landing/public/.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "docs" / "brand"
SCREENSHOTS = ROOT / "docs" / "screenshots"
LANDING_PUBLIC = ROOT / "landing" / "public"

NAVY = (10, 22, 40)
SLATE = (71, 85, 105)
SLATE_DARK = (51, 65, 85)
STROKE = (226, 232, 240)
ACCENT = (14, 165, 233)


def _draw_logo(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size // 16
    radius = size // 5
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        fill=NAVY,
    )

    cx = size // 2
    top = int(size * 0.17)
    bottom = int(size * 0.83)
    wing = int(size * 0.27)
    mid_y = int(size * 0.30)
    shield = [
        (cx, top),
        (cx + wing, mid_y),
        (cx + wing, int(size * 0.54)),
        (cx, bottom),
        (cx - wing, int(size * 0.54)),
        (cx - wing, mid_y),
    ]
    draw.polygon(shield, outline=STROKE, width=max(2, size // 36))

    check = [
        (int(size * 0.38), int(size * 0.51)),
        (int(size * 0.46), int(size * 0.59)),
        (int(size * 0.62), int(size * 0.42)),
    ]
    draw.line(check, fill=ACCENT, width=max(3, size // 28), joint="curve")

    line_y1 = int(size * 0.69)
    line_y2 = int(size * 0.75)
    inset = int(size * 0.33)
    draw.line(
        [(inset, line_y1), (size - inset, line_y1)],
        fill=SLATE,
        width=max(2, size // 52),
    )
    draw.line(
        [(inset + size // 20, line_y2), (size - inset - size // 20, line_y2)],
        fill=SLATE_DARK,
        width=max(2, size // 52),
    )
    return img


def _save_ico(path: Path, base: Image.Image) -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    icons = [base.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
    icons[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:],
    )


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    LANDING_PUBLIC.mkdir(parents=True, exist_ok=True)

    logo_512 = _draw_logo(512)
    logo_512.save(BRAND / "logo.png", "PNG")
    logo_512.resize((128, 128), Image.Resampling.LANCZOS).save(BRAND / "logo-sm.png", "PNG")
    logo_512.resize((180, 180), Image.Resampling.LANCZOS).save(BRAND / "apple-touch-icon.png", "PNG")
    _save_ico(BRAND / "favicon.ico", logo_512)

    svg_src = BRAND / "logo.svg"
    targets = [
        SCREENSHOTS / "logo.png",
        SCREENSHOTS / "favicon.ico",
        SCREENSHOTS / "apple-touch-icon.png",
        LANDING_PUBLIC / "logo.png",
        LANDING_PUBLIC / "favicon.ico",
        LANDING_PUBLIC / "apple-touch-icon.png",
    ]
    shutil.copy2(BRAND / "logo.png", targets[0])
    shutil.copy2(BRAND / "favicon.ico", targets[1])
    shutil.copy2(BRAND / "apple-touch-icon.png", targets[2])
    shutil.copy2(BRAND / "logo.png", targets[3])
    shutil.copy2(BRAND / "favicon.ico", targets[4])
    shutil.copy2(BRAND / "apple-touch-icon.png", targets[5])
    if svg_src.exists():
        shutil.copy2(svg_src, LANDING_PUBLIC / "logo.svg")

    print(f"Brand assets written to {BRAND}")
    print(f"Copied to {SCREENSHOTS} and {LANDING_PUBLIC}")


if __name__ == "__main__":
    main()
