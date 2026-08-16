from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from oculis_api.core.config import settings

_engine = None
_session_factory = None


def SessionLocal() -> Session:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        _session_factory = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False
        )
    return _session_factory()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
