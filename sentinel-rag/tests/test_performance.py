"""Performance layer — latency modes, query cache, batch queue."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from src import config
from src.db.session import init_db
from src.services.batch_queue import create_batch_job, get_job
from src.services.query_cache import get_cached_result, invalidate_tenant, set_cached_result
from src.services.retrieval_cache import clear_retrieval_cache, get_retrieval, set_retrieval


@pytest.fixture
def perf_db(tmp_path, monkeypatch):
    db_path = tmp_path / "perf_test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(config, "DATABASE_URL", url)
    monkeypatch.setattr(config, "QUERY_CACHE_ENABLED", True)
    monkeypatch.setattr(config, "RETRIEVAL_CACHE_ENABLED", True)
    import src.db.session as db_session

    db_session._engine = None
    db_session._SessionLocal = None
    init_db()
    yield
    clear_retrieval_cache()


@pytest.fixture()
def client(mocker):
    mocker.patch("src.api.main.init_db")
    mocker.patch("src.api.main.start_batch_worker")
    mocker.patch("src.api.main.stop_batch_worker")
    mocker.patch("src.retriever.get_collection_count", return_value={"parent": 2, "child": 8})
    from src.api.main import app

    return TestClient(app)


def test_max_retries_for_mode() -> None:
    assert config.max_retries_for_mode("standard") == config.MAX_RETRIES
    assert config.max_retries_for_mode("fast") == 1
    assert config.max_retries_for_mode("bedside") == 0


def test_skip_cross_validation_bedside() -> None:
    assert config.skip_cross_validation(
        "bedside",
        confidence=config.HIGH_CONFIDENCE,
        alignment=config.QUERY_ALIGNMENT_MIN,
        corpus_grounded=True,
        insufficient_context=False,
    )
    assert not config.skip_cross_validation(
        "bedside",
        confidence=config.HIGH_CONFIDENCE,
        alignment=config.QUERY_ALIGNMENT_MIN,
        corpus_grounded=False,
        insufficient_context=False,
    )
    assert not config.skip_cross_validation(
        "standard",
        confidence=0.99,
        alignment=0.99,
        corpus_grounded=True,
        insufficient_context=False,
    )


def test_query_cache_roundtrip(perf_db, mocker) -> None:
    mocker.patch(
        "src.services.query_cache.get_collection_count",
        return_value={"parent": 1, "child": 4},
    )
    payload = {
        "response": "Metformin is first-line.",
        "confidence": 0.9,
        "flagged": False,
        "retry_count": 0,
        "validation_verdict": "SUPPORTED",
        "sources": [],
        "messages": [],
    }
    set_cached_result("default", "What is first-line T2D therapy?", [], "fast", payload)
    cached = get_cached_result("default", "What is first-line T2D therapy?", [], "fast")
    assert cached is not None
    assert cached["cache_hit"] is True
    assert cached["response"] == payload["response"]

    invalidate_tenant("default")
    assert get_cached_result("default", "What is first-line T2D therapy?", [], "fast") is None


def test_retrieval_cache_lru() -> None:
    set_retrieval("q1", False, [{"id": "a"}])
    hit = get_retrieval("q1", False)
    assert hit is not None
    assert hit[0]["id"] == "a"
    clear_retrieval_cache()
    assert get_retrieval("q1", False) is None


def test_batch_job_lifecycle(perf_db, mocker) -> None:
    mocker.patch(
        "src.services.batch_queue.execute_query",
        return_value={
            "response": "ok",
            "confidence": 0.88,
            "flagged": False,
            "retry_count": 0,
            "validation_verdict": "SUPPORTED",
            "flag_reason": "",
            "response_time_ms": 50,
            "cache_hit": False,
            "latency_mode": "fast",
            "messages": [],
        },
    )
    job = create_batch_job(["Q1", "Q2"], "default", latency_mode="fast")
    assert job["status"] in {"queued", "running", "completed"}
    assert job["total"] == 2

    deadline = time.time() + 5
    final = job
    while time.time() < deadline:
        final = get_job(job["job_id"])
        if final["status"] == "completed":
            break
        time.sleep(0.05)

    assert final["status"] == "completed"
    assert final["completed"] == 2
    assert len(final["results"]) == 2
    assert all(item["ok"] for item in final["results"])


def test_batch_api(client, mocker) -> None:
    mocker.patch(
        "src.api.main.create_batch_job",
        return_value={
            "job_id": "job-1",
            "tenant_id": "default",
            "status": "queued",
            "latency_mode": "fast",
            "total": 1,
            "completed": 0,
            "results": [],
            "error": "",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        },
    )
    resp = client.post(
        "/v1/query/batch",
        json={"queries": ["What is metformin?"], "latency_mode": "fast"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "job-1"
