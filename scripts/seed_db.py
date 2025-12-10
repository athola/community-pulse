#!/usr/bin/env python3
"""Seed database with HN data."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from community_pulse.db.models import Author, Base, Post, PostTopic, Topic
from community_pulse.ingest.hn_loader import load_hn_items
from community_pulse.ingest.topic_extractor import extract_topics

load_dotenv()


def get_or_create_author(session: Session, external_id: str, handle: str) -> Author:
    """Get existing author or create new one."""
    author = session.query(Author).filter_by(external_id=external_id).first()
    if not author:
        author = Author(external_id=external_id, handle=handle)
        session.add(author)
        session.flush()
    return author


def get_or_create_topic(session: Session, slug: str) -> Topic:
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
            existing = session.query(Post).filter_by(external_id=str(item.id)).first()
            if existing:
                external_to_uuid[item.id] = existing.id
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
        sys.exit(1)

    seed_database(data_path)
