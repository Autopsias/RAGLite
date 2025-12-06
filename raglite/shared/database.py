"""SQLAlchemy database configuration.

Story 6.2: PostgreSQL External Data Schema & Storage

Provides Base class and session factory for ORM operations.
Follows singleton pattern from clients.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from raglite.shared.config import settings


def utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware).

    Replaces deprecated datetime.utcnow() for Python 3.12+ compatibility.
    """
    return datetime.now(UTC)


if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

Base = declarative_base()

# Module-level singletons
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Get SQLAlchemy engine (singleton).

    Returns:
        SQLAlchemy Engine instance configured for PostgreSQL.
    """
    global _engine
    if _engine is None:
        url = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_session() -> Session:
    """Get SQLAlchemy session.

    Returns:
        New SQLAlchemy Session instance.
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def reset_engine() -> None:
    """Reset engine and session factory (for testing).

    This allows tests to reinitialize the engine with different settings.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
