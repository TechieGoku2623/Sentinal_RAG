"""Clinical query orchestration for API and UI."""

from __future__ import annotations

import time
from typing import List

from src import config
from src.agent import run_agent
from src.services.query_cache import get_cached_result, set_cached_result
from src.services.workspace_service import (
    check_query_quota,
    increment_query_usage,
)


class QuotaExceededError(Exception):
    """Raised when a workspace exceeds its monthly query allowance."""


def execute_query(
    query: str,
    messages: List[dict] | None = None,
    tenant_id: str | None = None,
    latency_mode: str | None = None,
    use_cache: bool = True,
) -> dict:
    """Run the LangGraph agent with caching, metering, and latency modes."""
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    mode = (latency_mode or config.LATENCY_MODE).lower()
    ok, msg = check_query_quota(tenant)
    if not ok:
        raise QuotaExceededError(msg)

    if use_cache:
        cached = get_cached_result(tenant, query, messages, mode)
        if cached:
            cached["response_time_ms"] = 1
            increment_query_usage(tenant)
            return cached

    result = run_agent(query, messages or [], tenant_id=tenant, latency_mode=mode)
    increment_query_usage(tenant)

    if use_cache and not result.get("flagged"):
        set_cached_result(tenant, query, messages, mode, result)

    return result
