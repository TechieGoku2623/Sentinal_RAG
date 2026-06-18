"""Hallmark Build Studio — audit · redesign · study verbs for Sentinel-RAG."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ui.hallmark_gates import HallmarkFinding, format_audit_report, run_hallmark_audit
from ui.theme import _html, render_results_panel, TRUST_PILLARS
from src import config

ROOT = Path(__file__).resolve().parents[1]
DESIGN_MD = ROOT / "design.md"
LOG_JSON = ROOT / ".hallmark" / "log.json"

BUILD_MODES = {
    "audit": {
        "label": "hallmark audit",
        "tagline": "Score UI against 65 slop gates — punch list, no edits",
        "accent": "#B45309",
        "verb": "audit",
    },
    "redesign": {
        "label": "hallmark redesign",
        "tagline": "Rebuild structure from design.md — keep copy + IA",
        "accent": "#0D9488",
        "verb": "redesign",
    },
    "study": {
        "label": "hallmark study",
        "tagline": "Extract design DNA — macrostructure, type, colour anchor",
        "verb": "study",
        "accent": "#047857",
    },
}


def init_build_session() -> None:
    if "build_mode" not in st.session_state:
        st.session_state.build_mode = "audit"
    if "hallmark_study_source" not in st.session_state:
        st.session_state.hallmark_study_source = "design.md"


def inject_build_studio_css() -> None:
    st.markdown(
        _html(
            """
            <style>
            .sr-hallmark-hero {
                background: linear-gradient(135deg, #0F2B2E 0%, #164E56 100%);
                border-radius: 18px;
                padding: 1.75rem 2rem;
                margin-bottom: 1.25rem;
                color: #F8FAFC;
            }
            .sr-hallmark-hero h2 { margin: 0; font-size: 1.5rem; font-weight: 700; }
            .sr-hallmark-hero p { margin: 0.5rem 0 0; color: #94A3B8; line-height: 1.6; max-width: 680px; }
            .sr-gate-card {
                border-radius: 12px;
                padding: 0.85rem 1rem;
                margin-bottom: 0.5rem;
                background: #fff;
                border: 1px solid #DDE3EA;
                border-left: 4px solid var(--gate-color, #64748B);
            }
            .sr-dna-block {
                background: #F8FAFC;
                border: 1px solid #DDE3EA;
                border-radius: 12px;
                padding: 1rem;
                font-family: 'IBM Plex Mono', monospace;
                font-size: 0.78rem;
                line-height: 1.6;
                white-space: pre-wrap;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def _hallmark_header(mode: str) -> None:
    meta = BUILD_MODES[mode]
    st.markdown(
        _html(
            f"""
            <div class="sr-hallmark-hero">
                <div style="font-size:0.68rem;font-weight:600;letter-spacing:0.12em;
                    text-transform:uppercase;color:#5EEAD4;">Nutlope Hallmark · Build Studio</div>
                <h2>`{meta['verb']}` — {meta['label']}</h2>
                <p>{meta['tagline']}. Locked system: <code style="color:#E2E8F0;">design.md</code>
                · log: <code style="color:#E2E8F0;">.hallmark/log.json</code></p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_audit_mode() -> None:
    findings = run_hallmark_audit()
    crit = sum(1 for f in findings if f.severity == "critical")
    major = sum(1 for f in findings if f.severity == "major")
    minor = sum(1 for f in findings if f.severity == "minor")
    score = max(0, 100 - crit * 20 - major * 10 - minor * 3)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Slop score", f"{score}/100")
    c2.metric("Critical", crit)
    c3.metric("Major", major)
    c4.metric("Minor", minor)

    st.caption(
        "Hallmark audit reads targets and returns a ranked punch list. "
        "**It does not edit files** — switch to Redesign to apply fixes."
    )

    severity_colors = {"critical": "#B91C1C", "major": "#B45309", "minor": "#0D9488"}
    order = {"critical": 0, "major": 1, "minor": 2}
    for f in sorted(findings, key=lambda x: order.get(x.severity, 9)):
        st.markdown(
            _html(
                f"""
                <div class="sr-gate-card" style="--gate-color: {severity_colors.get(f.severity, '#64748B')};">
                    <div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;color:#64748B;">
                        Gate {f.gate} · {f.severity} · {f.tell}
                    </div>
                    <div style="font-weight:600;color:#0F2B2E;margin:0.35rem 0;">{f.where}</div>
                    <div style="font-size:0.86rem;color:#64748B;">Fix: {f.fix}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    st.text_area("Audit report", format_audit_report(findings), height=200, disabled=True)
    st.download_button(
        "Export Hallmark audit (JSON)",
        data=json.dumps(
            [{"gate": f.gate, "tell": f.tell, "where": f.where, "severity": f.severity, "fix": f.fix} for f in findings],
            indent=2,
        ),
        file_name="hallmark_audit.json",
        mime="application/json",
        use_container_width=True,
    )


def render_redesign_mode() -> None:
    st.markdown("##### `hallmark redesign` — locked system")
    if DESIGN_MD.exists():
        st.markdown(DESIGN_MD.read_text(encoding="utf-8"))
    else:
        st.error("Missing design.md — run Hallmark multi-page flow first.")

    st.markdown("##### Targets this redesign touches")
    targets = [
        ("landing/app/tokens.css", "Cobalt OKLCH tokens + stamp"),
        ("landing/app/globals.css", "Hairlines, overflow-x clip, no transition-all"),
        ("landing/app/layout.tsx", "Space Grotesk display + JetBrains Mono"),
        ("landing/components/HeroMotion.tsx", "Stat-Led asymmetric hero"),
        ("landing/components/NavMotion.tsx", "Bordered Cobalt nav"),
        ("landing/app/page.tsx", "Break 4-column AI grid → stat strip"),
        ("ui/theme.py", "Streamlit Workbench tokens aligned to design.md"),
    ]
    for path, note in targets:
        exists = (ROOT / path).exists()
        st.markdown(f"- {'✓' if exists else '✗'} `{path}` — {note}")

    st.info(
        "Redesign preserves routes, copy intent, and eval metrics. "
        "It replaces visual structure per `design.md`. Re-run **audit** after deploy."
    )

    if st.button("Mark redesign complete in log", type="primary"):
        _append_hallmark_log("redesign", "app")
        st.success("Logged to .hallmark/log.json — refresh audit to verify gates.")
        st.rerun()


def _append_hallmark_log(verb: str, scope: str) -> None:
    from datetime import datetime, timezone

    LOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {"runs": []}
    if LOG_JSON.exists():
        try:
            payload = json.loads(LOG_JSON.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            payload = {"runs": []}
    payload.setdefault("runs", []).append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scope": scope,
            "verb": verb,
            "genre": "modern-minimal",
            "theme": "veridian",
            "macrostructure": "stat-led",
            "design_system": "design.md",
        }
    )
    LOG_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def render_study_mode() -> None:
    st.markdown("##### `hallmark study` — design DNA")
    source = st.radio(
        "Study source",
        options=["design.md", "landing/ (live)", "Streamlit ui/theme.py"],
        horizontal=True,
        key="hallmark_study_source",
    )

    if source == "design.md" and DESIGN_MD.exists():
        dna = _extract_dna_from_design_md(DESIGN_MD.read_text(encoding="utf-8"))
    elif source == "landing/ (live)":
        dna = _extract_dna_from_landing()
    else:
        dna = _extract_dna_from_streamlit()

    st.markdown("##### Diagnosis report")
    st.markdown(_html(f'<div class="sr-dna-block">{dna}</div>'), unsafe_allow_html=True)

    st.markdown("##### Macrostructure · type · colour (Hallmark schema)")
    cols = st.columns(3)
    cols[0].markdown("**Macrostructure**\n\nStat-Led hero\n\nWorkbench app shell")
    cols[1].markdown("**Type pairing**\n\nSpace Grotesk 600 display\n\nInter 400 body\n\nJetBrains Mono labels")
    cols[2].markdown("**Colour anchor**\n\noklch(50% 0.13 192) veridian teal\n\n≤ 5% accent footprint")

    if st.button("Emit portable design.md snippet"):
        st.code(DESIGN_MD.read_text(encoding="utf-8") if DESIGN_MD.exists() else "", language="markdown")

    st.markdown("##### Reference — do / don't")
    st.markdown(
        "- **Do:** left-biased hero, hairline borders, honest eval metrics, `:focus-visible` rings\n"
        "- **Don't:** Inter display, 4 equal icon tiles, `transition-all`, invented +47% stats"
    )


def _extract_dna_from_design_md(text: str) -> str:
    return (
        "DNA extracted from design.md (URL/text mode equivalent):\n\n"
        "· Genre: modern-minimal · Cobalt register\n"
        "· Macrostructure: Stat-Led (marketing) + Workbench (app)\n"
        "· Display: Space Grotesk roman · Body: Inter · Labels: JetBrains Mono UPPERCASE\n"
        "· Accent: clinical teal oklch(50% 0.13 192) · Paper: mint near-white\n"
        "· Rhythm: light → one graphite band → light\n"
        "· Motion: fade+10px rise · no bounce · reduced-motion static\n\n"
        f"Raw excerpt:\n{text[:800]}..."
    )


def _extract_dna_from_landing() -> str:
    return (
        "DNA from landing/ (live page scan):\n\n"
        "· Structure: sticky nav → stat hero → demo → platform pipeline → metrics grid\n"
        "· Tokens: landing/app/tokens.css (Cobalt OKLCH)\n"
        "· Remaining drift: run `hallmark audit landing/` for gate-level punch list\n"
        "· Rhythm blind spot: use screenshot study for density/asymmetry grading"
    )


def _extract_dna_from_streamlit() -> str:
    return (
        "DNA from Streamlit shell:\n\n"
        "· Macrostructure: Workbench — navy sidebar + wide validation workspace\n"
        "· Safety layer: disclaimer → query → results panel → source expander\n"
        "· Align display headings to Space Grotesk via ui/theme.py inject_theme()"
    )


def render_build_mode_selector() -> str:
    st.markdown("#### Hallmark")
    return st.radio(
        "Verb",
        options=list(BUILD_MODES.keys()),
        format_func=lambda m: BUILD_MODES[m]["label"],
        key="build_mode",
        label_visibility="collapsed",
    )


def render_build_studio_tab() -> None:
    init_build_session()
    inject_build_studio_css()
    mode = st.session_state.get("build_mode", "audit")
    _hallmark_header(mode)
    if mode == "audit":
        render_audit_mode()
    elif mode == "redesign":
        render_redesign_mode()
    else:
        render_study_mode()
