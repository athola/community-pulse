"""Database connection management."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class _ConnectionState:
    """Module-level connection state container."""

    engine: Engine | None = None
    session_factory: sessionmaker[Session] | None = None


_state = _ConnectionState()


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


def get_engine() -> Engine:
    """Get or create SQLAlchemy engine."""
    if _state.engine is None:
        _state.engine = create_engine(get_database_url(), pool_pre_ping=True)
    return _state.engine


def get_session() -> Generator[Session, None, None]:
    """Yield a database session."""
    if _state.session_factory is None:
        _state.session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    session = _state.session_factory()
    try:
        yield session
    finally:
        session.close()
