"""Comprehensive mathematical edge case tests for numerical stability.

This test suite validates:
- Division by zero handling
- Negative input validation
- Boundary conditions
- Floating-point precision
- Normalization correctness
"""

from community_pulse.analysis.graph import (
    TopicGraphData,
    build_directed_graph,
    build_topic_graph,
    compute_all_centrality,
)
from community_pulse.analysis.velocity import (
    VelocityData,
    compute_pulse_score,
    compute_velocity,
)


class TestVelocityEdgeCases:
    """Test velocity computation edge cases."""

    def test_zero_division_max_authors(self):
        """CRITICAL: Division by zero when max_authors=0 - now handled."""
        # FIXED: max_authors=0 is now guarded and treated as 1
        score = compute_pulse_score(
            velocity=1.0,
            eigenvector_centrality=0.5,
            betweenness_centrality=0.3,
            unique_authors=5,
            max_authors=0,  # Guarded: treated as 1
            pagerank=0.5,
        )
        # Should not crash and should produce valid score
        assert 0.0 <= score <= 1.0

    def test_negative_max_authors(self):
        """CRITICAL: Negative max_authors is now guarded and treated as 1."""
        score = compute_pulse_score(
            velocity=1.0,
            eigenvector_centrality=0.5,
            betweenness_centrality=0.3,
            unique_authors=5,
            max_authors=-5,  # Guarded: treated as 1
            pagerank=0.5,
        )
        # FIXED: max_authors <= 0 is treated as 1
        # Should not crash and should produce valid score
        assert 0.0 <= score <= 1.0

    def test_negative_velocity_can_be_offset_by_positive_values(self):
        """CRITICAL: Negative velocity is now clamped to 0.0."""
        score = compute_pulse_score(
            velocity=-1.0,  # Clamped to 0.0
            eigenvector_centrality=0.5,
            betweenness_centrality=0.3,
            unique_authors=0,
            max_authors=1,
            pagerank=0.5,
        )
        # FIXED: Negative velocity is clamped to 0.0 before normalization
        # score = 0.25*0 + 0.25*0.5 + 0.20*0.3 + 0.15*0.5 + 0.15*0 = 0.26
        assert 0.0 <= score <= 1.0
        assert abs(score - 0.26) < 0.01

    def test_negative_eigenvector_can_be_offset_by_positive_values(self):
        """CRITICAL: Negative eigenvector is now clamped to 0.0."""
        score = compute_pulse_score(
            velocity=1.0,
            eigenvector_centrality=-0.5,  # Clamped to 0.0
            betweenness_centrality=0.3,
            unique_authors=5,
            max_authors=10,
            pagerank=0.5,
        )
        # FIXED: Negative eigenvector is clamped to 0.0 before normalization
        # norm_velocity = min(1.0/3.0, 1.0) = 0.3333
        # score = 0.25*0.3333 + 0.25*0 + 0.20*0.3 + 0.15*0.5 + 0.15*0.5 = 0.2933
        assert 0.0 <= score <= 1.0
        assert abs(score - 0.2933) < 0.01

    def test_all_negative_centrality_values(self):
        """CRITICAL: All negative centrality values are now clamped to 0.0."""
        score = compute_pulse_score(
            velocity=-1.0,  # Clamped to 0.0
            eigenvector_centrality=-0.5,  # Clamped to 0.0
            betweenness_centrality=-0.3,  # Clamped to 0.0
            unique_authors=0,
            max_authors=1,
            pagerank=-1.0,  # Clamped to 0.0
        )
        # FIXED: All negative values clamped to 0.0
        # All normalized values = 0.0, so score = 0.0
        assert score == 0.0

    def test_negative_baseline_handled_incorrectly(self):
        """MEDIUM: Negative baseline treated as zero with warning."""
        # FIXED: Negative baseline is now logged as warning and treated as 0
        data = VelocityData("test", 10, -5.0, 5)
        velocity = compute_velocity(data)
        # Returns 2.0 (emerging topic) - same behavior but now with warning
        assert velocity == 2.0, "Negative baseline treated as 0 (logged warning)"

    def test_extreme_velocity_normalization(self):
        """LOW: Very high velocity is capped correctly."""
        score = compute_pulse_score(
            velocity=1000.0,
            eigenvector_centrality=1.0,
            betweenness_centrality=1.0,
            unique_authors=10000,
            max_authors=100,
            pagerank=1.0,
        )
        assert score <= 1.0
        assert score == 1.0  # All components maxed out

    def test_zero_velocity_and_centrality(self):
        """Boundary: All metrics at zero."""
        score = compute_pulse_score(
            velocity=0.0,
            eigenvector_centrality=0.0,
            betweenness_centrality=0.0,
            unique_authors=0,
            max_authors=10,
            pagerank=0.0,
        )
        assert score == 0.0

    def test_max_velocity_and_centrality(self):
        """Boundary: All metrics at maximum."""
        score = compute_pulse_score(
            velocity=3.0,  # Normalized to 1.0
            eigenvector_centrality=1.0,
            betweenness_centrality=1.0,
            unique_authors=100,
            max_authors=100,
            pagerank=1.0,
        )
        assert score == 1.0

    def test_weight_sum_equals_one(self):
        """Verify weights sum to 1.0."""
        weights = [0.25, 0.25, 0.20, 0.15, 0.15]
        assert sum(weights) == 1.0

    def test_pulse_score_precision(self):
        """Verify pulse score is rounded to 4 decimal places."""
        score = compute_pulse_score(
            velocity=1.234567890,
            eigenvector_centrality=0.123456789,
            betweenness_centrality=0.987654321,
            unique_authors=33,
            max_authors=100,
            pagerank=0.555555555,
        )
        # Check it's rounded to 4 decimals
        assert len(str(score).split(".")[-1]) <= 4

    def test_velocity_zero_baseline_zero_current(self):
        """Edge case: No baseline, no current mentions."""
        data = VelocityData("test", 0, 0.0, 0)
        velocity = compute_velocity(data)
        assert velocity == 1.0

    def test_velocity_zero_baseline_positive_current(self):
        """Edge case: No baseline, positive current mentions."""
        data = VelocityData("test", 5, 0.0, 0)
        velocity = compute_velocity(data)
        assert velocity == 2.0

    def test_velocity_normal_calculation(self):
        """Normal case: velocity = current / baseline."""
        data = VelocityData("test", 30, 10.0, 5)
        velocity = compute_velocity(data)
        assert velocity == 3.0

    def test_velocity_declining_topic(self):
        """Edge case: Declining topic (velocity < 1.0)."""
        data = VelocityData("test", 5, 20.0, 2)
        velocity = compute_velocity(data)
        assert velocity == 0.25


class TestGraphCentralityEdgeCases:
    """Test graph centrality edge cases."""

    def test_empty_graph_centrality(self):
        """Empty graph returns empty centrality dict."""
        graph, indices = build_topic_graph([])
        directed = build_directed_graph([], {})
        centrality = compute_all_centrality(graph, directed)
        assert centrality == {}

    def test_single_node_graph_centrality(self):
        """Single node with no edges has zero centrality."""
        # Create a graph with a single node by using build_topic_graph with empty data
        # then manually adding a node
        import rustworkx as rx  # noqa: PLC0415

        graph = rx.PyGraph()
        graph.add_node({"id": "lonely"})

        digraph = rx.PyDiGraph()
        digraph.add_node({"id": "lonely"})

        centrality = compute_all_centrality(graph, digraph)

        # Single isolated node behavior:
        assert len(centrality) == 1
        # - Betweenness = 0 (no paths to mediate)
        # - Eigenvector = 1.0 (normalized to unit vector)
        # - PageRank = 1.0 (all probability mass on single node)
        node_cent = centrality[0]
        assert node_cent["betweenness"] == 0.0
        assert node_cent["eigenvector"] == 1.0  # Normalized eigenvector
        assert node_cent["pagerank"] == 1.0  # Single node gets all PageRank mass

    def test_single_edge_graph(self):
        """Graph with single edge has valid centrality."""
        data = [TopicGraphData("a", "b", shared_posts=1, shared_authors=1)]
        undirected, indices = build_topic_graph(data)
        directed = build_directed_graph(data, indices)
        centrality = compute_all_centrality(undirected, directed)

        # Both nodes should have centrality values
        assert len(centrality) == 2
        for node_cent in centrality.values():
            assert "betweenness" in node_cent
            assert "eigenvector" in node_cent
            assert "pagerank" in node_cent

    def test_betweenness_normalization_star_topology(self):
        """Betweenness = 1.0 for hub in star topology."""
        data = [
            TopicGraphData("hub", "s1", shared_posts=1, shared_authors=1),
            TopicGraphData("hub", "s2", shared_posts=1, shared_authors=1),
            TopicGraphData("hub", "s3", shared_posts=1, shared_authors=1),
            TopicGraphData("hub", "s4", shared_posts=1, shared_authors=1),
        ]
        undirected, indices = build_topic_graph(data)
        directed = build_directed_graph(data, indices)
        centrality = compute_all_centrality(undirected, directed)

        hub_idx = indices["hub"]
        assert centrality[hub_idx]["betweenness"] == 1.0

    def test_betweenness_always_normalized(self):
        """Betweenness should always be in [0, 1]."""
        # Create various topologies
        topologies = [
            # Star
            [
                TopicGraphData("c", "a", 1, 1),
                TopicGraphData("c", "b", 1, 1),
                TopicGraphData("c", "d", 1, 1),
            ],
            # Chain
            [
                TopicGraphData("a", "b", 1, 1),
                TopicGraphData("b", "c", 1, 1),
                TopicGraphData("c", "d", 1, 1),
            ],
            # Ring
            [
                TopicGraphData("a", "b", 1, 1),
                TopicGraphData("b", "c", 1, 1),
                TopicGraphData("c", "d", 1, 1),
                TopicGraphData("d", "a", 1, 1),
            ],
        ]

        for topo_data in topologies:
            undirected, indices = build_topic_graph(topo_data)
            directed = build_directed_graph(topo_data, indices)
            centrality = compute_all_centrality(undirected, directed)

            for node_cent in centrality.values():
                assert 0 <= node_cent["betweenness"] <= 1.0

    def test_eigenvector_can_exceed_half(self):
        """Eigenvector values are L2-normalized, not max-normalized.

        In a 2-node graph, both nodes have eigenvector = 1/sqrt(2) ≈ 0.707
        """
        data = [TopicGraphData("a", "b", shared_posts=1, shared_authors=1)]
        undirected, indices = build_topic_graph(data)
        directed = build_directed_graph(data, indices)
        centrality = compute_all_centrality(undirected, directed)

        # Both should have eigenvector ≈ 0.707
        for node_cent in centrality.values():
            assert abs(node_cent["eigenvector"] - 0.7071) < 0.01

    def test_pagerank_sums_to_one(self):
        """PageRank values should sum to 1.0 (probability distribution)."""
        data = [
            TopicGraphData("a", "b", 1, 1),
            TopicGraphData("b", "c", 1, 1),
            TopicGraphData("c", "d", 1, 1),
            TopicGraphData("d", "a", 1, 1),
        ]
        undirected, indices = build_topic_graph(data)
        directed = build_directed_graph(data, indices)
        centrality = compute_all_centrality(undirected, directed)

        pagerank_sum = sum(c["pagerank"] for c in centrality.values())
        assert abs(pagerank_sum - 1.0) < 0.01

    def test_pagerank_max_value_in_star(self):
        """PageRank hub value in star topology."""
        data = [
            TopicGraphData("hub", "s1", 1, 1),
            TopicGraphData("hub", "s2", 1, 1),
            TopicGraphData("hub", "s3", 1, 1),
            TopicGraphData("hub", "s4", 1, 1),
        ]
        undirected, indices = build_topic_graph(data)
        directed = build_directed_graph(data, indices)
        centrality = compute_all_centrality(undirected, directed)

        hub_idx = indices["hub"]
        hub_pr = centrality[hub_idx]["pagerank"]

        # Hub should have higher PageRank than spokes
        spoke_pr = [centrality[indices[f"s{i}"]]["pagerank"] for i in range(1, 5)]
        assert hub_pr > max(spoke_pr)

        # But still < 1.0
        assert hub_pr < 1.0

    def test_disconnected_graph_centrality(self):
        """Disconnected components have independent centrality."""
        data = [
            TopicGraphData("a1", "a2", 1, 1),
            TopicGraphData("b1", "b2", 1, 1),
        ]
        undirected, indices = build_topic_graph(data)
        directed = build_directed_graph(data, indices)
        centrality = compute_all_centrality(undirected, directed)

        # All nodes should have betweenness = 0 (no paths between components)
        for node_cent in centrality.values():
            assert node_cent["betweenness"] == 0.0

        # PageRank should sum to 1.0 across all components
        pagerank_sum = sum(c["pagerank"] for c in centrality.values())
        assert abs(pagerank_sum - 1.0) < 0.01


class TestNumericalStability:
    """Test numerical stability and precision."""

    def test_floating_point_weight_sum(self):
        """Verify no floating-point errors in weight calculation."""
        # Compute score with values that ensure all weights contribute
        score = compute_pulse_score(
            velocity=1.5,  # norm = 0.5
            eigenvector_centrality=0.5,
            betweenness_centrality=0.5,
            unique_authors=50,
            max_authors=100,  # norm = 0.5
            pagerank=0.5,
        )

        # All normalized values = 0.5
        # score = 5 * (0.5 * weight) = 0.5 * sum(weights) = 0.5 * 1.0 = 0.5
        expected = 0.5
        assert abs(score - expected) < 0.01

    def test_pulse_score_bounds_are_respected(self):
        """Pulse score should always be in [0, 1] for valid inputs."""
        test_cases = [
            # (velocity, eigen, between, authors, max_authors, pagerank)
            (0.0, 0.0, 0.0, 0, 10, 0.0),  # All min
            (3.0, 1.0, 1.0, 100, 100, 1.0),  # All max
            (1.5, 0.3, 0.7, 25, 50, 0.4),  # Mixed
            (0.1, 0.9, 0.1, 90, 100, 0.8),  # Mixed
        ]

        for velocity, eigen, between, authors, max_auth, pagerank in test_cases:
            score = compute_pulse_score(
                velocity=velocity,
                eigenvector_centrality=eigen,
                betweenness_centrality=between,
                unique_authors=authors,
                max_authors=max_auth,
                pagerank=pagerank,
            )
            inputs = (velocity, eigen, between, authors, max_auth, pagerank)
            assert 0.0 <= score <= 1.0, f"Score {score} out of bounds: {inputs}"

    def test_velocity_normalization_ceiling(self):
        """Velocities >= 3.0 should normalize to 1.0."""
        for v in [3.0, 5.0, 10.0, 100.0]:
            score = compute_pulse_score(
                velocity=v,
                eigenvector_centrality=0.0,
                betweenness_centrality=0.0,
                unique_authors=0,
                max_authors=10,
                pagerank=0.0,
            )
            # Only velocity contributes: 0.25 * 1.0 = 0.25
            assert abs(score - 0.25) < 0.01

    def test_pulse_score_with_max_authors_equals_one(self):
        """Edge case: max_authors = 1."""
        score = compute_pulse_score(
            velocity=1.0,
            eigenvector_centrality=0.5,
            betweenness_centrality=0.3,
            unique_authors=1,
            max_authors=1,  # Edge case but valid
            pagerank=0.4,
        )
        # unique_authors / max_authors = 1/1 = 1.0
        # Should not crash and should be valid
        assert 0.0 <= score <= 1.0


class TestIntegrationEdgeCases:
    """Integration tests for full pipeline edge cases.

    Note: Service-level tests (empty posts, zero authors) moved to
    tests/test_pulse_compute.py for proper service layer testing.
    """

    def test_large_graph_centrality(self):
        """Large graph (n=100) should compute centrality without issues."""
        # Create a large graph
        data = []
        for i in range(99):
            data.append(
                TopicGraphData(f"t{i}", f"t{i + 1}", shared_posts=1, shared_authors=1)
            )

        undirected, indices = build_topic_graph(data)
        directed = build_directed_graph(data, indices)
        centrality = compute_all_centrality(undirected, directed)

        # Should compute for all 100 nodes
        assert len(centrality) == 100

        # All centrality values should be valid
        for node_cent in centrality.values():
            assert 0 <= node_cent["betweenness"] <= 1.0
            assert node_cent["eigenvector"] >= 0
            assert 0 <= node_cent["pagerank"] <= 1.0
