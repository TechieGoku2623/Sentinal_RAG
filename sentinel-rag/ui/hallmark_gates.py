"""Hallmark slop-test gate scanner — audit verb for Sentinel-RAG targets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[1]

SCAN_TARGETS = [
    ROOT / "landing" / "app" / "globals.css",
    ROOT / "landing" / "app" / "layout.tsx",
    ROOT / "landing" / "app" / "page.tsx",
    ROOT / "landing" / "components" / "HeroMotion.tsx",
    ROOT / "landing" / "components" / "NavMotion.tsx",
    ROOT / "ui" / "theme.py",
    ROOT / "app.py",
]

BANNED_DISPLAY_FONTS = (
    "Inter",
    "Roboto",
    "Open Sans",
    "Poppins",
    "Lato",
)

EMOJI_PATTERN = re.compile(r"[⚑⬡◆◎✨🚀⚡🔥🎯✅👍👎]")


@dataclass
class HallmarkFinding:
    gate: int
    tell: str
    where: str
    severity: str  # critical | major | minor
    fix: str


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def run_hallmark_audit(extra_paths: Iterable[Path] | None = None) -> List[HallmarkFinding]:
    """Score codebase against Hallmark anti-patterns. Punch list only — no edits."""
    findings: List[HallmarkFinding] = []
    paths = list(SCAN_TARGETS)
    if extra_paths:
        paths.extend(extra_paths)

    blobs: list[tuple[str, str]] = []
    for path in paths:
        if path.exists():
            blobs.append((_rel(path), _read(path)))

    combined = "\n".join(text for _, text in blobs)

    design_md = ROOT / "design.md"
    if not design_md.exists():
        findings.append(
            HallmarkFinding(
                gate=0,
                tell="Missing design.md",
                where="project root",
                severity="critical",
                fix="Add design.md per Hallmark multi-page redesign flow.",
            )
        )

    log_path = ROOT / ".hallmark" / "log.json"
    if not log_path.exists():
        findings.append(
            HallmarkFinding(
                gate=0,
                tell="Missing .hallmark/log.json",
                where=".hallmark/",
                severity="minor",
                fix="Initialize project memory for diversification tracking.",
            )
        )

    # Gate 1 — Inter as display
    layout = _read(ROOT / "landing" / "app" / "layout.tsx")
    hero = _read(ROOT / "landing" / "components" / "HeroMotion.tsx")
    theme = _read(ROOT / "ui" / "theme.py")
    if "Space_Grotesk" not in layout and "--font-display" not in layout:
        findings.append(
            HallmarkFinding(
                gate=1,
                tell="Missing Space Grotesk display font",
                where="landing/app/layout.tsx",
                severity="major",
                fix="Load Space Grotesk as display per Cobalt theme.",
            )
        )
    if "Space Grotesk" not in theme:
        findings.append(
            HallmarkFinding(
                gate=1,
                tell="Streamlit theme missing Space Grotesk display",
                where="ui/theme.py",
                severity="minor",
                fix="Import Space Grotesk for headings in inject_theme().",
            )
        )

    # Gate 3 — three equal icon tiles
    page = _read(ROOT / "landing" / "app" / "page.tsx")
    if "lg:grid-cols-4" in page and "PILLARS" in page:
        findings.append(
            HallmarkFinding(
                gate=3,
                tell="Four-equal-column feature grid",
                where="landing/app/page.tsx",
                severity="critical",
                fix="Use asymmetric stat-led or wide+narrow rows — not 4 equal tiles.",
            )
        )

    # Gate 8 — AI template rhythm (soft check)
    if page.count("section") >= 6 and "Pricing" in page and "ThoughtLeadership" in page:
        findings.append(
            HallmarkFinding(
                gate=8,
                tell="Long marketing stack — verify Stat-Led hero breaks template",
                where="landing/app/page.tsx",
                severity="minor",
                fix="Ensure stat figure leads; one graphite band only.",
            )
        )

    # Gate 10 — transition-all
    for rel, text in blobs:
        if "transition-all" in text or "transition: all" in text:
            findings.append(
                HallmarkFinding(
                    gate=10,
                    tell="transition-all",
                    where=rel,
                    severity="major",
                    fix="Specify properties: border-color, opacity, transform — never `all`.",
                )
            )

    # Gate 12 — hover scale
    for rel, text in blobs:
        if "scale-105" in text or "hover:scale" in text:
            findings.append(
                HallmarkFinding(
                    gate=12,
                    tell="Uniform hover scale",
                    where=rel,
                    severity="minor",
                    fix="Remove hover:scale; use border-colour or 1px translate only.",
                )
            )

    # Gate 20 — missing stamp
    globals_css = _read(ROOT / "landing" / "app" / "globals.css")
    tokens_css = _read(ROOT / "landing" / "app" / "tokens.css")
    theme_py = _read(ROOT / "ui" / "theme.py")
    if "Hallmark ·" not in tokens_css:
        findings.append(
            HallmarkFinding(
                gate=20,
                tell="Missing Hallmark CSS stamp on tokens.css",
                where="landing/app/tokens.css",
                severity="major",
                fix="Add Hallmark stamp comment per design.md",
            )
        )
    if "Hallmark ·" not in theme_py:
        findings.append(
            HallmarkFinding(
                gate=20,
                tell="Missing Hallmark stamp on Streamlit theme",
                where="ui/theme.py",
                severity="minor",
                fix="Add Hallmark CSS comment in inject_theme()",
            )
        )

    # Gate 30 — emoji icons
    if EMOJI_PATTERN.search(page):
        findings.append(
            HallmarkFinding(
                gate=30,
                tell="Emoji used as feature icons",
                where="landing/app/page.tsx",
                severity="major",
                fix="Use mono labels or SVG — no emoji value-prop icons.",
            )
        )

    # Gate 34 — overflow-x clip
    if "overflow-x: clip" not in globals_css and "overflow-x: clip" not in tokens_css:
        findings.append(
            HallmarkFinding(
                gate=34,
                tell="Missing overflow-x clip",
                where="landing/app/globals.css",
                severity="critical",
                fix="Set overflow-x: clip on html and body.",
            )
        )

    # Gate 46 — honest metrics (invented stats)
    if "+47%" in combined or "50,000+" in combined or "10× faster" in combined:
        findings.append(
            HallmarkFinding(
                gate=46,
                tell="Invented marketing metrics",
                where="landing/",
                severity="critical",
                fix="Use eval_results.json numbers or labelled placeholders only.",
            )
        )

    # design.md drift — hardcoded hex in tailwind (allowed if tokens mapped)
    tailwind = _read(ROOT / "landing" / "tailwind.config.ts")
    if "#0369A1" in tailwind and "var(--color" not in tailwind:
        findings.append(
            HallmarkFinding(
                gate=48,
                tell="design-system drift — raw hex in Tailwind",
                where="landing/tailwind.config.ts",
                severity="major",
                fix="Map Tailwind colors to CSS variables from tokens.css.",
            )
        )

    return findings


def format_audit_report(findings: List[HallmarkFinding]) -> str:
    crit = sum(1 for f in findings if f.severity == "critical")
    major = sum(1 for f in findings if f.severity == "major")
    minor = sum(1 for f in findings if f.severity == "minor")
    lines = [f"{crit} critical · {major} major · {minor} minor", ""]
    for sev in ("critical", "major", "minor"):
        group = [f for f in findings if f.severity == sev]
        if not group:
            continue
        lines.append(sev.upper())
        for f in group:
            lines.append(f"  Gate {f.gate} · {f.tell}")
            lines.append(f"    Where: {f.where}")
            lines.append(f"    Fix: {f.fix}")
        lines.append("")
    return "\n".join(lines)
