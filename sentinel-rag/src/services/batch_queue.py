"""Async batch query queue for clinic-wide daily volume."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, List

from src import config
from src.db.models import BatchQueryJob
from src.db.session import get_session
from src.services.query_service import QuotaExceededError, execute_query

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None
_worker_lock = threading.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def start_batch_worker() -> None:
    global _executor
    with _worker_lock:
        if _executor is not None:
            return
        _executor = ThreadPoolExecutor(
            max_workers=config.BATCH_WORKER_THREADS,
            thread_name_prefix="sentinel-batch",
        )
        logger.info("Batch query worker started (%d threads).", config.BATCH_WORKER_THREADS)


def stop_batch_worker() -> None:
    global _executor
    with _worker_lock:
        if _executor:
            _executor.shutdown(wait=False, cancel_futures=True)
            _executor = None


def create_batch_job(
    queries: List[str],
    tenant_id: str,
    latency_mode: str = "fast",
) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    cleaned = [q.strip() for q in queries if q and q.strip()]
    if not cleaned:
        raise ValueError("At least one non-empty query is required.")
    with get_session() as session:
        session.add(
            BatchQueryJob(
                job_id=job_id,
                tenant_id=tenant_id,
                status="queued",
                latency_mode=latency_mode,
                total=len(cleaned),
                completed=0,
                results_json="[]",
            )
        )
    _enqueue_job(job_id, cleaned, tenant_id, latency_mode)
    return get_job(job_id)


def get_job(job_id: str) -> dict[str, Any]:
    with get_session() as session:
        row = session.query(BatchQueryJob).filter_by(job_id=job_id).first()
        if not row:
            raise KeyError(job_id)
        return _serialize_job(row)


def _serialize_job(row: BatchQueryJob) -> dict[str, Any]:
    return {
        "job_id": row.job_id,
        "tenant_id": row.tenant_id,
        "status": row.status,
        "latency_mode": row.latency_mode,
        "total": row.total,
        "completed": row.completed,
        "results": json.loads(row.results_json or "[]"),
        "error": row.error or "",
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _enqueue_job(
    job_id: str,
    queries: List[str],
    tenant_id: str,
    latency_mode: str,
) -> None:
    start_batch_worker()
    assert _executor is not None
    _executor.submit(_run_batch_job, job_id, queries, tenant_id, latency_mode)


def _run_batch_job(
    job_id: str,
    queries: List[str],
    tenant_id: str,
    latency_mode: str,
) -> None:
    _update_job(job_id, status="running")
    results: List[dict] = []
    try:
        for idx, query in enumerate(queries):
            try:
                result = execute_query(
                    query,
                    [],
                    tenant_id=tenant_id,
                    latency_mode=latency_mode,
                    use_cache=True,
                )
                results.append({"query": query, "ok": True, "result": _slim_result(result)})
            except QuotaExceededError as exc:
                results.append({"query": query, "ok": False, "error": str(exc)})
                _update_job(
                    job_id,
                    status="failed",
                    completed=idx + 1,
                    results_json=json.dumps(results),
                    error=str(exc),
                )
                return
            except Exception as exc:  # noqa: BLE001
                results.append({"query": query, "ok": False, "error": str(exc)})
            _update_job(
                job_id,
                completed=idx + 1,
                results_json=json.dumps(results),
            )
            if idx + 1 < len(queries):
                time.sleep(config.BATCH_INTER_QUERY_DELAY_SECONDS)
        _update_job(job_id, status="completed", results_json=json.dumps(results))
    except Exception as exc:  # noqa: BLE001
        logger.error("Batch job %s failed: %s", job_id, exc)
        _update_job(job_id, status="failed", error=str(exc), results_json=json.dumps(results))


def _slim_result(result: dict) -> dict:
    from src.text_utils import extract_clinical_answer

    return {
        "response": extract_clinical_answer(result.get("response", ""), result.get("messages")),
        "confidence": result.get("confidence"),
        "flagged": result.get("flagged"),
        "validation_verdict": result.get("validation_verdict"),
        "flag_reason": result.get("flag_reason", ""),
        "response_time_ms": result.get("response_time_ms"),
        "cache_hit": result.get("cache_hit", False),
        "latency_mode": result.get("latency_mode"),
    }


def _update_job(job_id: str, **fields) -> None:
    with get_session() as session:
        row = session.query(BatchQueryJob).filter_by(job_id=job_id).first()
        if not row:
            return
        for key, value in fields.items():
            setattr(row, key, value)
        row.updated_at = _utcnow()
