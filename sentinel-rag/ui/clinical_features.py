"""Real-world clinical workspace features — patient context, provenance, export."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone

import streamlit as st

from src import config
from src.recency_scorer import get_oldest_source_year, recency_label, should_warn_outdated
from src.reflection import score_confidence_breakdown, score_query_alignment
from src.text_utils import extract_clinical_answer, format_review_banner
from ui.theme import _html


def _esc(text: str) -> str:
    return html.escape(str(text or ""), quote=True)


def _render_html(body: str) -> None:
    st.markdown(_html(body), unsafe_allow_html=True)


def init_patient_context_state() -> None:
    defaults = {
        "patient_age": 0,
        "patient_sex": "Not specified",
        "patient_egfr": "",
        "patient_comorbidities": "",
        "patient_pregnancy": False,
        "clinical_review_notes": {},
        "last_clinical_query": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def build_patient_context_block() -> str:
    """Format optional patient context for query augmentation."""
    parts: list[str] = []
    age = st.session_state.get("patient_age", 0) or 0
    try:
        age_int = int(age)
    except (TypeError, ValueError):
        age_int = 0
    if age_int > 0:
        parts.append(f"{age_int}-year-old")
    sex = st.session_state.get("patient_sex", "Not specified")
    if sex and sex != "Not specified":
        parts.append(str(sex).lower())
    egfr = str(st.session_state.get("patient_egfr", "")).strip()
    if egfr:
        parts.append(f"eGFR {egfr} mL/min/1.73m²")
    if st.session_state.get("patient_pregnancy"):
        parts.append("pregnant")
    comorb = str(st.session_state.get("patient_comorbidities", "")).strip()
    if comorb:
        parts.append(f"comorbidities: {comorb}")
    if not parts:
        return ""
    return "Patient context: " + ", ".join(parts) + "."


def compose_clinical_query(question: str) -> str:
    """Prepend patient context when provided (real-world CDS pattern)."""
    q = (question or "").strip()
    ctx = build_patient_context_block()
    if not ctx:
        return q
    return f"{ctx}\n\nClinical question: {q}"


def render_patient_context_panel() -> None:
    """Optional patient factors — dose/contraindication queries need this in practice."""
    init_patient_context_state()
    with st.expander("Patient context (optional)", expanded=False):
        _render_html(
            """
            <p class="sr-feature-hint">
              Add demographics and renal function so protocol answers account for
              contraindications, dosing, and special populations — standard in
              bedside and pharmacy validation workflows.
            </p>
            """
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input(
                "Age (years)",
                min_value=0,
                max_value=120,
                step=1,
                key="patient_age",
            )
        with c2:
            st.selectbox(
                "Sex",
                ["Not specified", "Female", "Male", "Other"],
                key="patient_sex",
            )
        with c3:
            st.text_input(
                "eGFR (mL/min/1.73m²)",
                placeholder="e.g. 45",
                key="patient_egfr",
            )
        st.checkbox("Pregnant / lactating", key="patient_pregnancy")
        st.text_input(
            "Comorbidities (comma-separated)",
            placeholder="e.g. CKD stage 3, heart failure",
            key="patient_comorbidities",
        )
        preview = build_patient_context_block()
        if preview:
            st.caption(f"Will prepend: {preview}")


def _source_doc_texts(sources: list | None) -> list[str]:
    texts: list[str] = []
    for meta in sources or []:
        if isinstance(meta, dict):
            texts.append(str(meta.get("text") or meta.get("chunk") or ""))
    return texts


def render_confidence_breakdown(
    answer: str,
    sources: list | None,
    query: str,
) -> None:
    """Explainable AI — four deterministic grounding factors."""
    docs = _source_doc_texts(sources)
    breakdown = score_confidence_breakdown(answer, docs, query)
    alignment = score_query_alignment(query, docs)

    factors = [
        ("Context coverage", breakdown["coverage"], breakdown["weights"]["coverage"],
         "Vocabulary overlap with retrieved guidelines"),
        ("No hedging", breakdown["no_uncertainty"], breakdown["weights"]["no_uncertainty"],
         "Absence of uncertainty phrases"),
        ("Specificity", breakdown["specificity"], breakdown["weights"]["specificity"],
         "Substantive, protocol-level detail"),
        ("No contradiction", breakdown["no_contradiction"], breakdown["weights"]["no_contradiction"],
         "No negation conflicts with source terms"),
    ]

    bars = ""
    for label, score, weight, hint in factors:
        pct = int(score * 100)
        contrib = score * weight * 100
        bars += f"""
        <div class="sr-factor-row">
            <div class="sr-factor-head">
                <span class="sr-factor-label">{_esc(label)}</span>
                <span class="sr-factor-meta">{pct}% · weight {weight:.0%} · +{contrib:.0f} pts</span>
            </div>
            <div class="sr-factor-track">
                <div class="sr-factor-fill" style="width:{pct}%;"></div>
            </div>
            <div class="sr-factor-hint">{_esc(hint)}</div>
        </div>
        """

    _render_html(
        f"""
        <div class="sr-feature-panel">
            <div class="sr-feature-panel-title">Grounding score breakdown</div>
            <p class="sr-feature-hint">
                Deterministic audit trail — not a second LLM judge. Total aligns with
                agent confidence; query–corpus alignment: {alignment:.0%}.
            </p>
            {bars}
        </div>
        """
    )


def render_source_provenance(sources: list | None) -> None:
    """Dated citations with currency status (real-world guideline governance)."""
    if not sources:
        _render_html(
            """
            <div class="sr-feature-panel sr-feature-warn">
                <div class="sr-feature-panel-title">Source provenance</div>
                <p class="sr-feature-hint">No guideline passages retrieved. Upload or ingest
                protocols before relying on any answer.</p>
            </div>
            """
        )
        return

    oldest = get_oldest_source_year(sources)
    outdated = should_warn_outdated(sources)
    warn_html = ""
    if outdated and oldest:
        warn_html = (
            f'<p class="sr-provenance-warn">Oldest source: {oldest} — '
            "verify against current standard-of-care guidelines.</p>"
        )

    rows = ""
    seen: set[tuple[str, str]] = set()
    for meta in sources:
        if not isinstance(meta, dict):
            continue
        source = str(meta.get("source") or meta.get("doc_name") or "Unknown")
        year = int(meta.get("publication_year") or 0)
        key = (source, str(year))
        if key in seen:
            continue
        seen.add(key)
        icon, label = recency_label(year)
        year_disp = str(year) if year else "Unknown"
        excerpt = str(meta.get("text") or meta.get("chunk") or "")[:200]
        rows += f"""
        <div class="sr-provenance-row">
            <div class="sr-provenance-head">
                <span>{icon} {_esc(label)}</span>
                <span class="sr-provenance-meta">{_esc(source)} · {year_disp}</span>
            </div>
            <p class="sr-provenance-excerpt">{_esc(excerpt)}</p>
        </div>
        """

    _render_html(
        f"""
        <div class="sr-feature-panel">
            <div class="sr-feature-panel-title">Source provenance · {len(seen)} passage(s)</div>
            {warn_html}
            {rows}
        </div>
        """
    )


_FLAG_CHECKLISTS: dict[str, list[str]] = {
    "contradicted": [
        "Cross-check answer against the cited guideline PDF",
        "Consult secondary literature or local protocol owner",
        "Do not communicate to patient until senior review",
    ],
    "retries_exhausted": [
        "Rephrase the question with specific drug/indication terms",
        "Upload missing local protocol documents",
        "Escalate to clinical pharmacist or attending",
    ],
    "low_confidence": [
        "Read full source excerpts below",
        "Confirm dose, route, and monitoring steps manually",
        "Document override rationale if proceeding",
    ],
    "insufficient_context": [
        "Upload the relevant guideline to the sidebar",
        "Run re-index after ingest completes",
        "Retry with narrower clinical terms",
    ],
    "out_of_scope": [
        "Question may be outside indexed corpus",
        "Ingest specialty guidelines or use PubMed ingest via API",
        "Verify manually with authoritative source",
    ],
    "error": [
        "Retry the query after checking GROQ_API_KEY and ChromaDB",
        "Review application logs",
        "Do not use partial output",
    ],
}


def render_clinical_review_panel(
    *,
    query: str,
    result: dict,
    log_timestamp: str | None,
) -> None:
    """Escalation workflow when answers are flagged or need human sign-off."""
    flagged = bool(result.get("flagged"))
    confidence = float(result.get("confidence", 0.0))
    verdict = str(result.get("validation_verdict", "ERROR"))
    flag_reason = str(result.get("flag_reason", ""))
    retry_count = int(result.get("retry_count", 0))

    title, body = format_review_banner(
        flagged,
        confidence,
        verdict,
        flag_reason,
        retry_count,
        config.HIGH_CONFIDENCE,
        config.MED_CONFIDENCE,
    )

    tone = "bad" if flagged else "ok" if confidence >= config.HIGH_CONFIDENCE else "warn"
    checklist = _FLAG_CHECKLISTS.get(
        flag_reason,
        _FLAG_CHECKLISTS["low_confidence"] if flagged else [],
    )
    items_html = "".join(f"<li>{_esc(item)}</li>" for item in checklist)

    _render_html(
        f"""
        <div class="sr-review-panel sr-review-{tone}">
            <div class="sr-feature-panel-title">Clinical review · {_esc(title)}</div>
            {"<ul class='sr-review-checklist'>" + items_html + "</ul>" if items_html else ""}
        </div>
        """
    )
    st.markdown(body)

    if not log_timestamp:
        return

    reviewed = st.session_state.clinical_review_notes.get(log_timestamp)
    if reviewed:
        st.success(f"Marked clinically reviewed — {reviewed.get('note', 'no note')}")
        return

    note = st.text_input(
        "Review note (optional)",
        placeholder="e.g. Verified against ADA 2024 — appropriate for eGFR >30",
        key=f"review_note_{log_timestamp}",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Mark clinically reviewed", key=f"review_ok_{log_timestamp}", type="primary"):
            st.session_state.clinical_review_notes[log_timestamp] = {
                "note": note.strip() or "Reviewed",
                "at": datetime.now(timezone.utc).isoformat(),
                "query": query[:200],
            }
            st.rerun()
    with c2:
        if st.button("Needs follow-up", key=f"review_follow_{log_timestamp}"):
            st.session_state.clinical_review_notes[log_timestamp] = {
                "note": note.strip() or "Needs follow-up",
                "at": datetime.now(timezone.utc).isoformat(),
                "query": query[:200],
            }
            st.rerun()


def render_validation_export(*, query: str, result: dict) -> None:
    """Download validation report — required for QA, M&M, and protocol committees."""
    answer = extract_clinical_answer(
        result.get("response", ""),
        result.get("messages"),
    )
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "patient_context": build_patient_context_block(),
        "answer": answer,
        "confidence": result.get("confidence"),
        "flagged": result.get("flagged"),
        "flag_reason": result.get("flag_reason"),
        "validation_verdict": result.get("validation_verdict"),
        "retry_count": result.get("retry_count"),
        "response_time_ms": result.get("response_time_ms"),
        "sources": result.get("sources") or [],
        "log_timestamp": result.get("log_timestamp"),
    }

    md_lines = [
        "# Sentinel-RAG validation report",
        "",
        f"**Exported:** {payload['exported_at']}",
        f"**Confidence:** {float(payload['confidence'] or 0):.0%}",
        f"**Verdict:** {payload['validation_verdict']}",
        f"**Flagged:** {payload['flagged']}",
        "",
        "## Query",
        query,
        "",
    ]
    if payload["patient_context"]:
        md_lines.extend(["## Patient context", payload["patient_context"], ""])
    md_lines.extend([
        "## Answer",
        answer,
        "",
        "## Review status",
        "Requires qualified clinician verification before clinical use.",
    ])
    markdown_report = "\n".join(md_lines)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download JSON report",
            data=json.dumps(payload, indent=2, default=str),
            file_name="sentinel_validation_report.json",
            mime="application/json",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Download Markdown summary",
            data=markdown_report,
            file_name="sentinel_validation_report.md",
            mime="text/markdown",
            use_container_width=True,
        )


def render_validation_insights(*, query: str, result: dict) -> None:
    """Post-validation panels: breakdown, provenance, review, export."""
    answer = extract_clinical_answer(
        result.get("response", ""),
        result.get("messages"),
    )
    sources = result.get("sources") or []
    log_ts = result.get("log_timestamp")

    st.markdown(
        _html('<div class="sr-cc-section" style="margin-top:1rem;">Validation insights</div>'),
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2)
    with col_left:
        render_confidence_breakdown(answer, sources, query)
    with col_right:
        render_source_provenance(sources)

    render_clinical_review_panel(query=query, result=result, log_timestamp=log_ts)
    render_validation_export(query=query, result=result)
