"""Disk-backed query result cache for clinic-scale repeat questions."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from src import config
from src.db.models import QueryCacheEntry
from src.db.session import get_session
from src.retriever import get_collection_count

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _corpus_fingerprint() -> str:
    counts = get_collection_count()
    return f"{counts.get('parent', 0)}:{counts.get('child', 0)}"


def _cache_key(
    tenant_id: str,
    query: str,
    messages: List[dict],
    latency_mode: str,
) -> str:
    normalized_query = " ".join(query.strip().lower().split())
    msg_tail = json.dumps(messages[-2:], sort_keys=True) if messages else "[]"
    raw = f"{tenant_id}|{latency_mode}|{_corpus_fingerprint()}|{normalized_query}|{msg_tail}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_result(
    tenant_id: str,
    query: str,
    messages: List[dict] | None = None,
    latency_mode: str | None = None,
) -> Optional[dict[str, Any]]:
    if not config.QUERY_CACHE_ENABLED:
        return None
    mode = (latency_mode or config.LATENCY_MODE).lower()
    key = _cache_key(tenant_id, query, messages or [], mode)
    now = _utcnow()
    try:
        with get_session() as session:
            row = session.query(QueryCacheEntry).filter_by(cache_key=key).first()
            if not row:
                return None
            if row.expires_at <= now:
                session.delete(row)
                return None
            payload = json.loads(row.payload_json)
            payload["cache_hit"] = True
            return payload
    except Exception as exc:  # noqa: BLE001
        logger.warning("Query cache read failed: %s", exc)
        return None


def set_cached_result(
    tenant_id: str,
    query: str,
    messages: List[dict] | None,
    latency_mode: str | None,
    result: dict[str, Any],
) -> None:
    if not config.QUERY_CACHE_ENABLED:
        return
    mode = (latency_mode or config.LATENCY_MODE).lower()
    key = _cache_key(tenant_id, query, messages or [], mode)
    expires = _utcnow() + timedelta(seconds=config.QUERY_CACHE_TTL_SECONDS)
    serializable = {k: v for k, v in result.items() if k != "cache_hit"}
    try:
        with get_session() as session:
            existing = session.query(QueryCacheEntry).filter_by(cache_key=key).first()
            payload = json.dumps(serializable)
            if existing:
                existing.payload_json = payload
                existing.expires_at = expires
            else:
                session.add(
                    QueryCacheEntry(
                        cache_key=key,
                        tenant_id=tenant_id,
                        payload_json=payload,
                        expires_at=expires,
                    )
                )
            _enforce_max_entries(session)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Query cache write failed: %s", exc)


def invalidate_tenant(tenant_id: str) -> int:
    """Clear cache when guidelines change."""
    try:
        with get_session() as session:
            deleted = (
                session.query(QueryCacheEntry)
                .filter(QueryCacheEntry.tenant_id == tenant_id)
                .delete()
            )
            return int(deleted or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Query cache invalidate failed: %s", exc)
        return 0


def _enforce_max_entries(session) -> None:
    max_entries = config.QUERY_CACHE_MAX_ENTRIES
    count = session.query(QueryCacheEntry).count()
    if count <= max_entries:
        return
    overflow = count - max_entries
    oldest = (
        session.query(QueryCacheEntry)
        .order_by(QueryCacheEntry.created_at.asc())
        .limit(overflow)
        .all()
    )
    for row in oldest:
        session.delete(row)
