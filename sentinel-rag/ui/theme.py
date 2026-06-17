"""Professional healthcare UI theme for Sentinel-RAG.

Enterprise clinical visual language: restrained navy palette, crisp typography,
and accessible status semantics suitable for regulated healthcare demos.
"""

from __future__ import annotations

import base64
import os
import textwrap

import streamlit as st

# Brand assets (generated via scripts/generate_brand_assets.py)
_BRAND_ROOT = os.path.join(os.path.dirname(__file__), "..", "docs", "brand")
_SCREENSHOTS_ROOT = os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots")
LOGO_PATH = os.path.join(_BRAND_ROOT, "logo.png")
FAVICON_PATH = os.path.join(_BRAND_ROOT, "favicon.ico")
LOGO_FALLBACK = os.path.join(_SCREENSHOTS_ROOT, "logo.png")


def _resolve_logo_path() -> str | None:
    for path in (LOGO_PATH, LOGO_FALLBACK):
        if os.path.exists(path):
            return path
    return None


def _logo_data_uri() -> str:
    path = _resolve_logo_path()
    if not path:
        return ""
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return f"data:image/png;base64,{b64}"


# Design tokens
BRAND_NAME = "Sentinel-RAG"
BRAND_TAGLINE = "Clinical Protocol Guardian"
BRAND_SUBTITLE = (
    "Enterprise self-reflective RAG for guideline-grounded clinical protocol "
    "validation and audit-ready decision support."
)
SAMPLE_QUERIES = [
    "What is the first-line therapy for type 2 diabetes?",
    "What are metformin contraindications?",
    "What is the HbA1c target for elderly patients?",
    "Can metformin be used with kidney disease?",
]

TRUST_PILLARS = [
    ("Grounded answers", "Strict context-only generation with source citations."),
    ("Self-audit loop", "Deterministic confidence scoring before every response."),
    ("Human escalation", "Low-confidence outputs flagged for clinical review."),
    ("Privacy-first", "Local vector store and on-prem-capable architecture."),
]

SAFETY_LAYERS = [
    ("Retrieve", "Parent-child ChromaDB search over your guideline corpus."),
    ("Generate", "Llama 3.1 8B with a strict clinical prompt contract."),
    ("Reflect", "Four-factor deterministic grounding score."),
    ("Validate", "Independent second-model fact-check."),
    ("Govern", "Recency warnings, audit logs, and human feedback."),
]


def _html(body: str) -> str:
    """Prepare HTML for ``st.markdown(..., unsafe_allow_html=True)``.

    ``textwrap.dedent`` only removes the shared outer indent. Nested markup
    still leaves lines starting with 4+ spaces, which Streamlit Markdown renders
    as a fenced code block — so raw ``<div>`` tags appear on screen as text.
    """
    dedented = textwrap.dedent(body).strip()
    return "\n".join(line.lstrip() for line in dedented.splitlines())


from src.text_utils import extract_clinical_answer, format_review_banner, normalize_prose as _normalize_prose


def render_review_status(
    flagged: bool,
    confidence: float,
    verdict: str,
    flag_reason: str,
    retry_count: int,
    high: float,
    medium: float,
) -> None:
    """Native Streamlit status — always visible (not embedded in HTML blocks)."""
    title, body = format_review_banner(
        flagged, confidence, verdict, flag_reason, retry_count, high, medium,
    )
    message = f"**{title}** — {body}"
    if flagged:
        st.error(message)
    elif confidence >= high:
        st.success(message)
    elif confidence >= medium:
        st.warning(message)
    else:
        st.info(message)


def inject_theme() -> None:
    """Inject global CSS for a premium clinical interface."""
    st.markdown(
        _html(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;1,14..32,400&family=IBM+Plex+Mono:wght@400;500&display=swap');

        :root {
            --sr-navy: #0A1628;
            --sr-navy-mid: #142842;
            --sr-blue: #0369A1;
            --sr-blue-light: #0EA5E9;
            --sr-slate: #1E293B;
            --sr-muted: #64748B;
            --sr-bg: #F4F6F9;
            --sr-bg-subtle: #EEF2F6;
            --sr-card: #FFFFFF;
            --sr-border: #DDE3EA;
            --sr-success: #047857;
            --sr-warning: #B45309;
            --sr-danger: #B91C1C;
            --sr-shadow: 0 1px 2px rgba(10, 22, 40, 0.04), 0 8px 24px rgba(10, 22, 40, 0.06);
        }

        .stApp {
            background: var(--sr-bg);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: var(--sr-slate);
        }
        @keyframes srFadeUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes srFadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes srScaleIn {
            from { opacity: 0; transform: scale(0.96); }
            to { opacity: 1; transform: scale(1); }
        }
        @keyframes srShimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        @keyframes srPulse {
            0%, 100% { opacity: 0.45; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.06); }
        }
        @keyframes srRingDraw {
            from { stroke-dashoffset: 283; }
            to { stroke-dashoffset: var(--target, 0); }
        }
        @keyframes srProgressFill {
            from { width: 0; }
        }
        @keyframes srStepGlow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(13,148,136,0.35); }
            50% { box-shadow: 0 0 0 10px rgba(13,148,136,0); }
        }
        @keyframes srFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }

        .sr-animate-in { animation: srFadeUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) both; }
        .sr-animate-in-delay-1 { animation-delay: 0.08s; }
        .sr-animate-in-delay-2 { animation-delay: 0.16s; }
        .sr-animate-in-delay-3 { animation-delay: 0.24s; }
        .sr-animate-in-delay-4 { animation-delay: 0.32s; }
        .sr-results-panel { animation: srScaleIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) both; }

        [data-testid="stSidebar"] {
            background: var(--sr-navy);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        [data-testid="stSidebar"] * {
            color: #F1F5F9 !important;
        }
        [data-testid="stSidebar"] .stMarkdown h1,
        [data-testid="stSidebar"] .stMarkdown h2,
        [data-testid="stSidebar"] .stMarkdown h3,
        [data-testid="stSidebar"] .stMarkdown h4 {
            color: #FFFFFF !important;
            font-weight: 600;
            letter-spacing: -0.015em;
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.1);
        }
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 0.5rem 0.75rem;
        }
        .sr-sidebar-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 0.25rem 0 1rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 1rem;
        }
        .sr-sidebar-brand img {
            width: 48px;
            height: 48px;
            border-radius: 10px;
            flex-shrink: 0;
        }
        .sr-sidebar-brand .name {
            font-size: 0.95rem;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .sr-sidebar-brand .tagline {
            font-size: 0.72rem;
            font-weight: 500;
            color: #94A3B8;
            margin-top: 2px;
        }
        .block-container {
            padding-top: 1.5rem;
            max-width: 1100px;
        }

        .sr-hero {
            background: var(--sr-card);
            border-radius: 16px;
            padding: 1.75rem 2rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--sr-shadow);
            border: 1px solid var(--sr-border);
            border-left: 4px solid var(--sr-blue);
            color: var(--sr-slate);
            animation: srFadeUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        .sr-hero-badge {
            display: inline-block;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--sr-blue);
            background: #EFF6FF;
            border: 1px solid #BFDBFE;
            border-radius: 6px;
            padding: 0.3rem 0.75rem;
            margin-bottom: 0.85rem;
        }
        .sr-hero h1 {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin: 0 0 0.5rem 0;
            color: var(--sr-navy);
        }
        .sr-hero h1 span {
            display: block;
            font-size: 0.55em;
            font-weight: 600;
            color: var(--sr-muted);
            margin-top: 0.15rem;
        }
        .sr-hero p {
            font-size: 0.98rem;
            line-height: 1.65;
            color: var(--sr-muted);
            margin: 0;
            max-width: 720px;
        }
        .sr-hero-logo {
            width: 52px;
            height: 52px;
            border-radius: 12px;
            flex-shrink: 0;
            box-shadow: 0 4px 12px rgba(10, 22, 40, 0.12);
        }
        .sr-trust-bar {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }
        @media (max-width: 900px) {
            .sr-trust-bar { grid-template-columns: repeat(2, 1fr); }
        }
        .sr-trust-card {
            background: var(--sr-card);
            border: 1px solid var(--sr-border);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: var(--sr-shadow);
            animation: srFadeUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
        }
        .sr-trust-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(10, 22, 40, 0.08);
            border-color: rgba(3, 105, 161, 0.25);
        }        .sr-trust-card strong {
            display: block;
            color: var(--sr-navy);
            font-size: 0.85rem;
            margin-bottom: 0.35rem;
        }
        .sr-trust-card span {
            color: var(--sr-muted);
            font-size: 0.78rem;
            line-height: 1.45;
        }

        .sr-disclaimer {
            background: #FFFBEB;
            border: 1px solid #FDE68A;
            border-left: 4px solid #D97706;
            border-radius: 12px;
            padding: 0.85rem 1rem;
            margin-bottom: 1.25rem;
            font-size: 0.82rem;
            color: #92400E;
            line-height: 1.5;
            animation: srFadeUp 0.45s ease both;
        }

        .sr-panel {
            background: var(--sr-card);
            border: 1px solid var(--sr-border);
            border-radius: 16px;
            padding: 1.25rem 1.35rem;
            box-shadow: var(--sr-shadow);
            margin-bottom: 1rem;
            transition: box-shadow 0.3s ease;
        }
        .sr-panel:hover {
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
        }
        .sr-panel-title {
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--sr-blue);
            margin-bottom: 0.35rem;
        }        .sr-panel-heading {
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--sr-navy);
            margin: 0 0 0.5rem 0;
        }

        .sr-pipeline {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 0.5rem;
            margin: 1rem 0 0;
        }
        @media (max-width: 900px) {
            .sr-pipeline { grid-template-columns: 1fr; }
        }
        .sr-pipeline-step {
            background: #F8FAFC;
            border: 1px solid var(--sr-border);
            border-radius: 12px;
            padding: 0.75rem;
            text-align: center;
            transition: transform 0.25s ease, border-color 0.25s ease, background 0.25s ease;
        }
        .sr-pipeline-step:hover {
            transform: translateY(-2px);
            border-color: rgba(3, 105, 161, 0.3);
            background: #fff;
        }        .sr-pipeline-step .num {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.5rem;
            height: 1.5rem;
            border-radius: 999px;
            background: var(--sr-navy);
            color: white;
            font-size: 0.7rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }        .sr-pipeline-step:nth-child(1) .num { animation: srStepGlow 2.5s ease infinite 0s; }
        .sr-pipeline-step:nth-child(2) .num { animation: srStepGlow 2.5s ease infinite 0.5s; }
        .sr-pipeline-step:nth-child(3) .num { animation: srStepGlow 2.5s ease infinite 1s; }
        .sr-pipeline-step:nth-child(4) .num { animation: srStepGlow 2.5s ease infinite 1.5s; }
        .sr-pipeline-step:nth-child(5) .num { animation: srStepGlow 2.5s ease infinite 2s; }
        .sr-pipeline-loading .sr-pipeline-step { animation: srPulse 1.8s ease-in-out infinite; }
        .sr-pipeline-loading .sr-pipeline-step:nth-child(1) { animation-delay: 0s; }
        .sr-pipeline-loading .sr-pipeline-step:nth-child(2) { animation-delay: 0.2s; }
        .sr-pipeline-loading .sr-pipeline-step:nth-child(3) { animation-delay: 0.4s; }
        .sr-pipeline-loading .sr-pipeline-step:nth-child(4) { animation-delay: 0.6s; }
        .sr-pipeline-loading .sr-pipeline-step:nth-child(5) { animation-delay: 0.8s; }
        .sr-pipeline-step .label {
            display: block;
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--sr-navy);
        }
        .sr-pipeline-step .desc {
            display: block;
            font-size: 0.65rem;
            color: var(--sr-muted);
            margin-top: 0.2rem;
            line-height: 1.35;
        }

        .sr-metric-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            margin: 1rem 0;
        }
        @media (max-width: 768px) {
            .sr-metric-grid { grid-template-columns: repeat(2, 1fr); }
        }
        .sr-metric {
            background: #F8FAFC;
            border: 1px solid var(--sr-border);
            border-radius: 14px;
            padding: 1rem;
            text-align: center;
            animation: srFadeUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .sr-metric:hover { transform: translateY(-2px); border-color: rgba(3,105,161,0.25); }        .sr-metric:nth-child(1) { animation-delay: 0.05s; }
        .sr-metric:nth-child(2) { animation-delay: 0.12s; }
        .sr-metric:nth-child(3) { animation-delay: 0.19s; }
        .sr-metric:nth-child(4) { animation-delay: 0.26s; }
        .sr-metric .value {
            font-size: 1.65rem;
            font-weight: 700;
            color: var(--sr-navy);
            font-family: 'IBM Plex Mono', monospace;
        }
        .sr-metric .label {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--sr-muted);
            margin-top: 0.25rem;
        }

        .sr-status-high {
            background: #ECFDF5;
            border: 1px solid #A7F3D0;
            color: #065F46;
            border-radius: 12px;
            padding: 0.75rem 1rem;
            font-size: 0.88rem;
            margin: 0.5rem 0;
            animation: srFadeUp 0.45s ease both 0.2s;
        }
        .sr-status-med {
            background: #FFFBEB;
            border: 1px solid #FDE68A;
            color: #92400E;
            border-radius: 12px;
            padding: 0.75rem 1rem;
            font-size: 0.88rem;
            margin: 0.5rem 0;
            animation: srFadeUp 0.45s ease both 0.2s;
        }
        .sr-status-low, .sr-status-flag {
            background: #FEF2F2;
            border: 1px solid #FECACA;
            color: #991B1B;
            border-radius: 12px;
            padding: 0.75rem 1rem;
            font-size: 0.88rem;
            margin: 0.5rem 0;
            animation: srFadeUp 0.45s ease both 0.2s;
        }

        .sr-confidence-row {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin: 1rem 0;
            animation: srFadeUp 0.5s ease both;
        }
        .sr-ring-wrap {
            position: relative;
            width: 96px;
            height: 96px;
            flex-shrink: 0;
        }
        .sr-ring-wrap svg { transform: rotate(-90deg); }
        .sr-ring-wrap .sr-ring-value {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--sr-navy);
        }
        .sr-progress-track {
            flex: 1;
            height: 8px;
            background: #E2E8F0;
            border-radius: 999px;
            overflow: hidden;
        }
        .sr-progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #0369A1, #0EA5E9);
            animation: srProgressFill 1s cubic-bezier(0.22, 1, 0.36, 1) both;
        }

        .sr-loading-bar {
            height: 3px;
            border-radius: 999px;
            margin-top: 1rem;
            background: linear-gradient(90deg, #DDE3EA 0%, #0EA5E9 50%, #DDE3EA 100%);
            background-size: 200% 100%;
            animation: srShimmer 1.5s linear infinite;
        }

        .sr-response-box {
            background: var(--sr-bg-subtle);
            border: 1px solid var(--sr-border);
            border-left: 4px solid var(--sr-blue);
            border-radius: 10px;
            padding: 1.1rem 1.25rem;
            font-size: 0.95rem;
            line-height: 1.7;
            color: var(--sr-slate);
        }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        div[data-testid="stTabs"] button {
            font-weight: 600;
            font-size: 0.9rem;
            transition: color 0.2s ease, border-color 0.2s ease;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--sr-blue) !important;
            border-bottom-color: var(--sr-blue) !important;
        }
        .stButton > button {
            transition: transform 0.15s ease, box-shadow 0.2s ease, background 0.2s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
        }
        .stButton > button:active {
            transform: translateY(0);
        }
        .stButton > button[kind="primary"] {
            background: var(--sr-navy);
            border: 1px solid var(--sr-navy);
            border-radius: 8px;
            font-weight: 600;
            letter-spacing: 0.01em;
            box-shadow: 0 2px 8px rgba(10, 22, 40, 0.12);
        }
        .stButton > button[kind="primary"]:hover {
            background: var(--sr-navy-mid);
            border-color: var(--sr-navy-mid);
            box-shadow: 0 4px 14px rgba(10, 22, 40, 0.16);
        }
        [data-testid="stChatMessage"] {
            animation: srFadeUp 0.4s ease both;
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }

        .sr-footer {
            text-align: center;
            padding: 1.5rem 0 0.5rem;
            font-size: 0.78rem;
            color: var(--sr-muted);
        }
        </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_sidebar_brand(version: str = "v1.0") -> None:
    """Branded sidebar header with logo lockup."""
    logo_uri = _logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" alt="{BRAND_NAME}" />'
        if logo_uri
        else ""
    )
    st.markdown(
        _html(
            f"""
            <div class="sr-sidebar-brand">
                {logo_html}
                <div>
                    <div class="name">{BRAND_NAME}</div>
                    <div class="tagline">{BRAND_TAGLINE} · {version}</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    logo_uri = _logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" alt="{BRAND_NAME}" class="sr-hero-logo" />'
        if logo_uri
        else ""
    )

    st.markdown(
        _html(
            f"""
            <div class="sr-hero">
                <div class="sr-hero-badge">Clinical Decision Support · Research Prototype</div>
                <div style="display:flex;align-items:center;gap:16px;margin-bottom:0.65rem;">
                    {logo_html}
                    <h1>{BRAND_NAME}<span>{BRAND_TAGLINE}</span></h1>
                </div>
                <p>{BRAND_SUBTITLE}</p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

def render_trust_bar() -> None:
    cards = "".join(
        f'<div class="sr-trust-card sr-animate-in-delay-{i + 1}"><strong>{title}</strong>'
        f"<span>{desc}</span></div>"
        for i, (title, desc) in enumerate(TRUST_PILLARS)
    )
    st.markdown(f'<div class="sr-trust-bar">{cards}</div>', unsafe_allow_html=True)


def render_safety_disclaimer() -> None:
    st.markdown(
        _html(
            """
            <div class="sr-disclaimer">
                <strong>Research prototype — not a medical device.</strong>
                Sentinel-RAG supports clinician review of guideline-grounded answers.
                It must not be used for diagnosis, prescribing, or autonomous clinical
                decision-making. Every output requires verification by a qualified clinician.
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_pipeline_overview() -> None:
    steps = "".join(
        f'<div class="sr-pipeline-step">'
        f'<span class="num">{i}</span>'
        f'<span class="label">{label}</span>'
        f'<span class="desc">{desc}</span></div>'
        for i, (label, desc) in enumerate(SAFETY_LAYERS, start=1)
    )
    st.markdown(
        _html(
            f"""
            <div class="sr-panel">
                <div class="sr-panel-title">Safety architecture</div>
                <div class="sr-panel-heading">Five-layer validation pipeline</div>
                <p style="color:#64748B;font-size:0.88rem;margin:0;">
                    Every query passes through retrieval, generation, deterministic reflection,
                    independent cross-validation, and governance before reaching the clinician.
                </p>
                <div class="sr-pipeline">{steps}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_loading_pipeline() -> None:
    """Animated five-layer pipeline shown while the agent runs."""
    steps = "".join(
        f'<div class="sr-pipeline-step">'
        f'<span class="num">{i}</span>'
        f'<span class="label">{label}</span></div>'
        for i, (label, _) in enumerate(SAFETY_LAYERS, start=1)
    )
    st.markdown(
        _html(
            f"""
            <div class="sr-panel sr-animate-in">
                <div class="sr-panel-title">Processing</div>
                <div class="sr-panel-heading">Running five-layer safety pipeline…</div>
                <div class="sr-pipeline sr-pipeline-loading">{steps}</div>
                <div class="sr-loading-bar"></div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_confidence_gauge(confidence: float, flagged: bool) -> None:
    """Animated SVG confidence ring + progress bar."""
    pct = min(max(confidence, 0.0), 1.0)
    circumference = 283
    offset = circumference * (1 - pct)
    color = "#DC2626" if flagged or pct < 0.75 else "#D97706" if pct < 0.85 else "#059669"
    bar_width = f"{pct * 100:.1f}%"

    st.markdown(
        _html(
            f"""
            <div class="sr-confidence-row">
                <div class="sr-ring-wrap">
                    <svg width="96" height="96" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="45" fill="none" stroke="#E2E8F0" stroke-width="8"/>
                        <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="8"
                            stroke-linecap="round" stroke-dasharray="{circumference}"
                            stroke-dashoffset="{offset}"
                            style="--target: {offset}; animation: srRingDraw 1.1s cubic-bezier(0.22, 1, 0.36, 1) forwards;"/>
                    </svg>
                    <div class="sr-ring-value">{pct:.0%}</div>
                </div>
                <div style="flex:1;">
                    <div style="font-size:0.72rem;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.08em;color:#64748B;margin-bottom:0.35rem;">
                        Grounding confidence
                    </div>
                    <div class="sr-progress-track">
                        <div class="sr-progress-fill" style="width:{bar_width};"></div>
                    </div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_results_panel(
    response: str,
    confidence: float,
    flagged: bool,
    verdict: str,
    retry_count: int,
    response_time_ms: int | None,
    high: float,
    medium: float,
    messages: list | None = None,
    flag_reason: str = "",
) -> None:
    """Metrics panel (HTML) + native markdown for the clinical answer."""
    verdict_labels = {
        "SUPPORTED": "Supported",
        "PARTIALLY_SUPPORTED": "Partial",
        "CONTRADICTED": "Contradicted",
        "ERROR": "N/A",
    }
    verdict_label = verdict_labels.get(verdict, "N/A")
    latency = f"{response_time_ms}ms" if response_time_ms else "—"
    pct = min(max(confidence, 0.0), 1.0)
    circumference = 283
    offset = circumference * (1 - pct)
    ring_color = "#DC2626" if flagged or pct < 0.75 else "#D97706" if pct < 0.85 else "#059669"
    bar_width = f"{pct * 100:.1f}%"

    answer = extract_clinical_answer(response, messages)

    st.markdown(
        _html(
            f"""
            <div class="sr-results-panel sr-panel">
                <div class="sr-panel-title">Validation complete</div>

                <div class="sr-confidence-row">
                    <div class="sr-ring-wrap">
                        <svg width="96" height="96" viewBox="0 0 100 100">
                            <circle cx="50" cy="50" r="45" fill="none" stroke="#E2E8F0" stroke-width="8"/>
                            <circle cx="50" cy="50" r="45" fill="none" stroke="{ring_color}" stroke-width="8"
                                stroke-linecap="round" stroke-dasharray="{circumference}"
                                style="--target: {offset}; animation: srRingDraw 1.1s cubic-bezier(0.22, 1, 0.36, 1) forwards;"/>
                        </svg>
                        <div class="sr-ring-value">{pct:.0%}</div>
                    </div>
                    <div style="flex:1;">
                        <div style="font-size:0.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.08em;color:#64748B;margin-bottom:0.35rem;">
                            Grounding confidence
                        </div>
                        <div class="sr-progress-track">
                            <div class="sr-progress-fill" style="width:{bar_width};"></div>
                        </div>
                    </div>
                </div>

                <div class="sr-metric-grid">
                    <div class="sr-metric sr-animate-in-delay-1">
                        <div class="value">{verdict_label}</div>
                        <div class="label">Cross-validation</div>
                    </div>
                    <div class="sr-metric sr-animate-in-delay-2">
                        <div class="value">{retry_count}</div>
                        <div class="label">Re-query loops</div>
                    </div>
                    <div class="sr-metric sr-animate-in-delay-3">
                        <div class="value">{latency}</div>
                        <div class="label">Response time</div>
                    </div>
                    <div class="sr-metric sr-animate-in-delay-4">
                        <div class="value">{pct:.0%}</div>
                        <div class="label">Final score</div>
                    </div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    render_review_status(
        flagged, confidence, verdict, flag_reason, retry_count, high, medium,
    )

    st.markdown("##### Clinical protocol response")
    with st.container():
        st.markdown(answer)


def render_metric_row(
    confidence: float,
    verdict: str,
    retry_count: int,
    response_time_ms: int | None = None,
) -> None:
    verdict_labels = {
        "SUPPORTED": "Supported",
        "PARTIALLY_SUPPORTED": "Partial",
        "CONTRADICTED": "Contradicted",
        "ERROR": "N/A",
    }
    verdict_label = verdict_labels.get(verdict, "N/A")
    latency = f"{response_time_ms}ms" if response_time_ms else "—"

    st.markdown(
        _html(
            f"""
            <div class="sr-metric-grid">
                <div class="sr-metric">
                    <div class="value">{confidence:.0%}</div>
                    <div class="label">Grounding confidence</div>
                </div>
                <div class="sr-metric">
                    <div class="value">{verdict_label}</div>
                    <div class="label">Cross-validation</div>
                </div>
                <div class="sr-metric">
                    <div class="value">{retry_count}</div>
                    <div class="label">Re-query loops</div>
                </div>
                <div class="sr-metric">
                    <div class="value">{latency}</div>
                    <div class="label">Response time</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_status_banner(confidence: float, flagged: bool, high: float, medium: float) -> None:
    if flagged:
        st.markdown(
            _html(
                """
                <div class="sr-status-flag">
                    <strong>Flagged for clinical review</strong> — This response is not
                    sufficiently grounded in the available guidelines. Do not act on it
                    without verification by a qualified clinician.
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        return

    if confidence >= high:
        css = "sr-status-high"
        msg = (
            "<strong>High confidence</strong> — Answer is well grounded in the "
            "retrieved guideline passages."
        )
    elif confidence >= medium:
        css = "sr-status-med"
        msg = (
            "<strong>Moderate confidence</strong> — Review source citations before "
            "relying on this response."
        )
    else:
        css = "sr-status-low"
        msg = (
            "<strong>Low confidence</strong> — Response is weakly supported by the "
            "available guidelines."
        )

    st.markdown(f'<div class="{css}">{msg}</div>', unsafe_allow_html=True)


def render_response_panel(response: str, messages: list | None = None) -> None:
    answer = extract_clinical_answer(response, messages)
    st.markdown("##### Clinical protocol response")
    st.markdown(answer)


def render_footer(linkedin_url: str) -> None:
    st.markdown(
        _html(
            f"""
            <div class="sr-footer">
                Built for responsible clinical AI research ·
                <a href="{linkedin_url}" target="_blank" rel="noopener">Devasai Pranatheswar</a>
                · Documentation in <code>docs/</code>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
