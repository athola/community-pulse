"""Tests for pulse_compute service edge cases.

These tests cover full pipeline scenarios that were identified as stubs in
test_mathematical_edge_cases.py and need implementation in the services layer.
"""

import time
from datetime import datetime

import pytest

from community_pulse.plugins.base import RawPost
from community_pulse.services.pulse_compute import PulseComputeService


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

    def test_empty_posts_returns_empty_list(self):
        """Empty posts list should return empty topic list without crashing.

        GIVEN a data source that returns no posts
        WHEN the pulse computation is run
        THEN an empty list is returned without errors
        """
        plugin = MockPlugin(posts=[])
        service = PulseComputeService(plugin=plugin, num_posts=100)

        result = service.compute_pulse(save_snapshot=False)

        assert result == []

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
        assert len(result) > 0
        for topic in result:
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

        # Should return exactly one topic
        assert len(result) == 1
        topic = result[0]
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
                    f"{topics[(i+1) % len(topics)]}"
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

        assert len(result) > 0
        assert elapsed < 5.0, f"Performance regression: took {elapsed:.2f}s (limit: 5s)"
