"""Database connection management.

FUTURE EXPANSION: Connection Pooling and Session Management
------------------------------------------------------------
This module provides SQLAlchemy engine and session management for the persistence layer.
It is NOT currently used in the POC implementation, which operates statelessly against
the live Hacker News API without database persistence.

Architecture Pattern:
    - Thread-safe singleton engine creation with double-checked locking
    - Connection pooling with pre-ping for reliability
    - Context manager session factory for clean resource management

When This Activates:
    This module will be used when caching, historical tracking, or offline analysis
    features are implemented. The connection state management is ready to handle
    concurrent requests in a production environment.

Configuration:
    Requires DATABASE_URL environment variable (PostgreSQL connection string).
    Example: postgresql://user:pass@localhost:5432/community_pulse

Related Modules:
    - db/models.py: SQLAlchemy ORM models that will use these connections
    - data_sources/: Future repository implementations will call get_session()
"""

import os
import threading
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class _ConnectionState:
    """Module-level connection state container."""

    engine: Engine | None = None
    session_factory: sessionmaker[Session] | None = None


_state = _ConnectionState()
_lock = threading.Lock()


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


def get_engine() -> Engine:
    """Get or create SQLAlchemy engine."""
    if _state.engine is None:
        with _lock:
            if _state.engine is None:  # Double-check
                _state.engine = create_engine(get_database_url(), pool_pre_ping=True)
    assert _state.engine is not None  # noqa: S101 - Type narrowing after lock
    return _state.engine


def get_session() -> Generator[Session, None, None]:
    """Yield a database session."""
    if _state.session_factory is None:
        with _lock:
            if _state.session_factory is None:  # Double-check
                _state.session_factory = sessionmaker(
                    bind=get_engine(), expire_on_commit=False
                )
    assert _state.session_factory is not None  # noqa: S101 - Type narrowing
    session = _state.session_factory()
    try:
        yield session
    finally:
        session.close()
