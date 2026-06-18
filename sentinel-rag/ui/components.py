"""Elite UI HTML components for Streamlit — confidence arc, answer cards, pipeline."""

from __future__ import annotations

import html
import math

import streamlit as st

from ui.theme import _html


def _esc(text: str) -> str:
    return html.escape(str(text or ""), quote=True)


def _render_html(body: str) -> None:
    st.markdown(_html(body), unsafe_allow_html=True)


def section_header(
    badge: str,
    title: str,
    subtitle: str = "",
    *,
    anchor: str = "",
) -> None:
    """Premium section header with optional anchor id."""
    anchor_attr = f' id="{_esc(anchor)}"' if anchor else ""
    sub_html = (
        f'<p class="sr-section-sub">{_esc(subtitle)}</p>' if subtitle else ""
    )
    st.markdown(
        _html(
            f"""
            <div class="sr-section-header"{anchor_attr}>
                <div class="sr-section-badge">{_esc(badge)}</div>
                <h2 class="sr-section-title">{_esc(title)}</h2>
                {sub_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def section_divider(label: str = "") -> None:
    """Visual break between major workspace regions."""
    label_html = (
        f'<span class="sr-section-divider-label">{_esc(label)}</span>' if label else ""
    )
    _render_html(
        f"""
        <div class="sr-section-divider">
            {label_html}
        </div>
        """
    )


def stat_card(label: str, value: str, sub: str = "", tone: str = "neutral") -> str:
    """Dark metric tile HTML fragment (single-line — safe to concatenate)."""
    sub_html = f'<div class="sr-stat-sub">{_esc(sub)}</div>' if sub else ""
    return (
        f'<div class="sr-stat-card sr-stat-{tone}">'
        f'<div class="sr-stat-label">{_esc(label)}</div>'
        f'<div class="sr-stat-value">{_esc(value)}</div>'
        f"{sub_html}</div>"
    )


def stat_row(cards: list[str]) -> None:
    """Render a row of stat_card HTML fragments."""
    _render_html(f'<div class="sr-stat-row">{"".join(cards)}</div>')


def session_bar(turn: int, *, show_clear_hint: bool = True) -> None:
    """Session context strip above the query workspace."""
    hint = (
        '<span class="sr-session-hint">Clear resets conversation context</span>'
        if show_clear_hint
        else ""
    )
    _render_html(
        f"""
        <div class="sr-session-bar">
            <div>
                <span class="sr-session-label">Active session</span>
                <span class="sr-session-turn">Turn {turn}</span>
            </div>
            {hint}
        </div>
        """
    )


def feedback_prompt() -> None:
    """Styled label for clinician feedback controls."""
    _render_html(
        """
        <div class="sr-feedback-header">
            <span class="sr-feedback-icon">◈</span>
            <div>
                <div class="sr-feedback-title">Clinician feedback</div>
                <div class="sr-feedback-sub">Was this response helpful for protocol review?</div>
            </div>
        </div>
        """
    )


_VERDICT_LABELS = {
    "SUPPORTED": "Supported",
    "PARTIALLY_SUPPORTED": "Partial",
    "CONTRADICTED": "Contradicted",
    "ERROR": "N/A",
}


def app_topbar(workspace: str, *, api_ok: bool, groq_ok: bool) -> None:
    """Compact status strip at the top of the main workspace."""
    api_color = "#0EC788" if api_ok else "#E84040"
    llm_color = "#0EC788" if groq_ok else "#E84040"
    _render_html(
        f"""
        <div class="sr-app-topbar">
            <div class="sr-app-topbar-left">
                <span class="sr-app-topbar-dot"></span>
                <span class="sr-app-topbar-title">Sentinel-RAG</span>
                <span class="sr-app-topbar-workspace">{_esc(workspace)}</span>
            </div>
            <div class="sr-app-topbar-status">
                <span style="color:{api_color};">● API</span>
                <span style="color:{llm_color};">● LLM</span>
            </div>
        </div>
        """
    )


def platform_status_pill(*, online: bool, label: str, detail: str) -> None:
    """Sidebar-friendly status indicator."""
    tone = "ok" if online else "bad"
    _render_html(
        f"""
        <div class="sr-status-pill sr-status-pill-{tone}">
            <span class="sr-status-pill-dot"></span>
            <div>
                <div class="sr-status-pill-label">{_esc(label)}</div>
                <div class="sr-status-pill-detail">{_esc(detail)}</div>
            </div>
        </div>
        """
    )


def usage_meter_bar(*, used: int, limit: int, plan_name: str, price_label: str) -> None:
    """Dark HTML usage meter for the command center."""
    pct = min(int((used / limit) * 100) if limit else 0, 100)
    bar_color = "#0EC788" if pct < 80 else "#F0A500" if pct < 95 else "#E84040"
    _render_html(
        f"""
        <div class="sr-usage-meter">
            <div class="sr-usage-meter-head">
                <span>{_esc(plan_name)} · {_esc(price_label)}</span>
                <span>{used:,} / {limit:,} queries</span>
            </div>
            <div class="sr-usage-meter-track">
                <div class="sr-usage-meter-fill" style="width:{pct}%;background:{bar_color};"></div>
            </div>
        </div>
        """
    )


def confidence_arc(value: int, size: int = 88) -> str:
    """SVG confidence arc (270° sweep) with CSS draw animation."""
    value = max(0, min(100, int(value)))
    r = (size - 6) / 2
    cx = cy = size / 2
    circumference = 2 * math.pi * r
    arc_length = circumference * 0.75
    target_offset = arc_length * (1 - value / 100)

    if value >= 85:
        color = "#0EC788"
    elif value >= 75:
        color = "#F0A500"
    else:
        color = "#E84040"

    return f"""
    <div style="
      animation: srArcFadeUp 0.45s cubic-bezier(0.16,1,0.3,1) both;
      display: flex; flex-direction: column; align-items: flex-end;
    ">
      <svg width="{size}" height="{size}"
           style="transform: rotate(-225deg); flex-shrink:0; overflow: visible;">
        <circle cx="{cx}" cy="{cy}" r="{r}"
          fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="6"
          stroke-dasharray="{arc_length:.2f} {circumference:.2f}"
          stroke-linecap="round"/>
        <circle cx="{cx}" cy="{cy}" r="{r}"
          fill="none" stroke="{color}" stroke-width="6"
          stroke-dasharray="{arc_length:.2f} {circumference:.2f}"
          stroke-dashoffset="{arc_length:.2f}"
          stroke-linecap="round"
          style="
            filter: drop-shadow(0 0 6px {color}60);
            animation: srArcDraw 1.4s cubic-bezier(0.16,1,0.3,1) forwards;
            --target-offset: {target_offset:.2f};
          "/>
      </svg>
      <div style="
        position: relative; margin-top: -{size}px;
        width: {size}px; height: {size}px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        animation: srArcCountUp 0.4s ease 0.6s both;
      ">
        <span style="
          font-family: 'JetBrains Mono', monospace;
          font-size: 17px; font-weight: 500;
          color: {color}; letter-spacing: -0.02em; line-height: 1;
        ">{value}%</span>
        <span style="
          font-size: 9px; color: #3D5A73;
          letter-spacing: 0.06em; text-transform: uppercase;
          font-family: Inter, sans-serif;
        ">conf</span>
      </div>
    </div>
    """


def answer_card(
    answer: str,
    confidence: int,
    retries: int,
    latency_ms: int,
    doc_count: int,
    flagged: bool,
    sources: list[dict] | None = None,
    verdict: str = "ERROR",
    cache_hit: bool = False,
) -> None:
    """Render the full answer card with confidence arc."""
    sources = sources or []
    verdict_label = _VERDICT_LABELS.get(verdict, "N/A")
    border_color = (
        "rgba(14,199,136,0.2)"
        if confidence >= 85
        else "rgba(240,165,0,0.2)"
        if confidence >= 75
        else "rgba(232,64,64,0.3)"
    )
    flag_animation = "animation: srPulseRed 2s ease infinite;" if flagged else ""

    card_html = f"""
    <div style="
      background: #0C1825;
      border: 1px solid {border_color};
      border-radius: 10px;
      overflow: hidden;
      position: relative;
      margin-bottom: 16px;
      animation: srArcFadeUp 0.45s cubic-bezier(0.16,1,0.3,1) both;
      {flag_animation}
    ">
    """

    if flagged:
        card_html += """
      <div style="
        position:absolute;left:0;top:0;bottom:0;width:3px;
        background:#E84040;border-radius:10px 0 0 10px;
        animation:srPulseRed 2s ease infinite;
      "></div>
        """

    card_html += f"""
      <div style="
        display:flex;align-items:center;justify-content:space-between;
        padding:12px 20px 0;gap:12px;flex-wrap:wrap;
      ">
        <div style="
          font-family:'JetBrains Mono',monospace;font-size:10px;
          letter-spacing:0.1em;text-transform:uppercase;color:#3D5A73;
        ">Latest validation</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <span style="
            font-family:'JetBrains Mono',monospace;font-size:10px;
            padding:3px 8px;border-radius:999px;
            background:rgba(14,199,136,0.12);color:#0EC788;
            border:1px solid rgba(14,199,136,0.25);
          ">{_esc(verdict_label)}</span>
          {"<span style=\"font-family:'JetBrains Mono',monospace;font-size:10px;padding:3px 8px;border-radius:999px;background:rgba(255,255,255,0.06);color:#7A9AB8;border:1px solid rgba(255,255,255,0.08);\">cached</span>" if cache_hit else ""}
        </div>
      </div>
      <div style="
        display:flex;align-items:flex-start;justify-content:space-between;
        padding:16px 20px 0;gap:16px;
      ">
        <p style="
          font-family: Inter, sans-serif;
          font-size: 15px; line-height: 1.75;
          color: #E8F0F8; flex:1; margin:0;
        ">{_esc(answer)}</p>
        {confidence_arc(confidence)}
      </div>
    """

    if flagged:
        card_html += """
      <div style="
        margin: 16px 20px 0;
        background: rgba(232,64,64,0.08);
        border: 1px solid rgba(232,64,64,0.25);
        border-radius: 6px;
        padding: 10px 14px;
        display: flex; gap: 10px; align-items: flex-start;
      ">
        <span style="font-size:14px;margin-top:1px;">⚠</span>
        <div>
          <p style="font-family:'JetBrains Mono',monospace;font-size:11px;
                    letter-spacing:0.08em;text-transform:uppercase;
                    color:#E84040;margin:0 0 4px;">Flagged for clinical review</p>
          <p style="font-family:Inter,sans-serif;font-size:13px;
                    color:#7A9AB8;margin:0;line-height:1.5;">
            Confidence below threshold. A qualified clinician must verify this
            response before clinical use.
          </p>
        </div>
      </div>
        """

    meta_rows = [
        ("Retries", str(retries)),
        ("Latency", f"{latency_ms}ms"),
        ("Sources", str(doc_count)),
    ]
    meta_html = ""
    for label, val in meta_rows:
        meta_html += f"""
        <div style="display:flex;flex-direction:column;gap:2px;">
          <span style="font-family:Inter,sans-serif;font-size:11px;color:#3D5A73;
                       text-transform:uppercase;letter-spacing:0.06em;">{label}</span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:14px;
                       color:#E8F0F8;font-weight:500;">{_esc(val)}</span>
        </div>"""

    card_html += f"""
      <div style="
        display:flex;gap:24px;padding:14px 20px;
        border-top:1px solid rgba(255,255,255,0.05);margin-top:16px;
        animation: srArcCountUp 0.4s ease 0.4s both;
      ">
        {meta_html}
      </div>
    </div>
    """

    st.markdown(_html(card_html), unsafe_allow_html=True)

    if sources:
        with st.expander(f"{len(sources)} source{'s' if len(sources) > 1 else ''}"):
            for src in sources:
                _render_html(
                    f"""
                    <div style="
                      padding:8px 12px;background:#132233;border-radius:6px;
                      border-left:2px solid #0A7A55;margin-bottom:8px;
                    ">
                      <p style="font-family:'JetBrains Mono',monospace;font-size:11px;
                                 color:#0EC788;margin:0 0 4px;">
                        {_esc(src.get('id', ''))} · {_esc(src.get('section', ''))}
                      </p>
                      <p style="font-family:Inter,sans-serif;font-size:13px;
                                 color:#7A9AB8;margin:0;line-height:1.5;">
                        {_esc(src.get('excerpt', ''))}
                      </p>
                    </div>
                    """
                )


def agent_pipeline_status(stage: str) -> None:
    """Animated pipeline tracker for agent processing."""
    stages = [
        ("retrieve", "⬡", "Retrieve"),
        ("generate", "◈", "Generate"),
        ("reflect", "◎", "Reflect"),
        ("output", "◆", "Output"),
    ]
    stage_ids = [s[0] for s in stages]
    current_idx = stage_ids.index(stage) if stage in stage_ids else -1

    nodes_html = ""
    for i, (sid, icon, label) in enumerate(stages):
        is_active = sid == stage
        is_done = i < current_idx
        color = "#0EC788" if is_active else "#0A7A55" if is_done else "#3D5A73"
        bg = "rgba(14,199,136,0.12)" if is_active else "transparent"
        border_clr = "rgba(14,199,136,0.4)" if is_active else "rgba(255,255,255,0.07)"
        ring = (
            """
          <div style="position:absolute;inset:-5px;border-radius:50%;
                      border:1px solid rgba(14,199,136,0.3);
                      animation:srPulseRing 2s ease infinite;">
          </div>"""
            if is_active
            else ""
        )
        connector = ""
        if i < len(stages) - 1:
            width = "100%" if is_done else "0%"
            connector = f"""
            <div style="width:32px;height:1px;background:rgba(255,255,255,0.06);
                        margin:0 4px 14px;position:relative;">
              <div style="height:100%;width:{width};background:#0A7A55;
                          transition:width 0.3s cubic-bezier(0.16,1,0.3,1);"></div>
            </div>"""

        nodes_html += f"""
        <div style="display:flex;align-items:center;">
          <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
            <div style="position:relative;width:28px;height:28px;">
              {ring}
              <div style="
                width:28px;height:28px;border-radius:50%;
                background:{bg};border:1px solid {border_clr};
                display:flex;align-items:center;justify-content:center;
                font-size:13px;color:{color};
                transition:all 0.22s cubic-bezier(0.16,1,0.3,1);
              ">{"✓" if is_done else icon}</div>
            </div>
            <span style="
              font-family:'JetBrains Mono',monospace;font-size:9px;
              letter-spacing:0.08em;text-transform:uppercase;color:{color};
            ">{label}</span>
          </div>
          {connector}
        </div>
        """

    retry_badge = ""
    if stage == "retrieve":
        retry_badge = """
        <div style="
          margin-left:auto;
          font-family:'JetBrains Mono',monospace;font-size:11px;
          color:#F0A500;background:rgba(240,165,0,0.1);
          border:1px solid rgba(240,165,0,0.2);border-radius:4px;padding:2px 8px;
        ">re-querying</div>"""

    _render_html(
        f"""
        <div style="
          display:flex;align-items:center;gap:0;
          padding:12px 16px;
          background:#0C1825;
          border:1px solid rgba(255,255,255,0.05);
          border-radius:8px;margin-bottom:16px;
          animation: srArcFadeUp 0.4s cubic-bezier(0.16,1,0.3,1) both;
        ">
          {nodes_html}
          {retry_badge}
        </div>
        """
    )


def sources_from_metadata(metadata_list: list) -> list[dict]:
    """Map retriever metadata to answer-card source shape."""
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for meta in metadata_list or []:
        if not isinstance(meta, dict):
            continue
        source = str(meta.get("source", "") or "Unknown")
        year = meta.get("publication_year", 0) or 0
        key = (source, str(year))
        if key in seen:
            continue
        seen.add(key)
        section = f"{year}" if year else "guideline"
        excerpt = str(meta.get("text", "") or meta.get("chunk", "") or source)[:280]
        out.append({"id": source, "section": section, "excerpt": excerpt or source})
    return out
