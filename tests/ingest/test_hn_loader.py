"""Tests for HN data loader."""

from community_pulse.ingest.hn_loader import parse_hn_item
from community_pulse.ingest.topic_extractor import extract_keywords, extract_topics


def test_parse_hn_story() -> None:
    """Test parsing a HN story."""
    data = {
        "id": 12345,
        "type": "story",
        "by": "testuser",
        "time": 1704067200,  # 2024-01-01 00:00:00 UTC
        "title": "Show HN: My AI Project",
        "url": "https://example.com",
        "score": 100,
        "kids": [1, 2, 3],
    }
    item = parse_hn_item(data)

    assert item is not None
    assert item.id == 12345
    assert item.type == "story"
    assert item.by == "testuser"
    assert item.title == "Show HN: My AI Project"
    assert item.score == 100


def test_parse_hn_comment() -> None:
    """Test parsing a HN comment."""
    data = {
        "id": 67890,
        "type": "comment",
        "by": "commenter",
        "time": 1704067200,
        "text": "Great project! I love the AI features.",
        "parent": 12345,
    }
    item = parse_hn_item(data)

    assert item is not None
    assert item.type == "comment"
    assert item.parent == 12345
    assert "AI features" in (item.text or "")


def test_parse_deleted_item() -> None:
    """Test that deleted items return None."""
    data = {"id": 11111, "deleted": True}
    assert parse_hn_item(data) is None


def test_extract_topics_ai() -> None:
    """Test extracting AI topic."""
    topics = extract_topics("Check out my new machine learning model", "AI Project")
    slugs = [t[0] for t in topics]
    assert "ai" in slugs


def test_extract_topics_multiple() -> None:
    """Test extracting multiple topics."""
    topics = extract_topics(
        "Built with Python and PostgreSQL on AWS", "My FastAPI Project"
    )
    slugs = [t[0] for t in topics]
    assert "python" in slugs
    assert "database" in slugs
    assert "cloud" in slugs


def test_extract_keywords() -> None:
    """Test keyword extraction."""
    text = (
        "Python is great for machine learning. "
        "Python also works well with databases."
    )
    keywords = extract_keywords(text, top_n=3)
    assert "python" in keywords
