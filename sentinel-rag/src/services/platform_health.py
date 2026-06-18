"""Platform health checks for Streamlit ↔ API integration."""

from __future__ import annotations

import os
from typing import Any

import httpx


def api_base_url() -> str:
    return os.getenv("SENTINEL_API_URL", "http://localhost:8000").rstrip("/")


def check_api_health(timeout: float = 2.5) -> dict[str, Any]:
    """Ping FastAPI /health — best-effort, never raises."""
    url = f"{api_base_url()}/health"
    try:
        resp = httpx.get(url, timeout=timeout)
        if resp.status_code == 200:
            body = resp.json()
            return {"ok": True, "url": url, **body}
        return {"ok": False, "url": url, "status": resp.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": str(exc)}
