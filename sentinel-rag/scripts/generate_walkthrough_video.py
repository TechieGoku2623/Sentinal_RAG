"""Assemble the 7-clip Sentinel-RAG walkthrough video with MoviePy + Pillow.

Renders the full storyboard from docs/VEO_VIDEO_PROMPTS.md without Google Veo:
  Hook → Problem → Activates → High confidence → Retry → Flagged → Close → Title

Run:
    pip install -r requirements-video.txt
    python scripts/generate_walkthrough_video.py

Outputs:
    docs/walkthrough.mp4      — H.264 (universal: GitHub, LinkedIn, Safari, Windows)
    docs/walkthrough.webm     — VP9 (web fallback: Chrome, Firefox, Edge)
    landing/public/           — copies for Next.js static embed
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from walkthrough_frames import (  # noqa: E402
    ALL_CLIP_RENDERERS,
    BONUS_CLIP_RENDERERS,
    CLIP_RENDERERS,
    FPS,
    render_frames,
    render_title_card,
)

OUT_DOCS = ROOT / "docs" / "walkthrough.mp4"
OUT_PUBLIC = ROOT / "landing" / "public"


def _write_mp4(video, path: Path, fps: int) -> None:
    """H.264 MP4 - universal (GitHub, LinkedIn, Safari, Chrome, Windows)."""
    video.write_videofile(
        str(path),
        fps=fps,
        codec="libx264",
        audio=False,
        preset="medium",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger=None,
    )


def _write_webm_from_mp4(mp4_path: Path, webm_path: Path) -> bool:
    """Transcode MP4 to WebM VP9 using bundled ffmpeg (imageio-ffmpeg)."""
    import subprocess

    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("WebM skipped: pip install imageio-ffmpeg")
        return False

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(mp4_path),
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "32",
        "-b:v",
        "0",
        str(webm_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return webm_path.exists()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"WebM skipped: {exc}")
        return False


def _write_webm(video, path: Path, fps: int) -> None:
    """WebM VP9 - open web fallback (Firefox, Chrome, Edge)."""
    tmp_mp4 = path.with_suffix(".tmp.mp4")
    try:
        _write_mp4(video, tmp_mp4, fps)
        if _write_webm_from_mp4(tmp_mp4, path):
            return
    finally:
        tmp_mp4.unlink(missing_ok=True)
    # Direct encode fallback
    try:
        video.write_videofile(
            str(path),
            fps=fps,
            codec="libvpx-vp9",
            audio=False,
            ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "32", "-b:v", "0"],
            logger=None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"WebM skipped ({exc}).")


def export_formats(video, fps: int, *, stem: str = "walkthrough") -> dict[str, Path]:
    """Export walkthrough in all supported delivery formats."""
    docs_dir = ROOT / "docs"
    public_dir = OUT_PUBLIC
    docs_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    mp4_docs = docs_dir / f"{stem}.mp4"
    mp4_public = public_dir / f"{stem}.mp4"

    print(f"Writing MP4 (H.264 / yuv420p / faststart) -> {mp4_docs} (~{video.duration:.1f}s)...")
    _write_mp4(video, mp4_docs, fps)
    shutil.copy2(mp4_docs, mp4_public)
    outputs["mp4"] = mp4_docs

    webm_docs = docs_dir / f"{stem}.webm"
    webm_public = public_dir / f"{stem}.webm"
    print(f"Writing WebM (VP9) -> {webm_docs}...")
    if _write_webm_from_mp4(mp4_docs, webm_docs):
        shutil.copy2(webm_docs, webm_public)
        outputs["webm"] = webm_docs

    return outputs


def _clip(name: str, fn, duration: float, fps: int):
    from moviepy import ImageSequenceClip

    print(f"Rendering {name} ({duration}s @ {fps} fps)...")
    return ImageSequenceClip(render_frames(fn, duration, fps), fps=fps)


def build_video(fps: int = FPS, include_title: bool = True, include_bonus: bool = False):
    from moviepy import ColorClip, ImageSequenceClip, concatenate_videoclips
    from moviepy.video.fx import CrossFadeIn

    clip_list = list(CLIP_RENDERERS)
    if include_bonus:
        clip_list = clip_list + list(BONUS_CLIP_RENDERERS)

    parts = []
    for name, fn, duration in clip_list:
        clip = _clip(name, fn, duration, fps)
        if name == "clip_03":
            clip = clip.with_effects([CrossFadeIn(0.3)])
        parts.append(clip)

        if name == "clip_01":
            parts.append(ColorClip(size=(1920, 1080), color=(0, 0, 0)).with_duration(0.5))
        if name == "clip_04":
            last = clip.get_frame(max(0, clip.duration - 0.05))
            parts.append(ImageSequenceClip([last], fps=fps).with_duration(0.5))

    if include_title:
        print("Rendering title card (4s)...")
        parts.append(_clip("title", render_title_card, 4.0, fps))

    return concatenate_videoclips(parts, method="compose", padding=-0.3 if len(parts) > 2 else 0)


def export_individual_clips(fps: int = FPS) -> None:
    """Write each clip as a separate MP4 under docs/walkthrough_clips/."""
    out_dir = ROOT / "docs" / "walkthrough_clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fn, duration in ALL_CLIP_RENDERERS:
        clip = _clip(name, fn, duration, fps)
        path = out_dir / f"{name}.mp4"
        print(f"Exporting {path}...")
        _write_mp4(clip, path, fps)
    print(f"All clips written to {out_dir}")


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
        help="Clips 03-06 only (~32s product demo for README).",
    )
    parser.add_argument(
        "--with-bonus",
        action="store_true",
        help="Append bonus clips A/B/C after clip 07 (~82s total with title).",
    )
    parser.add_argument(
        "--export-clips",
        action="store_true",
        help="Export each clip separately to docs/walkthrough_clips/.",
    )
    args = parser.parse_args()

    if args.export_clips:
        export_individual_clips(fps=args.fps)

    if args.product_only:
        video = build_product_demo(fps=args.fps)
        stem = "walkthrough-product"
    else:
        video = build_video(
            fps=args.fps,
            include_title=not args.no_title,
            include_bonus=args.with_bonus,
        )
        stem = "walkthrough-full" if args.with_bonus else "walkthrough"

    outputs = export_formats(video, args.fps, stem=stem)
    print("\nSupported formats written:")
    for fmt, path in outputs.items():
        kb = path.stat().st_size // 1024
        print(f"  {fmt.upper():5}  {path}  ({kb} KB)")

    if args.with_bonus and "mp4" in outputs:
        shutil.copy2(outputs["mp4"], ROOT / "docs" / "walkthrough.mp4")
        shutil.copy2(outputs["mp4"], OUT_PUBLIC / "walkthrough.mp4")
        if "webm" in outputs:
            shutil.copy2(outputs["webm"], ROOT / "docs" / "walkthrough.webm")
            shutil.copy2(outputs["webm"], OUT_PUBLIC / "walkthrough.webm")
        print("Full cut also copied to docs/walkthrough.mp4 + .webm (landing embed).")

    print("\nClips: docs/walkthrough_clips/clip_01.mp4 ... bonus_c.mp4 (use --export-clips)")


if __name__ == "__main__":
    main()
