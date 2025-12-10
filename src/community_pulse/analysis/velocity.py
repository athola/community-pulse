"""Velocity and pulse score computation."""

from dataclasses import dataclass


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
    """
    if data.baseline_mentions <= 0:
        # No baseline: if we have current mentions, it's emerging
        return 2.0 if data.current_mentions > 0 else 1.0

    return data.current_mentions / data.baseline_mentions


def compute_pulse_score(
    velocity: float,
    eigenvector_centrality: float,
    betweenness_centrality: float,
    unique_authors: int,
    max_authors: int = 100,
) -> float:
    """Compute combined pulse score.

    Weights:
    - 30% velocity (momentum)
    - 30% eigenvector centrality (convergence/importance)
    - 25% betweenness centrality (bridge topics)
    - 15% author spread (relational)

    Returns score between 0 and 1.
    """
    # Normalize velocity (cap at 3x baseline)
    norm_velocity = min(velocity / 3.0, 1.0)

    # Centrality already 0-1 from rustworkx
    norm_eigen = min(eigenvector_centrality, 1.0)
    norm_between = min(betweenness_centrality, 1.0)

    # Normalize author count
    norm_authors = min(unique_authors / max_authors, 1.0)

    score = (
        0.30 * norm_velocity
        + 0.30 * norm_eigen
        + 0.25 * norm_between
        + 0.15 * norm_authors
    )

    return round(score, 4)
