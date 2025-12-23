"""Comprehensive tests for pulse API endpoints.

This module tests:
1. HN API failure fallback scenarios
2. Pagination with offset/limit parameters
3. Validation error handling (negative cases)
4. Rank comparison endpoint functionality
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from community_pulse.analysis.graph import TopicGraphData
from community_pulse.api.app import create_app
from community_pulse.services.pulse_compute import (
    ComputedTopic,
    PulseResult,
    SamplePostData,
)


@pytest.fixture
def client() -> TestClient:
    """Create test client for API endpoints."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_computed_topics() -> list[ComputedTopic]:
    """Create mock computed topics for testing."""
    return [
        ComputedTopic(
            slug="ai",
            label="Artificial Intelligence",
            pulse_score=0.85,
            velocity=2.1,
            centrality=0.7,
            mention_count=150,
            unique_authors=45,
            pulse_rank=1,
            mention_rank=1,
            sample_posts=[
                SamplePostData(
                    id="12345",
                    title="GPT-4 Advances",
                    url="https://news.ycombinator.com/item?id=12345",
                    score=500,
                    comment_count=200,
                )
            ],
        ),
        ComputedTopic(
            slug="rust",
            label="Rust Programming",
            pulse_score=0.72,
            velocity=1.8,
            centrality=0.5,
            mention_count=89,
            unique_authors=32,
            pulse_rank=2,
            mention_rank=4,  # Significant difference: 4 - 2 = 2
            sample_posts=[
                SamplePostData(
                    id="12346",
                    title="Rust 1.75 Released",
                    url="https://news.ycombinator.com/item?id=12346",
                    score=300,
                    comment_count=100,
                )
            ],
        ),
        ComputedTopic(
            slug="python",
            label="Python",
            pulse_score=0.65,
            velocity=1.2,
            centrality=0.6,
            mention_count=120,
            unique_authors=55,
            pulse_rank=3,
            mention_rank=2,  # No change - still significant for reverse
            sample_posts=[
                SamplePostData(
                    id="12347",
                    title="Python 3.12 Performance",
                    url="https://news.ycombinator.com/item?id=12347",
                    score=250,
                    comment_count=80,
                )
            ],
        ),
        ComputedTopic(
            slug="javascript",
            label="JavaScript",
            pulse_score=0.58,
            velocity=1.1,
            centrality=0.55,
            mention_count=95,
            unique_authors=40,
            pulse_rank=4,
            mention_rank=3,  # Slight difference: 3 - 4 = -1 (not significant)
            sample_posts=[
                SamplePostData(
                    id="12348",
                    title="Bun 1.0 Released",
                    url="https://news.ycombinator.com/item?id=12348",
                    score=200,
                    comment_count=60,
                )
            ],
        ),
    ]


# =============================================================================
# HN API FAILURE FALLBACK TESTS
# =============================================================================


class TestAPIFailureFallback:
    """Test fallback to mock data when HN API fails."""

    def test_current_pulse_falls_back_to_mock_when_api_fails(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test /pulse/current returns mock data when API fails."""
        # Mock compute_live_pulse to simulate API failure
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: None,
        )

        response = client.get("/pulse/current")

        assert response.status_code == 200
        data = response.json()

        # Should return mock data
        assert data["data_source"] == "mock"
        assert len(data["topics"]) > 0
        assert "snapshot_id" in data
        assert "captured_at" in data

        # Mock topics should have expected structure
        topic = data["topics"][0]
        assert "id" in topic
        assert "slug" in topic
        assert "label" in topic
        assert "pulse_score" in topic

    def test_current_pulse_returns_live_data_when_api_succeeds(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/current returns live data when compute_live_pulse succeeds."""
        # Mock compute_live_pulse to return data
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/current")

        assert response.status_code == 200
        data = response.json()

        # Should return live data
        assert data["data_source"] == "live"
        assert len(data["topics"]) == 4
        assert data["topics"][0]["slug"] == "ai"
        assert data["topics"][0]["pulse_score"] == 0.85

    def test_graph_falls_back_to_mock_when_api_fails(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test /pulse/graph returns mock data when API fails."""
        # Mock compute_live_pulse_with_edges to simulate API failure
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse_with_edges",
            lambda num_stories: PulseResult(topics=[], edges=[]),
        )

        response = client.get("/pulse/graph")

        assert response.status_code == 200
        data = response.json()

        # Should return mock data
        assert data["data_source"] == "mock"
        assert len(data["nodes"]) > 0
        assert "edges" in data
        assert "clusters" in data
        assert "captured_at" in data

    def test_graph_returns_live_data_when_api_succeeds(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/graph returns live data when API succeeds."""
        # Create mock edges for the topics
        mock_edges = [
            TopicGraphData(
                topic_a="ai", topic_b="python", shared_posts=5, shared_authors=3
            ),
            TopicGraphData(
                topic_a="ai", topic_b="rust", shared_posts=3, shared_authors=2
            ),
        ]

        # Mock compute_live_pulse_with_edges to return data
        mock_result = PulseResult(topics=mock_computed_topics, edges=mock_edges)
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse_with_edges",
            lambda num_stories: mock_result,
        )

        response = client.get("/pulse/graph")

        assert response.status_code == 200
        data = response.json()

        # Should return live data
        assert data["data_source"] == "live"
        assert len(data["nodes"]) == 4
        assert data["nodes"][0]["slug"] == "ai"
        # Should have edges with real co-occurrence data
        assert len(data["edges"]) == 2
        # Verify edges use actual shared_posts count
        assert data["edges"][0]["shared_posts"] == 5
        assert data["edges"][0]["weight"] == 5.0

    def test_live_pulse_returns_empty_when_api_fails(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test /pulse/live returns empty response when API fails."""
        # Mock compute_live_pulse to simulate API failure
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: None,
        )

        response = client.get("/pulse/live")

        assert response.status_code == 200
        data = response.json()

        # Should return empty topics list with appropriate message
        assert data["topics"] == []
        assert data["stories_analyzed"] == 0
        assert data["total_count"] == 0
        assert data["data_source"] == "live"
        assert "No topics found" in data["hypothesis_evidence"]


# =============================================================================
# PAGINATION TESTS
# =============================================================================


class TestPagination:
    """Test pagination with offset and limit parameters."""

    def test_current_pulse_pagination_with_limit(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/current respects limit parameter."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/current?limit=2")

        assert response.status_code == 200
        data = response.json()

        # Should only return 2 topics
        assert len(data["topics"]) == 2
        assert data["total_count"] == 4  # Total available

    def test_current_pulse_pagination_with_offset(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/current respects offset parameter."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/current?offset=1")

        assert response.status_code == 200
        data = response.json()

        # Should skip first topic
        assert len(data["topics"]) == 3
        assert data["topics"][0]["slug"] == "rust"  # Second topic
        assert data["total_count"] == 4

    def test_current_pulse_pagination_with_offset_and_limit(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/current with both offset and limit."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/current?offset=1&limit=1")

        assert response.status_code == 200
        data = response.json()

        # Should return only the second topic
        assert len(data["topics"]) == 1
        assert data["topics"][0]["slug"] == "rust"
        assert data["total_count"] == 4

    def test_current_pulse_offset_exceeds_total_count(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/current when offset exceeds total topics."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/current?offset=10")

        assert response.status_code == 200
        data = response.json()

        # Should return empty topics list
        assert len(data["topics"]) == 0
        assert data["total_count"] == 4

    def test_live_pulse_pagination_with_limit(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/live respects limit parameter."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/live?limit=2")

        assert response.status_code == 200
        data = response.json()

        # Should only return 2 topics
        assert len(data["topics"]) == 2
        assert data["total_count"] == 4

    def test_live_pulse_pagination_with_offset(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/live respects offset parameter."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/live?offset=1")

        assert response.status_code == 200
        data = response.json()

        # Should skip first topic
        assert len(data["topics"]) == 3
        assert data["topics"][0]["slug"] == "rust"
        assert data["total_count"] == 4

    def test_live_pulse_offset_exceeds_total_count(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/live when offset exceeds total topics."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/live?offset=10")

        assert response.status_code == 200
        data = response.json()

        # Should return empty topics list
        assert len(data["topics"]) == 0
        assert data["total_count"] == 4


# =============================================================================
# VALIDATION ERROR TESTS
# =============================================================================


class TestValidationErrors:
    """Test validation error handling for invalid parameters."""

    def test_current_pulse_negative_min_score(self, client: TestClient) -> None:
        """Test /pulse/current rejects negative min_score."""
        response = client.get("/pulse/current?min_score=-0.5")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_current_pulse_min_score_above_one(self, client: TestClient) -> None:
        """Test /pulse/current rejects min_score > 1.0."""
        response = client.get("/pulse/current?min_score=1.5")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_current_pulse_limit_too_large(self, client: TestClient) -> None:
        """Test /pulse/current rejects limit > 100."""
        response = client.get("/pulse/current?limit=500")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_current_pulse_negative_offset(self, client: TestClient) -> None:
        """Test /pulse/current rejects negative offset."""
        response = client.get("/pulse/current?offset=-1")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_live_pulse_num_stories_too_large(self, client: TestClient) -> None:
        """Test /pulse/live rejects num_stories > 200."""
        response = client.get("/pulse/live?num_stories=500")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_live_pulse_limit_too_large(self, client: TestClient) -> None:
        """Test /pulse/live rejects limit > 100."""
        response = client.get("/pulse/live?limit=200")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_live_pulse_negative_offset(self, client: TestClient) -> None:
        """Test /pulse/live rejects negative offset."""
        response = client.get("/pulse/live?offset=-1")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_compare_rankings_num_stories_too_large(self, client: TestClient) -> None:
        """Test /pulse/live/compare rejects num_stories > 200."""
        response = client.get("/pulse/live/compare?num_stories=500")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# =============================================================================
# RANK COMPARISON ENDPOINT TESTS
# =============================================================================


class TestRankComparison:
    """Test rank comparison endpoint functionality."""

    def test_compare_rankings_returns_valid_comparison(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/live/compare returns valid comparison data."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/live/compare")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "pulse_ranking" in data
        assert "mention_ranking" in data
        assert "differences" in data
        assert "hypothesis_supported" in data
        assert "explanation" in data

        # Verify rankings are lists of topic slugs
        assert isinstance(data["pulse_ranking"], list)
        assert isinstance(data["mention_ranking"], list)
        assert len(data["pulse_ranking"]) == 4
        assert len(data["mention_ranking"]) == 4

        # Verify pulse ranking order (by pulse_score)
        assert data["pulse_ranking"] == ["ai", "rust", "python", "javascript"]

        # Verify mention ranking order (by mention_count)
        # ai=150, python=120, javascript=95, rust=89
        assert data["mention_ranking"] == ["ai", "python", "javascript", "rust"]

    def test_compare_rankings_detects_differences(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/live/compare detects ranking differences."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/live/compare")

        assert response.status_code == 200
        data = response.json()

        # Rankings should differ
        assert data["pulse_ranking"] != data["mention_ranking"]
        assert data["hypothesis_supported"] is True

        # Should have differences for rust (pulse_rank=2, mention_rank=4, diff=2)
        # and python (pulse_rank=3, mention_rank=2, diff=-1 - not significant)
        # Actually rust has diff=2 which is >= SIGNIFICANT_RANK_DIFF
        assert len(data["differences"]) >= 1

        # Verify difference structure
        diff = data["differences"][0]
        assert "topic" in diff
        assert "pulse_rank" in diff
        assert "mention_rank" in diff
        assert "change" in diff
        assert "direction" in diff
        assert "reasons" in diff

    def test_compare_rankings_with_identical_rankings(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test /pulse/live/compare when rankings match."""
        # Create topics with identical pulse and mention rankings
        identical_topics = [
            ComputedTopic(
                slug="topic1",
                label="Topic 1",
                pulse_score=0.9,
                velocity=1.0,
                centrality=0.5,
                mention_count=100,
                unique_authors=50,
                pulse_rank=1,
                mention_rank=1,
                sample_posts=[],
            ),
            ComputedTopic(
                slug="topic2",
                label="Topic 2",
                pulse_score=0.5,
                velocity=1.0,
                centrality=0.3,
                mention_count=50,
                unique_authors=25,
                pulse_rank=2,
                mention_rank=2,
                sample_posts=[],
            ),
        ]

        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: identical_topics,
        )

        response = client.get("/pulse/live/compare")

        assert response.status_code == 200
        data = response.json()

        # Rankings should be identical
        assert data["pulse_ranking"] == data["mention_ranking"]
        assert data["hypothesis_supported"] is False
        assert "identical" in data["explanation"].lower()

    def test_compare_rankings_returns_empty_when_no_data(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test /pulse/live/compare when no topics available."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: None,
        )

        response = client.get("/pulse/live/compare")

        assert response.status_code == 200
        data = response.json()

        # Should return empty rankings
        assert data["pulse_ranking"] == []
        assert data["mention_ranking"] == []
        assert data["differences"] == []
        assert data["hypothesis_supported"] is False
        assert "No topics found" in data["explanation"]


# =============================================================================
# ADDITIONAL EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_current_pulse_with_min_score_filters_topics(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/current filters topics by min_score."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/current?min_score=0.7")

        assert response.status_code == 200
        data = response.json()

        # Should only return topics with pulse_score >= 0.7
        assert len(data["topics"]) == 2  # ai (0.85) and rust (0.72)
        assert all(t["pulse_score"] >= 0.7 for t in data["topics"])

    def test_graph_with_min_edge_weight_filters_edges(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/graph filters edges by min_edge_weight."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/graph?min_edge_weight=5")

        assert response.status_code == 200
        data = response.json()

        # All edges should meet weight threshold
        for edge in data["edges"]:
            assert edge["weight"] >= 5.0

    def test_live_pulse_with_custom_num_stories(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/live with custom num_stories parameter."""
        # Track num_stories parameter
        called_with: dict[str, Any] = {}

        def mock_compute(num_stories: int) -> list[ComputedTopic]:
            called_with["num_stories"] = num_stories
            return mock_computed_topics

        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse", mock_compute
        )

        response = client.get("/pulse/live?num_stories=50")

        assert response.status_code == 200
        assert called_with["num_stories"] == 50

    def test_live_pulse_hypothesis_evidence_with_rank_differences(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/live generates hypothesis evidence for rank differences."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/live")

        assert response.status_code == 200
        data = response.json()

        # Should have hypothesis evidence explaining rank differences
        assert "hypothesis_evidence" in data
        assert len(data["hypothesis_evidence"]) > 0

        # With mock data, rust has significant rank difference (mention=4, pulse=2)
        # Evidence should mention boosted topics
        evidence = data["hypothesis_evidence"]
        assert "boosted" in evidence.lower() or "pulse" in evidence.lower()

    def test_current_pulse_timestamp_format(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/current returns valid ISO timestamp."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/current")

        assert response.status_code == 200
        data = response.json()

        # Verify timestamp is valid ISO format
        timestamp = data["captured_at"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_graph_limits_edges_to_fifteen(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        mock_computed_topics: list[ComputedTopic],
    ) -> None:
        """Test /pulse/graph limits edges to 15 for visualization."""
        monkeypatch.setattr(
            "community_pulse.api.routes.pulse.compute_live_pulse",
            lambda num_stories: mock_computed_topics,
        )

        response = client.get("/pulse/graph")

        assert response.status_code == 200
        data = response.json()

        # Should limit edges to 15
        assert len(data["edges"]) <= 15
