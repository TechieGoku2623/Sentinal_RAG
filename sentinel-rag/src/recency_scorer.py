"""Temporal recency scoring for Sentinel-RAG.

==============================================================================
WHY RECENCY MATTERS IN CLINICAL AI
==============================================================================
A retrieved guideline can be perfectly *relevant* and perfectly *grounded* and
still be *dangerous* — because medicine moves. First-line therapies, dosing,
contraindications, and screening intervals are revised as new evidence lands.
An answer faithfully grounded in a 2012 guideline may directly contradict the
2024 standard of care.

Relevance scoring (embeddings) and grounding scoring (reflection.py) both treat
the corpus as timeless. This module adds the missing temporal axis: it converts
a source's publication year into a recency score and lets the agent (a) lower
its confidence and (b) surface an explicit "verify against current guidelines"
warning when the evidence behind an answer is aging or outdated.

This is intentionally a deterministic, auditable heuristic (no LLM): a clinical
reviewer can read the bands below and reason about exactly when and why the
system de-rates a source.
"""

from __future__ import annotations

import datetime
from typing import Iterable, Optional

from src import config

# Reference "now" for age calculations. Pinned (via config) to keep scoring and
# tests deterministic; bump config.CURRENT_YEAR when rolling the project year.
CURRENT_YEAR = config.CURRENT_YEAR

# A source older than this many years triggers the outdated warning and the
# confidence penalty in the agent.
OUTDATED_THRESHOLD_YEARS = config.AGING_YEARS


def calculate_recency_score(publication_year: int) -> float:
    """Map a publication year to a recency score in [0.20, 1.00].

    Bands (years since CURRENT_YEAR):
        <= 1  -> 1.00  Very recent  (current standard of care)
        <= 3  -> 0.85  Recent
        <= 5  -> 0.65  Acceptable   (verify, but generally usable)
        <= 10 -> 0.40  Aging        (likely superseded in places)
        > 10  -> 0.20  Outdated     (treat with strong caution)

    A missing/invalid year is treated as outdated (0.20) — we never reward an
    unknown vintage, because we cannot vouch for its currency.
    """
    if not publication_year or publication_year <= 0:
        return 0.20

    years_old = CURRENT_YEAR - publication_year

    # A future-dated source (data entry error) is treated as "very recent"
    # rather than penalized.
    if years_old < 0:
        return 1.0

    if years_old <= 1:
        return 1.0   # Very recent
    if years_old <= 3:
        return 0.85  # Recent
    if years_old <= 5:
        return 0.65  # Acceptable
    if years_old <= 10:
        return 0.40  # Aging
    return 0.20      # Outdated


def _years_from_metadata(retrieved_docs_metadata: Iterable[dict]) -> list:
    """Extract valid integer publication years from a list of metadata dicts."""
    years = []
    for md in retrieved_docs_metadata or []:
        year = (md or {}).get("publication_year")
        try:
            year = int(year)
        except (TypeError, ValueError):
            continue
        if year > 0:
            years.append(year)
    return years


def get_oldest_source_year(retrieved_docs_metadata: Iterable[dict]) -> Optional[int]:
    """Return the oldest publication year among retrieved sources.

    Returns None if no source carries a usable publication year.
    """
    years = _years_from_metadata(retrieved_docs_metadata)
    return min(years) if years else None


def should_warn_outdated(retrieved_docs_metadata: Iterable[dict]) -> bool:
    """True if ANY retrieved source is older than OUTDATED_THRESHOLD_YEARS.

    A single stale source is enough to warrant a warning: the clinician should
    know that part of the answer may rest on superseded evidence.
    """
    oldest = get_oldest_source_year(retrieved_docs_metadata)
    if oldest is None:
        return False
    return (CURRENT_YEAR - oldest) > OUTDATED_THRESHOLD_YEARS


def recency_label(publication_year: int) -> tuple:
    """Return a (icon, label) pair for displaying a source's currency.

    Examples (with CURRENT_YEAR = 2025):
        2023 -> ("✅", "Current")
        2018 -> ("⚠️", "Aging")
        2015 -> ("🔴", "Outdated")
    """
    if not publication_year or publication_year <= 0:
        return ("🔴", "Unknown date")

    years_old = CURRENT_YEAR - publication_year
    if years_old <= 3:
        return ("✅", "Current")
    if years_old <= 9:
        return ("⚠️", "Aging")
    return ("🔴", "Outdated")


def is_recent(publication_year: int, within_years: int = config.RECENT_YEARS) -> bool:
    """True if the source was published within ``within_years`` of CURRENT_YEAR."""
    if not publication_year or publication_year <= 0:
        return False
    return (CURRENT_YEAR - publication_year) <= within_years


def current_year() -> int:
    """Return today's calendar year (helper for callers that want live dates)."""
    return datetime.date.today().year
