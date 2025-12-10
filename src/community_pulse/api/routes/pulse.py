"""Pulse API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Query

from community_pulse.models.pulse import (
    ClusterInfo,
    GraphResponse,
    PulseResponse,
    SamplePost,
    TopicEdge,
    TopicNode,
)

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
