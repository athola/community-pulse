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
        data_source="live",
    )
    assert len(response.nodes) == 2
    assert len(response.edges) == 1
    assert response.data_source == "live"


def test_pulse_response() -> None:
    """Test creating a pulse response."""
    now = datetime.now(timezone.utc)
    response = PulseResponse(
        topics=[TopicNode(id="1", slug="ai", label="AI", pulse_score=0.9)],
        snapshot_id="snap123",
        captured_at=now,
        data_source="live",
        total_count=1,
    )
    assert response.snapshot_id == "snap123"
    assert response.data_source == "live"
    assert response.total_count == 1
