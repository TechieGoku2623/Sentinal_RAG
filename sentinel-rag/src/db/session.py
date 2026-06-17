"""Database engine and session factory."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src import config
from src.db.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def _database_url() -> str:
    return os.getenv("DATABASE_URL", config.DATABASE_URL)


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = _database_url()
        connect_args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def init_db() -> None:
    """Create tables if they do not exist."""
    engine = get_engine()
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", _database_url())


@contextmanager
def get_session() -> Iterator[Session]:
    if _SessionLocal is None:
        get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
