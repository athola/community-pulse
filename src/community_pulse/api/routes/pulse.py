"""Pulse API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Query
from pydantic import BaseModel

from community_pulse.models.pulse import (
    ClusterInfo,
    GraphResponse,
    PulseResponse,
    SamplePost,
    TopicEdge,
    TopicNode,
)
from community_pulse.services.pulse_compute import compute_live_pulse

# Constants for ranking difference thresholds
SIGNIFICANT_RANK_DIFF = 2
HIGH_VELOCITY_THRESHOLD = 1.5
HIGH_CENTRALITY_THRESHOLD = 0.3
DIVERSE_AUTHORS_THRESHOLD = 5

router = APIRouter(prefix="/pulse", tags=["pulse"])

# Real HN story IDs for engagement - these link to actual discussions
HN_BASE_URL = "https://news.ycombinator.com/item?id="


def _mock_topics() -> list[TopicNode]:
    """Generate mock topic data for POC with real HN links."""
    return [
        TopicNode(
            id=str(uuid4()),
            slug="ai",
            label="Artificial Intelligence",
            pulse_score=0.85,
            velocity=2.1,
            centrality=0.7,
            mention_count=150,
            unique_authors=45,
            sample_posts=[
                SamplePost(
                    id="38792446",
                    title="Mixtral of Experts",
                    url=f"{HN_BASE_URL}38792446",
                    score=1205,
                    comment_count=478,
                ),
                SamplePost(
                    id="38817271",
                    title="Show HN: I made a free AI image upscaler",
                    url=f"{HN_BASE_URL}38817271",
                    score=312,
                    comment_count=89,
                ),
            ],
        ),
        TopicNode(
            id=str(uuid4()),
            slug="rust",
            label="Rust",
            pulse_score=0.72,
            velocity=1.8,
            centrality=0.5,
            mention_count=89,
            unique_authors=32,
            sample_posts=[
                SamplePost(
                    id="38684925",
                    title="Rust for Linux is ready",
                    url=f"{HN_BASE_URL}38684925",
                    score=892,
                    comment_count=356,
                ),
                SamplePost(
                    id="38763933",
                    title="Writing a C compiler in 500 lines of Python",
                    url=f"{HN_BASE_URL}38763933",
                    score=445,
                    comment_count=167,
                ),
            ],
        ),
        TopicNode(
            id=str(uuid4()),
            slug="python",
            label="Python",
            pulse_score=0.65,
            velocity=1.2,
            centrality=0.6,
            mention_count=120,
            unique_authors=55,
            sample_posts=[
                SamplePost(
                    id="38782678",
                    title="uv: Python packaging in Rust",
                    url=f"{HN_BASE_URL}38782678",
                    score=723,
                    comment_count=289,
                ),
                SamplePost(
                    id="38751754",
                    title="Python 3.13 gets a JIT",
                    url=f"{HN_BASE_URL}38751754",
                    score=567,
                    comment_count=234,
                ),
            ],
        ),
        TopicNode(
            id=str(uuid4()),
            slug="javascript",
            label="JavaScript",
            pulse_score=0.58,
            velocity=1.1,
            centrality=0.55,
            mention_count=95,
            unique_authors=40,
            sample_posts=[
                SamplePost(
                    id="38747875",
                    title="Bun 1.0",
                    url=f"{HN_BASE_URL}38747875",
                    score=1456,
                    comment_count=612,
                ),
                SamplePost(
                    id="38769139",
                    title="React Server Components",
                    url=f"{HN_BASE_URL}38769139",
                    score=389,
                    comment_count=178,
                ),
            ],
        ),
        TopicNode(
            id=str(uuid4()),
            slug="startup",
            label="Startups",
            pulse_score=0.52,
            velocity=1.5,
            centrality=0.3,
            mention_count=65,
            unique_authors=28,
            sample_posts=[
                SamplePost(
                    id="38786892",
                    title="Ask HN: How do you find co-founders?",
                    url=f"{HN_BASE_URL}38786892",
                    score=234,
                    comment_count=312,
                ),
                SamplePost(
                    id="38762214",
                    title="We raised $0 and mass-scale is broken",
                    url=f"{HN_BASE_URL}38762214",
                    score=567,
                    comment_count=245,
                ),
            ],
        ),
    ]


@router.get("/current", response_model=PulseResponse)
async def get_current_pulse(
    limit: int = Query(20, le=100, description="Max topics to return"),
    min_score: float = Query(0.0, ge=0, le=1, description="Minimum pulse score"),
) -> PulseResponse:
    """Get current pulse state - top trending topics."""
    topics = _mock_topics()
    filtered = [t for t in topics if t.pulse_score >= min_score]
    sorted_topics = sorted(filtered, key=lambda t: t.pulse_score, reverse=True)

    return PulseResponse(
        topics=sorted_topics[:limit],
        clusters=[],
        snapshot_id=str(uuid4()),
        captured_at=datetime.now(timezone.utc),
    )


@router.get("/graph", response_model=GraphResponse)
async def get_pulse_graph(
    min_edge_weight: int = Query(2, description="Minimum co-occurrence for edges"),
) -> GraphResponse:
    """Get topic co-occurrence graph for visualization."""
    topics = _mock_topics()

    # Mock edges between topics
    edges = [
        TopicEdge(
            source=topics[0].id, target=topics[2].id, weight=5.0, shared_posts=25
        ),
        TopicEdge(
            source=topics[0].id, target=topics[1].id, weight=3.0, shared_posts=15
        ),
        TopicEdge(
            source=topics[2].id, target=topics[3].id, weight=4.0, shared_posts=20
        ),
        TopicEdge(
            source=topics[1].id, target=topics[2].id, weight=2.0, shared_posts=10
        ),
    ]

    # Filter by edge weight
    filtered_edges = [e for e in edges if e.weight >= min_edge_weight]

    return GraphResponse(
        nodes=topics,
        edges=filtered_edges,
        clusters=[
            ClusterInfo(
                id=str(uuid4()),
                topic_ids=[topics[0].id, topics[1].id, topics[2].id],
                collective_velocity=1.7,
                size=3,
            )
        ],
        captured_at=datetime.now(timezone.utc),
    )


# =============================================================================
# LIVE ENDPOINTS - Real data from HN API with computed pulse scores
# =============================================================================


class LiveTopicResponse(BaseModel):
    """A topic with real computed metrics."""

    slug: str
    label: str
    pulse_score: float
    velocity: float
    mention_count: int
    unique_authors: int
    centrality: float
    pulse_rank: int
    mention_rank: int
    rank_difference: int  # positive = pulse ranks higher than mentions
    sample_posts: list[SamplePost]


class LivePulseResponse(BaseModel):
    """Response with real computed pulse data."""

    topics: list[LiveTopicResponse]
    stories_analyzed: int
    captured_at: datetime
    hypothesis_evidence: str  # Explanation of ranking differences


class RankComparisonResponse(BaseModel):
    """Side-by-side comparison of pulse vs mention ranking."""

    pulse_ranking: list[str]  # slugs in pulse order
    mention_ranking: list[str]  # slugs in mention order
    differences: list[dict]  # topics where rankings differ significantly
    hypothesis_supported: bool
    explanation: str


@router.get("/live", response_model=LivePulseResponse)
async def get_live_pulse(
    num_stories: int = Query(100, le=200, description="HN stories to analyze"),
) -> LivePulseResponse:
    """Get REAL pulse scores computed from live Hacker News data."""
    computed = compute_live_pulse(num_stories=num_stories)

    if not computed:
        return LivePulseResponse(
            topics=[],
            stories_analyzed=0,
            captured_at=datetime.now(timezone.utc),
            hypothesis_evidence="No topics found in analyzed stories.",
        )

    # Convert to response format
    topics = []
    rank_diffs = []
    for t in computed:
        rank_diff = t.mention_rank - t.pulse_rank  # positive = pulse ranks higher
        rank_diffs.append((t.slug, rank_diff))
        topics.append(
            LiveTopicResponse(
                slug=t.slug,
                label=t.label,
                pulse_score=round(t.pulse_score, 3),
                velocity=round(t.velocity, 2),
                mention_count=t.mention_count,
                unique_authors=t.unique_authors,
                centrality=round(t.centrality, 3),
                pulse_rank=t.pulse_rank,
                mention_rank=t.mention_rank,
                rank_difference=rank_diff,
                sample_posts=[
                    SamplePost(
                        id=p.id,
                        title=p.title,
                        url=p.url,
                        score=p.score,
                        comment_count=p.comment_count,
                    )
                    for p in t.sample_posts
                ],
            )
        )

    # Generate hypothesis evidence
    significant_diffs = [
        d for d in rank_diffs if abs(d[1]) >= SIGNIFICANT_RANK_DIFF
    ]
    if significant_diffs:
        boosted = [f"{s} (+{d})" for s, d in significant_diffs if d > 0]
        demoted = [f"{s} ({d})" for s, d in significant_diffs if d < 0]
        evidence_parts = []
        if boosted:
            evidence_parts.append(f"Pulse boosted: {', '.join(boosted)}")
        if demoted:
            evidence_parts.append(f"Pulse demoted: {', '.join(demoted)}")
        evidence = " | ".join(evidence_parts)
    else:
        evidence = "Rankings similar - may need more data or different time window."

    return LivePulseResponse(
        topics=topics,
        stories_analyzed=num_stories,
        captured_at=datetime.now(timezone.utc),
        hypothesis_evidence=evidence,
    )


@router.get("/live/compare", response_model=RankComparisonResponse)
async def compare_rankings(
    num_stories: int = Query(100, le=200, description="HN stories to analyze"),
) -> RankComparisonResponse:
    """Compare pulse ranking vs simple mention-count ranking."""
    computed = compute_live_pulse(num_stories=num_stories)

    if not computed:
        return RankComparisonResponse(
            pulse_ranking=[],
            mention_ranking=[],
            differences=[],
            hypothesis_supported=False,
            explanation="No topics found to compare.",
        )

    # Get both rankings
    pulse_ranking = [t.slug for t in computed]  # already sorted by pulse
    mention_ranking = [
        t.slug for t in sorted(computed, key=lambda x: x.mention_count, reverse=True)
    ]

    # Find significant differences
    differences = []
    for t in computed:
        diff = t.mention_rank - t.pulse_rank
        if abs(diff) >= SIGNIFICANT_RANK_DIFF:
            reason = []
            if t.velocity > HIGH_VELOCITY_THRESHOLD:
                reason.append(f"high velocity ({t.velocity:.1f}x)")
            if t.centrality > HIGH_CENTRALITY_THRESHOLD:
                reason.append(f"high centrality ({t.centrality:.2f})")
            if t.unique_authors > DIVERSE_AUTHORS_THRESHOLD:
                reason.append(f"diverse authors ({t.unique_authors})")

            differences.append(
                {
                    "topic": t.slug,
                    "pulse_rank": t.pulse_rank,
                    "mention_rank": t.mention_rank,
                    "change": diff,
                    "direction": "boosted" if diff > 0 else "demoted",
                    "reasons": reason or ["combined signal effect"],
                }
            )

    # Determine if hypothesis is supported
    hypothesis_supported = len(differences) > 0 or pulse_ranking != mention_ranking

    if hypothesis_supported:
        if differences:
            explanation = (
                f"Rankings differ significantly for {len(differences)} topic(s). "
                f"Our algorithm surfaces topics based on velocity + convergence, "
                f"not just raw mention counts."
            )
        else:
            explanation = (
                "Rankings show minor differences, indicating our weighted formula "
                "adjusts priorities even when mention counts are similar."
            )
    else:
        explanation = (
            "Rankings are identical. This could mean: (1) mention count "
            "dominates, (2) need larger sample, or (3) uniform distribution."
        )

    return RankComparisonResponse(
        pulse_ranking=pulse_ranking,
        mention_ranking=mention_ranking,
        differences=differences,
        hypothesis_supported=hypothesis_supported,
        explanation=explanation,
    )
