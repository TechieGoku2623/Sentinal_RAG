"""Streamlit UI for Sentinel-RAG — Clinical Protocol Guardian.

Premium clinician-facing interface over the self-reflective LangGraph agent.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src import config
from src.db.session import init_db
from src.feedback_logger import log_human_feedback
from src.services.audit_service import get_platform_stats
from src.services.knowledge_service import ingest_uploaded_file
from src.services.platform_health import check_api_health
from src.services.query_service import QuotaExceededError, execute_query
from src.services.recollection_service import record_from_validation
from src.retriever import get_collection_count
from src.text_utils import extract_clinical_answer
from ui.clinical_features import (
    compose_clinical_query,
    init_patient_context_state,
    render_patient_context_panel,
    render_validation_insights,
)
from ui.command_center import render_command_center
from ui.saas_shell import (
    current_tenant,
    init_saas_session,
    render_onboarding_wizard,
    render_saas_sidebar_extras,
)
from ui.components import (
    agent_pipeline_status,
    answer_card,
    app_topbar,
    feedback_prompt,
    platform_status_pill,
    section_divider,
    section_header,
    session_bar,
    sources_from_metadata,
)
from ui.theme import (
    SAMPLE_QUERIES,
    _html,
    inject_theme,
    render_footer,
    render_loading_pipeline,
    render_pipeline_overview,
    render_safety_disclaimer,
    render_sidebar_brand,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

HISTORY_CSV = "query_history.csv"
HIGH_CONFIDENCE = config.HIGH_CONFIDENCE
MEDIUM_CONFIDENCE = config.MED_CONFIDENCE
LINKEDIN_URL = "https://www.linkedin.com/in/devasai-pranatheswar"


def load_history() -> pd.DataFrame:
    if os.path.exists(HISTORY_CSV):
        try:
            return pd.read_csv(HISTORY_CSV)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not read query history: {exc}")
    return pd.DataFrame(
        columns=["timestamp", "query", "confidence", "flagged", "retry_count"]
    )


def append_history(query: str, confidence: float, flagged: bool, retry_count: int) -> None:
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "confidence": round(confidence, 4),
        "flagged": flagged,
        "retry_count": retry_count,
    }
    try:
        df = load_history()
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        df.to_csv(HISTORY_CSV, index=False)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not save query to history: {exc}")


def render_sidebar() -> None:
    with st.sidebar:
        render_sidebar_brand("v1.0")
        render_saas_sidebar_extras()

        st.markdown(
            _html(
                """
                <p style="font-size:0.82rem;line-height:1.55;color:#7A9AB8;margin:0;">
                    Guideline-grounded validation with deterministic scoring,
                    cross-model verification, and human escalation.
                </p>
                """
            ),
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown(
            _html('<div class="sr-sidebar-section">Knowledge base</div>'),
            unsafe_allow_html=True,
        )
        uploaded_files = st.file_uploader(
            "Upload clinical guidelines",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            help="PDF and plain-text protocol documents are chunked and indexed locally.",
        )
        if uploaded_files:
            _handle_uploads(uploaded_files)

        try:
            counts = get_collection_count()
        except Exception as exc:  # noqa: BLE001
            counts = {"parent": 0, "child": 0}
            st.error(f"Could not read guideline count: {exc}")

        c1, c2 = st.columns(2)
        c1.metric("Parent", counts.get("parent", 0))
        c2.metric("Child", counts.get("child", 0))

        st.divider()
        _render_feedback_stats()
        st.divider()

        st.markdown(
            _html('<div class="sr-sidebar-section">Platform</div>'),
            unsafe_allow_html=True,
        )
        api = check_api_health()
        if api.get("ok"):
            platform_status_pill(
                online=True,
                label="API online",
                detail=(
                    f"{api.get('chroma_parent_chunks', 0)} parent chunks · "
                    f"{api.get('url', 'localhost:8000')}"
                ),
            )
        else:
            platform_status_pill(
                online=False,
                label="API offline",
                detail=(
                    f"Start with uvicorn src.api.main:app --reload --port 8000 · "
                    f"{api.get('url', 'localhost:8000')}"
                ),
            )
        st.markdown(
            _html(
                """
                <p style="font-size:0.72rem;color:#3D5A73;margin:0.35rem 0 0;line-height:1.5;">
                    REST on <code style="color:#7A9AB8;">:8000</code> ·
                    SQLite at <code style="color:#7A9AB8;">data/sentinel.db</code>
                </p>
                """
            ),
            unsafe_allow_html=True,
        )

        if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and os.getenv(
            "LANGCHAIN_API_KEY"
        ):
            project = os.getenv("LANGCHAIN_PROJECT", "sentinel-rag-clinical")
            st.markdown(
                f"[View LangSmith traces](https://smith.langchain.com/) · `{project}`"
            )


def _render_feedback_stats() -> None:
    st.markdown(
        _html('<div class="sr-sidebar-section">Quality metrics</div>'),
        unsafe_allow_html=True,
    )
    try:
        stats = get_platform_stats(current_tenant())
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Stats unavailable: {exc}")
        return

    if stats["total_interactions"] == 0:
        st.caption("No interactions logged yet. Run a validation to begin building the reward-model dataset.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Sessions", stats["total_interactions"])
        st.metric("Avg confidence", f"{stats['avg_confidence']:.0%}")
    with col_b:
        st.metric("Flag rate", f"{stats['flag_rate']:.0%}")
        rating = stats["avg_human_rating"]
        st.metric(
            "Clinician rating",
            f"{rating:.1f}/5" if stats["total_rated"] else "—",
        )


def _handle_uploads(uploaded_files) -> None:
    tenant = current_tenant()
    for uploaded in uploaded_files:
        try:
            meta = ingest_uploaded_file(
                uploaded.name,
                uploaded.getbuffer().tobytes(),
                tenant_id=tenant,
                actor="ui",
            )
            st.success(
                f"Ingested {meta['parent_chunks']} parent + {meta['child_chunks']} "
                f"child chunks from {uploaded.name}"
            )
        except ValueError as exc:
            st.warning(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to ingest {uploaded.name}: {exc}")


def render_validate_tab() -> None:
    init_patient_context_state()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_log_timestamp" not in st.session_state:
        st.session_state.last_log_timestamp = None
    if "feedback_given" not in st.session_state:
        st.session_state.feedback_given = {}
    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    section_header(
        "Clinical workspace",
        "Ask a protocol question",
        "Grounded answers with deterministic confidence scoring, cross-model verification, "
        "and human-in-the-loop escalation.",
        anchor="clinical-query",
    )

    render_safety_disclaimer()
    render_patient_context_panel()

    completed_turns = len(st.session_state.messages) // 2
    header_left, header_right = st.columns([4, 1])
    with header_left:
        session_bar(completed_turns + 1)
    with header_right:
        st.markdown('<div style="height:0.65rem;"></div>', unsafe_allow_html=True)
        if st.button("Clear session", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_result = None
            st.rerun()

    if not st.session_state.messages and st.session_state.last_result is None:
        render_pipeline_overview()

    if st.session_state.messages:
        st.markdown(
            _html('<div class="sr-cc-section" style="margin-top:0;">Conversation</div>'),
            unsafe_allow_html=True,
        )
        last_idx = len(st.session_state.messages) - 1
        for i, msg in enumerate(st.session_state.messages):
            if (
                st.session_state.last_result
                and msg.get("role") == "assistant"
                and i == last_idx
            ):
                continue
            with st.chat_message(msg.get("role", "assistant")):
                content = msg.get("content", "")
                if msg.get("role") == "assistant":
                    st.markdown(extract_clinical_answer(content, [msg]))
                else:
                    st.markdown(content)

    if st.session_state.last_result:
        result = st.session_state.last_result
        display_query = st.session_state.get("last_clinical_query") or ""
        _render_results(
            response=result.get("response", ""),
            confidence=float(result.get("confidence", 0.0)),
            flagged=bool(result.get("flagged", False)),
            retry_count=int(result.get("retry_count", 0)),
            verdict=result.get("validation_verdict", "ERROR"),
            sources=result.get("sources", []),
            response_time_ms=result.get("response_time_ms"),
            messages=result.get("messages", []),
            flag_reason=result.get("flag_reason", ""),
            cache_hit=bool(result.get("cache_hit", False)),
        )
        render_validation_insights(query=display_query, result=result)

    st.markdown(
        _html('<div class="sr-cc-section" style="margin-top:1.5rem;">New query</div>'),
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        if "query_input" not in st.session_state:
            st.session_state.query_input = ""

        st.markdown('<div class="sr-chip-hint">Suggested prompts</div>', unsafe_allow_html=True)
        chip_cols = st.columns(len(SAMPLE_QUERIES))
        for idx, (col, sample) in enumerate(zip(chip_cols, SAMPLE_QUERIES)):
            with col:
                short = sample.split(",")[0][:42] + ("…" if len(sample.split(",")[0]) > 42 else "")
                if st.button(short, key=f"sample_{idx}", use_container_width=True):
                    st.session_state.query_input = sample
                    st.rerun()

        query = st.text_area(
            "Enter your protocol question",
            height=120,
            placeholder="e.g. What is the first-line therapy for type 2 diabetes, and what are the contraindications?",
            label_visibility="collapsed",
            key="query_input",
        )

        run_col, hint_col = st.columns([1, 2])
        with run_col:
            validate_clicked = st.button(
                "Validate protocol →",
                type="primary",
                use_container_width=True,
            )
        with hint_col:
            st.markdown(
                _html(
                    '<p style="margin:0.65rem 0 0;font-size:0.72rem;color:#3D5A73;">'
                    "Every run passes retrieve → generate → reflect → validate → govern.</p>"
                ),
                unsafe_allow_html=True,
            )

    if validate_clicked:
        if not query or not query.strip():
            st.warning("Please enter a clinical query first.")
            return

        full_query = compose_clinical_query(query.strip())
        st.session_state.last_clinical_query = full_query

        try:
            loading_slot = st.empty()
            for stage in ("retrieve", "generate", "reflect"):
                with loading_slot.container():
                    agent_pipeline_status(stage)
            result = execute_query(
                full_query,
                st.session_state.messages,
                tenant_id=current_tenant(),
            )
            with loading_slot.container():
                agent_pipeline_status("output")
            loading_slot.empty()
        except QuotaExceededError as exc:
            st.error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"The agent failed to process this query: {exc}")
            return

        st.session_state.messages = result.get("messages", st.session_state.messages)
        st.session_state.last_log_timestamp = result.get("log_timestamp") or None
        st.session_state.last_result = result

        append_history(
            full_query,
            float(result.get("confidence", 0.0)),
            bool(result.get("flagged", False)),
            int(result.get("retry_count", 0)),
        )
        record_from_validation(
            full_query,
            result,
            learner_level="trainee",
            tenant_id=current_tenant(),
        )
        st.rerun()

    _render_feedback_widget()


def _render_feedback_widget() -> None:
    ts = st.session_state.get("last_log_timestamp")
    if not ts:
        return

    st.divider()
    already = st.session_state.get("feedback_given", {}).get(ts)
    if already:
        st.caption(f"Thank you — clinician feedback recorded ({already}/5).")
        return

    st.markdown(
        _html('<div style="height:0.35rem;"></div>'),
        unsafe_allow_html=True,
    )
    feedback_prompt()
    up, ok, down = st.columns(3)
    rating = None
    with up:
        if st.button("Excellent (5)", key=f"fb_up_{ts}", use_container_width=True):
            rating = 5
    with ok:
        if st.button("Acceptable (3)", key=f"fb_ok_{ts}", use_container_width=True):
            rating = 3
    with down:
        if st.button("Not helpful (1)", key=f"fb_down_{ts}", use_container_width=True):
            rating = 1

    if rating is not None:
        try:
            log_human_feedback(ts, rating)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not record feedback: {exc}")
            return
        st.session_state.feedback_given[ts] = rating
        st.success("Feedback recorded — thank you.")
        st.rerun()


def _render_results(
    response: str,
    confidence: float,
    flagged: bool,
    retry_count: int,
    verdict: str = "ERROR",
    sources: list | None = None,
    response_time_ms: int | None = None,
    messages: list | None = None,
    flag_reason: str = "",
    cache_hit: bool = False,
) -> None:
    answer = extract_clinical_answer(response, messages)
    pct = int(min(max(confidence, 0.0), 1.0) * 100)
    latency = response_time_ms or 0
    doc_count = len(sources or [])

    answer_card(
        answer=answer,
        confidence=pct,
        retries=retry_count,
        latency_ms=latency,
        doc_count=doc_count,
        flagged=flagged,
        sources=sources_from_metadata(sources or []),
        verdict=verdict,
        cache_hit=cache_hit,
    )



def main() -> None:
    init_db()
    init_saas_session()
    favicon = "docs/brand/favicon.ico" if os.path.exists("docs/brand/favicon.ico") else None
    page_config: dict = {
        "page_title": "Sentinel-RAG · Clinical Protocol Guardian",
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }
    if favicon:
        page_config["page_icon"] = favicon
    st.set_page_config(**page_config)
    inject_theme()
    render_sidebar()

    if not render_onboarding_wizard():
        render_footer(LINKEDIN_URL)
        return

    api = check_api_health()
    app_topbar(
        current_tenant(),
        api_ok=bool(api.get("ok")),
        groq_ok=bool(os.getenv("GROQ_API_KEY")),
    )

    render_command_center()
    section_divider("Clinical workspace")
    render_validate_tab()

    render_footer(LINKEDIN_URL)


if __name__ == "__main__":
    main()
