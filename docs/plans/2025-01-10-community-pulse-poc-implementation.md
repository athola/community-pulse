# Community Pulse POC Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working POC that ingests Hacker News data, computes pulse scores using velocity and co-occurrence analysis, and displays results in a React Native Web frontend.

**Architecture:** FastAPI backend with PostgreSQL (Supabase) for storage, rustworkx for graph analysis, and React Native Web frontend with force-graph visualization. Data flows: HN corpus → parser → DB → materialized views → pulse computation → GraphQL/REST → frontend.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, rustworkx, Pydantic v2, React Native Web, Expo Router, react-force-graph-2d, recharts, TanStack Query.

---

## Phase 1: Backend Foundation

### Task 1: Database Models

**Files:**
- Create: `src/community_pulse/db/__init__.py`
- Create: `src/community_pulse/db/connection.py`
- Create: `src/community_pulse/db/models.py`
- Test: `tests/db/test_models.py`

**Step 1: Create db package init**

```python
# src/community_pulse/db/__init__.py
"""Database package for Community Pulse."""

from community_pulse.db.connection import get_engine, get_session
from community_pulse.db.models import Author, Post, Topic, PostTopic

__all__ = ["get_engine", "get_session", "Author", "Post", "Topic", "PostTopic"]
```

**Step 2: Create connection module**

```python
# src/community_pulse/db/connection.py
"""Database connection management."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


def get_engine() -> Engine:
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
    return _engine


def get_session() -> Generator[Session, None, None]:
    """Yield a database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

**Step 3: Create models module**

```python
# src/community_pulse/db/models.py
"""SQLAlchemy models for Community Pulse."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {dict[str, Any]: JSONB}


class Author(Base):
    """Author of posts in the community."""

    __tablename__ = "authors"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author")


class Topic(Base):
    """Extracted topic/theme from posts."""

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    post_topics: Mapped[list["PostTopic"]] = relationship(
        "PostTopic", back_populates="topic"
    )


class Post(Base):
    """Content item (story, comment) from the community."""

    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    author_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("authors.id"), nullable=True
    )
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("posts.id"), nullable=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    author: Mapped[Author | None] = relationship("Author", back_populates="posts")
    parent: Mapped["Post | None"] = relationship("Post", remote_side=[id])
    post_topics: Mapped[list["PostTopic"]] = relationship(
        "PostTopic", back_populates="post"
    )

    __table_args__ = (
        Index("idx_posts_posted_at", "posted_at"),
        Index("idx_posts_author_time", "author_id", "posted_at"),
    )


class PostTopic(Base):
    """Association between posts and topics."""

    __tablename__ = "post_topics"

    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    relevance: Mapped[float] = mapped_column(Float, default=1.0)

    post: Mapped[Post] = relationship("Post", back_populates="post_topics")
    topic: Mapped[Topic] = relationship("Topic", back_populates="post_topics")

    __table_args__ = (Index("idx_post_topics_topic", "topic_id"),)
```

**Step 4: Write model tests**

```python
# tests/db/__init__.py
"""Database tests package."""
```

```python
# tests/db/test_models.py
"""Tests for database models."""

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
    from datetime import datetime, timezone

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
    from datetime import datetime, timezone

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
```

**Step 5: Run tests**

Run: `uv run pytest tests/db/test_models.py -v`
Expected: All 4 tests PASS

**Step 6: Commit**

```bash
git add src/community_pulse/db/ tests/db/
git commit -m "feat(db): add SQLAlchemy models for authors, posts, topics"
```

---

### Task 2: Pydantic Schemas

**Files:**
- Create: `src/community_pulse/models/__init__.py`
- Create: `src/community_pulse/models/pulse.py`
- Test: `tests/models/test_pulse.py`

**Step 1: Create models package init**

```python
# src/community_pulse/models/__init__.py
"""Pydantic models for API schemas."""

from community_pulse.models.pulse import (
    GraphResponse,
    PulseResponse,
    TopicEdge,
    TopicHistory,
    TopicNode,
)

__all__ = [
    "GraphResponse",
    "PulseResponse",
    "TopicEdge",
    "TopicHistory",
    "TopicNode",
]
```

**Step 2: Create pulse schemas**

```python
# src/community_pulse/models/pulse.py
"""Pydantic models for pulse API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class TopicNode(BaseModel):
    """A topic node in the pulse graph."""

    id: str
    slug: str
    label: str
    pulse_score: float = Field(ge=0, le=1)
    velocity: float = Field(default=1.0)
    centrality: float = Field(default=0.0, ge=0, le=1)
    mention_count: int = Field(default=0, ge=0)
    unique_authors: int = Field(default=0, ge=0)


class TopicEdge(BaseModel):
    """An edge between topics (co-occurrence)."""

    source: str
    target: str
    weight: float = Field(ge=0)
    shared_posts: int = Field(default=0, ge=0)


class TopicHistory(BaseModel):
    """Historical pulse data for a topic."""

    topic_id: str
    timestamp: datetime
    pulse_score: float
    velocity: float
    mention_count: int


class ClusterInfo(BaseModel):
    """Information about a topic cluster."""

    id: str
    topic_ids: list[str]
    collective_velocity: float
    size: int


class GraphResponse(BaseModel):
    """Response containing the pulse graph."""

    nodes: list[TopicNode]
    edges: list[TopicEdge]
    clusters: list[ClusterInfo] = Field(default_factory=list)
    captured_at: datetime


class PulseResponse(BaseModel):
    """Response containing current pulse state."""

    topics: list[TopicNode]
    clusters: list[ClusterInfo] = Field(default_factory=list)
    snapshot_id: str
    captured_at: datetime
```

**Step 3: Write schema tests**

```python
# tests/models/__init__.py
"""Model tests package."""
```

```python
# tests/models/test_pulse.py
"""Tests for pulse Pydantic models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from community_pulse.models.pulse import (
    GraphResponse,
    PulseResponse,
    TopicEdge,
    TopicNode,
)


def test_topic_node_valid() -> None:
    """Test creating a valid topic node."""
    node = TopicNode(
        id="123",
        slug="machine-learning",
        label="Machine Learning",
        pulse_score=0.75,
        velocity=1.5,
        centrality=0.3,
    )
    assert node.pulse_score == 0.75
    assert node.velocity == 1.5


def test_topic_node_score_bounds() -> None:
    """Test pulse score must be between 0 and 1."""
    with pytest.raises(ValidationError):
        TopicNode(
            id="123",
            slug="test",
            label="Test",
            pulse_score=1.5,  # Invalid: > 1
        )


def test_topic_edge_valid() -> None:
    """Test creating a valid topic edge."""
    edge = TopicEdge(source="topic1", target="topic2", weight=5.0, shared_posts=10)
    assert edge.weight == 5.0


def test_graph_response() -> None:
    """Test creating a graph response."""
    now = datetime.now(timezone.utc)
    response = GraphResponse(
        nodes=[
            TopicNode(id="1", slug="ai", label="AI", pulse_score=0.8),
            TopicNode(id="2", slug="ml", label="ML", pulse_score=0.6),
        ],
        edges=[TopicEdge(source="1", target="2", weight=3.0)],
        captured_at=now,
    )
    assert len(response.nodes) == 2
    assert len(response.edges) == 1


def test_pulse_response() -> None:
    """Test creating a pulse response."""
    now = datetime.now(timezone.utc)
    response = PulseResponse(
        topics=[TopicNode(id="1", slug="ai", label="AI", pulse_score=0.9)],
        snapshot_id="snap123",
        captured_at=now,
    )
    assert response.snapshot_id == "snap123"
```

**Step 4: Run tests**

Run: `uv run pytest tests/models/test_pulse.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/community_pulse/models/ tests/models/
git commit -m "feat(models): add Pydantic schemas for pulse API"
```

---

### Task 3: HN Data Ingestion

**Files:**
- Create: `src/community_pulse/ingest/__init__.py`
- Create: `src/community_pulse/ingest/hn_loader.py`
- Create: `src/community_pulse/ingest/topic_extractor.py`
- Create: `scripts/fetch_hn_data.py`
- Test: `tests/ingest/test_hn_loader.py`

**Step 1: Create ingest package**

```python
# src/community_pulse/ingest/__init__.py
"""Data ingestion package."""

from community_pulse.ingest.hn_loader import HNItem, load_hn_items, parse_hn_item
from community_pulse.ingest.topic_extractor import extract_topics

__all__ = ["HNItem", "load_hn_items", "parse_hn_item", "extract_topics"]
```

**Step 2: Create HN loader**

```python
# src/community_pulse/ingest/hn_loader.py
"""Hacker News data loader."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class HNItem:
    """Parsed Hacker News item."""

    id: int
    type: str  # "story", "comment", "job", "poll"
    by: str | None
    time: datetime
    text: str | None
    title: str | None
    url: str | None
    score: int
    parent: int | None
    kids: list[int]


def parse_hn_item(data: dict) -> HNItem | None:
    """Parse a raw HN API response into an HNItem."""
    if not data or data.get("deleted") or data.get("dead"):
        return None

    item_type = data.get("type", "unknown")
    if item_type not in ("story", "comment"):
        return None

    timestamp = data.get("time", 0)
    posted_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return HNItem(
        id=data.get("id", 0),
        type=item_type,
        by=data.get("by"),
        time=posted_at,
        text=data.get("text"),
        title=data.get("title"),
        url=data.get("url"),
        score=data.get("score", 0),
        parent=data.get("parent"),
        kids=data.get("kids", []),
    )


def load_hn_items(path: Path) -> list[HNItem]:
    """Load HN items from a JSON file."""
    with open(path) as f:
        raw_items = json.load(f)

    items = []
    for raw in raw_items:
        item = parse_hn_item(raw)
        if item:
            items.append(item)

    return items
```

**Step 3: Create topic extractor**

```python
# src/community_pulse/ingest/topic_extractor.py
"""Simple keyword-based topic extraction."""

import re
from collections import Counter

# Common tech topics to extract
TOPIC_PATTERNS: dict[str, list[str]] = {
    "ai": ["artificial intelligence", "ai ", " ai", "machine learning", "ml ", "llm", "gpt", "chatgpt", "claude"],
    "rust": ["rust ", " rust", "rustlang", "cargo"],
    "python": ["python", "django", "fastapi", "flask"],
    "javascript": ["javascript", "typescript", "node.js", "nodejs", "react", "vue", "angular"],
    "golang": ["golang", " go ", "go1."],
    "database": ["postgres", "postgresql", "mysql", "sqlite", "mongodb", "redis"],
    "cloud": ["aws", "azure", "gcp", "kubernetes", "k8s", "docker"],
    "security": ["security", "vulnerability", "cve-", "exploit", "breach"],
    "startup": ["startup", "founder", "yc ", "y combinator", "funding", "series a"],
    "open-source": ["open source", "opensource", "github", "gitlab", "foss"],
}


def extract_topics(text: str | None, title: str | None = None) -> list[tuple[str, float]]:
    """Extract topics from text content.

    Returns list of (topic_slug, relevance_score) tuples.
    """
    if not text and not title:
        return []

    combined = f"{title or ''} {text or ''}".lower()
    found_topics: list[tuple[str, float]] = []

    for slug, patterns in TOPIC_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined:
                # Simple relevance: title match = 1.0, text match = 0.8
                relevance = 1.0 if title and pattern in title.lower() else 0.8
                found_topics.append((slug, relevance))
                break  # Only count each topic once

    return found_topics


def extract_keywords(text: str | None, top_n: int = 10) -> list[str]:
    """Extract top keywords from text (simple frequency-based)."""
    if not text:
        return []

    # Simple tokenization
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())

    # Filter common words
    stopwords = {
        "the", "and", "for", "that", "this", "with", "from", "are", "was",
        "were", "been", "have", "has", "had", "will", "would", "could",
        "should", "can", "may", "might", "must", "shall", "not", "but",
        "you", "your", "they", "their", "them", "what", "which", "who",
        "how", "when", "where", "why", "all", "each", "every", "both",
        "few", "more", "most", "other", "some", "such", "than", "too",
        "very", "just", "also", "now", "only", "over", "own", "same",
    }

    filtered = [w for w in words if w not in stopwords]
    counts = Counter(filtered)

    return [word for word, _ in counts.most_common(top_n)]
```

**Step 4: Write ingest tests**

```python
# tests/ingest/__init__.py
"""Ingest tests package."""
```

```python
# tests/ingest/test_hn_loader.py
"""Tests for HN data loader."""

from datetime import datetime, timezone

from community_pulse.ingest.hn_loader import HNItem, parse_hn_item
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
        "Built with Python and PostgreSQL on AWS",
        "My FastAPI Project"
    )
    slugs = [t[0] for t in topics]
    assert "python" in slugs
    assert "database" in slugs
    assert "cloud" in slugs


def test_extract_keywords() -> None:
    """Test keyword extraction."""
    text = "Python is great for machine learning. Python also works well with databases."
    keywords = extract_keywords(text, top_n=3)
    assert "python" in keywords
```

**Step 5: Run tests**

Run: `uv run pytest tests/ingest/ -v`
Expected: All 6 tests PASS

**Step 6: Create HN fetch script**

```python
# scripts/fetch_hn_data.py
#!/usr/bin/env python3
"""Fetch recent Hacker News data for Community Pulse POC."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

HN_API = "https://hacker-news.firebaseio.com/v0"
OUTPUT_DIR = Path("data")


async def fetch_item(client: httpx.AsyncClient, item_id: int) -> dict | None:
    """Fetch a single HN item."""
    try:
        resp = await client.get(f"{HN_API}/item/{item_id}.json")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching {item_id}: {e}")
        return None


async def fetch_top_stories(client: httpx.AsyncClient, limit: int = 100) -> list[int]:
    """Fetch top story IDs."""
    resp = await client.get(f"{HN_API}/topstories.json")
    resp.raise_for_status()
    return resp.json()[:limit]


async def fetch_with_comments(
    client: httpx.AsyncClient,
    story_id: int,
    max_comments: int = 20
) -> list[dict]:
    """Fetch a story and its top comments."""
    items = []

    story = await fetch_item(client, story_id)
    if story:
        items.append(story)

        # Fetch top comments
        kids = story.get("kids", [])[:max_comments]
        for kid_id in kids:
            comment = await fetch_item(client, kid_id)
            if comment:
                items.append(comment)

    return items


async def main() -> None:
    """Fetch HN data and save to JSON."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Fetching top stories...")
        story_ids = await fetch_top_stories(client, limit=50)

        all_items = []
        for i, story_id in enumerate(story_ids):
            print(f"Fetching story {i+1}/{len(story_ids)}: {story_id}")
            items = await fetch_with_comments(client, story_id, max_comments=10)
            all_items.extend(items)
            await asyncio.sleep(0.1)  # Be nice to the API

        # Save to file
        output_path = OUTPUT_DIR / "hn_sample.json"
        with open(output_path, "w") as f:
            json.dump(all_items, f, indent=2)

        print(f"Saved {len(all_items)} items to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 7: Commit**

```bash
git add src/community_pulse/ingest/ tests/ingest/ scripts/fetch_hn_data.py
git commit -m "feat(ingest): add HN data loader and topic extraction"
```

---

### Task 4: Graph Analysis with rustworkx

**Files:**
- Create: `src/community_pulse/analysis/__init__.py`
- Create: `src/community_pulse/analysis/graph.py`
- Create: `src/community_pulse/analysis/velocity.py`
- Test: `tests/analysis/test_graph.py`

**Step 1: Add rustworkx dependency**

```bash
uv add rustworkx
```

**Step 2: Create analysis package**

```python
# src/community_pulse/analysis/__init__.py
"""Graph analysis package."""

from community_pulse.analysis.graph import (
    build_topic_graph,
    compute_centrality,
    detect_clusters,
)
from community_pulse.analysis.velocity import compute_velocity, compute_pulse_score

__all__ = [
    "build_topic_graph",
    "compute_centrality",
    "detect_clusters",
    "compute_velocity",
    "compute_pulse_score",
]
```

**Step 3: Create graph analysis module**

```python
# src/community_pulse/analysis/graph.py
"""Graph analysis using rustworkx."""

from dataclasses import dataclass

import rustworkx as rx


@dataclass
class TopicGraphData:
    """Data for building the topic graph."""

    topic_a: str
    topic_b: str
    shared_posts: int
    shared_authors: int


def build_topic_graph(
    cooccurrence_data: list[TopicGraphData],
) -> tuple[rx.PyGraph, dict[str, int]]:
    """Build an undirected topic co-occurrence graph.

    Returns:
        Tuple of (graph, topic_id_to_node_index mapping)
    """
    graph: rx.PyGraph = rx.PyGraph()
    topic_indices: dict[str, int] = {}

    for row in cooccurrence_data:
        # Add nodes if not present
        for topic_id in [row.topic_a, row.topic_b]:
            if topic_id not in topic_indices:
                node_idx = graph.add_node({"id": topic_id})
                topic_indices[topic_id] = node_idx

        # Add weighted edge
        graph.add_edge(
            topic_indices[row.topic_a],
            topic_indices[row.topic_b],
            {"weight": row.shared_authors, "posts": row.shared_posts},
        )

    return graph, topic_indices


def compute_centrality(graph: rx.PyGraph) -> dict[int, dict[str, float]]:
    """Compute centrality metrics for all nodes.

    Returns:
        Dict mapping node index to centrality metrics.
    """
    if graph.num_nodes() == 0:
        return {}

    # Compute different centrality measures
    betweenness = rx.betweenness_centrality(graph)
    pagerank = rx.pagerank(graph, alpha=0.85)

    # Eigenvector centrality can fail on disconnected graphs
    try:
        eigenvector = rx.eigenvector_centrality(graph, max_iter=100)
    except rx.FailedToConverge:
        eigenvector = {i: 0.0 for i in graph.node_indices()}

    return {
        node_idx: {
            "betweenness": betweenness.get(node_idx, 0.0),
            "eigenvector": eigenvector.get(node_idx, 0.0),
            "pagerank": pagerank.get(node_idx, 0.0),
        }
        for node_idx in graph.node_indices()
    }


def detect_clusters(graph: rx.PyGraph) -> list[set[int]]:
    """Detect topic clusters using connected components.

    For a more sophisticated approach, we'd use Louvain,
    but connected components work for the POC.
    """
    if graph.num_nodes() == 0:
        return []

    return rx.connected_components(graph)
```

**Step 4: Create velocity module**

```python
# src/community_pulse/analysis/velocity.py
"""Velocity and pulse score computation."""

from dataclasses import dataclass


@dataclass
class VelocityData:
    """Velocity data for a topic."""

    topic_id: str
    current_mentions: int
    baseline_mentions: float
    unique_authors: int


def compute_velocity(data: VelocityData) -> float:
    """Compute velocity ratio for a topic.

    Velocity = current_rate / baseline_rate
    A velocity > 1.0 means the topic is trending up.
    """
    if data.baseline_mentions <= 0:
        # No baseline: if we have current mentions, it's emerging
        return 2.0 if data.current_mentions > 0 else 1.0

    return data.current_mentions / data.baseline_mentions


def compute_pulse_score(
    velocity: float,
    eigenvector_centrality: float,
    betweenness_centrality: float,
    unique_authors: int,
    max_authors: int = 100,
) -> float:
    """Compute combined pulse score.

    Weights:
    - 30% velocity (momentum)
    - 30% eigenvector centrality (convergence/importance)
    - 25% betweenness centrality (bridge topics)
    - 15% author spread (relational)

    Returns score between 0 and 1.
    """
    # Normalize velocity (cap at 3x baseline)
    norm_velocity = min(velocity / 3.0, 1.0)

    # Centrality already 0-1 from rustworkx
    norm_eigen = min(eigenvector_centrality, 1.0)
    norm_between = min(betweenness_centrality, 1.0)

    # Normalize author count
    norm_authors = min(unique_authors / max_authors, 1.0)

    score = (
        0.30 * norm_velocity
        + 0.30 * norm_eigen
        + 0.25 * norm_between
        + 0.15 * norm_authors
    )

    return round(score, 4)
```

**Step 5: Write analysis tests**

```python
# tests/analysis/__init__.py
"""Analysis tests package."""
```

```python
# tests/analysis/test_graph.py
"""Tests for graph analysis."""

import pytest

from community_pulse.analysis.graph import (
    TopicGraphData,
    build_topic_graph,
    compute_centrality,
    detect_clusters,
)
from community_pulse.analysis.velocity import (
    VelocityData,
    compute_pulse_score,
    compute_velocity,
)


def test_build_empty_graph() -> None:
    """Test building a graph with no data."""
    graph, indices = build_topic_graph([])
    assert graph.num_nodes() == 0
    assert graph.num_edges() == 0


def test_build_simple_graph() -> None:
    """Test building a simple graph."""
    data = [
        TopicGraphData("ai", "ml", shared_posts=10, shared_authors=5),
        TopicGraphData("ai", "python", shared_posts=8, shared_authors=4),
    ]
    graph, indices = build_topic_graph(data)

    assert graph.num_nodes() == 3
    assert graph.num_edges() == 2
    assert "ai" in indices
    assert "ml" in indices
    assert "python" in indices


def test_compute_centrality() -> None:
    """Test centrality computation."""
    data = [
        TopicGraphData("ai", "ml", shared_posts=10, shared_authors=5),
        TopicGraphData("ai", "python", shared_posts=8, shared_authors=4),
        TopicGraphData("ml", "python", shared_posts=3, shared_authors=2),
    ]
    graph, indices = build_topic_graph(data)
    centrality = compute_centrality(graph)

    # AI should have higher centrality (connected to both)
    ai_idx = indices["ai"]
    assert ai_idx in centrality
    assert "betweenness" in centrality[ai_idx]
    assert "eigenvector" in centrality[ai_idx]
    assert "pagerank" in centrality[ai_idx]


def test_detect_clusters_connected() -> None:
    """Test cluster detection on connected graph."""
    data = [
        TopicGraphData("ai", "ml", shared_posts=10, shared_authors=5),
    ]
    graph, _ = build_topic_graph(data)
    clusters = detect_clusters(graph)

    # Should be one cluster with both topics
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_detect_clusters_disconnected() -> None:
    """Test cluster detection on disconnected graph."""
    data = [
        TopicGraphData("ai", "ml", shared_posts=10, shared_authors=5),
        TopicGraphData("rust", "golang", shared_posts=5, shared_authors=3),
    ]
    graph, _ = build_topic_graph(data)
    clusters = detect_clusters(graph)

    # Should be two separate clusters
    assert len(clusters) == 2


def test_compute_velocity_normal() -> None:
    """Test velocity computation."""
    data = VelocityData(
        topic_id="ai",
        current_mentions=20,
        baseline_mentions=10.0,
        unique_authors=5,
    )
    velocity = compute_velocity(data)
    assert velocity == 2.0  # 20/10


def test_compute_velocity_no_baseline() -> None:
    """Test velocity with no baseline."""
    data = VelocityData(
        topic_id="new-topic",
        current_mentions=5,
        baseline_mentions=0.0,
        unique_authors=3,
    )
    velocity = compute_velocity(data)
    assert velocity == 2.0  # Emerging topic


def test_compute_pulse_score() -> None:
    """Test pulse score computation."""
    score = compute_pulse_score(
        velocity=2.0,
        eigenvector_centrality=0.5,
        betweenness_centrality=0.3,
        unique_authors=50,
        max_authors=100,
    )
    # 0.30 * (2/3) + 0.30 * 0.5 + 0.25 * 0.3 + 0.15 * 0.5
    # = 0.20 + 0.15 + 0.075 + 0.075 = 0.50
    assert 0.4 <= score <= 0.6
```

**Step 6: Run tests**

Run: `uv run pytest tests/analysis/ -v`
Expected: All 8 tests PASS

**Step 7: Commit**

```bash
git add src/community_pulse/analysis/ tests/analysis/ pyproject.toml uv.lock
git commit -m "feat(analysis): add graph analysis with rustworkx"
```

---

### Task 5: FastAPI Application

**Files:**
- Create: `src/community_pulse/api/__init__.py`
- Create: `src/community_pulse/api/app.py`
- Create: `src/community_pulse/api/routes/__init__.py`
- Create: `src/community_pulse/api/routes/health.py`
- Create: `src/community_pulse/api/routes/pulse.py`
- Test: `tests/api/test_health.py`

**Step 1: Create API package**

```python
# src/community_pulse/api/__init__.py
"""FastAPI application package."""

from community_pulse.api.app import create_app

__all__ = ["create_app"]
```

**Step 2: Create app factory**

```python
# src/community_pulse/api/app.py
"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from community_pulse.api.routes import health, pulse


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Community Pulse API",
        description="Detect emerging trends in online communities",
        version="0.1.0",
    )

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(pulse.router)

    return app


# For uvicorn
app = create_app()
```

**Step 3: Create routes package**

```python
# src/community_pulse/api/routes/__init__.py
"""API routes package."""
```

**Step 4: Create health route**

```python
# src/community_pulse/api/routes/health.py
"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
```

**Step 5: Create pulse routes (mock data for now)**

```python
# src/community_pulse/api/routes/pulse.py
"""Pulse API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Query

from community_pulse.models.pulse import (
    ClusterInfo,
    GraphResponse,
    PulseResponse,
    TopicEdge,
    TopicNode,
)

router = APIRouter(prefix="/pulse", tags=["pulse"])


def _mock_topics() -> list[TopicNode]:
    """Generate mock topic data for POC."""
    return [
        TopicNode(
            id=str(uuid4()),
            slug="ai",
            label="Artificial Intelligence",
            pulse_score=0.85,
            velocity=2.1,
            centrality=0.7,
            mention_count=150,
            unique_authors=45,
        ),
        TopicNode(
            id=str(uuid4()),
            slug="rust",
            label="Rust",
            pulse_score=0.72,
            velocity=1.8,
            centrality=0.5,
            mention_count=89,
            unique_authors=32,
        ),
        TopicNode(
            id=str(uuid4()),
            slug="python",
            label="Python",
            pulse_score=0.65,
            velocity=1.2,
            centrality=0.6,
            mention_count=120,
            unique_authors=55,
        ),
        TopicNode(
            id=str(uuid4()),
            slug="javascript",
            label="JavaScript",
            pulse_score=0.58,
            velocity=1.1,
            centrality=0.55,
            mention_count=95,
            unique_authors=40,
        ),
        TopicNode(
            id=str(uuid4()),
            slug="startup",
            label="Startups",
            pulse_score=0.52,
            velocity=1.5,
            centrality=0.3,
            mention_count=65,
            unique_authors=28,
        ),
    ]


@router.get("/current", response_model=PulseResponse)
async def get_current_pulse(
    limit: int = Query(20, le=100, description="Max topics to return"),
    min_score: float = Query(0.0, ge=0, le=1, description="Minimum pulse score"),
) -> PulseResponse:
    """Get current pulse state - top trending topics."""
    topics = _mock_topics()
    filtered = [t for t in topics if t.pulse_score >= min_score]
    sorted_topics = sorted(filtered, key=lambda t: t.pulse_score, reverse=True)

    return PulseResponse(
        topics=sorted_topics[:limit],
        clusters=[],
        snapshot_id=str(uuid4()),
        captured_at=datetime.now(timezone.utc),
    )


@router.get("/graph", response_model=GraphResponse)
async def get_pulse_graph(
    min_edge_weight: int = Query(2, description="Minimum co-occurrence for edges"),
) -> GraphResponse:
    """Get topic co-occurrence graph for visualization."""
    topics = _mock_topics()

    # Mock edges between topics
    edges = [
        TopicEdge(source=topics[0].id, target=topics[2].id, weight=5.0, shared_posts=25),
        TopicEdge(source=topics[0].id, target=topics[1].id, weight=3.0, shared_posts=15),
        TopicEdge(source=topics[2].id, target=topics[3].id, weight=4.0, shared_posts=20),
        TopicEdge(source=topics[1].id, target=topics[2].id, weight=2.0, shared_posts=10),
    ]

    # Filter by edge weight
    filtered_edges = [e for e in edges if e.weight >= min_edge_weight]

    return GraphResponse(
        nodes=topics,
        edges=filtered_edges,
        clusters=[
            ClusterInfo(
                id=str(uuid4()),
                topic_ids=[topics[0].id, topics[1].id, topics[2].id],
                collective_velocity=1.7,
                size=3,
            )
        ],
        captured_at=datetime.now(timezone.utc),
    )
```

**Step 6: Write API tests**

```python
# tests/api/__init__.py
"""API tests package."""
```

```python
# tests/api/test_health.py
"""Tests for health endpoint."""

from fastapi.testclient import TestClient

from community_pulse.api.app import create_app


def test_health_check() -> None:
    """Test health check returns healthy status."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_current_pulse() -> None:
    """Test current pulse endpoint returns data."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/pulse/current")

    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "snapshot_id" in data
    assert len(data["topics"]) > 0


def test_pulse_graph() -> None:
    """Test pulse graph endpoint returns nodes and edges."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/pulse/graph")

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
```

**Step 7: Run tests**

Run: `uv run pytest tests/api/ -v`
Expected: All 3 tests PASS

**Step 8: Commit**

```bash
git add src/community_pulse/api/ tests/api/
git commit -m "feat(api): add FastAPI application with pulse endpoints"
```

---

## Phase 2: Frontend Foundation

### Task 6: Frontend Project Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/app.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/babel.config.js`
- Create: `frontend/metro.config.js`
- Create: `frontend/app/_layout.tsx`
- Create: `frontend/app/index.tsx`

**Step 1: Initialize Expo project**

```bash
cd /home/alext/community-pulse
mkdir -p frontend
cd frontend
npx create-expo-app@latest . --template blank-typescript
```

**Step 2: Add dependencies**

```bash
cd frontend
npm install react-force-graph-2d recharts @tanstack/react-query
npm install --save-dev @types/react
```

**Step 3: Create app layout**

```tsx
// frontend/app/_layout.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, StyleSheet } from 'react-native';

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <View style={styles.container}>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: '#0f1419' },
            headerTintColor: '#e2e8f0',
            headerTitleStyle: { fontWeight: '600' },
            contentStyle: { backgroundColor: '#0f1419' },
          }}
        />
      </View>
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f1419',
  },
});
```

**Step 4: Create main screen**

```tsx
// frontend/app/index.tsx
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
}

interface PulseResponse {
  topics: TopicNode[];
  snapshot_id: string;
  captured_at: string;
}

async function fetchPulse(): Promise<PulseResponse> {
  const response = await fetch(`${API_URL}/pulse/current`);
  if (!response.ok) {
    throw new Error('Failed to fetch pulse data');
  }
  return response.json();
}

export default function PulseScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['pulse'],
    queryFn: fetchPulse,
    refetchInterval: 30000, // Refresh every 30s
  });

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#22d3ee" />
        <Text style={styles.loadingText}>Loading pulse...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Failed to load pulse data</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Community Pulse</Text>
      <View style={styles.topicList}>
        {data?.topics.map((topic) => (
          <View key={topic.id} style={styles.topicCard}>
            <Text style={styles.topicLabel}>{topic.label}</Text>
            <View style={styles.metrics}>
              <Text style={styles.score}>
                {Math.round(topic.pulse_score * 100)}
              </Text>
              <Text style={styles.velocity}>
                {topic.velocity > 1 ? '↑' : '→'}
                {((topic.velocity - 1) * 100).toFixed(0)}%
              </Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#0f1419',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f1419',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#e2e8f0',
    marginBottom: 20,
  },
  loadingText: {
    color: '#94a3b8',
    marginTop: 12,
  },
  errorText: {
    color: '#f87171',
  },
  topicList: {
    gap: 12,
  },
  topicCard: {
    backgroundColor: '#1a1f26',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2d3748',
  },
  topicLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e2e8f0',
    marginBottom: 8,
  },
  metrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  score: {
    fontSize: 28,
    fontWeight: '700',
    color: '#22d3ee',
  },
  velocity: {
    fontSize: 14,
    color: '#4ade80',
  },
});
```

**Step 5: Test frontend locally**

```bash
cd frontend
npm run web
```

Expected: Browser opens at localhost:8081 showing "Community Pulse" with loading state (API not running yet)

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): initialize React Native Web with Expo"
```

---

### Task 7: Flow Graph Visualization

**Files:**
- Create: `frontend/components/FlowGraph.tsx`
- Create: `frontend/hooks/usePulseGraph.ts`
- Modify: `frontend/app/index.tsx`

**Step 1: Create graph hook**

```tsx
// frontend/hooks/usePulseGraph.ts
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

export interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
  centrality: number;
}

export interface TopicEdge {
  source: string;
  target: string;
  weight: number;
}

export interface GraphData {
  nodes: TopicNode[];
  edges: TopicEdge[];
}

async function fetchGraph(): Promise<GraphData> {
  const response = await fetch(`${API_URL}/pulse/graph`);
  if (!response.ok) {
    throw new Error('Failed to fetch graph data');
  }
  const data = await response.json();
  return {
    nodes: data.nodes,
    edges: data.edges,
  };
}

export function usePulseGraph() {
  return useQuery({
    queryKey: ['pulse-graph'],
    queryFn: fetchGraph,
    refetchInterval: 60000, // Refresh every minute
  });
}
```

**Step 2: Create FlowGraph component**

```tsx
// frontend/components/FlowGraph.tsx
import { useCallback, useRef, useEffect, useState } from 'react';
import { View, StyleSheet, Platform, Text } from 'react-native';

// Only import on web
let ForceGraph2D: any = null;
if (Platform.OS === 'web') {
  ForceGraph2D = require('react-force-graph-2d').default;
}

interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
  centrality: number;
}

interface TopicEdge {
  source: string;
  target: string;
  weight: number;
}

interface FlowGraphProps {
  nodes: TopicNode[];
  edges: TopicEdge[];
  onNodeClick?: (node: TopicNode) => void;
}

const colors = {
  low: '#3b5068',
  mid: '#0d9488',
  high: '#22d3ee',
  text: '#e2e8f0',
  edge: '#2d3748',
};

function getNodeColor(pulseScore: number): string {
  if (pulseScore < 0.4) return colors.low;
  if (pulseScore < 0.7) return colors.mid;
  return colors.high;
}

export function FlowGraph({ nodes, edges, onNodeClick }: FlowGraphProps) {
  const graphRef = useRef<any>();
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      const updateDimensions = () => {
        setDimensions({
          width: window.innerWidth,
          height: window.innerHeight - 100,
        });
      };
      updateDimensions();
      window.addEventListener('resize', updateDimensions);
      return () => window.removeEventListener('resize', updateDimensions);
    }
  }, []);

  const graphData = {
    nodes: nodes.map((n) => ({
      ...n,
      val: 4 + n.pulse_score * 16, // Node size
    })),
    links: edges.map((e) => ({
      source: e.source,
      target: e.target,
      value: e.weight,
    })),
  };

  const handleNodeClick = useCallback(
    (node: any) => {
      if (onNodeClick) {
        onNodeClick(node);
      }
    },
    [onNodeClick]
  );

  if (Platform.OS !== 'web' || !ForceGraph2D) {
    return (
      <View style={styles.fallback}>
        <Text style={styles.fallbackText}>
          Graph visualization available on web only
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeLabel="label"
        nodeColor={(node: any) => getNodeColor(node.pulse_score)}
        nodeVal={(node: any) => node.val}
        linkColor={() => colors.edge}
        linkWidth={(link: any) => 0.5 + link.value}
        backgroundColor="#0f1419"
        onNodeClick={handleNodeClick}
        width={dimensions.width}
        height={dimensions.height}
        cooldownTicks={100}
        d3VelocityDecay={0.3}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  fallback: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f1419',
  },
  fallbackText: {
    color: '#94a3b8',
  },
});
```

**Step 3: Update main screen with view toggle**

```tsx
// frontend/app/index.tsx
import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Pressable,
  ScrollView,
  useWindowDimensions,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { FlowGraph } from '../components/FlowGraph';
import { usePulseGraph } from '../hooks/usePulseGraph';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
}

interface PulseResponse {
  topics: TopicNode[];
  snapshot_id: string;
  captured_at: string;
}

async function fetchPulse(): Promise<PulseResponse> {
  const response = await fetch(`${API_URL}/pulse/current`);
  if (!response.ok) {
    throw new Error('Failed to fetch pulse data');
  }
  return response.json();
}

type ViewType = 'cards' | 'graph';

export default function PulseScreen() {
  const { width } = useWindowDimensions();
  const isMobile = width < 768;

  const [view, setView] = useState<ViewType>(isMobile ? 'cards' : 'graph');

  const pulseQuery = useQuery({
    queryKey: ['pulse'],
    queryFn: fetchPulse,
    refetchInterval: 30000,
  });

  const graphQuery = usePulseGraph();

  const isLoading = pulseQuery.isLoading || graphQuery.isLoading;
  const error = pulseQuery.error || graphQuery.error;

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#22d3ee" />
        <Text style={styles.loadingText}>Loading pulse...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Failed to load pulse data</Text>
        <Text style={styles.errorDetail}>{String(error)}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* View Toggle */}
      <View style={styles.toggleContainer}>
        <Pressable
          style={[styles.toggleBtn, view === 'cards' && styles.toggleActive]}
          onPress={() => setView('cards')}
        >
          <Text
            style={[
              styles.toggleText,
              view === 'cards' && styles.toggleTextActive,
            ]}
          >
            Cards
          </Text>
        </Pressable>
        <Pressable
          style={[styles.toggleBtn, view === 'graph' && styles.toggleActive]}
          onPress={() => setView('graph')}
        >
          <Text
            style={[
              styles.toggleText,
              view === 'graph' && styles.toggleTextActive,
            ]}
          >
            Graph
          </Text>
        </Pressable>
      </View>

      {/* Content */}
      {view === 'cards' ? (
        <ScrollView style={styles.scrollView}>
          <View style={styles.topicList}>
            {pulseQuery.data?.topics.map((topic) => (
              <View key={topic.id} style={styles.topicCard}>
                <Text style={styles.topicLabel}>{topic.label}</Text>
                <View style={styles.metrics}>
                  <Text style={styles.score}>
                    {Math.round(topic.pulse_score * 100)}
                  </Text>
                  <Text style={styles.velocity}>
                    {topic.velocity > 1 ? '↑' : '→'}
                    {((topic.velocity - 1) * 100).toFixed(0)}%
                  </Text>
                </View>
              </View>
            ))}
          </View>
        </ScrollView>
      ) : (
        graphQuery.data && (
          <FlowGraph
            nodes={graphQuery.data.nodes}
            edges={graphQuery.data.edges}
            onNodeClick={(node) => console.log('Clicked:', node.label)}
          />
        )
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f1419',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f1419',
  },
  loadingText: {
    color: '#94a3b8',
    marginTop: 12,
  },
  errorText: {
    color: '#f87171',
    fontSize: 16,
  },
  errorDetail: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 8,
  },
  toggleContainer: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
  },
  toggleBtn: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#1a1f26',
  },
  toggleActive: {
    backgroundColor: '#22d3ee',
  },
  toggleText: {
    color: '#94a3b8',
    fontWeight: '600',
  },
  toggleTextActive: {
    color: '#0f1419',
  },
  scrollView: {
    flex: 1,
  },
  topicList: {
    padding: 16,
    gap: 12,
  },
  topicCard: {
    backgroundColor: '#1a1f26',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2d3748',
  },
  topicLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e2e8f0',
    marginBottom: 8,
  },
  metrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  score: {
    fontSize: 28,
    fontWeight: '700',
    color: '#22d3ee',
  },
  velocity: {
    fontSize: 14,
    color: '#4ade80',
  },
});
```

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): add flow graph visualization with view toggle"
```

---

## Phase 3: Integration & Deployment

### Task 8: Data Seeding Script

**Files:**
- Create: `scripts/seed_db.py`
- Modify: `pyproject.toml` (add script entry)

**Step 1: Create seed script**

```python
# scripts/seed_db.py
#!/usr/bin/env python3
"""Seed database with HN data."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from community_pulse.db.models import Author, Base, Post, PostTopic, Topic
from community_pulse.ingest.hn_loader import load_hn_items
from community_pulse.ingest.topic_extractor import extract_topics

load_dotenv()


def get_or_create_author(session, external_id: str, handle: str) -> Author:
    """Get existing author or create new one."""
    author = session.query(Author).filter_by(external_id=external_id).first()
    if not author:
        author = Author(external_id=external_id, handle=handle)
        session.add(author)
        session.flush()
    return author


def get_or_create_topic(session, slug: str) -> Topic:
    """Get existing topic or create new one."""
    topic = session.query(Topic).filter_by(slug=slug).first()
    if not topic:
        label = slug.replace("-", " ").title()
        topic = Topic(slug=slug, label=label)
        session.add(topic)
        session.flush()
    return topic


def seed_database(data_path: Path) -> None:
    """Seed database from HN data file."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print(f"Loading data from {data_path}...")
        items = load_hn_items(data_path)
        print(f"Loaded {len(items)} items")

        # Track parent mappings for comments
        external_to_uuid: dict[int, str] = {}

        for item in items:
            # Skip if already exists
            existing = session.query(Post).filter_by(
                external_id=str(item.id)
            ).first()
            if existing:
                continue

            # Create author if present
            author = None
            if item.by:
                author = get_or_create_author(session, item.by, item.by)

            # Create post
            post = Post(
                external_id=str(item.id),
                author_id=author.id if author else None,
                title=item.title,
                content=item.text,
                url=item.url,
                posted_at=item.time,
                score=item.score,
                metadata_={"type": item.type},
            )

            # Link to parent if comment
            if item.parent and item.parent in external_to_uuid:
                post.parent_id = external_to_uuid[item.parent]

            session.add(post)
            session.flush()
            external_to_uuid[item.id] = post.id

            # Extract and link topics
            topics = extract_topics(item.text, item.title)
            for slug, relevance in topics:
                topic = get_or_create_topic(session, slug)
                post_topic = PostTopic(
                    post_id=post.id,
                    topic_id=topic.id,
                    relevance=relevance,
                )
                session.add(post_topic)

        session.commit()
        print("Database seeded successfully!")

        # Print stats
        post_count = session.query(Post).count()
        topic_count = session.query(Topic).count()
        author_count = session.query(Author).count()
        print(f"  Posts: {post_count}")
        print(f"  Topics: {topic_count}")
        print(f"  Authors: {author_count}")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    data_path = Path("data/hn_sample.json")
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        print("Run scripts/fetch_hn_data.py first")
        exit(1)

    seed_database(data_path)
```

**Step 2: Add httpx dependency for fetch script**

```bash
uv add httpx
```

**Step 3: Commit**

```bash
git add scripts/seed_db.py pyproject.toml uv.lock
git commit -m "feat(scripts): add database seeding from HN data"
```

---

### Task 9: Docker and Render Configuration

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `render.yaml`
- Create: `.env.example`

**Step 1: Create backend Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run
CMD ["uv", "run", "uvicorn", "community_pulse.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: community_pulse
      POSTGRES_USER: pulse
      POSTGRES_PASSWORD: pulse_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pulse -d community_pulse"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://pulse:pulse_dev@db:5432/community_pulse
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

**Step 3: Create render.yaml**

```yaml
# render.yaml
services:
  - type: web
    name: community-pulse-api
    runtime: python
    repo: https://github.com/athola/community-pulse
    buildCommand: pip install uv && uv sync --frozen --no-dev
    startCommand: uv run uvicorn community_pulse.api.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: community-pulse-db
          property: connectionString
      - key: PYTHON_VERSION
        value: "3.12"
    plan: free

  - type: web
    name: community-pulse-web
    runtime: static
    repo: https://github.com/athola/community-pulse
    rootDir: frontend
    buildCommand: npm install && npx expo export -p web
    staticPublishPath: dist
    envVars:
      - key: EXPO_PUBLIC_API_URL
        value: https://community-pulse-api.onrender.com
    headers:
      - path: /*
        name: Cache-Control
        value: no-cache
    plan: free

databases:
  - name: community-pulse-db
    plan: free
    postgresMajorVersion: 16
```

**Step 4: Create .env.example**

```bash
# .env.example
DATABASE_URL=postgresql://pulse:pulse_dev@localhost:5432/community_pulse
EXPO_PUBLIC_API_URL=http://localhost:8000
```

**Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml render.yaml .env.example
git commit -m "feat(deploy): add Docker and Render configuration"
```

---

### Task 10: Final Integration Test

**Step 1: Start local environment**

```bash
# Terminal 1: Start database
docker-compose up db

# Terminal 2: Fetch and seed data
uv run python scripts/fetch_hn_data.py
cp .env.example .env
uv run python scripts/seed_db.py

# Terminal 3: Start API
uv run uvicorn community_pulse.api.app:app --reload

# Terminal 4: Start frontend
cd frontend && npm run web
```

**Step 2: Verify endpoints**

```bash
# Health check
curl http://localhost:8000/health

# Get pulse
curl http://localhost:8000/pulse/current | jq

# Get graph
curl http://localhost:8000/pulse/graph | jq
```

**Step 3: Verify frontend**

Open http://localhost:8081 in browser
- [ ] Cards view shows topics with scores
- [ ] Graph view shows connected nodes
- [ ] Toggle switches views correctly

**Step 4: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests PASS

**Step 5: Final commit and push**

```bash
git add .
git commit -m "feat: complete POC integration"
git push origin master
```

---

## Summary

| Phase | Tasks | Key Deliverables |
|-------|-------|------------------|
| 1. Backend | 1-5 | DB models, Pydantic schemas, HN ingestion, graph analysis, FastAPI app |
| 2. Frontend | 6-7 | React Native Web app, FlowGraph visualization |
| 3. Integration | 8-10 | Data seeding, Docker, Render config, integration test |

**Total estimated tasks:** 10 major tasks, ~50 bite-sized steps

**Verification commands:**
- `uv run pytest -v` — Run all tests
- `uv run ruff check src tests` — Lint check
- `uv run mypy src tests` — Type check
- `docker-compose up` — Local environment
