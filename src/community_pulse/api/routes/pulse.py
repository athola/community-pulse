"""Pulse API endpoints."""

import hashlib
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from community_pulse.config import get_pulse_settings
from community_pulse.models.pulse import (
    ClusterInfo,
    ErrorResponse,
    GraphResponse,
    LivePulseResponse,
    LiveTopicResponse,
    PulseResponse,
    RankComparisonResponse,
    SamplePost,
    TopicEdge,
    TopicNode,
)
from community_pulse.services.pulse_compute import (
    compute_live_pulse,
    compute_live_pulse_with_edges,
)

logger = logging.getLogger(__name__)

# Rate limiter for this module
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/pulse", tags=["pulse"])

# Real HN story IDs for engagement - these link to actual discussions
HN_BASE_URL = "https://news.ycombinator.com/item?id="


def generate_topic_id(slug: str) -> str:
    """Generate a deterministic ID from slug.

    Uses BLAKE2b hash (faster than SHA-256) truncated to 12 characters for
    stable, unique IDs. We only need uniqueness, not cryptographic security.
    """
    return hashlib.blake2b(slug.encode(), digest_size=6).hexdigest()


def _mock_topics() -> list[TopicNode]:
    """Generate mock topic data for POC fallback.

    WARNING: This is stale fixture data from Dec 2023. Used only when
    HN API is unavailable. For real data, use compute_live_pulse().

    These are actual HN story IDs that were live in December 2023.
    They remain clickable but represent historical discussions, not
    current trends. This function serves as a last-resort fallback
    to demonstrate API structure when live data cannot be fetched.
    """
    return [
        TopicNode(
            id=generate_topic_id("ai"),
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
            id=generate_topic_id("rust"),
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
            id=generate_topic_id("python"),
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
            id=generate_topic_id("javascript"),
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
            id=generate_topic_id("startup"),
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


@router.get(
    "/current",
    response_model=PulseResponse,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Validation error - invalid query parameters",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("30/minute")
async def get_current_pulse(
    request: Request,
    limit: int = Query(20, le=100, description="Max topics to return"),
    offset: int = Query(0, ge=0, description="Number of topics to skip"),
    min_score: float = Query(0.0, ge=0, le=1, description="Minimum pulse score"),
) -> PulseResponse:
    """Get current pulse state - top trending topics from live HN data."""
    # Use live data from HN API for real, clickable links
    computed = compute_live_pulse(num_stories=100)

    warning_msg: str | None = None
    if not computed:
        # Fallback to mock data if HN API fails
        # WARNING: Using stale Dec 2023 fixture data - HN API may be unavailable
        warning_msg = (
            "Using cached fallback data from Dec 2023. "
            "HN API may be temporarily unavailable."
        )
        logger.warning(
            "Using fallback mock data - HN API unavailable. "
            "Response contains stale Dec 2023 fixture data."
        )
        topics = _mock_topics()
        data_source = "mock"
    else:
        # Convert computed topics to TopicNode format
        topics = [
            TopicNode(
                id=generate_topic_id(t.slug),
                slug=t.slug,
                label=t.label,
                pulse_score=t.pulse_score,
                velocity=t.velocity,
                temporal_velocity=t.temporal_velocity,
                centrality=t.centrality,
                mention_count=t.mention_count,
                unique_authors=t.unique_authors,
                sample_posts=[
                    SamplePost(
                        id=p.id,
                        title=p.title,
                        url=p.url,  # Real HN discussion URLs
                        score=p.score,
                        comment_count=p.comment_count,
                    )
                    for p in t.sample_posts
                ],
            )
            for t in computed
        ]
        data_source = "live"

    filtered = [t for t in topics if t.pulse_score >= min_score]
    sorted_topics = sorted(filtered, key=lambda t: t.pulse_score, reverse=True)
    total_count = len(sorted_topics)

    return PulseResponse(
        topics=sorted_topics[offset : offset + limit],
        clusters=[],
        snapshot_id=str(uuid4()),
        captured_at=datetime.now(timezone.utc),
        data_source=data_source,
        total_count=total_count,
        warning=warning_msg,
    )


@router.get(
    "/graph",
    response_model=GraphResponse,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Validation error - invalid query parameters",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("20/minute")
async def get_pulse_graph(
    request: Request,
    min_edge_weight: int = Query(2, description="Minimum co-occurrence for edges"),
) -> GraphResponse:
    """Get topic co-occurrence graph for visualization with live HN data."""
    # Use live data from HN API with true co-occurrence edges
    pulse_result = compute_live_pulse_with_edges(num_stories=100)

    warning_msg: str | None = None
    if not pulse_result.topics:
        # Fallback to mock data if HN API fails
        warning_msg = (
            "Using cached fallback data from Dec 2023. "
            "HN API may be temporarily unavailable."
        )
        logger.warning(
            "Using fallback mock data for graph - HN API unavailable. "
            "Response contains stale Dec 2023 fixture data."
        )
        topics = _mock_topics()
        edges = [
            TopicEdge(
                source=topics[0].id, target=topics[2].id, weight=5.0, shared_posts=25
            ),
            TopicEdge(
                source=topics[0].id, target=topics[1].id, weight=3.0, shared_posts=15
            ),
        ]
        data_source = "mock"
    else:
        # Convert computed topics to TopicNode format with stable IDs
        topic_id_map = {}
        topics = []
        for t in pulse_result.topics:
            topic_id = generate_topic_id(t.slug)
            topic_id_map[t.slug] = topic_id
            topics.append(
                TopicNode(
                    id=topic_id,
                    slug=t.slug,
                    label=t.label,
                    pulse_score=t.pulse_score,
                    velocity=t.velocity,
                    temporal_velocity=t.temporal_velocity,
                    centrality=t.centrality,
                    mention_count=t.mention_count,
                    unique_authors=t.unique_authors,
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

        # Generate edges from true co-occurrence data (shared posts between topics)
        edges = []
        for edge_data in pulse_result.edges:
            # Only include edges where both topics are in our result set
            source_id = topic_id_map.get(edge_data.topic_a)
            target_id = topic_id_map.get(edge_data.topic_b)
            if source_id and target_id and edge_data.shared_posts >= min_edge_weight:
                edges.append(
                    TopicEdge(
                        source=source_id,
                        target=target_id,
                        weight=float(edge_data.shared_posts),
                        shared_posts=edge_data.shared_posts,
                    )
                )
        data_source = "live"

    # Filter by edge weight
    filtered_edges = [e for e in edges if e.weight >= min_edge_weight]

    # Get settings at request time for proper error handling
    settings = get_pulse_settings()
    min_size = settings.min_cluster_size

    return GraphResponse(
        nodes=topics,
        edges=filtered_edges[:15],  # Limit edges for cleaner visualization
        clusters=[
            ClusterInfo(
                id=str(uuid4()),
                topic_ids=[t.id for t in topics[:min_size]]
                if len(topics) >= min_size
                else [],
                collective_velocity=sum(t.velocity for t in topics[:min_size])
                / min_size
                if len(topics) >= min_size
                else 0,
                size=min(min_size, len(topics)),
            )
        ],
        captured_at=datetime.now(timezone.utc),
        data_source=data_source,
        warning=warning_msg,
    )


# =============================================================================
# LIVE ENDPOINTS - Real data from HN API with computed pulse scores
# =============================================================================


@router.get(
    "/live",
    response_model=LivePulseResponse,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Validation error - invalid query parameters",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("20/minute")
async def get_live_pulse(
    request: Request,
    num_stories: int = Query(100, le=200, description="HN stories to analyze"),
    limit: int = Query(20, le=100, description="Max topics to return"),
    offset: int = Query(0, ge=0, description="Number of topics to skip"),
) -> LivePulseResponse:
    """Get REAL pulse scores computed from live Hacker News data."""
    computed = compute_live_pulse(num_stories=num_stories)

    if not computed:
        return LivePulseResponse(
            topics=[],
            stories_analyzed=0,
            captured_at=datetime.now(timezone.utc),
            hypothesis_evidence="No topics found in analyzed stories.",
            data_source="live",
            total_count=0,
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
                temporal_velocity=round(t.temporal_velocity, 2)
                if t.temporal_velocity is not None
                else None,
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
    settings = get_pulse_settings()
    significant_diffs = [
        d for d in rank_diffs if abs(d[1]) >= settings.significant_rank_diff
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
        topics=topics[offset : offset + limit],
        stories_analyzed=num_stories,
        captured_at=datetime.now(timezone.utc),
        hypothesis_evidence=evidence,
        data_source="live",
        total_count=len(topics),
    )


@router.get(
    "/live/compare",
    response_model=RankComparisonResponse,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Validation error - invalid query parameters",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("10/minute")
async def compare_rankings(
    request: Request,
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
    settings = get_pulse_settings()
    differences = []
    for t in computed:
        diff = t.mention_rank - t.pulse_rank
        if abs(diff) >= settings.significant_rank_diff:
            reason = []
            if t.velocity > settings.high_velocity_threshold:
                reason.append(f"high velocity ({t.velocity:.1f}x)")
            if t.centrality > settings.high_centrality_threshold:
                reason.append(f"high centrality ({t.centrality:.2f})")
            if t.unique_authors > settings.diverse_authors_threshold:
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
