"""Database connection management using factory pattern.

Provides SQLAlchemy engine and session management for the persistence layer.
Currently NOT used in POC (operates statelessly against live HN API).

Architecture Pattern:
    On-demand factory pattern with lazy initialization. Each call to
    SessionFactory.create() returns an independent session factory configured
    for the current environment.

When This Activates:
    When caching, historical tracking, or offline analysis features are
    implemented. See GitHub issue for database integration roadmap.

Configuration:
    Requires DATABASE_URL environment variable (PostgreSQL connection string).
    Example: postgresql://user:pass@localhost:5432/community_pulse

Related Modules:
    - db/models.py: SQLAlchemy ORM models
    - data_sources/: Future repository implementations
"""

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


class SessionFactory:
    """Factory for creating database session factories.

    Uses on-demand creation pattern - each call creates a fresh session factory
    configured with the current DATABASE_URL. This avoids global state while
    still supporting connection pooling at the engine level.

    Usage:
        factory = SessionFactory.create()
        with factory() as session:
            # use session
    """

    _engine: Engine | None = None

    @classmethod
    def get_engine(cls) -> Engine:
        """Get or create shared engine (pooling happens at engine level)."""
        if cls._engine is None:
            cls._engine = create_engine(get_database_url(), pool_pre_ping=True)
        return cls._engine

    @classmethod
    def create(cls) -> sessionmaker[Session]:
        """Create a new session factory bound to the shared engine."""
        return sessionmaker(bind=cls.get_engine(), expire_on_commit=False)

    @classmethod
    def reset(cls) -> None:
        """Reset engine (useful for testing or reconfiguration)."""
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Usage:
        with get_session() as session:
            # use session
    """
    factory = SessionFactory.create()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
