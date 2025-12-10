"""SQLAlchemy models for Community Pulse."""

from datetime import datetime
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
        DateTime(timezone=True), default=datetime.utcnow
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
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
        "metadata", JSON, default=dict, nullable=False
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
