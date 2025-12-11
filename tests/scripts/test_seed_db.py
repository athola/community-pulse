"""Tests for database seeding script."""

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the functions we'll test
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
# ruff: noqa: E402
from seed_db import (  # type: ignore[import-not-found]
    get_or_create_author,
    get_or_create_topic,
    seed_database,
)

from community_pulse.db.models import Author, Base, Post, Topic


@pytest.fixture
def in_memory_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(in_memory_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    yield session
    session.close()


def test_get_or_create_author_new(test_session) -> None:
    """Test creating a new author."""
    author = get_or_create_author(test_session, "user123", "testuser")

    assert author.external_id == "user123"
    assert author.handle == "testuser"
    assert author.id is not None


def test_get_or_create_author_existing(test_session) -> None:
    """Test retrieving an existing author."""
    # Create first author
    author1 = get_or_create_author(test_session, "user123", "testuser")
    test_session.flush()
    author1_id = author1.id

    # Try to create same author again
    author2 = get_or_create_author(test_session, "user123", "testuser")

    assert author2.id == author1_id
    assert test_session.query(Author).count() == 1


def test_get_or_create_topic_new(test_session) -> None:
    """Test creating a new topic."""
    topic = get_or_create_topic(test_session, "machine-learning")

    assert topic.slug == "machine-learning"
    assert topic.label == "Machine Learning"
    assert topic.id is not None


def test_get_or_create_topic_existing(test_session) -> None:
    """Test retrieving an existing topic."""
    # Create first topic
    topic1 = get_or_create_topic(test_session, "python")
    test_session.flush()
    topic1_id = topic1.id

    # Try to create same topic again
    topic2 = get_or_create_topic(test_session, "python")

    assert topic2.id == topic1_id
    assert test_session.query(Topic).count() == 1


def test_seed_database_with_sample_data(tmp_path, monkeypatch) -> None:
    """Test seeding database with sample HN data."""
    # Create sample data file
    sample_data = [
        {
            "id": 12345,
            "type": "story",
            "by": "testuser",
            "time": 1704067200,  # 2024-01-01 00:00:00 UTC
            "title": "Show HN: My AI Project",
            "url": "https://example.com",
            "score": 100,
            "kids": [],
        },
        {
            "id": 12346,
            "type": "comment",
            "by": "commenter",
            "time": 1704070800,  # 2024-01-01 01:00:00 UTC
            "text": "Great project! I love Python and AI.",
            "parent": 12345,
            "score": 10,
        },
    ]

    data_file = tmp_path / "test_data.json"
    with open(data_file, "w") as f:
        json.dump(sample_data, f)

    # Create temporary database URL
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    # Set environment variable
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Seed the database
    seed_database(data_file)

    # Verify data was inserted
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        posts = session.query(Post).all()
        assert len(posts) == 2

        # Check story
        story = session.query(Post).filter_by(external_id="12345").first()
        assert story is not None
        assert story.title == "Show HN: My AI Project"
        assert story.author is not None
        assert story.author.handle == "testuser"

        # Check comment
        comment = session.query(Post).filter_by(external_id="12346").first()
        assert comment is not None
        assert comment.content == "Great project! I love Python and AI."
        assert comment.parent_id == story.id

        # Check topics were extracted
        topics = session.query(Topic).all()
        assert len(topics) >= 1  # At least AI should be extracted

        # Check authors
        authors = session.query(Author).all()
        assert len(authors) == 2
    finally:
        session.close()


def test_seed_database_missing_env_var(tmp_path, monkeypatch) -> None:
    """Test that seed_database raises error when DATABASE_URL is not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    data_file = tmp_path / "test_data.json"
    data_file.write_text("[]")

    with pytest.raises(ValueError, match="DATABASE_URL not set"):
        seed_database(data_file)


def test_seed_database_handles_duplicate_posts(tmp_path, monkeypatch) -> None:
    """Test that running seed_database twice doesn't create duplicates."""
    # Create sample data
    sample_data = [
        {
            "id": 12345,
            "type": "story",
            "by": "testuser",
            "time": 1704067200,
            "title": "Test Story",
            "score": 50,
        }
    ]

    data_file = tmp_path / "test_data.json"
    with open(data_file, "w") as f:
        json.dump(sample_data, f)

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Seed twice
    seed_database(data_file)
    seed_database(data_file)

    # Verify only one post exists
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        post_count = session.query(Post).count()
        assert post_count == 1
    finally:
        session.close()
