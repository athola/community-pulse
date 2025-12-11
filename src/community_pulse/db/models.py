"""SQLAlchemy models for Community Pulse.

FUTURE EXPANSION: Data Persistence Schema
------------------------------------------
These models define the database schema for storing community data, but are NOT
currently used in the POC implementation. The POC operates entirely in-memory,
fetching live data from Hacker News API without persistence.

Schema Design Philosophy:
    1. Normalized: Separate tables for Authors, Posts, Topics with proper foreign keys
    2. Flexible: JSON metadata columns for platform-specific attributes
    3. Temporal: Timestamps for historical analysis and trend tracking
    4. Indexed: Strategic indexes on common query patterns (time-based, author-based)
    5. Relational: PostTopic junction table supports many-to-many topic assignments

Model Overview:

    Author:
        Represents community members who create content. Tracks external_id
        (e.g., HN username) separately from internal UUID for data integrity
        and multi-platform support.

    Post:
        Unified model for both stories and comments (distinguished by parent_id).
        Self-referential relationship supports comment threads. Nullable fields support
        various content types (stories have titles/urls, comments have content).

    Topic:
        Extracted themes/subjects from content analysis. Uses slug for URL-friendly
        identifiers and label for display. Will be populated by NLP/topic modeling.

    PostTopic:
        Many-to-many association with relevance scoring. Allows posts to belong to
        multiple topics with weighted relationships.

When This Activates:
    These models become active when implementing caching, historical analysis, or
    offline capabilities. The schema is PostgreSQL-optimized but portable to other
    SQL databases with minor adjustments.

Migration Path:
    When ready to persist data, implement Alembic migrations and create repository
    classes in data_sources/ that use these models via db/connection.py sessions.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {dict[str, Any]: JSON}


class Author(Base):
    """Author of posts in the community."""

    __tablename__ = "authors"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=lambda: {}, nullable=False
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
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
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
        "metadata", JSON, default=lambda: {}, nullable=False
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
        UUID(as_uuid=False),
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relevance: Mapped[float] = mapped_column(Float, default=1.0)

    post: Mapped[Post] = relationship("Post", back_populates="post_topics")
    topic: Mapped[Topic] = relationship("Topic", back_populates="post_topics")

    __table_args__ = (Index("idx_post_topics_topic", "topic_id"),)
