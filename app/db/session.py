from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _get_engine():
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# Lazy-initialized engine — created on first use
_engine = None
_SessionLocal = None


def _ensure_session_factory():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    SessionLocal = _ensure_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_session_factory():
    """Reset the session factory (used in tests)."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
