"""Clinical query orchestration for API and UI."""

from __future__ import annotations

from typing import List

from src import config
from src.agent import run_agent
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
) -> dict:
    """Run the LangGraph agent with tenant-scoped audit logging and usage metering."""
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    ok, msg = check_query_quota(tenant)
    if not ok:
        raise QuotaExceededError(msg)

    result = run_agent(query, messages or [], tenant_id=tenant)
    increment_query_usage(tenant)
    return result
