"""Pydantic models for pulse API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SamplePost(BaseModel):
    """A sample post for engagement - links to real content."""

    id: str = Field(description="Unique identifier for the post")
    title: str = Field(description="Post title text")
    url: str = Field(description="Direct link to HN discussion")
    score: int = Field(default=0, ge=0, description="Post score/points")
    comment_count: int = Field(default=0, ge=0, description="Number of comments")


class TopicNode(BaseModel):
    """A topic node in the pulse graph."""

    id: str = Field(description="Unique topic identifier")
    slug: str = Field(description="URL-safe topic identifier")
    label: str = Field(description="Human-readable topic name")
    pulse_score: float = Field(ge=0, le=1, description="Combined pulse score from 0-1")
    velocity: float = Field(
        default=1.0,
        description=(
            "Relative popularity vs other topics (>1 = above avg, <1 = below avg)"
        ),
    )
    temporal_velocity: float | None = Field(
        default=None,
        description=(
            "True velocity vs historical baseline "
            "(>1 = growing, <1 = declining, null = no history)"
        ),
    )
    centrality: float = Field(
        default=0.0, ge=0, le=1, description="Network importance score"
    )
    mention_count: int = Field(
        default=0, ge=0, description="Total mentions in time window"
    )
    unique_authors: int = Field(
        default=0, ge=0, description="Distinct authors discussing topic"
    )
    sample_posts: list[SamplePost] = Field(
        default_factory=list, description="Representative posts"
    )


class TopicEdge(BaseModel):
    """An edge between topics (co-occurrence)."""

    source: str = Field(description="Source topic ID")
    target: str = Field(description="Target topic ID")
    weight: float = Field(ge=0, description="Co-occurrence strength")
    shared_posts: int = Field(
        default=0, ge=0, description="Posts mentioning both topics"
    )


class TopicHistory(BaseModel):
    """Historical pulse data for a topic."""

    topic_id: str = Field(description="Topic identifier")
    timestamp: datetime = Field(description="Data capture timestamp")
    pulse_score: float = Field(description="Pulse score at this time")
    velocity: float = Field(description="Velocity at this time")
    mention_count: int = Field(description="Mentions at this time")


class ClusterInfo(BaseModel):
    """Information about a topic cluster."""

    id: str = Field(description="Cluster identifier")
    topic_ids: list[str] = Field(description="Topic IDs in this cluster")
    collective_velocity: float = Field(description="Aggregate cluster momentum")
    size: int = Field(description="Number of topics in cluster")


class GraphResponse(BaseModel):
    """Response containing the pulse graph."""

    nodes: list[TopicNode] = Field(description="Topic nodes in the graph")
    edges: list[TopicEdge] = Field(description="Edges between topics")
    clusters: list[ClusterInfo] = Field(
        default_factory=list, description="Topic clusters"
    )
    captured_at: datetime = Field(description="Graph snapshot timestamp")
    data_source: str = Field(
        description="Data source: 'live' from HN API or 'mock' fallback"
    )
    warning: str | None = Field(
        default=None,
        description="Warning message when using fallback data",
    )


class PulseResponse(BaseModel):
    """Response containing current pulse state."""

    topics: list[TopicNode] = Field(description="Active topics")
    clusters: list[ClusterInfo] = Field(
        default_factory=list, description="Topic clusters"
    )
    snapshot_id: str = Field(description="Unique snapshot identifier")
    captured_at: datetime = Field(description="Data capture timestamp")
    data_source: str = Field(
        description="Data source: 'live' from HN API or 'mock' fallback"
    )
    total_count: int = Field(
        description="Total number of topics matching filters (before pagination)"
    )
    warning: str | None = Field(
        default=None,
        description="Warning message when using fallback data",
    )


class LiveTopicResponse(BaseModel):
    """A topic with real computed metrics."""

    slug: str = Field(description="URL-safe topic identifier")
    label: str = Field(description="Human-readable topic name")
    pulse_score: float = Field(description="Combined pulse score from 0-1")
    velocity: float = Field(
        description="Relative popularity vs other topics (>1 = above avg)"
    )
    temporal_velocity: float | None = Field(
        default=None,
        description=(
            "True velocity vs historical baseline (>1 = growing, null = no history)"
        ),
    )
    mention_count: int = Field(description="Total mentions in time window")
    unique_authors: int = Field(description="Distinct authors discussing topic")
    centrality: float = Field(description="Network importance score")
    pulse_rank: int = Field(description="Rank by pulse score (1=highest)")
    mention_rank: int = Field(description="Rank by mention count (1=highest)")
    rank_difference: int = Field(description="Pulse rank minus mention rank")
    sample_posts: list[SamplePost] = Field(description="Representative posts")


class LivePulseResponse(BaseModel):
    """Response with real computed pulse data."""

    topics: list[LiveTopicResponse] = Field(description="Computed topic data")
    stories_analyzed: int = Field(description="Number of HN stories analyzed")
    captured_at: datetime = Field(description="Data capture timestamp")
    hypothesis_evidence: str = Field(description="Explanation of ranking differences")
    data_source: str = Field(description="Data source: 'live' or 'mock'")
    total_count: int = Field(description="Total number of topics (before pagination)")


class RankComparisonResponse(BaseModel):
    """Side-by-side comparison of pulse vs mention ranking."""

    pulse_ranking: list[str] = Field(description="Topic slugs in pulse score order")
    mention_ranking: list[str] = Field(description="Topic slugs in mention count order")
    differences: list[dict[str, Any]] = Field(
        description="Topics with significant rank differences"
    )
    hypothesis_supported: bool = Field(
        description="Whether pulse differs from mentions"
    )
    explanation: str = Field(description="Analysis of ranking differences")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(description="Error message describing what went wrong")
