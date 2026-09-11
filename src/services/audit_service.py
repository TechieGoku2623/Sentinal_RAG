"""Audit trail and interaction persistence (SQLite + legacy CSV)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from src import config
from src.db.models import AuditEvent, Interaction
from src.db.session import get_session
from src.feedback_logger import (
    get_feedback_stats,
    log_human_feedback as log_csv_feedback,
    log_interaction as log_csv_interaction,
)

logger = logging.getLogger(__name__)


def log_interaction(
    agent_result: dict,
    response_time_ms: int,
    tenant_id: str | None = None,
) -> str:
    """Log to CSV (reward model) and SQLite (audit platform)."""
    timestamp = log_csv_interaction(agent_result, response_time_ms)
    if not timestamp:
        timestamp = datetime.now().isoformat(timespec="microseconds")

    tenant = tenant_id or config.DEFAULT_TENANT_ID
    try:
        response = str(agent_result.get("response", "") or "")
        preview = response.strip().replace("\n", " ")[:512]
        sources = agent_result.get("sources")
        doc_count = len(sources) if isinstance(sources, list) else len(
            agent_result.get("retrieved_docs", []) or []
        )
        with get_session() as session:
            session.add(
                Interaction(
                    timestamp=timestamp,
                    tenant_id=tenant,
                    conversation_id=str(agent_result.get("conversation_id", "")),
                    query=str(agent_result.get("query", "") or ""),
                    response_preview=preview,
                    confidence_score=round(float(agent_result.get("confidence", 0.0)), 4),
                    validation_verdict=str(agent_result.get("validation_verdict", "")),
                    flagged=bool(agent_result.get("flagged", False)),
                    retry_count=int(agent_result.get("retry_count", 0)),
                    retrieved_doc_count=doc_count,
                    response_time_ms=int(response_time_ms),
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to persist interaction to database: %s", exc)

    return timestamp


def log_human_feedback(timestamp: str, rating: int) -> bool:
    """Update rating in CSV and database."""
    ok = log_csv_feedback(timestamp, rating)
    try:
        with get_session() as session:
            row = session.query(Interaction).filter_by(timestamp=timestamp).first()
            if row:
                row.human_rating = max(1, min(5, int(rating)))
                return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to update human rating in database: %s", exc)
    return ok


def log_audit_event(
    event_type: str,
    detail: str,
    actor: str = "system",
    tenant_id: str | None = None,
) -> None:
    try:
        with get_session() as session:
            session.add(
                AuditEvent(
                    tenant_id=tenant_id or config.DEFAULT_TENANT_ID,
                    event_type=event_type,
                    actor=actor,
                    detail=detail,
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to log audit event: %s", exc)


def get_platform_stats(tenant_id: str | None = None) -> dict:
    """Aggregate metrics from DB with CSV fallback for legacy rows."""
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    default = {
        "total_interactions": 0,
        "avg_confidence": 0.0,
        "flag_rate": 0.0,
        "avg_human_rating": 0.0,
        "total_rated": 0,
        "total_audit_events": 0,
        "total_documents": 0,
    }
    try:
        with get_session() as session:
            rows = (
                session.query(Interaction)
                .filter(Interaction.tenant_id == tenant)
                .all()
            )
            if not rows:
                return default

            confidences = [r.confidence_score for r in rows]
            flagged = sum(1 for r in rows if r.flagged)
            ratings = [r.human_rating for r in rows if r.human_rating]
            audit_count = (
                session.query(AuditEvent)
                .filter(AuditEvent.tenant_id == tenant)
                .count()
            )
            from src.db.models import DocumentRegistry

            doc_count = (
                session.query(DocumentRegistry)
                .filter(DocumentRegistry.tenant_id == tenant)
                .count()
            )
            total = len(rows)
            return {
                "total_interactions": total,
                "avg_confidence": round(sum(confidences) / total, 4),
                "flag_rate": round(flagged / total, 4),
                "avg_human_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
                "total_rated": len(ratings),
                "total_audit_events": audit_count,
                "total_documents": doc_count,
            }
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to compute platform stats: %s", exc)
        return default


def list_interactions(limit: int = 50, tenant_id: str | None = None) -> List[dict]:
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    try:
        with get_session() as session:
            rows = (
                session.query(Interaction)
                .filter(Interaction.tenant_id == tenant)
                .order_by(Interaction.id.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "timestamp": r.timestamp,
                    "query": r.query,
                    "confidence": r.confidence_score,
                    "flagged": r.flagged,
                    "retry_count": r.retry_count,
                    "validation_verdict": r.validation_verdict,
                    "response_time_ms": r.response_time_ms,
                    "human_rating": r.human_rating,
                }
                for r in rows
            ]
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list interactions: %s", exc)
        return []


def list_audit_events(limit: int = 50, tenant_id: str | None = None) -> List[dict]:
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    try:
        with get_session() as session:
            rows = (
                session.query(AuditEvent)
                .filter(AuditEvent.tenant_id == tenant)
                .order_by(AuditEvent.id.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "event_type": r.event_type,
                    "actor": r.actor,
                    "detail": r.detail,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list audit events: %s", exc)
        return []
