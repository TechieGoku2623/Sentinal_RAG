# Supported video formats

Sentinel-RAG walkthrough exports use **web-safe, universally supported** codecs.

## Generated files

| File | Codec | Best for |
| ---- | ----- | -------- |
| `walkthrough.mp4` | **H.264** (AVC) · yuv420p · faststart | GitHub, LinkedIn, Twitter/X, Safari, iOS, Windows Media Player, PowerPoint |
| `walkthrough.webm` | **VP9** · yuv420p | Chrome, Firefox, Edge, HTML5 `<video>` fallback |
| `walkthrough-product.mp4` | H.264 (32s cut) | README / technical demo (clips 03–06) |
| `demo.mp4` | H.264 (~12s) | Short product preview |
| `demo.gif` | GIF | GitHub markdown preview (no video player needed) |

Regenerate:

```powershell
pip install -r requirements-video.txt
python scripts/generate_walkthrough_video.py
```

## Platform compatibility

| Platform | Recommended format |
| -------- | ------------------ |
| **GitHub README** | Link to `walkthrough.mp4` or use `demo.gif` |
| **LinkedIn native upload** | `walkthrough.mp4` (H.264, 1080p, 16:9) |
| **Next.js landing page** | Both WebM + MP4 in `<video>` (auto-fallback) |
| **Loom / YouTube embed** | Upload MP4 or record in-browser |
| **PowerPoint / Keynote** | Insert → Video → `walkthrough.mp4` |
| **WhatsApp / Slack** | `walkthrough.mp4` |

## Technical specs (full walkthrough)

| Setting | Value |
| ------- | ----- |
| Resolution | 1920 × 1080 (1080p) |
| Aspect ratio | 16:9 |
| Frame rate | 24 fps |
| Pixel format | yuv420p (required for Safari / iOS) |
| MP4 profile | H.264 High / faststart (streaming-friendly) |
| Duration | ~58s (7 clips + title) |
| Audio | None (add music in CapCut / DaVinci) |

## HTML embed (copy-paste)

```html
<video controls playsinline poster="/logo.png" width="100%">
  <source src="/walkthrough.webm" type="video/webm" />
  <source src="/walkthrough.mp4" type="video/mp4" />
</video>
```

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| Video won't play in Safari | Regenerate with `python scripts/generate_walkthrough_video.py` (yuv420p + faststart) |
| Black screen in browser | Hard-refresh; confirm `landing/public/walkthrough.mp4` exists |
| GitHub README won't autoplay | Use a download link or `demo.gif` instead |
| File too large for upload | Use `--product-only` for 32s cut, or re-encode: `ffmpeg -i walkthrough.mp4 -vf scale=1280:720 walkthrough-720p.mp4` |
