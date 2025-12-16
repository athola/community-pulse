"""Tests for database models."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from community_pulse.db.models import Author, Base, Post, PostTopic, Topic


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a test session."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


def test_author_creation(session: Session) -> None:
    """Test creating an author."""
    author = Author(external_id="user123", handle="testuser")
    session.add(author)
    session.commit()

    assert author.id is not None
    assert author.external_id == "user123"
    assert author.handle == "testuser"


def test_topic_creation(session: Session) -> None:
    """Test creating a topic."""
    topic = Topic(slug="machine-learning", label="Machine Learning")
    session.add(topic)
    session.commit()

    assert topic.id is not None
    assert topic.slug == "machine-learning"


def test_post_with_author(session: Session) -> None:
    """Test creating a post with an author."""
    author = Author(external_id="user456", handle="poster")
    session.add(author)
    session.flush()

    post = Post(
        external_id="post123",
        author_id=author.id,
        title="Test Post",
        posted_at=datetime.now(timezone.utc),
    )
    session.add(post)
    session.commit()

    assert post.author == author
    assert author.posts == [post]


def test_post_topic_association(session: Session) -> None:
    """Test associating posts with topics."""
    topic = Topic(slug="ai", label="AI")
    post = Post(external_id="post789", posted_at=datetime.now(timezone.utc))
    session.add_all([topic, post])
    session.flush()

    post_topic = PostTopic(post_id=post.id, topic_id=topic.id, relevance=0.95)
    session.add(post_topic)
    session.commit()

    assert len(post.post_topics) == 1
    assert post.post_topics[0].topic == topic
    assert post.post_topics[0].relevance == 0.95
