"""Assemble the 7-clip Sentinel-RAG walkthrough video with MoviePy + Pillow.

Renders the full storyboard from docs/VEO_VIDEO_PROMPTS.md without Google Veo:
  Hook → Problem → Activates → High confidence → Retry → Flagged → Close → Title

Run:
    pip install -r requirements-video.txt
    python scripts/generate_walkthrough_video.py

Outputs:
    docs/walkthrough.mp4
    landing/public/walkthrough.mp4
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from walkthrough_frames import (  # noqa: E402
    CLIP_RENDERERS,
    FPS,
    render_frames,
    render_title_card,
)

OUT_DOCS = ROOT / "docs" / "walkthrough.mp4"
OUT_PUBLIC = ROOT / "landing" / "public" / "walkthrough.mp4"


def _clip(name: str, fn, duration: float, fps: int):
    from moviepy import ImageSequenceClip

    print(f"Rendering {name} ({duration}s @ {fps} fps)...")
    return ImageSequenceClip(render_frames(fn, duration, fps), fps=fps)


def build_video(fps: int = FPS, include_title: bool = True):
    from moviepy import ColorClip, concatenate_videoclips
    from moviepy.video.fx import CrossFadeIn

    parts = []
    for i, (name, fn, duration) in enumerate(CLIP_RENDERERS):
        clip = _clip(name, fn, duration, fps)
        if name == "clip_03":
            clip = clip.with_effects([CrossFadeIn(0.3)])
        parts.append(clip)

        if name == "clip_01":
            parts.append(ColorClip(size=(1920, 1080), color=(0, 0, 0)).with_duration(0.5))
        if name == "clip_04":
            last = clip.get_frame(max(0, clip.duration - 0.05))
            from moviepy import ImageSequenceClip

            parts.append(ImageSequenceClip([last], fps=fps).with_duration(0.5))

    if include_title:
        print("Rendering title card (4s)...")
        parts.append(_clip("title", render_title_card, 4.0, fps))

    return concatenate_videoclips(parts, method="compose", padding=-0.3 if len(parts) > 2 else 0)


def build_product_demo(fps: int = FPS):
    from moviepy import ImageSequenceClip, concatenate_videoclips

    parts = [_clip(name, fn, dur, fps) for name, fn, dur in CLIP_RENDERERS[2:6]]
    return concatenate_videoclips(parts, method="compose")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Sentinel-RAG walkthrough MP4.")
    parser.add_argument("--fps", type=int, default=FPS, help="Frames per second (default 24).")
    parser.add_argument("--no-title", action="store_true", help="Skip 4s title card.")
    parser.add_argument(
        "--product-only",
        action="store_true",
        help="Clips 03–06 only (~32s product demo for README).",
    )
    args = parser.parse_args()

    video = (
        build_product_demo(fps=args.fps)
        if args.product_only
        else build_video(fps=args.fps, include_title=not args.no_title)
    )

    OUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing {OUT_DOCS} (~{video.duration:.1f}s)...")
    video.write_videofile(
        str(OUT_DOCS),
        fps=args.fps,
        codec="libx264",
        audio=False,
        preset="medium",
        ffmpeg_params=["-pix_fmt", "yuv420p"],
        logger=None,
    )

    shutil.copy2(OUT_DOCS, OUT_PUBLIC)
    print(f"Copied to {OUT_PUBLIC}")
    print("Done.")


if __name__ == "__main__":
    main()
