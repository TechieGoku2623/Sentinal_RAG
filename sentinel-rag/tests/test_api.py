"""API integration tests (agent and external calls mocked)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(mocker):
    mocker.patch("src.api.main.init_db")
    mocker.patch("src.retriever.get_collection_count", return_value={"parent": 2, "child": 8})
    from src.api.main import app

    return TestClient(app)


def test_health(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["chroma_parent_chunks"] == 2


def test_query_endpoint(client, mocker) -> None:
    mocker.patch(
        "src.api.main.execute_query",
        return_value={
            "response": "answer\n---\nConfidence: 90%",
            "confidence": 0.9,
            "flagged": False,
            "retry_count": 0,
            "validation_verdict": "SUPPORTED",
            "conversation_id": "cid-1",
            "response_time_ms": 120,
            "log_timestamp": "ts-1",
            "sources": [],
            "messages": [{"role": "assistant", "content": "answer"}],
        },
    )
    resp = client.post("/v1/query", json={"query": "What is metformin?"})
    assert resp.status_code == 200
    assert resp.json()["response"] == "answer"
    assert resp.json()["confidence"] == 0.9


def test_knowledge_overview(client, mocker) -> None:
    mocker.patch(
        "src.api.main.get_knowledge_overview",
        return_value={"collection_counts": {"parent": 1, "child": 3}, "documents": []},
    )
    resp = client.get("/v1/knowledge")
    assert resp.status_code == 200
    assert resp.json()["collection_counts"]["child"] == 3


def test_api_key_required_when_set(client, mocker) -> None:
    mocker.patch("src.api.deps.os.getenv", return_value="secret-key")
    resp = client.post("/v1/query", json={"query": "test"})
    assert resp.status_code == 401

    resp = client.post(
        "/v1/query",
        json={"query": "test"},
        headers={"X-API-Key": "secret-key"},
    )
    assert resp.status_code != 401
