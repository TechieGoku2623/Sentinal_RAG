"""Tests for mission-control dashboard helpers."""

from __future__ import annotations

import json
from pathlib import Path

from ui.command_center import _collect_action_items, _load_eval_summary


def test_load_eval_summary_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("ui.command_center.EVAL_JSON", tmp_path / "missing.json")
    assert _load_eval_summary() == {}


def test_load_eval_summary_reads_summary(tmp_path, monkeypatch):
    path = tmp_path / "eval_results.json"
    path.write_text(
        json.dumps({"summary": {"keyword_match_rate": 0.54, "questions_evaluated": 50}}),
        encoding="utf-8",
    )
    monkeypatch.setattr("ui.command_center.EVAL_JSON", path)
    summary = _load_eval_summary()
    assert summary["keyword_match_rate"] == 0.54
    assert summary["questions_evaluated"] == 50


def test_collect_action_items_api_offline(monkeypatch):
    monkeypatch.setattr(
        "ui.command_center.list_interactions",
        lambda **_: [],
    )
    items = _collect_action_items(
        api={"ok": False, "url": "http://localhost:8000/health"},
        usage={"queries_used": 0, "queries_limit": 100, "usage_pct": 0.1},
        overview={"documents": [], "collection_counts": {"parent": 0, "child": 0}},
    )
    titles = {i["title"] for i in items}
    assert "API offline" in titles
    assert "No guidelines indexed" in titles
