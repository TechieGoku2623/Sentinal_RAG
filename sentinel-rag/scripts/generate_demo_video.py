"""Generate docs/demo.mp4 — automated product walkthrough video.

Renders UI frames with Pillow (no browser or mic required). Uses the same
story arc as generate_demo_data.py: high-confidence answer, self-correction,
and human escalation.

Run:
    pip install imageio imageio-ffmpeg
    python scripts/generate_demo_video.py

Outputs:
    docs/demo.mp4
    landing/public/demo.mp4
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from generate_demo_gif import DEMO_STEPS, render_frame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DOCS = ROOT / "docs" / "demo.mp4"
OUT_PUBLIC = ROOT / "landing" / "public" / "demo.mp4"
FPS = 24


def build_frames():
    keyframes = [render_frame(step, i) for i, step in enumerate(DEMO_STEPS)]
    frames: list = []
    durations_ms: list[int] = []
    tween_steps = 6

    for i, kf in enumerate(keyframes):
        hold_frames = max(1, int(DEMO_STEPS[i]["frame_ms"] / 1000 * FPS))
        for _ in range(hold_frames):
            frames.append(kf)
        if i < len(keyframes) - 1:
            nxt = keyframes[i + 1]
            for t in range(1, tween_steps + 1):
                from PIL import Image

                alpha = t / (tween_steps + 1)
                frames.append(Image.blend(kf, nxt, alpha))
    return frames


def main() -> None:
    try:
        import imageio.v3 as iio
    except ImportError as exc:
        raise SystemExit(
            "Install video dependencies first:\n  pip install imageio imageio-ffmpeg"
        ) from exc

    frames = build_frames()
    OUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)

    # imageio expects RGB numpy arrays
    arrays = [__import__("numpy").array(f.convert("RGB")) for f in frames]

    for out_path in (OUT_DOCS, OUT_PUBLIC):
        iio.imwrite(
            out_path,
            arrays,
            fps=FPS,
            codec="libx264",
            quality=8,
            pixelformat="yuv420p",
            macro_block_size=1,
        )
        print(f"Wrote {out_path} ({len(arrays)} frames @ {FPS} fps, ~{len(arrays)/FPS:.1f}s)")


if __name__ == "__main__":
    main()
