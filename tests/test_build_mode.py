"""Hallmark Build Studio tests."""

from __future__ import annotations

from ui.build_mode import BUILD_MODES
from ui.hallmark_gates import run_hallmark_audit


def test_hallmark_verbs() -> None:
    assert set(BUILD_MODES.keys()) == {"audit", "redesign", "study"}
    assert BUILD_MODES["audit"]["verb"] == "audit"


def test_hallmark_audit_runs() -> None:
    findings = run_hallmark_audit()
    assert isinstance(findings, list)
