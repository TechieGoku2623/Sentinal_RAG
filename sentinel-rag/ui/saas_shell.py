"""SaaS application shell — workspace, onboarding, dashboard, settings."""

from __future__ import annotations

import os

import streamlit as st

from src import config
from src.services.audit_service import list_audit_events
from src.services.knowledge_service import get_knowledge_overview, ingest_uploaded_file
from src.services.workspace_service import (
    PLANS,
    create_workspace,
    ensure_default_workspace,
    get_usage,
    is_onboarding_complete,
    list_workspaces,
    set_onboarding_complete,
    update_workspace_plan,
)
from ui.theme import _html, render_sidebar_brand


def init_saas_session() -> None:
    ensure_default_workspace()
    if "workspace_select" not in st.session_state:
        st.session_state.workspace_select = config.DEFAULT_TENANT_ID
    pending = st.session_state.pop("pending_workspace_select", None)
    if pending:
        st.session_state.workspace_select = pending
    if "user_email" not in st.session_state:
        st.session_state.user_email = "clinician@workspace.local"

    tid = current_tenant()
    if not st.session_state.get("onboarding_step"):
        if is_onboarding_complete(tid):
            st.session_state.onboarding_complete = True
        else:
            usage = get_usage(tid)
            if usage["documents_used"] > 0 or usage["total_sessions"] > 0:
                set_onboarding_complete(tid, True)
                st.session_state.onboarding_complete = True
            else:
                st.session_state.onboarding_complete = False


def current_tenant() -> str:
    return str(st.session_state.get("workspace_select", config.DEFAULT_TENANT_ID))


def render_usage_meter(compact: bool = False) -> None:
    usage = get_usage(current_tenant())
    pct = int(usage["usage_pct"] * 100)
    bar_color = "#0369A1" if pct < 80 else "#B45309" if pct < 95 else "#B91C1C"
    if compact:
        st.markdown(
            _html(
                f"""
                <div style="margin:0.5rem 0 1rem;">
                    <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#94A3B8;">
                        <span>{usage['plan_name']} plan</span>
                        <span>{usage['queries_used']}/{usage['queries_limit']} queries</span>
                    </div>
                    <div style="height:6px;background:rgba(255,255,255,0.1);border-radius:999px;margin-top:4px;overflow:hidden;">
                        <div style="width:{pct}%;height:100%;background:{bar_color};border-radius:999px;"></div>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
    else:
        st.progress(min(usage["usage_pct"], 1.0))
        st.caption(
            f"{usage['queries_used']:,} / {usage['queries_limit']:,} validation queries this month "
            f"({usage['plan_name']} · {usage['price_label']})"
        )


def render_workspace_sidebar() -> None:
    workspaces = list_workspaces()
    options = {w["tenant_id"]: w["name"] for w in workspaces}
    if not options:
        options = {config.DEFAULT_TENANT_ID: "Default Clinical Workspace"}

    option_keys = list(options.keys())
    current = current_tenant()
    if current not in option_keys:
        option_keys.insert(0, current)
    if st.session_state.workspace_select not in option_keys:
        st.session_state.workspace_select = option_keys[0]

    st.selectbox(
        "Workspace",
        options=option_keys,
        format_func=lambda tid: options.get(tid, tid),
        key="workspace_select",
    )
    render_usage_meter(compact=True)


def render_onboarding_wizard() -> bool:
    """Return True when onboarding is complete and app can proceed."""
    if st.session_state.get("onboarding_complete"):
        return True

    st.markdown(
        _html(
            """
            <div class="sr-hero">
                <div class="sr-hero-badge">Step 1 of 3 · Workspace setup</div>
                <h1>Welcome to Sentinel-RAG<span>Clinical Protocol Guardian</span></h1>
                <p>Create your clinical workspace to validate protocol questions against
                your own guideline corpus — with audit trails and usage governance built in.</p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    step = st.session_state.get("onboarding_step", 1)

    if step == 1:
        st.markdown("##### Create your workspace")
        name = st.text_input("Organization / clinic name", placeholder="Metro Endocrine Clinic")
        email = st.text_input("Work email", value=st.session_state.get("user_email", ""))
        plan = st.selectbox(
            "Plan",
            options=list(PLANS.keys()),
            format_func=lambda p: f"{PLANS[p].name} — {PLANS[p].price_label}",
        )
        if st.button("Continue →", type="primary"):
            if not name.strip():
                st.warning("Enter an organization name.")
            else:
                ws = create_workspace(name, email or "admin@workspace.local", plan)
                st.session_state.pending_workspace_select = ws["tenant_id"]
                st.session_state.user_email = email
                st.session_state.onboarding_step = 2
                st.rerun()

    elif step == 2:
        st.markdown("##### Upload your first guideline")
        st.caption(
            "PDF or plain-text clinical protocols are chunked and indexed locally — "
            "nothing leaves your environment."
        )
        uploaded = st.file_uploader(
            "Guideline document",
            type=["pdf", "txt"],
            key="onboarding_upload",
        )
        if uploaded is not None:
            try:
                meta = ingest_uploaded_file(
                    uploaded.name,
                    uploaded.getbuffer().tobytes(),
                    tenant_id=current_tenant(),
                    actor="onboarding",
                )
                st.success(
                    f"Ingested {meta['parent_chunks']} parent + {meta['child_chunks']} "
                    f"child chunks from {uploaded.name}"
                )
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:  # noqa: BLE001
                st.error(f"Upload failed: {exc}")

        overview = get_knowledge_overview(current_tenant())
        doc_count = len(overview.get("documents", []))
        st.metric("Documents indexed", doc_count)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Back"):
                st.session_state.onboarding_step = 1
                st.rerun()
        with c2:
            if st.button("Continue →", type="primary", disabled=doc_count == 0):
                st.session_state.onboarding_step = 3
                st.rerun()
            if doc_count == 0:
                st.caption("Upload at least one document above to continue.")

    elif step == 3:
        st.markdown("##### Run your first validation")
        st.success("Workspace ready. You can now validate clinical protocol questions.")
        if st.button("Enter workspace →", type="primary"):
            set_onboarding_complete(current_tenant(), True)
            st.session_state.onboarding_complete = True
            st.session_state.pop("onboarding_step", None)
            st.rerun()

    return False


def render_dashboard_tab() -> None:
    usage = get_usage(current_tenant())
    stats_cols = st.columns(4)
    stats_cols[0].metric("Plan", usage["plan_name"])
    stats_cols[1].metric("Queries this month", f"{usage['queries_used']:,}")
    stats_cols[2].metric("Avg confidence", f"{usage['avg_confidence']:.0%}")
    stats_cols[3].metric("Flag rate", f"{usage['flag_rate']:.0%}")

    st.markdown("##### Usage")
    render_usage_meter()

    left, right = st.columns(2)
    with left:
        st.markdown("##### Knowledge base")
        overview = get_knowledge_overview(current_tenant())
        docs = overview.get("documents", [])
        counts = overview.get("collection_counts", {})
        st.metric("Indexed documents", len(docs))
        st.metric("Parent chunks", counts.get("parent", 0))
        st.metric("Child chunks", counts.get("child", 0))

    with right:
        st.markdown("##### Recent audit events")
        events = list_audit_events(limit=8, tenant_id=current_tenant())
        if not events:
            st.caption("No audit events yet.")
        else:
            for ev in events:
                st.caption(f"**{ev.get('event_type', '')}** — {ev.get('detail', '')[:80]}")

    st.markdown(
        _html(
            """
            <div class="sr-panel" style="margin-top:1rem;">
                <div class="sr-panel-title">SaaS platform</div>
                <div class="sr-panel-heading">How your workspace is governed</div>
                <p style="color:#64748B;font-size:0.88rem;margin:0;">
                    Every validation is metered, logged, and subject to plan limits.
                    Upgrade for higher query volume, more documents, and API access.
                    Full architecture: <code>docs/SAAS_ARCHITECTURE.md</code>
                </p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_settings_tab() -> None:
    usage = get_usage(current_tenant())
    st.markdown("##### Workspace settings")
    st.text_input("Workspace ID", value=current_tenant(), disabled=True)
    st.text_input("Signed in as", value=st.session_state.get("user_email", ""), disabled=True)

    st.markdown("##### Subscription")
    plan_keys = list(PLANS.keys())
    current_idx = plan_keys.index(usage["plan"]) if usage["plan"] in plan_keys else 0
    new_plan = st.selectbox(
        "Plan tier (prototype — no billing yet)",
        options=plan_keys,
        index=current_idx,
        format_func=lambda p: (
            f"{PLANS[p].name} — {PLANS[p].price_label} · "
            f"{PLANS[p].queries_per_month:,} queries/mo"
        ),
    )
    if st.button("Update plan"):
        if update_workspace_plan(current_tenant(), new_plan):
            st.success(f"Plan updated to {PLANS[new_plan].name}.")
            st.rerun()

    st.markdown("##### API access")
    api_key_set = bool(os.getenv("SENTINEL_API_KEY") or config.API_KEY)
    st.code("uvicorn src.api.main:app --reload --port 8000", language="bash")
    if api_key_set:
        st.success("API key configured. Use header `X-API-Key` on `/v1/*` endpoints.")
    else:
        st.warning("Set `SENTINEL_API_KEY` in `.env` to enable API authentication.")

    st.markdown("##### Reset onboarding")
    if st.button("Re-run setup wizard"):
        set_onboarding_complete(current_tenant(), False)
        st.session_state.onboarding_complete = False
        st.session_state.onboarding_step = 1
        st.rerun()


def render_saas_sidebar_extras() -> None:
    """Call after render_sidebar_brand inside sidebar."""
    render_workspace_sidebar()
    st.divider()
    if st.button("＋ New workspace", use_container_width=True):
        st.session_state.onboarding_complete = False
        st.session_state.onboarding_step = 1
        st.rerun()
