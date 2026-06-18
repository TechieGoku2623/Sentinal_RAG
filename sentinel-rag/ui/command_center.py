"""Mission-control dashboard — see full platform state, then act."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.retriever import get_collection_count
from src.services.audit_service import get_platform_stats, list_interactions
from src.services.knowledge_service import get_knowledge_overview
from src.services.platform_health import check_api_health
from src.services.workspace_service import get_usage
from ui.components import stat_card, stat_row, usage_meter_bar
from ui.saas_shell import current_tenant
from ui.theme import _html

ROOT = Path(__file__).resolve().parents[1]
EVAL_JSON = ROOT / "data" / "eval" / "eval_results.json"


def inject_command_center_css() -> None:
    st.markdown(
        _html(
            """
            <style>
            .sr-cc-header {
                position: relative;
                background: linear-gradient(135deg, #0C1825 0%, #132233 55%, #0A1F2E 100%);
                border: 1px solid rgba(14, 199, 136, 0.18);
                border-radius: 16px;
                padding: 1.65rem 1.85rem;
                margin-bottom: 1.25rem;
                color: #E8F0F8;
                overflow: hidden;
                box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
            }
            .sr-cc-header::before {
                content: "";
                position: absolute;
                inset: 0;
                background: radial-gradient(ellipse 80% 60% at 100% 0%, rgba(14, 199, 136, 0.12), transparent 55%);
                pointer-events: none;
            }
            .sr-cc-header h1 {
                position: relative;
                margin: 0;
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.75rem;
                font-weight: 700;
                letter-spacing: -0.03em;
            }
            .sr-cc-header p {
                position: relative;
                margin: 0.5rem 0 0;
                color: #7A9AB8;
                font-size: 0.92rem;
                max-width: 720px;
                line-height: 1.6;
            }
            .sr-cc-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                font-size: 0.62rem;
                font-weight: 600;
                letter-spacing: 0.16em;
                text-transform: uppercase;
                color: #0EC788;
                margin-bottom: 0.45rem;
            }
            .sr-cc-badge::before {
                content: "";
                width: 6px;
                height: 6px;
                border-radius: 999px;
                background: #0EC788;
                box-shadow: 0 0 8px #0EC788;
            }
            .sr-cc-tile {
                background: #0C1825;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 0.9rem 1rem;
                min-height: 92px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
                transition: border-color 0.2s ease, transform 0.2s ease;
            }
            .sr-cc-tile:hover {
                border-color: rgba(14, 199, 136, 0.25);
                transform: translateY(-1px);
            }
            .sr-cc-tile-label {
                font-size: 0.65rem;
                font-weight: 600;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #3D5A73;
                margin-bottom: 0.3rem;
            }
            .sr-cc-tile-value {
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.2rem;
                font-weight: 700;
                color: #E8F0F8;
                line-height: 1.2;
            }
            .sr-cc-tile-sub {
                font-size: 0.76rem;
                color: #7A9AB8;
                margin-top: 0.25rem;
                line-height: 1.35;
            }
            .sr-cc-tile.ok { border-left: 3px solid #0EC788; }
            .sr-cc-tile.warn { border-left: 3px solid #F0A500; }
            .sr-cc-tile.bad { border-left: 3px solid #E84040; }
            .sr-cc-tile.neutral { border-left: 3px solid #14B8A6; }
            .sr-cc-action-row {
                background: #0C1825;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 0.8rem 1rem;
                margin-bottom: 0.5rem;
            }
            .sr-cc-action-title {
                font-weight: 600;
                font-size: 0.88rem;
                color: #E8F0F8;
            }
            .sr-cc-action-detail {
                font-size: 0.78rem;
                color: #7A9AB8;
                margin-top: 0.2rem;
                line-height: 1.45;
            }
            .sr-cc-section {
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.68rem;
                font-weight: 500;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: #3D5A73;
                margin: 1.25rem 0 0.65rem;
            }
            .sr-cc-health-bar {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 0.85rem 1.25rem;
                background: #0C1825;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 1rem 1.15rem;
                margin-bottom: 1rem;
            }
            .sr-cc-health-dot {
                width: 10px;
                height: 10px;
                border-radius: 999px;
                flex-shrink: 0;
            }
            .sr-cc-health-dot.ok { background: #0EC788; box-shadow: 0 0 0 4px rgba(14, 199, 136, 0.2); }
            .sr-cc-health-dot.warn { background: #F0A500; box-shadow: 0 0 0 4px rgba(240, 165, 0, 0.2); }
            .sr-cc-health-dot.bad { background: #E84040; box-shadow: 0 0 0 4px rgba(232, 64, 64, 0.2); }
            .sr-cc-health-label {
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1rem;
                font-weight: 600;
                color: #E8F0F8;
            }
            .sr-cc-health-meta {
                font-size: 0.78rem;
                color: #7A9AB8;
            }
            .sr-cc-pipeline {
                display: flex;
                flex-wrap: wrap;
                gap: 0.4rem;
                margin-bottom: 1rem;
            }
            .sr-cc-pipeline-step {
                flex: 1 1 auto;
                min-width: 72px;
                text-align: center;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.58rem;
                font-weight: 500;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                padding: 0.5rem 0.35rem;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: #0C1825;
                color: #3D5A73;
            }
            .sr-cc-pipeline-step.active {
                border-color: rgba(14, 199, 136, 0.45);
                background: rgba(14, 199, 136, 0.1);
                color: #0EC788;
            }
            @keyframes srCcFadeUp {
                from { opacity: 0; transform: translateY(12px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .sr-cc-header { animation: srCcFadeUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) both; }
            .sr-cc-health-bar { animation: srCcFadeUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both; }
            .sr-cc-tile { animation: srCcFadeUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) both; }
            @media (prefers-reduced-motion: reduce) {
                .sr-cc-header, .sr-cc-health-bar, .sr-cc-tile { animation: none !important; }
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def _tile(label: str, value: str, sub: str = "", tone: str = "neutral") -> str:
    return _html(
        f"""
        <div class="sr-cc-tile {tone}">
            <div class="sr-cc-tile-label">{label}</div>
            <div class="sr-cc-tile-value">{value}</div>
            {f'<div class="sr-cc-tile-sub">{sub}</div>' if sub else ''}
        </div>
        """
    )


def _load_eval_summary() -> dict[str, Any]:
    if not EVAL_JSON.exists():
        return {}
    try:
        data = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
        return data.get("summary", {})
    except (OSError, json.JSONDecodeError):
        return {}


def _readiness_score(
    *,
    api_ok: bool,
    groq_ok: bool,
    doc_count: int,
    db_ok: bool,
    blockers: int,
) -> tuple[int, str, str]:
    score = 100
    if not api_ok:
        score -= 25
    if not groq_ok:
        score -= 25
    if doc_count == 0:
        score -= 20
    if not db_ok:
        score -= 10
    score = max(0, min(100, score - blockers * 5))
    if score >= 85:
        return score, "Operational", "ok"
    if score >= 60:
        return score, "Degraded", "warn"
    return score, "Blocked", "bad"


def _render_health_bar(label: str, score: int, meta: str, tone: str) -> None:
    st.markdown(
        _html(
            f"""
            <div class="sr-cc-health-bar">
                <span class="sr-cc-health-dot {tone}"></span>
                <div>
                    <div class="sr-cc-health-label">Platform readiness · {label} ({score}/100)</div>
                    <div class="sr-cc-health-meta">{meta}</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _render_pipeline_strip(active_step: str = "govern") -> None:
    steps = [
        ("retrieve", "Retrieve"),
        ("generate", "Generate"),
        ("reflect", "Reflect"),
        ("validate", "Validate"),
        ("govern", "Govern"),
    ]
    chips = "".join(
        f'<div class="sr-cc-pipeline-step{" active" if key == active_step else ""}">{name}</div>'
        for key, name in steps
    )
    st.markdown(
        _html(f'<div class="sr-cc-pipeline">{chips}</div>'),
        unsafe_allow_html=True,
    )


def _collect_action_items(
    *,
    api: dict,
    usage: dict,
    overview: dict,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    doc_count = len(overview.get("documents", []))
    counts = overview.get("collection_counts", {})

    if not api.get("ok"):
        items.append(
            {
                "severity": "critical",
                "title": "API offline",
                "detail": f"Start FastAPI at {api.get('url', 'localhost:8000')}",
            }
        )
    if doc_count == 0 or counts.get("parent", 0) == 0:
        items.append(
            {
                "severity": "critical",
                "title": "No guidelines indexed",
                "detail": "Upload PDF/TXT protocols in the sidebar file uploader.",
            }
        )
    if not os.getenv("GROQ_API_KEY"):
        items.append(
            {
                "severity": "critical",
                "title": "GROQ_API_KEY missing",
                "detail": "Set GROQ_API_KEY in .env for Llama inference.",
            }
        )
    if usage.get("usage_pct", 0) >= 0.9:
        items.append(
            {
                "severity": "major",
                "title": "Query quota nearly exhausted",
                "detail": f"{usage['queries_used']:,} / {usage['queries_limit']:,} used this month.",
            }
        )

    flagged = list_interactions(limit=50, tenant_id=current_tenant())
    flagged_count = sum(1 for r in flagged if r.get("flagged"))
    if flagged_count:
        items.append(
            {
                "severity": "major",
                "title": f"{flagged_count} validation(s) flagged for review",
                "detail": "Review flagged answers in the clinical query section below.",
            }
        )

    if not items:
        items.append(
            {
                "severity": "ok",
                "title": "All systems nominal",
                "detail": "Ask a clinical question below or expand your knowledge base.",
            }
        )
    return items


def render_command_center() -> None:
    tenant = current_tenant()
    inject_command_center_css()

    usage = get_usage(tenant)
    api = check_api_health()
    overview = get_knowledge_overview(tenant)
    counts = overview.get("collection_counts", {})
    doc_count = len(overview.get("documents", []))

    try:
        chroma = get_collection_count()
    except Exception:  # noqa: BLE001
        chroma = counts

    try:
        stats = get_platform_stats(tenant)
    except Exception:  # noqa: BLE001
        stats = {
            "total_interactions": 0,
            "avg_confidence": 0.0,
            "flag_rate": 0.0,
            "avg_human_rating": 0.0,
            "total_rated": 0,
        }

    eval_sum = _load_eval_summary()

    groq_ok = bool(os.getenv("GROQ_API_KEY"))
    db_ok = (ROOT / "data" / "sentinel.db").exists()

    action_items = _collect_action_items(
        api=api,
        usage=usage,
        overview=overview,
    )
    blocker_count = sum(1 for i in action_items if i["severity"] in ("critical", "major"))
    readiness, readiness_label, readiness_tone = _readiness_score(
        api_ok=api.get("ok", False),
        groq_ok=groq_ok,
        doc_count=doc_count,
        db_ok=db_ok,
        blockers=blocker_count,
    )
    readiness_meta = (
        f"{blocker_count} action item(s) · "
        f"{usage['queries_used']:,}/{usage['queries_limit']:,} queries"
    )

    st.markdown(
        _html(
            f"""
            <div class="sr-cc-header">
                <div class="sr-cc-badge">Mission control</div>
                <h1>Command Center · {usage.get('plan_name', 'Workspace')}</h1>
                <p>
                    Live visibility for <strong style="color:#E8F0F8;">{tenant}</strong> —
                    system health, knowledge base coverage, validation quality, and what to fix next.
                </p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    _render_health_bar(readiness_label, readiness, readiness_meta, readiness_tone)
    _render_pipeline_strip()

    st.markdown('<div class="sr-cc-section">System status</div>', unsafe_allow_html=True)
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    with r1c1:
        if api.get("ok"):
            st.markdown(
                _tile("API", "Online", api.get("url", "")[:40], "ok"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                _tile("API", "Offline", "uvicorn src.api.main:app", "bad"),
                unsafe_allow_html=True,
            )
    with r1c2:
        st.markdown(
            _tile(
                "LLM",
                "Ready" if groq_ok else "Missing key",
                "Groq · Llama 3.1" if groq_ok else "Set GROQ_API_KEY",
                "ok" if groq_ok else "bad",
            ),
            unsafe_allow_html=True,
        )
    with r1c3:
        kb_tone = "ok" if doc_count > 0 else "warn"
        st.markdown(
            _tile(
                "Knowledge base",
                f"{doc_count} docs",
                f"{chroma.get('parent', 0)} parent · {chroma.get('child', 0)} child chunks",
                kb_tone,
            ),
            unsafe_allow_html=True,
        )
    with r1c4:
        st.markdown(
            _tile(
                "Audit store",
                "SQLite OK" if db_ok else "Not initialized",
                "data/sentinel.db",
                "ok" if db_ok else "warn",
            ),
            unsafe_allow_html=True,
        )
    with r1c5:
        st.markdown(
            _tile(
                "Sessions",
                str(stats["total_interactions"]),
                f"Flag rate {stats['flag_rate']:.0%}" if stats["total_interactions"] else "No runs yet",
                "neutral",
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sr-cc-section">Workspace & quality</div>', unsafe_allow_html=True)
    eval_match = (
        f"{eval_sum.get('keyword_match_rate', 0):.0%}"
        if eval_sum
        else "—"
    )
    stat_row(
        [
            stat_card("Plan", usage["plan_name"]),
            stat_card("Queries", f"{usage['queries_used']:,}", f"of {usage['queries_limit']:,}"),
            stat_card(
                "Avg confidence",
                f"{stats['avg_confidence']:.0%}" if stats["total_interactions"] else "—",
            ),
            stat_card(
                "Flag rate",
                f"{stats['flag_rate']:.0%}" if stats["total_interactions"] else "—",
            ),
            stat_card("Eval match", eval_match),
            stat_card("Sessions", str(stats["total_interactions"])),
        ]
    )

    usage_meter_bar(
        used=usage["queries_used"],
        limit=usage["queries_limit"],
        plan_name=usage["plan_name"],
        price_label=usage["price_label"],
    )

    left, right = st.columns([1.1, 1])

    with left:
        st.markdown('<div class="sr-cc-section">Recent validations</div>', unsafe_allow_html=True)
        rows = list_interactions(limit=8, tenant_id=tenant)
        if not rows:
            st.markdown(
                _html(
                    """
                    <div class="sr-cc-action-row" style="border-left:3px solid #14B8A6;">
                        <div class="sr-cc-action-title">No validations yet</div>
                        <div class="sr-cc-action-detail">
                            Ask a clinical question in the workspace below to run your first protocol check.
                        </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        else:
            df = pd.DataFrame(rows)
            display_cols = [
                c
                for c in ("timestamp", "query", "confidence", "flagged", "validation_verdict")
                if c in df.columns
            ]
            if display_cols:
                view = df[display_cols].head(8).copy()
                if "confidence" in view.columns:
                    view["confidence"] = view["confidence"].apply(
                        lambda v: f"{float(v):.0%}" if pd.notna(v) else "—"
                    )
                if "flagged" in view.columns:
                    view["flagged"] = view["flagged"].apply(lambda v: "Yes" if v else "No")
                st.dataframe(
                    view,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "timestamp": st.column_config.TextColumn("Time", width="small"),
                        "query": st.column_config.TextColumn("Query", width="large"),
                        "confidence": st.column_config.TextColumn("Confidence", width="small"),
                        "flagged": st.column_config.TextColumn("Flagged", width="small"),
                        "validation_verdict": st.column_config.TextColumn("Verdict", width="small"),
                    },
                )
            flagged_n = sum(1 for r in rows if r.get("flagged"))
            if flagged_n:
                st.caption(f"{flagged_n} of last {len(rows)} runs flagged for clinical review.")

        with st.expander("Benchmark eval (offline)", expanded=bool(eval_sum)):
            if eval_sum:
                e1, e2, e3, e4 = st.columns(4)
                e1.metric("Questions", eval_sum.get("questions_evaluated", 0))
                e2.metric("Validation agree", f"{eval_sum.get('validation_agreement_rate', 0):.0%}")
                e3.metric("Avg latency", f"{eval_sum.get('avg_response_time_ms', 0) / 1000:.0f}s")
                e4.metric("Protocol accuracy", f"{eval_sum.get('protocol_accuracy', 0):.0%}")
                target = eval_sum.get("protocol_accuracy_target", 0.99)
                if eval_sum.get("protocol_accuracy", 0) < target:
                    st.caption(
                        f"Target protocol accuracy: {target:.0%} — expand the knowledge base or re-run eval."
                    )
            else:
                st.caption("Run `python scripts/run_eval.py` to populate data/eval/eval_results.json.")

    with right:
        critical_items = [i for i in action_items if i["severity"] in ("critical", "major")]
        other_items = [i for i in action_items if i["severity"] not in ("critical", "major")]

        st.markdown('<div class="sr-cc-section">Action queue</div>', unsafe_allow_html=True)
        queue = critical_items or other_items[:1]
        for item in queue:
            sev = item["severity"]
            border = {
                "critical": "#E84040",
                "major": "#F0A500",
                "minor": "#0EC788",
                "ok": "#0EC788",
            }.get(sev, "#3D5A73")
            st.markdown(
                _html(
                    f"""
                    <div class="sr-cc-action-row" style="border-left:3px solid {border};">
                        <div class="sr-cc-action-title">{item['title']}</div>
                        <div class="sr-cc-action-detail">{item['detail']}</div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

        if other_items and critical_items:
            with st.expander(f"Other actions ({len(other_items)})", expanded=False):
                for item in other_items:
                    st.caption(f"**{item['title']}** — {item['detail']}")
