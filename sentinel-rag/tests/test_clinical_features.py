"""Tests for clinical workspace helpers."""

from __future__ import annotations

from src.reflection import score_confidence, score_confidence_breakdown
from ui.clinical_features import build_patient_context_block, compose_clinical_query


def test_score_confidence_breakdown_matches_total() -> None:
    docs = [
        "Metformin is first-line for type 2 diabetes. Contraindicated if eGFR below 30."
    ]
    response = (
        "Metformin remains first-line for type 2 diabetes and is contraindicated "
        "when eGFR is below 30."
    )
    breakdown = score_confidence_breakdown(response, docs, "metformin first line?")
    assert breakdown["total"] == score_confidence(response, docs, "metformin first line?")
    assert 0.0 <= breakdown["coverage"] <= 1.0


def test_compose_clinical_query_without_context() -> None:
    assert compose_clinical_query("What is first-line T2D therapy?") == (
        "What is first-line T2D therapy?"
    )


def test_compose_clinical_query_with_context(monkeypatch) -> None:
    class FakeState(dict):
        def get(self, key, default=None):
            return {
                "patient_age": 72,
                "patient_sex": "Male",
                "patient_egfr": "45",
                "patient_pregnancy": False,
                "patient_comorbidities": "CKD stage 3",
            }.get(key, default)

    monkeypatch.setattr("ui.clinical_features.st.session_state", FakeState())
    block = build_patient_context_block()
    assert "72-year-old" in block
    assert "eGFR 45" in block
    composed = compose_clinical_query("Can we use metformin?")
    assert composed.startswith("Patient context:")
    assert "Can we use metformin?" in composed
