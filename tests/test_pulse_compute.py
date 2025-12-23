"""Tests for pulse_compute service edge cases.

These tests cover full pipeline scenarios that were identified as stubs in
test_mathematical_edge_cases.py and need implementation in the services layer.
"""

import time
from datetime import datetime

import pytest

from community_pulse.plugins.base import RawPost
from community_pulse.services.pulse_compute import (
    PulseComputeService,
    PulseResult,
)


class MockPlugin:
    """Mock data source plugin for testing."""

    name = "mock"

    def __init__(self, posts: list[RawPost] | None = None):
        self._posts = posts if posts is not None else []

    def fetch_posts(self, limit: int = 100) -> list[RawPost]:
        """Return configured posts up to limit."""
        return self._posts[:limit]

    def get_post_url(self, post_id: str) -> str:
        """Generate mock URL."""
        return f"https://mock.example.com/{post_id}"


class TestPulseComputeEdgeCases:
    """Edge case tests for PulseComputer service."""

    def test_empty_posts_returns_empty_result(self):
        """Empty posts list should return empty PulseResult without crashing.

        GIVEN a data source that returns no posts
        WHEN the pulse computation is run
        THEN an empty PulseResult is returned without errors
        """
        plugin = MockPlugin(posts=[])
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        assert isinstance(result, PulseResult)
        assert result.topics == []
        assert result.edges == []

    def test_zero_max_authors_handled(self):
        """All posts from single author should not cause division by zero.

        GIVEN posts where all are from the same author
        WHEN the pulse computation is run
        THEN valid pulse scores are computed without division errors
        """
        posts = [
            RawPost(
                id=f"post-{i}",
                title=f"AI and machine learning post {i}",
                content="Deep learning neural network transformer",
                author="single_author",  # All posts from same author
                url=f"https://example.com/{i}",
                score=100 + i,
                comment_count=10,
                posted_at=datetime.now(),
            )
            for i in range(5)
        ]
        plugin = MockPlugin(posts=posts)
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        # Should compute without division by zero errors
        assert len(result.topics) > 0
        for topic in result.topics:
            assert topic.pulse_score >= 0
            assert topic.unique_authors == 1  # All from single author

    def test_single_topic_returns_valid_pulse(self):
        """Single topic detected should return valid pulse score.

        GIVEN posts that only mention a single topic
        WHEN the pulse computation is run
        THEN a valid pulse score is returned (centrality = 0 for isolated node)
        """
        posts = [
            RawPost(
                id=f"rust-{i}",
                title=f"Rust programming language post {i}",
                content="Rust memory safety borrow checker",
                author=f"author_{i}",
                url=f"https://example.com/rust-{i}",
                score=50 + i,
                comment_count=5,
                posted_at=datetime.now(),
            )
            for i in range(3)
        ]
        plugin = MockPlugin(posts=posts)
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        # Should return exactly one topic with no edges
        assert len(result.topics) == 1
        assert len(result.edges) == 0  # No co-occurrence with single topic
        topic = result.topics[0]
        assert topic.slug == "rust"
        assert topic.pulse_score >= 0
        # Single node has no edges, so centrality should be 0
        assert topic.centrality == 0.0

    @pytest.mark.slow
    def test_large_post_set_performance(self):
        """Large post set (1000+) should complete in reasonable time.

        GIVEN a large set of 1000 posts with varied topics
        WHEN the pulse computation is run
        THEN it completes within 5 seconds
        """
        topics = ["ai", "rust", "python", "javascript", "database"]
        posts = [
            RawPost(
                id=f"post-{i}",
                title=f"{topics[i % len(topics)]} post number {i}",
                content=(
                    f"Content about {topics[i % len(topics)]} and "
                    f"{topics[(i + 1) % len(topics)]}"
                ),
                author=f"author_{i % 50}",  # 50 unique authors
                url=f"https://example.com/{i}",
                score=i % 100,
                comment_count=i % 20,
                posted_at=datetime.now(),
            )
            for i in range(1000)
        ]
        plugin = MockPlugin(posts=posts)
        service = PulseComputeService(plugin=plugin, num_posts=1000)

        start = time.perf_counter()
        result = service.compute_pulse(save_snapshot=False)
        elapsed = time.perf_counter() - start

        assert len(result.topics) > 0
        assert elapsed < 5.0, f"Performance regression: took {elapsed:.2f}s (limit: 5s)"


class TestCooccurrenceEdges:
    """Tests for true co-occurrence edge computation."""

    def test_cooccurrence_edges_from_shared_posts(self):
        """Posts mentioning multiple topics create co-occurrence edges.

        GIVEN posts that mention multiple topics together
        WHEN the pulse computation is run
        THEN edges are created with accurate shared_posts counts
        """
        # Create 3 posts: 2 mention both AI and Python, 1 mentions just Rust
        posts = [
            RawPost(
                id="post-1",
                title="AI and Python machine learning",
                content="Deep learning with Python libraries",
                author="author_1",
                url="https://example.com/1",
                score=100,
                comment_count=10,
                posted_at=datetime.now(),
            ),
            RawPost(
                id="post-2",
                title="Python for AI applications",
                content="Building AI models in Python",
                author="author_2",
                url="https://example.com/2",
                score=80,
                comment_count=5,
                posted_at=datetime.now(),
            ),
            RawPost(
                id="post-3",
                title="Rust programming language",
                content="Memory safety in Rust",
                author="author_3",
                url="https://example.com/3",
                score=60,
                comment_count=3,
                posted_at=datetime.now(),
            ),
        ]
        plugin = MockPlugin(posts=posts)
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        # Should have 3 topics: ai, python, rust
        assert len(result.topics) == 3
        topic_slugs = {t.slug for t in result.topics}
        assert topic_slugs == {"ai", "python", "rust"}

        # Should have exactly 1 edge: ai-python (from 2 shared posts)
        assert len(result.edges) == 1
        edge = result.edges[0]
        assert {edge.topic_a, edge.topic_b} == {"ai", "python"}
        assert edge.shared_posts == 2  # Two posts mention both AI and Python

    def test_no_edges_when_topics_dont_cooccur(self):
        """Topics that never appear together have no edges.

        GIVEN posts where each topic appears independently
        WHEN the pulse computation is run
        THEN no co-occurrence edges are created
        """
        posts = [
            RawPost(
                id="ai-post",
                title="AI and machine learning",
                content="Neural networks",
                author="author_1",
                url="https://example.com/1",
                score=100,
                comment_count=10,
                posted_at=datetime.now(),
            ),
            RawPost(
                id="rust-post",
                title="Rust programming",
                content="Memory safety",
                author="author_2",
                url="https://example.com/2",
                score=80,
                comment_count=5,
                posted_at=datetime.now(),
            ),
        ]
        plugin = MockPlugin(posts=posts)
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        assert len(result.topics) == 2
        assert len(result.edges) == 0  # No shared posts = no edges

    def test_shared_authors_tracked_in_edges(self):
        """Edge data includes shared author count.

        GIVEN posts mentioning multiple topics from same author
        WHEN the pulse computation is run
        THEN edges track shared author counts
        """
        # Same author posts about both AI and Python
        posts = [
            RawPost(
                id="post-1",
                title="AI with Python",
                content="Building ML models",
                author="shared_author",
                url="https://example.com/1",
                score=100,
                comment_count=10,
                posted_at=datetime.now(),
            ),
            RawPost(
                id="post-2",
                title="More AI Python content",
                content="Deep learning frameworks",
                author="shared_author",
                url="https://example.com/2",
                score=80,
                comment_count=5,
                posted_at=datetime.now(),
            ),
        ]
        plugin = MockPlugin(posts=posts)
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        assert len(result.edges) == 1
        edge = result.edges[0]
        assert edge.shared_posts == 2
        assert edge.shared_authors == 1  # Same author for both topics


class TestNoTopicsExtractedEdgeCase:
    """Tests for posts that don't match any known topic patterns."""

    def test_posts_without_recognized_topics_returns_empty_result(self):
        """Posts containing no recognized topic keywords return empty result.

        GIVEN posts that contain generic content without topic keywords
        WHEN the pulse computation is run
        THEN an empty PulseResult is returned without errors
        """
        posts = [
            RawPost(
                id="generic-1",
                title="Just a random post about nothing specific",
                content="Some generic content that doesn't match topics",
                author="author_1",
                url="https://example.com/1",
                score=100,
                comment_count=10,
                posted_at=datetime.now(),
            ),
            RawPost(
                id="generic-2",
                title="Another post with no topic keywords",
                content="More content without matching any patterns",
                author="author_2",
                url="https://example.com/2",
                score=80,
                comment_count=5,
                posted_at=datetime.now(),
            ),
        ]
        plugin = MockPlugin(posts=posts)
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        # Should return empty result when no topics extracted
        assert isinstance(result, PulseResult)
        assert result.topics == []
        assert result.edges == []
