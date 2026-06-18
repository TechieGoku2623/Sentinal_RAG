"""Smoke test for fullstack platform health."""

from __future__ import annotations

from src.services.platform_health import api_base_url, check_api_health
from src.text_utils import extract_clinical_answer


def test_extract_clinical_answer_importable_from_app_path() -> None:
    assert extract_clinical_answer("Hello\n---\nConfidence: 90%", None) == "Hello"


def test_api_health_offline_graceful() -> None:
    result = check_api_health()
    assert "ok" in result
    assert "url" in result


def test_api_base_url_default() -> None:
    assert api_base_url().endswith("8000") or "localhost" in api_base_url()
