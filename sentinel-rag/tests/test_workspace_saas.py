"""Tests for SaaS workspace layer, quotas, and shared text helpers."""

from __future__ import annotations

import pytest

from src import config
from src.db.session import get_session, init_db
from src.services.workspace_service import (
    PLANS,
    check_document_quota,
    check_query_quota,
    create_workspace,
    ensure_default_workspace,
    get_usage,
    increment_query_usage,
    is_onboarding_complete,
    list_workspaces,
    set_onboarding_complete,
)
from src.text_utils import extract_clinical_answer, format_review_banner


@pytest.fixture
def saas_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(config, "DATABASE_URL", url)
    import src.db.session as db_session

    db_session._engine = None
    db_session._SessionLocal = None
    init_db()
    yield


def test_default_workspace_starter_plan_and_onboarding_pending(saas_db):
    ensure_default_workspace()
    workspaces = list_workspaces()
    default = next(w for w in workspaces if w["tenant_id"] == config.DEFAULT_TENANT_ID)
    assert default["plan_id"] == "starter"
    assert is_onboarding_complete(config.DEFAULT_TENANT_ID) is False


def test_create_workspace_and_usage_metering(saas_db):
    ws = create_workspace("Metro Clinic", "admin@metro.test", "starter")
    tenant = ws["tenant_id"]

    ok, _ = check_query_quota(tenant)
    assert ok is True

    increment_query_usage(tenant)
    usage = get_usage(tenant)
    assert usage["queries_used"] == 1
    assert usage["queries_limit"] == PLANS["starter"].queries_per_month


def test_query_quota_blocks_at_limit(saas_db):
    ws = create_workspace("Quota Test", "q@test.dev", "starter")
    tenant = ws["tenant_id"]
    limit = PLANS["starter"].queries_per_month
    for _ in range(limit):
        increment_query_usage(tenant)
    ok, msg = check_query_quota(tenant)
    assert ok is False
    assert "limit reached" in msg.lower()


def test_document_quota_enforced(saas_db):
    ws = create_workspace("Doc Test", "d@test.dev", "starter")
    tenant = ws["tenant_id"]
    from src.db.models import DocumentRegistry

    with get_session() as session:
        for i in range(PLANS["starter"].max_documents):
            session.add(
                DocumentRegistry(
                    tenant_id=tenant,
                    doc_name=f"doc_{i}",
                    source=f"doc_{i}.txt",
                    source_type="local",
                )
            )

    ok, msg = check_document_quota(tenant)
    assert ok is False
    assert "document limit" in msg.lower()


def test_onboarding_complete_persists(saas_db):
    ws = create_workspace("Onboard Co", "o@test.dev", "starter")
    tenant = ws["tenant_id"]
    assert is_onboarding_complete(tenant) is False
    set_onboarding_complete(tenant, True)
    assert is_onboarding_complete(tenant) is True


def test_format_review_banner_partial_supported_not_high_confidence():
    title, body = format_review_banner(
        flagged=False,
        confidence=0.92,
        verdict="PARTIALLY_SUPPORTED",
        flag_reason="",
        retry_count=0,
        high=0.85,
        medium=0.60,
    )
    assert title == "Moderate confidence"
    assert "partial support" in body.lower()


def test_extract_clinical_answer_from_messages():
    messages = [{"role": "assistant", "content": "Metformin is first-line therapy."}]
    answer = extract_clinical_answer("", messages)
    assert "Metformin" in answer
