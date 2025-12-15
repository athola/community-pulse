"""Tests for graph analysis."""

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
    assert "degree_centrality" in centrality[ai_idx]


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
