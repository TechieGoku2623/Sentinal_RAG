"""In-memory LRU cache for Chroma retrieval results."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from threading import Lock
from typing import List

from src import config

_lock = Lock()
_cache: OrderedDict[str, list] = OrderedDict()


def _key(query: str, expanded: bool) -> str:
    normalized = " ".join(query.strip().lower().split())
    return hashlib.sha256(f"{normalized}|{expanded}".encode()).hexdigest()


def get_retrieval(query: str, expanded: bool = False) -> list | None:
    if not config.RETRIEVAL_CACHE_ENABLED:
        return None
    key = _key(query, expanded)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return list(_cache[key])
    return None


def set_retrieval(query: str, expanded: bool, records: List[dict]) -> None:
    if not config.RETRIEVAL_CACHE_ENABLED:
        return
    key = _key(query, expanded)
    with _lock:
        _cache[key] = list(records)
        _cache.move_to_end(key)
        while len(_cache) > config.RETRIEVAL_CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)


def clear_retrieval_cache() -> None:
    with _lock:
        _cache.clear()
