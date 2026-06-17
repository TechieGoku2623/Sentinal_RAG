"""Tests for clinical recollection and spaced repetition."""

from __future__ import annotations

import pytest

from src.db.models import RecollectionTopic
from src.db.session import get_session, init_db
from src.services.recollection_service import (
    _topic_key,
    ensure_topic,
    get_recollection_summary,
    record_from_validation,
    record_study_attempt,
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    from src.db import session as session_module

    session_module._engine = None
    session_module._SessionLocal = None
    init_db()
    yield
    session_module._engine = None
    session_module._SessionLocal = None


def test_topic_key_normalizes_whitespace() -> None:
    assert _topic_key("  What   is  metformin? ") == "what is metformin?"


def test_record_from_validation_creates_topic(db) -> None:
    topic_id = record_from_validation(
        "What is first-line therapy for type 2 diabetes?",
        {"confidence": 0.82, "flagged": False, "sources": [{"source": "ADA"}]},
        learner_level="trainee",
    )
    assert topic_id is not None
    summary = get_recollection_summary("trainee")
    assert summary["total_topics"] == 1


def test_spaced_repetition_increases_interval_on_success(db) -> None:
    topic_id = ensure_topic(
        "Metformin starting dose?",
        learner_level="experienced",
        category="diabetes",
    )
    assert topic_id is not None

    with get_session() as session:
        before = session.query(RecollectionTopic).filter_by(id=topic_id).one()
        start_interval = before.interval_days

    assert record_study_attempt(topic_id, 5, recalled_correctly=True, learner_level="experienced")

    with get_session() as session:
        after = session.query(RecollectionTopic).filter_by(id=topic_id).one()
        assert after.repetition_count >= 1
        assert after.mastery_score > 0
        assert after.interval_days >= start_interval


def test_failed_recall_resets_schedule(db) -> None:
    topic_id = ensure_topic("HbA1c target in elderly?", learner_level="trainee")
    record_study_attempt(topic_id, 5, recalled_correctly=True, learner_level="trainee")
    record_study_attempt(topic_id, 1, recalled_correctly=False, learner_level="trainee")

    with get_session() as session:
        row = session.query(RecollectionTopic).filter_by(id=topic_id).one()
        assert row.interval_days == 1
        assert row.lapse_count >= 1


def test_flagged_validation_surfaces_in_summary(db) -> None:
    record_from_validation(
        "Drug interaction with warfarin?",
        {"confidence": 0.4, "flagged": True, "sources": []},
        learner_level="trainee",
    )
    summary = get_recollection_summary("trainee")
    assert summary["flagged_topics"] == 1
    assert "flagged" in summary["brief"].lower()
