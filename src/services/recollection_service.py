"""Clinical recollection — spaced repetition and learning recall for trainees and experts."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from src import config
from src.db.models import RecollectionTopic, StudyAttempt
from src.db.session import get_session
from src.retriever import retrieve_with_metadata

logger = logging.getLogger(__name__)

EVAL_QUESTIONS_PATH = Path("data/eval/eval_questions.json")
MAX_INTERVAL_DAYS = 30
TRAINEE_HINT_PREFIX = (
    "**Learning focus:** Try to recall the guideline-backed answer before revealing. "
    "Note indications, contraindications, and monitoring steps.\n\n"
)
EXPERIENCED_HINT_PREFIX = (
    "**Quick recall:** State the protocol decision point from memory, then verify.\n\n"
)


def _utcnow() -> datetime:
    """Naive UTC timestamp (SQLite-compatible)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _topic_key(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    return normalized[:512]


def _infer_category(query: str) -> str:
    lower = query.lower()
    if any(k in lower for k in ("diabetes", "metformin", "hba1c", "insulin")):
        return "diabetes"
    if any(k in lower for k in ("hypertension", "blood pressure", "ace")):
        return "hypertension"
    if any(k in lower for k in ("contraind", "warning", "adverse")):
        return "safety"
    return "general"


def _load_seed_questions(limit: int = 20) -> List[dict]:
    if not EVAL_QUESTIONS_PATH.exists():
        return []
    try:
        items = json.loads(EVAL_QUESTIONS_PATH.read_text(encoding="utf-8"))
        return items[:limit]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load eval questions for recollection: %s", exc)
        return []


def record_from_validation(
    query: str,
    agent_result: dict,
    learner_level: str = "trainee",
    tenant_id: str | None = None,
) -> int | None:
    """Save or refresh a topic after a protocol validation run."""
    if not query or not query.strip():
        return None

    tenant = tenant_id or config.DEFAULT_TENANT_ID
    key = _topic_key(query)
    sources = agent_result.get("sources") or []
    guideline = ""
    if sources and isinstance(sources[0], dict):
        guideline = str(sources[0].get("source") or "")

    try:
        with get_session() as session:
            row = (
                session.query(RecollectionTopic)
                .filter_by(tenant_id=tenant, topic_key=key, learner_level=learner_level)
                .first()
            )
            now = _utcnow()
            confidence = float(agent_result.get("confidence", 0.0))
            flagged = bool(agent_result.get("flagged", False))

            if row:
                row.topic = query.strip()
                row.last_confidence = confidence
                row.flagged = flagged
                row.guideline_source = guideline or row.guideline_source
                row.updated_at = now
                if flagged and row.next_review_at > now:
                    row.next_review_at = now
                topic_id = row.id
            else:
                topic = RecollectionTopic(
                    tenant_id=tenant,
                    learner_level=learner_level,
                    topic_key=key,
                    topic=query.strip(),
                    category=_infer_category(query),
                    guideline_source=guideline,
                    last_confidence=confidence,
                    flagged=flagged,
                    next_review_at=now + timedelta(days=1),
                )
                session.add(topic)
                session.flush()
                topic_id = topic.id
            return topic_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to record recollection topic: %s", exc)
        return None


def record_study_attempt(
    topic_id: int,
    self_rating: int,
    recalled_correctly: bool,
    learner_level: str = "trainee",
    notes: str = "",
    tenant_id: str | None = None,
) -> bool:
    """Log a self-assessment and update spaced-repetition schedule."""
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    rating = max(1, min(5, int(self_rating)))

    try:
        with get_session() as session:
            topic = session.query(RecollectionTopic).filter_by(id=topic_id).first()
            if not topic:
                return False

            session.add(
                StudyAttempt(
                    topic_id=topic_id,
                    tenant_id=tenant,
                    learner_level=learner_level,
                    self_rating=rating,
                    recalled_correctly=recalled_correctly,
                    notes=notes or "",
                )
            )

            now = _utcnow()
            success = recalled_correctly or rating >= 4

            if success:
                topic.repetition_count += 1
                topic.lapse_count = 0
                if topic.repetition_count == 1:
                    topic.interval_days = 1
                elif topic.repetition_count == 2:
                    topic.interval_days = 3
                else:
                    topic.interval_days = min(
                        MAX_INTERVAL_DAYS,
                        max(1, int(topic.interval_days * topic.ease_factor)),
                    )
                topic.ease_factor = min(3.0, topic.ease_factor + 0.1)
                topic.mastery_score = min(1.0, topic.mastery_score + 0.15)
            else:
                topic.lapse_count += 1
                topic.repetition_count = 0
                topic.interval_days = 1
                topic.ease_factor = max(1.3, topic.ease_factor - 0.2)
                topic.mastery_score = max(0.0, topic.mastery_score - 0.1)
                topic.next_review_at = now

            topic.last_reviewed_at = now
            topic.updated_at = now
            topic.next_review_at = now + timedelta(days=topic.interval_days)
            return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to record study attempt: %s", exc)
        return False


def get_due_topics(
    learner_level: str = "trainee",
    limit: int = 10,
    tenant_id: str | None = None,
) -> List[dict]:
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    now = _utcnow()
    try:
        with get_session() as session:
            rows = (
                session.query(RecollectionTopic)
                .filter(
                    RecollectionTopic.tenant_id == tenant,
                    RecollectionTopic.learner_level == learner_level,
                    RecollectionTopic.next_review_at <= now,
                )
                .order_by(RecollectionTopic.flagged.desc(), RecollectionTopic.next_review_at)
                .limit(limit)
                .all()
            )
            return [_topic_to_dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load due topics: %s", exc)
        return []


def get_recent_topics(
    learner_level: str = "trainee",
    limit: int = 10,
    tenant_id: str | None = None,
) -> List[dict]:
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    try:
        with get_session() as session:
            rows = (
                session.query(RecollectionTopic)
                .filter_by(tenant_id=tenant, learner_level=learner_level)
                .order_by(RecollectionTopic.updated_at.desc())
                .limit(limit)
                .all()
            )
            return [_topic_to_dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load recent topics: %s", exc)
        return []


def get_study_queue(
    learner_level: str = "trainee",
    limit: int = 8,
    tenant_id: str | None = None,
) -> List[dict]:
    """Build a mixed queue: due reviews, flagged topics, then seed questions."""
    queue: List[dict] = []
    seen_keys: set[str] = set()

    for item in get_due_topics(learner_level, limit=limit, tenant_id=tenant_id):
        key = item["topic_key"]
        if key not in seen_keys:
            item["queue_reason"] = "due_for_review"
            queue.append(item)
            seen_keys.add(key)

    try:
        with get_session() as session:
            flagged = (
                session.query(RecollectionTopic)
                .filter_by(tenant_id=tenant_id or config.DEFAULT_TENANT_ID, learner_level=learner_level, flagged=True)
                .order_by(RecollectionTopic.updated_at.desc())
                .limit(limit)
                .all()
            )
            for row in flagged:
                if row.topic_key not in seen_keys and len(queue) < limit:
                    data = _topic_to_dict(row)
                    data["queue_reason"] = "flagged_validation"
                    queue.append(data)
                    seen_keys.add(row.topic_key)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load flagged topics: %s", exc)

    for seed in _load_seed_questions(limit):
        question = seed.get("question", "")
        key = _topic_key(question)
        if key in seen_keys or len(queue) >= limit:
            continue
        queue.append({
            "id": None,
            "topic": question,
            "topic_key": key,
            "category": seed.get("category", "general"),
            "guideline_source": seed.get("source", "Guidelines"),
            "mastery_score": 0.0,
            "flagged": False,
            "queue_reason": "curriculum_seed",
            "keywords": seed.get("expected_answer_keywords", []),
        })
        seen_keys.add(key)

    return queue[:limit]


def get_recollection_summary(
    learner_level: str = "trainee",
    tenant_id: str | None = None,
) -> dict:
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    now = _utcnow()
    default = {
        "learner_level": learner_level,
        "total_topics": 0,
        "due_today": 0,
        "flagged_topics": 0,
        "avg_mastery": 0.0,
        "study_sessions": 0,
        "brief": "Start by validating a protocol or running a study session to build your recollection map.",
        "weak_categories": [],
    }
    try:
        with get_session() as session:
            topics = (
                session.query(RecollectionTopic)
                .filter_by(tenant_id=tenant, learner_level=learner_level)
                .all()
            )
            attempts = (
                session.query(StudyAttempt)
                .filter_by(tenant_id=tenant, learner_level=learner_level)
                .count()
            )
            if not topics:
                default["study_sessions"] = attempts
                return default

            due = sum(1 for t in topics if _as_utc(t.next_review_at) <= now)
            flagged = sum(1 for t in topics if t.flagged)
            mastery = sum(t.mastery_score for t in topics) / len(topics)

            category_scores: dict[str, list[float]] = {}
            for t in topics:
                category_scores.setdefault(t.category, []).append(t.mastery_score)
            weak = sorted(
                category_scores.items(),
                key=lambda kv: sum(kv[1]) / len(kv[1]),
            )[:3]
            weak_labels = [name for name, _ in weak if name != "general"]

            brief = _build_brief(learner_level, len(topics), due, flagged, weak_labels)

            return {
                "learner_level": learner_level,
                "total_topics": len(topics),
                "due_today": due,
                "flagged_topics": flagged,
                "avg_mastery": round(mastery, 2),
                "study_sessions": attempts,
                "brief": brief,
                "weak_categories": weak_labels,
            }
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to build recollection summary: %s", exc)
        return default


def _build_brief(
    learner_level: str,
    total: int,
    due: int,
    flagged: int,
    weak_categories: List[str],
) -> str:
    role = "trainee" if learner_level == "trainee" else "experienced clinician"
    parts = [
        f"As a {role}, you have {total} protocol topic(s) in your recollection map."
    ]
    if due:
        parts.append(f"{due} topic(s) are due for review today.")
    if flagged:
        parts.append(f"{flagged} topic(s) were flagged during validation — prioritize those.")
    if weak_categories:
        parts.append(
            "Focus areas: " + ", ".join(weak_categories) + "."
        )
    if learner_level == "trainee":
        parts.append(
            "Use study mode to recall answers before revealing guideline-backed explanations."
        )
    else:
        parts.append(
            "Use quick recall to stress-test protocol decisions, then verify against sources."
        )
    return " ".join(parts)


def _topic_to_dict(row: RecollectionTopic) -> dict:
    return {
        "id": row.id,
        "topic": row.topic,
        "topic_key": row.topic_key,
        "category": row.category,
        "guideline_source": row.guideline_source,
        "mastery_score": round(row.mastery_score, 2),
        "interval_days": row.interval_days,
        "repetition_count": row.repetition_count,
        "next_review_at": row.next_review_at.isoformat() if row.next_review_at else "",
        "last_confidence": row.last_confidence,
        "flagged": row.flagged,
    }


def get_guideline_snippet_for_topic(topic: str, max_chars: int = 600) -> str:
    """Retrieve a short guideline excerpt to support recollection review."""
    records = retrieve_with_metadata(topic)
    if not records:
        return "No indexed guideline passage found for this topic. Ingest guidelines or external evidence first."
    text = records[0].get("text", "")
    meta = records[0].get("metadata") or {}
    source = meta.get("source", "Guideline")
    snippet = text.strip().replace("\n", " ")[:max_chars]
    return f"**Source:** {source}\n\n{snippet}{'…' if len(text) > max_chars else ''}"


def format_study_prompt(topic: str, learner_level: str) -> str:
    prefix = TRAINEE_HINT_PREFIX if learner_level == "trainee" else EXPERIENCED_HINT_PREFIX
    return prefix + f"**Question:** {topic}"


def ensure_topic(
    topic: str,
    learner_level: str = "trainee",
    category: str = "general",
    guideline_source: str = "",
    tenant_id: str | None = None,
) -> int | None:
    """Create a recollection topic if it does not exist (e.g. curriculum seed)."""
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    key = _topic_key(topic)
    try:
        with get_session() as session:
            row = (
                session.query(RecollectionTopic)
                .filter_by(tenant_id=tenant, topic_key=key, learner_level=learner_level)
                .first()
            )
            if row:
                return row.id
            topic_row = RecollectionTopic(
                tenant_id=tenant,
                learner_level=learner_level,
                topic_key=key,
                topic=topic.strip(),
                category=category,
                guideline_source=guideline_source,
                next_review_at=_utcnow() + timedelta(days=1),
            )
            session.add(topic_row)
            session.flush()
            return topic_row.id
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to ensure recollection topic: %s", exc)
        return None
