"""Pydantic models for pulse API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class TopicNode(BaseModel):
    """A topic node in the pulse graph."""

    id: str
    slug: str
    label: str
    pulse_score: float = Field(ge=0, le=1)
    velocity: float = Field(default=1.0)
    centrality: float = Field(default=0.0, ge=0, le=1)
    mention_count: int = Field(default=0, ge=0)
    unique_authors: int = Field(default=0, ge=0)


class TopicEdge(BaseModel):
    """An edge between topics (co-occurrence)."""

    source: str
    target: str
    weight: float = Field(ge=0)
    shared_posts: int = Field(default=0, ge=0)


class TopicHistory(BaseModel):
    """Historical pulse data for a topic."""

    topic_id: str
    timestamp: datetime
    pulse_score: float
    velocity: float
    mention_count: int


class ClusterInfo(BaseModel):
    """Information about a topic cluster."""

    id: str
    topic_ids: list[str]
    collective_velocity: float
    size: int


class GraphResponse(BaseModel):
    """Response containing the pulse graph."""

    nodes: list[TopicNode]
    edges: list[TopicEdge]
    clusters: list[ClusterInfo] = Field(default_factory=list)
    captured_at: datetime


class PulseResponse(BaseModel):
    """Response containing current pulse state."""

    topics: list[TopicNode]
    clusters: list[ClusterInfo] = Field(default_factory=list)
    snapshot_id: str
    captured_at: datetime
