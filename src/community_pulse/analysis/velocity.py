"""Velocity and pulse score computation.

Formula Evolution: 4-Signal to 5-Signal Design
-----------------------------------------------

Original Design (4-signal):
    30% velocity, 30% eigenvector centrality, 25% betweenness, 15% sentiment

Current Implementation (5-signal):
    25% velocity, 25% eigenvector centrality, 20% betweenness,
    15% PageRank, 15% author spread

Rationale for Evolution:

1. **Added PageRank (15%)**
   - Complements eigenvector centrality with flow-based authority
   - Eigenvector measures importance via connections to important nodes
   - PageRank measures influence via information flow patterns
   - Together they provide richer understanding of topic prominence

2. **Replaced sentiment with author spread (15%)**
   - More objective: count-based vs. subjective sentiment analysis
   - Easier to compute: no NLP model required
   - Better proxy for convergence: diverse voices = genuine emergence
   - Avoids sentiment analysis pitfalls (sarcasm, domain-specificity)

3. **Rebalanced weights to 25/25/20/15/15**
   - Velocity and eigenvector remain primary signals (25% each)
   - Betweenness reduced to 20% to accommodate new signals
   - PageRank and author spread at 15% each as supporting signals
   - Total still 100%, all signals contribute meaningfully

This evolution was driven by POC implementation findings and maintains
the core principle: detect emergent collective movement via multi-signal
convergence.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Velocity normalization cap: velocities >= this value normalize to 1.0
# This caps exponential growth at 3x baseline to prevent score saturation
VELOCITY_CAP = 3.0


@dataclass
class VelocityData:
    """Velocity data for a topic."""

    topic_id: str
    current_mentions: int
    baseline_mentions: float
    unique_authors: int


def compute_velocity(data: VelocityData) -> float:
    """Compute velocity ratio for a topic.

    Velocity = current_rate / baseline_rate
    A velocity > 1.0 means the topic is trending up.

    Args:
        data: VelocityData with current and baseline mentions

    Returns:
        float: Velocity ratio (>= 0.0)
            - 1.0 = stable (matches baseline)
            - >1.0 = trending up
            - <1.0 = declining
            - 2.0 = emerging (no baseline but has current mentions)

    Note:
        - Negative baseline values are invalid and treated as zero (logged as warning)
        - Current mentions are clamped to >= 0 for safety

    """
    # Input validation: clamp current mentions to non-negative
    current = max(0, data.current_mentions)

    # Handle invalid negative baseline
    if data.baseline_mentions < 0:
        logger.warning(
            f"Negative baseline ({data.baseline_mentions}) for topic {data.topic_id}. "
            "Treating as zero (emerging topic)."
        )
        baseline = 0.0
    else:
        baseline = data.baseline_mentions

    if baseline <= 0:
        # No baseline: if we have current mentions, it's emerging
        return 2.0 if current > 0 else 1.0

    return current / baseline


def compute_pulse_score(  # noqa: PLR0913
    velocity: float,
    eigenvector_centrality: float,
    betweenness_centrality: float,
    unique_authors: int,
    max_authors: int = 100,
    pagerank: float = 0.0,
) -> float:
    """Compute combined pulse score using all centrality measures.

    Weights:
    - 25% velocity (momentum - how fast topic is growing)
    - 25% eigenvector centrality (importance via connection to important topics)
    - 20% betweenness centrality (bridge topics connecting communities)
    - 15% PageRank (flow-based influence/authority)
    - 15% author spread (diversity of perspectives)

    Args:
        velocity: Topic velocity ratio (current/baseline mentions)
        eigenvector_centrality: Eigenvector centrality from graph (0-1)
        betweenness_centrality: Betweenness centrality from graph (0-1)
        unique_authors: Number of unique authors discussing topic
        max_authors: Maximum expected authors for normalization (default: 100)
        pagerank: PageRank score from graph (0-1)

    Returns:
        float: Combined pulse score in [0, 1] range, rounded to 4 decimals

    Note:
        Normalization assumptions:
        - Velocity is capped at VELOCITY_CAP (3.0) to prevent saturation
        - Centrality measures expected in [0, 1] from rustworkx
        - max_authors default of 100 is arbitrary - adjust based on community size
        - All negative inputs are clamped to 0.0 for mathematical safety
        - max_authors <= 0 is treated as 1 to prevent division by zero

    """
    # Input validation: clamp all inputs to non-negative values
    velocity = max(0.0, velocity)
    eigenvector_centrality = max(0.0, eigenvector_centrality)
    betweenness_centrality = max(0.0, betweenness_centrality)
    pagerank = max(0.0, pagerank)
    unique_authors = max(0, unique_authors)

    # Guard against division by zero in max_authors
    if max_authors <= 0:
        max_authors = 1

    # Normalize velocity (cap at VELOCITY_CAP)
    norm_velocity = min(velocity / VELOCITY_CAP, 1.0)

    # Centrality measures - already 0-1 from rustworkx but cap for safety
    norm_eigen = min(eigenvector_centrality, 1.0)
    norm_between = min(betweenness_centrality, 1.0)
    norm_pagerank = min(pagerank, 1.0)

    # Normalize author count
    norm_authors = min(unique_authors / max_authors, 1.0)

    score = (
        0.25 * norm_velocity
        + 0.25 * norm_eigen
        + 0.20 * norm_between
        + 0.15 * norm_pagerank
        + 0.15 * norm_authors
    )

    return round(score, 4)
