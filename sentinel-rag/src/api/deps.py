"""FastAPI dependency injection helpers."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status

from src import config


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    """Optional API-key gate. Disabled when SENTINEL_API_KEY is unset."""
    expected = os.getenv("SENTINEL_API_KEY", config.API_KEY)
    if not expected:
        return "dev"
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )
    return x_api_key
