"""Interaction + feedback logging for Sentinel-RAG.

==============================================================================
WHY LOG EVERY INTERACTION — THE PATH FROM v1 TO v2
==============================================================================
Sentinel-RAG's confidence today is a deterministic *heuristic* (reflection.py):
hand-weighted factors a human can read and audit. That is the right v1 choice —
it is transparent and needs no labelled data. But the ceiling on a heuristic is
the designer's intuition.

The v2 move is a *learned reward model*: a model trained to predict whether an
answer is actually trustworthy, from features of the interaction plus a human
quality label. To train that, you need data — (features, human_rating) pairs
collected from real use. This module is that collection layer.

Every agent run appends a row of features (confidence, validation verdict,
flag, retries, retrieved-doc count, latency, a response preview). When a user
rates a response (👍/👌/👎), we fill in the ``human_rating`` for that row. Over
time ``confidence_log.csv`` becomes a supervised dataset: inputs = the logged
features, target = human_rating. That is exactly the signal a reward model
learns from.

The logger is intentionally best-effort and crash-proof: logging must never
take down a clinical response. Every public function swallows its own errors.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from src import config

logger = logging.getLogger(__name__)

FEEDBACK_FILE = config.FEEDBACK_FILE

# Column order is the on-disk schema. Append-only; do not reorder existing
# columns (it would break previously written rows / downstream training code).
FEEDBACK_COLS: List[str] = [
    "timestamp",
    "conversation_id",
    "query",
    "response_preview",
    "confidence_score",
    "validation_verdict",
    "flagged",
    "retry_count",
    "retrieved_doc_count",
    "response_time_ms",
    "human_rating",  # "" until the user rates this interaction (1-5)
]

# Valid human rating scale (reward signal).
MIN_RATING = 1
MAX_RATING = 5


def _ensure_file() -> Path:
    """Ensure the feedback CSV (and its directory) exists with a header row."""
    path = Path(FEEDBACK_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=FEEDBACK_COLS).writeheader()
    return path


def log_interaction(agent_result: dict, response_time_ms: int) -> str:
    """Append one interaction's features to the confidence log.

    Args:
        agent_result: The dict returned by ``agent.run_agent`` (response,
            confidence, flagged, retry_count, conversation_id, validation_verdict,
            sources, query, ...).
        response_time_ms: Wall-clock time taken to produce the response.

    Returns:
        The ISO timestamp written for this row (the row's key), or "" on error.
        ``human_rating`` starts empty and is filled later via
        ``log_human_feedback``.
    """
    # Microsecond resolution so the timestamp is a robust unique row key even
    # for interactions logged within the same second.
    timestamp = datetime.now().isoformat(timespec="microseconds")

    try:
        response = str(agent_result.get("response", "") or "")
        preview = response.strip().replace("\n", " ")[:100]

        # retrieved_doc_count: prefer explicit sources, fall back to docs.
        sources = agent_result.get("sources")
        if isinstance(sources, list):
            doc_count = len(sources)
        else:
            doc_count = len(agent_result.get("retrieved_docs", []) or [])

        row = {
            "timestamp": timestamp,
            "conversation_id": agent_result.get("conversation_id", ""),
            "query": str(agent_result.get("query", "") or ""),
            "response_preview": preview,
            "confidence_score": round(float(agent_result.get("confidence", 0.0)), 4),
            "validation_verdict": agent_result.get("validation_verdict", ""),
            "flagged": bool(agent_result.get("flagged", False)),
            "retry_count": int(agent_result.get("retry_count", 0)),
            "retrieved_doc_count": doc_count,
            "response_time_ms": int(response_time_ms),
            "human_rating": "",  # filled by log_human_feedback
        }

        path = _ensure_file()
        with path.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=FEEDBACK_COLS).writerow(row)

        logger.info("Logged interaction %s (confidence=%.2f, %dms).",
                    timestamp, row["confidence_score"], response_time_ms)
        return timestamp

    except Exception as exc:  # noqa: BLE001 - logging must never break a response
        logger.error("Failed to log interaction: %s", exc)
        return ""


def _read_all_rows() -> List[dict]:
    """Read every logged row as a list of dicts (empty list if no file)."""
    path = Path(FEEDBACK_FILE)
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def log_human_feedback(timestamp: str, rating: int) -> bool:
    """Attach a human quality rating (1-5) to a previously logged interaction.

    This is the supervised target for the future reward model: it pairs the
    interaction's logged features with a human judgement of quality.

    Args:
        timestamp: The row key returned by ``log_interaction``.
        rating: Human rating on a 1-5 scale (clamped to range).

    Returns:
        True if a row was found and updated, else False.
    """
    try:
        rating = max(MIN_RATING, min(MAX_RATING, int(rating)))
    except (TypeError, ValueError):
        logger.error("Invalid rating %r — must be an int 1-5.", rating)
        return False

    try:
        rows = _read_all_rows()
        if not rows:
            logger.warning("No feedback log to update.")
            return False

        updated = False
        for row in rows:
            if row.get("timestamp") == timestamp:
                row["human_rating"] = rating
                updated = True
                break

        if not updated:
            logger.warning("No interaction found for timestamp=%s", timestamp)
            return False

        path = Path(FEEDBACK_FILE)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=FEEDBACK_COLS)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("Recorded human rating %d for interaction %s.", rating, timestamp)
        return True

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to record human feedback: %s", exc)
        return False


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_feedback_stats() -> dict:
    """Aggregate the confidence log into headline metrics for the UI.

    Returns a dict:
        total_interactions: int
        avg_confidence: float (0-1)
        flag_rate: float (0-1, fraction flagged for review)
        avg_human_rating: float (1-5, over RATED rows only; 0.0 if none)
        total_rated: int (rows with a human rating)
    """
    default = {
        "total_interactions": 0,
        "avg_confidence": 0.0,
        "flag_rate": 0.0,
        "avg_human_rating": 0.0,
        "total_rated": 0,
    }

    try:
        rows = _read_all_rows()
        total = len(rows)
        if total == 0:
            return default

        confidences = [_to_float(r.get("confidence_score")) for r in rows]
        flagged = sum(
            1 for r in rows
            if str(r.get("flagged", "")).strip().lower() in ("true", "1")
        )

        ratings = []
        for r in rows:
            raw = str(r.get("human_rating", "")).strip()
            if raw:
                ratings.append(_to_float(raw))

        return {
            "total_interactions": total,
            "avg_confidence": round(sum(confidences) / total, 4),
            "flag_rate": round(flagged / total, 4),
            "avg_human_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
            "total_rated": len(ratings),
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to compute feedback stats: %s", exc)
        return default
