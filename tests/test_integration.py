"""Full-stack integration tests for Community Pulse POC.

This test module verifies that all components work together:
1. HN data loading
2. Topic extraction
3. Graph building
4. Pulse score computation
5. API endpoints
"""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
from community_pulse.api.app import create_app
from community_pulse.ingest.hn_loader import load_hn_items, parse_hn_item
from community_pulse.ingest.topic_extractor import extract_topics


class TestHNDataLoading:
    """Test HN data loading pipeline."""

    def test_parse_hn_item(self) -> None:
        """Test parsing HN item from raw data."""
        raw_data = {
            "id": 12345,
            "type": "story",
            "by": "testuser",
            "time": 1704067200,
            "title": "Building AI with Rust",
            "url": "https://example.com",
            "score": 42,
            "kids": [1, 2, 3],
        }

        item = parse_hn_item(raw_data)

        assert item is not None
        assert item.id == 12345
        assert item.type == "story"
        assert item.by == "testuser"
        assert item.title == "Building AI with Rust"
        assert item.score == 42
        assert len(item.kids) == 3

    def test_load_hn_items_from_file(self) -> None:
        """Test loading HN items from JSON file."""
        test_data = [
            {
                "id": 1,
                "type": "story",
                "by": "user1",
                "time": 1704067200,
                "title": "Python for Machine Learning",
                "score": 100,
            },
            {
                "id": 2,
                "type": "comment",
                "by": "user2",
                "time": 1704067300,
                "text": "Great insights on AI and databases!",
                "parent": 1,
            },
            {"id": 3, "deleted": True},  # Should be filtered out
            {"id": 4, "type": "job"},  # Should be filtered out
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            items = load_hn_items(temp_path)

            # Should only load story and comment (2 items)
            assert len(items) == 2
            assert items[0].id == 1
            assert items[0].type == "story"
            assert items[1].id == 2
            assert items[1].type == "comment"
        finally:
            temp_path.unlink()


class TestTopicExtraction:
    """Test topic extraction functionality."""

    def test_extract_ai_topic(self) -> None:
        """Test extracting AI/ML topics."""
        topics = extract_topics(
            "This is a great machine learning model using GPT", "AI Research"
        )

        slugs = [t[0] for t in topics]
        assert "ai" in slugs

        # Title match should have higher relevance
        ai_topic = next(t for t in topics if t[0] == "ai")
        assert ai_topic[1] == 1.0  # Title match

    def test_extract_multiple_topics(self) -> None:
        """Test extracting multiple topics from text."""
        topics = extract_topics(
            "Built with Python FastAPI, deployed on AWS with PostgreSQL",
            "My Cloud Startup",
        )

        slugs = [t[0] for t in topics]
        assert "python" in slugs
        assert "cloud" in slugs
        assert "database" in slugs
        assert "startup" in slugs

        # Should have at least 4 topics
        assert len(topics) >= 4

    def test_extract_topics_empty_input(self) -> None:
        """Test handling empty input."""
        topics = extract_topics(None, None)
        assert topics == []

    def test_topic_relevance_scoring(self) -> None:
        """Test relevance scoring (title vs text)."""
        # Title match
        topics_title = extract_topics("some content", "Rust Programming")
        rust_title = next((t for t in topics_title if t[0] == "rust"), None)
        assert rust_title is not None
        assert rust_title[1] == 1.0

        # Text match only
        topics_text = extract_topics("Using rust for systems programming", None)
        rust_text = next((t for t in topics_text if t[0] == "rust"), None)
        assert rust_text is not None
        assert rust_text[1] == 0.8


class TestGraphBuilding:
    """Test graph analysis pipeline."""

    def test_build_empty_graph(self) -> None:
        """Test building graph with no data."""
        graph, indices = build_topic_graph([])

        assert graph.num_nodes() == 0
        assert graph.num_edges() == 0
        assert len(indices) == 0

    def test_build_simple_graph(self) -> None:
        """Test building graph with co-occurrence data."""
        data = [
            TopicGraphData("ai", "python", shared_posts=10, shared_authors=5),
            TopicGraphData("ai", "rust", shared_posts=5, shared_authors=3),
            TopicGraphData("python", "database", shared_posts=8, shared_authors=4),
        ]

        graph, indices = build_topic_graph(data)

        # 4 unique topics
        assert graph.num_nodes() == 4
        assert "ai" in indices
        assert "python" in indices
        assert "rust" in indices
        assert "database" in indices

        # 3 edges
        assert graph.num_edges() == 3

    def test_compute_centrality_measures(self) -> None:
        """Test centrality computation on graph."""
        data = [
            TopicGraphData("ai", "python", shared_posts=10, shared_authors=5),
            TopicGraphData("ai", "rust", shared_posts=5, shared_authors=3),
            TopicGraphData("python", "database", shared_posts=8, shared_authors=4),
        ]

        graph, indices = build_topic_graph(data)
        centrality = compute_centrality(graph)

        # All nodes should have centrality metrics
        for node_idx in indices.values():
            assert node_idx in centrality
            assert "betweenness" in centrality[node_idx]
            assert "eigenvector" in centrality[node_idx]
            assert "pagerank" in centrality[node_idx]

        # AI should have high centrality (connected to 2 others)
        ai_idx = indices["ai"]
        ai_centrality = centrality[ai_idx]
        assert ai_centrality["betweenness"] >= 0
        assert ai_centrality["eigenvector"] >= 0

    def test_detect_clusters(self) -> None:
        """Test cluster detection."""
        # Create disconnected graph
        data = [
            TopicGraphData("ai", "python", shared_posts=10, shared_authors=5),
            TopicGraphData("rust", "golang", shared_posts=5, shared_authors=3),
        ]

        graph, _ = build_topic_graph(data)
        clusters = detect_clusters(graph)

        # Should have 2 clusters (disconnected components)
        assert len(clusters) == 2
        assert all(len(cluster) == 2 for cluster in clusters)


class TestVelocityComputation:
    """Test velocity and pulse score computation."""

    def test_compute_velocity_normal(self) -> None:
        """Test velocity computation with normal baseline."""
        data = VelocityData(
            topic_id="ai",
            current_mentions=30,
            baseline_mentions=10.0,
            unique_authors=15,
        )

        velocity = compute_velocity(data)
        assert velocity == 3.0  # 30 / 10

    def test_compute_velocity_no_baseline(self) -> None:
        """Test velocity with no baseline (emerging topic)."""
        data = VelocityData(
            topic_id="new-tech",
            current_mentions=5,
            baseline_mentions=0.0,
            unique_authors=3,
        )

        velocity = compute_velocity(data)
        assert velocity == 2.0  # Emerging topic default

    def test_compute_velocity_declining(self) -> None:
        """Test velocity for declining topic."""
        data = VelocityData(
            topic_id="old-tech",
            current_mentions=5,
            baseline_mentions=20.0,
            unique_authors=2,
        )

        velocity = compute_velocity(data)
        assert velocity == 0.25  # 5 / 20

    def test_compute_pulse_score(self) -> None:
        """Test pulse score computation."""
        score = compute_pulse_score(
            velocity=2.0,
            eigenvector_centrality=0.6,
            betweenness_centrality=0.4,
            unique_authors=50,
            max_authors=100,
        )

        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0

        # Should be relatively high (all metrics are good)
        assert score > 0.4

    def test_pulse_score_bounds(self) -> None:
        """Test pulse score stays within bounds."""
        # Maximum values
        score_max = compute_pulse_score(
            velocity=10.0,  # Will be capped at 3.0
            eigenvector_centrality=1.0,
            betweenness_centrality=1.0,
            unique_authors=200,  # Will be capped
            max_authors=100,
        )
        assert score_max <= 1.0

        # Minimum values
        score_min = compute_pulse_score(
            velocity=0.0,
            eigenvector_centrality=0.0,
            betweenness_centrality=0.0,
            unique_authors=0,
        )
        assert score_min >= 0.0


class TestAPIEndpoints:
    """Test API endpoints with integration scenarios."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_health_endpoint(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_current_pulse_endpoint(self, client: TestClient) -> None:
        """Test current pulse endpoint returns valid data."""
        response = client.get("/pulse/current")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "topics" in data
        assert "snapshot_id" in data
        assert "captured_at" in data
        assert "clusters" in data

        # Verify topics have required fields
        if data["topics"]:
            topic = data["topics"][0]
            assert "id" in topic
            assert "slug" in topic
            assert "label" in topic
            assert "pulse_score" in topic
            assert "velocity" in topic
            assert "centrality" in topic

            # Validate pulse score bounds
            assert 0.0 <= topic["pulse_score"] <= 1.0

    def test_current_pulse_with_filters(self, client: TestClient) -> None:
        """Test pulse endpoint with query parameters."""
        response = client.get("/pulse/current?limit=3&min_score=0.5")

        assert response.status_code == 200
        data = response.json()

        # Should respect limit
        assert len(data["topics"]) <= 3

        # All topics should meet min_score
        for topic in data["topics"]:
            assert topic["pulse_score"] >= 0.5

    def test_graph_endpoint(self, client: TestClient) -> None:
        """Test graph endpoint returns valid structure."""
        response = client.get("/pulse/graph")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "nodes" in data
        assert "edges" in data
        assert "clusters" in data
        assert "captured_at" in data

        # Verify nodes have required fields
        if data["nodes"]:
            node = data["nodes"][0]
            assert "id" in node
            assert "slug" in node
            assert "label" in node
            assert "pulse_score" in node

        # Verify edges have required fields
        if data["edges"]:
            edge = data["edges"][0]
            assert "source" in edge
            assert "target" in edge
            assert "weight" in edge
            assert "shared_posts" in edge

    def test_graph_with_edge_filter(self, client: TestClient) -> None:
        """Test graph endpoint with edge weight filter."""
        response = client.get("/pulse/graph?min_edge_weight=3")

        assert response.status_code == 200
        data = response.json()

        # All edges should meet weight threshold
        for edge in data["edges"]:
            assert edge["weight"] >= 3.0


class TestFullStackIntegration:
    """End-to-end integration tests."""

    def test_complete_pipeline(self) -> None:
        """Test complete data flow from HN data to pulse scores."""
        # Step 1: Create sample HN data
        test_data = [
            {
                "id": 1,
                "type": "story",
                "by": "user1",
                "time": 1704067200,
                "title": "Machine Learning with Rust",
                "score": 150,
            },
            {
                "id": 2,
                "type": "story",
                "by": "user2",
                "time": 1704067300,
                "title": "Python FastAPI Tutorial",
                "score": 100,
            },
            {
                "id": 3,
                "type": "comment",
                "by": "user3",
                "time": 1704067400,
                "text": "Great insights on AI and machine learning!",
                "parent": 1,
            },
        ]

        # Step 2: Load and parse HN items
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            items = load_hn_items(temp_path)
            assert len(items) == 3

            # Step 3: Extract topics
            topics_found = set()
            for item in items:
                topics = extract_topics(item.text, item.title)
                for slug, _ in topics:
                    topics_found.add(slug)

            # Should find multiple topics
            assert (
                "ai" in topics_found
                or "rust" in topics_found
                or "python" in topics_found
            )

            # Step 4: Build graph from co-occurrences
            # Simulate co-occurrence data
            graph_data = [
                TopicGraphData("ai", "rust", shared_posts=1, shared_authors=1),
                TopicGraphData("ai", "python", shared_posts=1, shared_authors=1),
            ]

            graph, indices = build_topic_graph(graph_data)
            assert graph.num_nodes() > 0
            assert graph.num_edges() > 0

            # Step 5: Compute centrality
            centrality = compute_centrality(graph)
            assert len(centrality) > 0

            # Step 6: Compute pulse scores
            for topic_id in topics_found:
                if topic_id in indices:
                    node_idx = indices[topic_id]
                    metrics = centrality[node_idx]

                    velocity_data = VelocityData(
                        topic_id=topic_id,
                        current_mentions=10,
                        baseline_mentions=5.0,
                        unique_authors=3,
                    )
                    velocity = compute_velocity(velocity_data)

                    pulse_score = compute_pulse_score(
                        velocity=velocity,
                        eigenvector_centrality=metrics["eigenvector"],
                        betweenness_centrality=metrics["betweenness"],
                        unique_authors=velocity_data.unique_authors,
                    )

                    # Validate final score
                    assert 0.0 <= pulse_score <= 1.0

        finally:
            temp_path.unlink()

    def test_api_serves_consistent_data(self) -> None:
        """Test that API serves consistent data across calls."""
        app = create_app()
        client = TestClient(app)

        # Make multiple requests
        response1 = client.get("/pulse/current")
        response2 = client.get("/pulse/current")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Should have same topic structure (mock data)
        assert len(data1["topics"]) == len(data2["topics"])

        # Snapshot IDs should be different (new snapshot each time)
        assert data1["snapshot_id"] != data2["snapshot_id"]
