"""Graph analysis using rustworkx."""

import logging
from dataclasses import dataclass

import rustworkx as rx

logger = logging.getLogger(__name__)


@dataclass
class TopicGraphData:
    """Data for building the topic graph."""

    topic_a: str
    topic_b: str
    shared_posts: int
    shared_authors: int


@dataclass
class GraphPair:
    """Pair of undirected and directed graphs for different analyses."""

    undirected: rx.PyGraph
    directed: rx.PyDiGraph
    topic_indices: dict[str, int]


def build_topic_graph(
    cooccurrence_data: list[TopicGraphData],
) -> tuple[rx.PyGraph, dict[str, int]]:
    """Build an undirected topic co-occurrence graph.

    Args:
        cooccurrence_data: List of topic pair co-occurrence data.

    Returns:
        Tuple of (graph, topic_id_to_node_index mapping).

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


def build_directed_graph(
    cooccurrence_data: list[TopicGraphData],
    topic_indices: dict[str, int],
) -> rx.PyDiGraph:
    """Build a directed graph with bidirectional edges for PageRank.

    PageRank requires a directed graph. We simulate undirected behavior
    by adding edges in both directions (A→B and B→A).
    """
    digraph: rx.PyDiGraph = rx.PyDiGraph()

    # Add all nodes first
    for topic_id, expected_idx in sorted(topic_indices.items(), key=lambda x: x[1]):
        actual_idx = digraph.add_node({"id": topic_id})
        if actual_idx != expected_idx:  # noqa: S101 - Critical invariant check
            msg = f"Index mismatch: {actual_idx} != {expected_idx}"
            raise ValueError(msg)

    # Add bidirectional edges
    for row in cooccurrence_data:
        idx_a = topic_indices[row.topic_a]
        idx_b = topic_indices[row.topic_b]
        weight = {"weight": row.shared_authors, "posts": row.shared_posts}

        # Add edge in both directions for PageRank symmetry
        digraph.add_edge(idx_a, idx_b, weight)
        digraph.add_edge(idx_b, idx_a, weight)

    return digraph


def compute_centrality(graph: rx.PyGraph) -> dict[int, dict[str, float]]:
    """Compute centrality metrics for all nodes.

    Args:
        graph: Undirected graph to compute centrality on.

    Returns:
        Dict mapping node index to centrality metrics (betweenness, eigenvector,
        degree_centrality). Note: 'degree_centrality' is a fallback for PageRank.

    """
    if graph.num_nodes() == 0:
        return {}

    if graph.num_edges() == 0:
        logger.warning("Graph has no edges - centrality scores will be zero")
        return {
            idx: {"betweenness": 0.0, "eigenvector": 0.0}
            for idx in graph.node_indices()
        }

    # Betweenness centrality: identifies bridge topics between communities
    # rustworkx normalizes to [0, 1]: 0 = never on shortest path,
    # 1 = on all shortest paths
    betweenness_raw = rx.betweenness_centrality(graph)
    betweenness = dict(betweenness_raw) if betweenness_raw else {}

    # Eigenvector centrality: importance via connections to important nodes
    # rustworkx uses L2 normalization (||v||_2 = 1), so values can exceed 0.5
    # For a 2-node connected graph, each node gets ~0.707 (1/√2), not 0.5
    eigenvector: dict[int, float]
    try:
        eigenvector_raw = rx.eigenvector_centrality(graph, max_iter=100)
        eigenvector = dict(eigenvector_raw) if eigenvector_raw else {}
    except rx.FailedToConverge:
        eigenvector = dict.fromkeys(graph.node_indices(), 0.0)

    # For PageRank, use degree centrality as fallback
    # (proper PageRank computed separately on directed graph)
    degree_centrality: dict[int, float] = {}
    if graph.num_nodes() > 0:
        degrees = {node: graph.degree(node) for node in graph.node_indices()}
        max_degree = max(degrees.values()) if degrees else 1
        degree_centrality = {
            node: degree / max_degree if max_degree > 0 else 0.0
            for node, degree in degrees.items()
        }

    return {
        node_idx: {
            "betweenness": betweenness.get(node_idx, 0.0),
            "eigenvector": eigenvector.get(node_idx, 0.0),
            "degree_centrality": degree_centrality.get(node_idx, 0.0),
        }
        for node_idx in graph.node_indices()
    }


def compute_pagerank(digraph: rx.PyDiGraph, alpha: float = 0.85) -> dict[int, float]:
    """Compute PageRank on a directed graph.

    Args:
        digraph: Directed graph (use bidirectional edges for undirected behavior)
        alpha: Damping factor (default 0.85, standard value)

    Returns:
        Dict mapping node index to PageRank score.

    Note:
        PageRank normalization:
        - Values sum to 1.0 across all nodes
        - For n nodes, typical values are around 1/n for uniform distribution
        - Maximum possible value is 1.0 (if all edges point to one node)
        - Alpha=0.85 is the standard damping factor used in original PageRank

    """
    if digraph.num_nodes() == 0:
        return {}

    try:
        pagerank_raw = rx.pagerank(digraph, alpha=alpha)
        return dict(pagerank_raw) if pagerank_raw else {}
    except rx.FailedToConverge:
        logger.warning("PageRank failed to converge")
        num_nodes = digraph.num_nodes()
        return dict.fromkeys(digraph.node_indices(), 1.0 / num_nodes)


def compute_all_centrality(
    undirected: rx.PyGraph,
    directed: rx.PyDiGraph,
) -> dict[int, dict[str, float]]:
    """Compute all centrality metrics using appropriate graph types.

    Args:
        undirected: Undirected graph for symmetric metrics
        directed: Directed graph with bidirectional edges for PageRank

    Returns:
        Dict mapping node index to all centrality metrics.

    Note:
        Graph type rationale:
        - Eigenvector centrality uses undirected graph (symmetric influence)
        - Betweenness centrality uses undirected graph (bridge topics)
        - PageRank uses directed graph with bidirectional edges

        Normalization ranges:
        - Eigenvector: L2 normalized, can exceed 0.5
        - Betweenness: [0, 1], 0=never on shortest path, 1=on all paths
        - PageRank: Sum to 1.0 across all nodes

    """
    if undirected.num_nodes() == 0:
        return {}

    # Betweenness on undirected graph - convert CentralityMapping to dict
    # rustworkx normalizes betweenness to [0, 1] range automatically
    betweenness_raw = rx.betweenness_centrality(undirected)
    betweenness = dict(betweenness_raw) if betweenness_raw else {}

    # Eigenvector on undirected graph
    # rustworkx uses L2 normalization: ||v||_2 = 1
    # For a 2-node connected graph, each node gets ~0.707 (1/√2), not 0.5
    eigenvector: dict[int, float]
    try:
        eigenvector_raw = rx.eigenvector_centrality(undirected, max_iter=100)
        eigenvector = dict(eigenvector_raw) if eigenvector_raw else {}
    except rx.FailedToConverge:
        eigenvector = dict.fromkeys(undirected.node_indices(), 0.0)

    # PageRank on directed graph (with bidirectional edges)
    pagerank = compute_pagerank(directed)

    return {
        node_idx: {
            "betweenness": betweenness.get(node_idx, 0.0),
            "eigenvector": eigenvector.get(node_idx, 0.0),
            "pagerank": pagerank.get(node_idx, 0.0),
        }
        for node_idx in undirected.node_indices()
    }


def detect_clusters(graph: rx.PyGraph) -> list[set[int]]:
    """Detect topic clusters using connected components.

    For a more sophisticated approach, we'd use Louvain,
    but connected components work for the POC.
    """
    if graph.num_nodes() == 0:
        return []

    return rx.connected_components(graph)
