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

from src import config
from src.db.session import init_db
from src.feedback_logger import log_human_feedback
from src.ingest import ingest_all_guidelines
from src.recency_scorer import recency_label
from src.services.audit_service import get_platform_stats, list_audit_events, list_interactions
from src.services.knowledge_service import (
    get_knowledge_overview,
    ingest_openfda,
    ingest_pubmed,
    ingest_uploaded_file,
    remove_document,
)
from src.services.query_service import QuotaExceededError, execute_query
from src.services.recollection_service import (
    ensure_topic,
    format_study_prompt,
    get_due_topics,
    get_guideline_snippet_for_topic,
    get_recollection_summary,
    get_recent_topics,
    get_study_queue,
    record_from_validation,
    record_study_attempt,
)
from src.retriever import get_collection_count
from ui.saas_shell import (
    current_tenant,
    init_saas_session,
    render_dashboard_tab,
    render_onboarding_wizard,
    render_saas_sidebar_extras,
    render_settings_tab,
)
from ui.theme import (
    SAMPLE_QUERIES,
    inject_theme,
    render_footer,
    render_hero,
    render_loading_pipeline,
    render_pipeline_overview,
    render_results_panel,
    render_safety_disclaimer,
    render_sidebar_brand,
    render_trust_bar,
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


def _learner_level() -> str:
    return st.session_state.get("learner_level", "trainee")


def render_sidebar() -> None:
    with st.sidebar:
        render_sidebar_brand("v1.0")
        render_saas_sidebar_extras()

        st.markdown("#### Learning profile")
        st.radio(
            "I am a…",
            options=["trainee", "experienced"],
            format_func=lambda x: (
                "Trainee — guided recall & hints"
                if x == "trainee"
                else "Experienced — quick protocol refresh"
            ),
            key="learner_level",
        )

        st.markdown(
            "Enterprise-grade clinical protocol validation with "
            "deterministic grounding scores, cross-model verification, "
            "and human-in-the-loop escalation."
        )
        st.divider()

        st.markdown("#### Knowledge base")
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

        st.markdown("#### Platform")
        st.markdown(
            "- REST API on `:8000` (`uvicorn src.api.main:app`)\n"
            "- SQLite audit store (`data/sentinel.db`)\n"
            "- PubMed + OpenFDA ingest\n"
            "- Document registry + delete"
        )

        if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and os.getenv(
            "LANGCHAIN_API_KEY"
        ):
            project = os.getenv("LANGCHAIN_PROJECT", "sentinel-rag-clinical")
            st.markdown(
                f"[View LangSmith traces](https://smith.langchain.com/) · `{project}`"
            )


def _render_feedback_stats() -> None:
    st.markdown("#### Quality metrics")
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
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_log_timestamp" not in st.session_state:
        st.session_state.last_log_timestamp = None
    if "feedback_given" not in st.session_state:
        st.session_state.feedback_given = {}
    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    render_safety_disclaimer()

    completed_turns = len(st.session_state.messages) // 2
    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.markdown(
            f"**Protocol validation workspace** · Turn {completed_turns + 1}"
        )
    with header_right:
        if st.button("Clear session", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_result = None
            st.rerun()

    if not st.session_state.messages and st.session_state.last_result is None:
        render_pipeline_overview()

    for msg in st.session_state.messages:
        with st.chat_message(msg.get("role", "assistant")):
            content = msg.get("content", "")
            if msg.get("role") == "assistant":
                st.markdown(extract_clinical_answer(content, [msg]))
            else:
                st.markdown(content)

    st.markdown("##### Clinical query")
    if "query_input" not in st.session_state:
        st.session_state.query_input = ""

    st.caption("Suggested queries — click to populate")
    chip_cols = st.columns(len(SAMPLE_QUERIES))
    for idx, (col, sample) in enumerate(zip(chip_cols, SAMPLE_QUERIES)):
        with col:
            if st.button(f"Example {idx + 1}", key=f"sample_{idx}", use_container_width=True):
                st.session_state.query_input = sample
                st.rerun()

    query = st.text_area(
        "Enter your protocol question",
        height=100,
        placeholder="e.g. What is the first-line therapy for type 2 diabetes, and what are the contraindications?",
        label_visibility="collapsed",
        key="query_input",
    )

    run_col, _ = st.columns([1, 3])
    with run_col:
        validate_clicked = st.button("Validate protocol", type="primary", use_container_width=True)

    if validate_clicked:
        if not query or not query.strip():
            st.warning("Please enter a clinical query first.")
            return

        try:
            loading_slot = st.empty()
            with loading_slot.container():
                render_loading_pipeline()
            result = execute_query(
                query.strip(),
                st.session_state.messages,
                tenant_id=current_tenant(),
            )
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
            query.strip(),
            float(result.get("confidence", 0.0)),
            bool(result.get("flagged", False)),
            int(result.get("retry_count", 0)),
        )
        record_from_validation(
            query.strip(),
            result,
            learner_level=_learner_level(),
            tenant_id=current_tenant(),
        )

    if st.session_state.last_result:
        result = st.session_state.last_result
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
        )

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

    st.markdown("**Clinician feedback** — Was this response helpful for protocol review?")
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


def _format_source_citation(meta: dict) -> str:
    source = str(meta.get("source", "") or "Unknown source")
    year = meta.get("publication_year", 0) or 0
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = 0
    icon, label = recency_label(year)
    year_str = str(year) if year > 0 else "undated"
    return f"{source} · {year_str} · {icon} {label}"


def _render_source_citations(sources: list) -> None:
    if not sources:
        return

    seen = set()
    unique = []
    for meta in sources:
        key = (str(meta.get("source", "")), meta.get("publication_year", 0))
        if key not in seen:
            seen.add(key)
            unique.append(meta)

    with st.expander(f"Source guidelines ({len(unique)})", expanded=False):
        st.caption("Verify currency and institutional approval before clinical use.")
        for meta in unique:
            st.markdown(f"- {_format_source_citation(meta)}")


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
) -> None:
    render_results_panel(
        response,
        confidence,
        flagged,
        verdict,
        retry_count,
        response_time_ms,
        HIGH_CONFIDENCE,
        MEDIUM_CONFIDENCE,
        messages=messages,
        flag_reason=flag_reason,
    )
    _render_source_citations(sources or [])


def render_history_tab() -> None:
    st.markdown("##### Audit trail")
    st.caption("Complete log of protocol validations with confidence and escalation status.")

    rows = list_interactions(limit=200, tenant_id=current_tenant())
    if not rows:
        st.info("No validations yet. Completed queries will appear here for audit review.")
        return

    df = pd.DataFrame(rows)
    total = len(df)
    flagged_count = sum(1 for v in df["flagged"] if v)
    avg_conf = df["confidence"].mean() if "confidence" in df.columns else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total validations", total)
    m2.metric("Flagged for review", flagged_count)
    m3.metric("Avg confidence", f"{avg_conf:.0%}")

    def _highlight_flagged(row):
        is_flagged = bool(row.get("flagged", False))
        return ["background-color: #FEE2E2" if is_flagged else "" for _ in row]

    try:
        styled = df.style.apply(_highlight_flagged, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
    except Exception:  # noqa: BLE001
        st.dataframe(df, use_container_width=True, hide_index=True)

    try:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Export audit log (CSV)",
            data=csv_bytes,
            file_name="sentinel_rag_audit_log.csv",
            mime="text/csv",
            use_container_width=True,
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not prepare export: {exc}")


def render_admin_tab() -> None:
    st.markdown("##### Knowledge base admin")
    st.caption("Manage indexed guidelines, external evidence, and platform audit events.")

    tenant = current_tenant()
    overview = get_knowledge_overview(tenant)
    counts = overview.get("collection_counts", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Parent chunks", counts.get("parent", 0))
    c2.metric("Child chunks", counts.get("child", 0))
    c3.metric("Registered docs", len(overview.get("documents", [])))

    if st.button("Re-index local `data/guidelines/`", use_container_width=True):
        with st.spinner("Re-indexing local guidelines…"):
            ingest_all_guidelines()
        st.success("Local guidelines re-indexed.")
        st.rerun()

    documents = overview.get("documents", [])
    if documents:
        st.markdown("**Indexed documents**")
        for doc in documents:
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(
                    f"**{doc['doc_name']}** · {doc.get('source_type', 'local')} · "
                    f"{doc.get('source', '')} · "
                    f"{doc.get('parent_chunks', 0)}p / {doc.get('child_chunks', 0)}c"
                )
            with col_b:
                if st.button("Remove", key=f"del_{doc['doc_name']}"):
                    remove_document(doc["doc_name"], tenant_id=tenant, actor="admin-ui")
                    st.success(f"Removed {doc['doc_name']}")
                    st.rerun()
    else:
        st.info("No documents indexed yet. Upload files or ingest external evidence.")

    st.divider()
    st.markdown("**Platform audit events**")
    events = list_audit_events(limit=20, tenant_id=tenant)
    if events:
        st.dataframe(events, use_container_width=True, hide_index=True)
    else:
        st.caption("No audit events yet.")


def render_external_tab() -> None:
    tenant = current_tenant()
    st.markdown("##### External evidence ingest")
    st.caption(
        "Pull PubMed abstracts or FDA drug labels into the local ChromaDB index. "
        "Verify clinical currency before relying on any source."
    )

    st.markdown("**PubMed**")
    pubmed_query = st.text_input(
        "PubMed search query",
        placeholder="metformin type 2 diabetes first-line",
        key="pubmed_query",
    )
    pubmed_max = st.slider("Max articles", 1, 25, 5, key="pubmed_max")
    if st.button("Ingest from PubMed", use_container_width=True):
        if not pubmed_query.strip():
            st.warning("Enter a PubMed search query.")
        else:
            with st.spinner("Fetching PubMed abstracts…"):
                result = ingest_pubmed(
                    pubmed_query.strip(),
                    max_results=pubmed_max,
                    tenant_id=tenant,
                    actor="ui",
                )
            if result.get("articles", 0):
                st.success(result.get("message", "PubMed ingest complete."))
            else:
                st.warning(result.get("message", "No results."))

    st.divider()
    st.markdown("**OpenFDA drug labels**")
    drug_name = st.text_input("Drug name", placeholder="metformin", key="openfda_drug")
    if st.button("Ingest FDA label", use_container_width=True):
        if not drug_name.strip():
            st.warning("Enter a drug name.")
        else:
            with st.spinner("Fetching FDA label…"):
                result = ingest_openfda(drug_name.strip(), tenant_id=tenant, actor="ui")
            if result.get("found"):
                st.success(result.get("message", "OpenFDA ingest complete."))
            else:
                st.warning(result.get("message", "Drug not found."))


def render_recollection_tab() -> None:
    tenant = current_tenant()
    level = _learner_level()
    st.markdown("##### Clinical recollection")
    if level == "trainee":
        st.caption(
            "Build long-term protocol memory with guided recall, guideline snippets, "
            "and spaced repetition. Topics from your validation runs are saved automatically."
        )
    else:
        st.caption(
            "Refresh protocol decisions with quick-recall prompts and spaced review. "
            "Prior validation topics and flagged items resurface when you need them."
        )

    summary = get_recollection_summary(level, tenant_id=tenant)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Topics tracked", summary["total_topics"])
    m2.metric("Due today", summary["due_today"])
    m3.metric("Flagged for review", summary["flagged_topics"])
    m4.metric("Avg mastery", f"{summary['avg_mastery']:.0%}")

    st.info(summary["brief"])

    if "study_queue" not in st.session_state:
        st.session_state.study_queue = []
    if "study_index" not in st.session_state:
        st.session_state.study_index = 0
    if "study_revealed" not in st.session_state:
        st.session_state.study_revealed = False

    st.divider()
    st.markdown("**Study session**")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Start / refresh study queue", use_container_width=True):
            st.session_state.study_queue = get_study_queue(level, limit=8, tenant_id=tenant)
            st.session_state.study_index = 0
            st.session_state.study_revealed = False
            st.rerun()
    with col_b:
        if st.button("Jump to due reviews only", use_container_width=True):
            st.session_state.study_queue = get_due_topics(level, limit=8, tenant_id=tenant)
            st.session_state.study_index = 0
            st.session_state.study_revealed = False
            st.rerun()

    queue = st.session_state.study_queue
    if not queue:
        st.markdown(
            "_No study queue yet. Run **Protocol validation** or click "
            "**Start / refresh study queue** to pull curriculum and past topics._"
        )
    else:
        idx = min(st.session_state.study_index, len(queue) - 1)
        card = queue[idx]
        st.progress((idx + 1) / len(queue), text=f"Card {idx + 1} of {len(queue)} · {card.get('queue_reason', 'review')}")

        st.markdown(format_study_prompt(card["topic"], level))

        if level == "trainee" and card.get("keywords"):
            with st.expander("Hint keywords (trainee)", expanded=False):
                st.write(", ".join(card["keywords"]))

        if st.button("Reveal guideline excerpt", key=f"reveal_{idx}"):
            st.session_state.study_revealed = True

        if st.session_state.study_revealed:
            st.markdown(get_guideline_snippet_for_topic(card["topic"]))
            if level == "trainee":
                st.markdown(
                    "**Reflect:** What indication, dose, contraindication, or monitoring step "
                    "will you remember for next time?"
                )

            st.markdown("**How well did you recall this?**")
            r1, r2, r3, r4, r5 = st.columns(5)
            rating = None
            with r1:
                if st.button("1", key=f"rate1_{idx}"):
                    rating = 1
            with r2:
                if st.button("2", key=f"rate2_{idx}"):
                    rating = 2
            with r3:
                if st.button("3", key=f"rate3_{idx}"):
                    rating = 3
            with r4:
                if st.button("4", key=f"rate4_{idx}"):
                    rating = 4
            with r5:
                if st.button("5", key=f"rate5_{idx}"):
                    rating = 5

            if rating is not None:
                topic_id = card.get("id") or ensure_topic(
                    card["topic"],
                    learner_level=level,
                    category=card.get("category", "general"),
                    guideline_source=card.get("guideline_source", ""),
                    tenant_id=tenant,
                )
                if topic_id:
                    record_study_attempt(
                        topic_id,
                        rating,
                        recalled_correctly=rating >= 4,
                        learner_level=level,
                        tenant_id=tenant,
                    )
                st.session_state.study_index = min(idx + 1, len(queue) - 1)
                st.session_state.study_revealed = False
                if idx + 1 >= len(queue):
                    st.success("Study session complete — topics rescheduled for spaced review.")
                    st.session_state.study_queue = []
                st.rerun()

    st.divider()
    st.markdown("**Recall from past sessions**")
    recent = get_recent_topics(level, limit=8, tenant_id=tenant)
    if not recent:
        st.caption("Past validation topics will appear here for quick recollection.")
    else:
        for item in recent:
            c1, c2 = st.columns([5, 1])
            with c1:
                flag = " · flagged" if item.get("flagged") else ""
                st.markdown(
                    f"**{item['topic'][:120]}** · mastery {item['mastery_score']:.0%}{flag}"
                )
            with c2:
                if st.button("Review", key=f"recall_{item['id']}"):
                    st.session_state.study_queue = [item]
                    st.session_state.study_index = 0
                    st.session_state.study_revealed = False
                    st.rerun()


def main() -> None:
    init_db()
    init_saas_session()
    favicon = (
        "docs/brand/favicon.ico"
        if os.path.exists("docs/brand/favicon.ico")
        else "docs/screenshots/favicon.ico"
    )
    st.set_page_config(
        page_title="Sentinel-RAG · Clinical Protocol Guardian",
        page_icon=favicon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()
    render_sidebar()

    if not render_onboarding_wizard():
        render_footer(LINKEDIN_URL)
        return

    render_hero()
    render_trust_bar()

    tab_dash, tab_validate, tab_recollection, tab_external, tab_admin, tab_history, tab_settings = st.tabs([
        "Dashboard",
        "Protocol validation",
        "Clinical recollection",
        "External evidence",
        "Admin console",
        "Audit trail",
        "Settings",
    ])
    with tab_dash:
        render_dashboard_tab()
    with tab_validate:
        render_validate_tab()
    with tab_recollection:
        render_recollection_tab()
    with tab_external:
        render_external_tab()
    with tab_admin:
        render_admin_tab()
    with tab_history:
        render_history_tab()
    with tab_settings:
        render_settings_tab()

    st.divider()
    render_footer(LINKEDIN_URL)


if __name__ == "__main__":
    main()
