"""Graph analysis using rustworkx."""

from dataclasses import dataclass
from typing import Any

import rustworkx as rx


@dataclass
class TopicGraphData:
    """Data for building the topic graph."""

    topic_a: str
    topic_b: str
    shared_posts: int
    shared_authors: int


def build_topic_graph(
    cooccurrence_data: list[TopicGraphData],
) -> tuple[rx.PyGraph, dict[str, int]]:
    """Build an undirected topic co-occurrence graph.

    Returns
    -------
        Tuple of (graph, topic_id_to_node_index mapping)

    """
    graph: rx.PyGraph = rx.PyGraph()
    topic_indices: dict[str, int] = {}

    for row in cooccurrence_data:
        # Add nodes if not present
        for topic_id in [row.topic_a, row.topic_b]:
            if topic_id not in topic_indices:
                node_idx = graph.add_node({"id": topic_id})
                topic_indices[topic_id] = node_idx

        # Add weighted edge
        graph.add_edge(
            topic_indices[row.topic_a],
            topic_indices[row.topic_b],
            {"weight": row.shared_authors, "posts": row.shared_posts},
        )

    return graph, topic_indices


def compute_centrality(graph: rx.PyGraph) -> dict[int, dict[str, float]]:
    """Compute centrality metrics for all nodes.

    Returns
    -------
        Dict mapping node index to centrality metrics.

    """
    if graph.num_nodes() == 0:
        return {}

    # Compute different centrality measures
    betweenness = rx.betweenness_centrality(graph)

    # For undirected graphs, use degree centrality as a proxy for pagerank
    # since pagerank requires a directed graph
    degree_centrality = {}
    if graph.num_nodes() > 0:
        degrees = {node: graph.degree(node) for node in graph.node_indices()}
        max_degree = max(degrees.values()) if degrees else 1
        degree_centrality = {
            node: degree / max_degree if max_degree > 0 else 0.0
            for node, degree in degrees.items()
        }

    # Eigenvector centrality can fail on disconnected graphs
    eigenvector: Any
    try:
        eigenvector = rx.eigenvector_centrality(graph, max_iter=100)
    except rx.FailedToConverge:
        eigenvector = dict.fromkeys(graph.node_indices(), 0.0)

    return {
        node_idx: {
            "betweenness": betweenness[node_idx] if node_idx in betweenness else 0.0,
            "eigenvector": eigenvector[node_idx] if node_idx in eigenvector else 0.0,
            "pagerank": degree_centrality.get(node_idx, 0.0),
        }
        for node_idx in graph.node_indices()
    }


def detect_clusters(graph: rx.PyGraph) -> list[set[int]]:
    """Detect topic clusters using connected components.

    For a more sophisticated approach, we'd use Louvain,
    but connected components work for the POC.
    """
    if graph.num_nodes() == 0:
        return []

    return rx.connected_components(graph)
