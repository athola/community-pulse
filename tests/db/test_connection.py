"""Tests for database connection management."""

import pytest

from community_pulse.db.connection import get_database_url


def test_get_database_url_missing_env_var(monkeypatch):
    """Test that get_database_url raises ValueError when DATABASE_URL is not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    expected_message = "DATABASE_URL environment variable is required"
    with pytest.raises(ValueError, match=expected_message):
        get_database_url()


def test_get_database_url_returns_value(monkeypatch):
    """Test that get_database_url returns the DATABASE_URL when set."""
    expected_url = "postgresql://user:pass@localhost:5432/testdb"
    monkeypatch.setenv("DATABASE_URL", expected_url)

    result = get_database_url()

    assert result == expected_url
