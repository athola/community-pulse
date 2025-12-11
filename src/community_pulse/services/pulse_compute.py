"""Pulse computation service - runs analysis on community data via plugins."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from community_pulse.analysis.graph import (
    TopicGraphData,
    build_directed_graph,
    build_topic_graph,
    compute_all_centrality,
)
from community_pulse.analysis.velocity import compute_pulse_score
from community_pulse.ingest.topic_extractor import extract_topics
from community_pulse.plugins.base import DataSourcePlugin, RawPost
from community_pulse.plugins.hackernews import HackerNewsPlugin

logger = logging.getLogger(__name__)


@dataclass
class SamplePostData:
    """A sample post for display in results."""

    id: str
    title: str
    url: str
    score: int
    comment_count: int


@dataclass
class ComputedTopic:
    """A topic with computed pulse metrics from real data."""

    slug: str
    label: str
    pulse_score: float
    velocity: float
    mention_count: int
    unique_authors: int
    centrality: float
    sample_posts: list[SamplePostData] = field(default_factory=list)
    # For hypothesis validation - compare to simple ranking
    mention_rank: int = 0
    pulse_rank: int = 0


class PulseComputeService:
    """Service to compute pulse scores from any community data source."""

    # Topic slug to human-readable label
    TOPIC_LABELS = {
        "ai": "AI / Machine Learning",
        "rust": "Rust",
        "python": "Python",
        "javascript": "JavaScript",
        "golang": "Go",
        "database": "Databases",
        "cloud": "Cloud / Infrastructure",
        "security": "Security",
        "startup": "Startups",
        "open-source": "Open Source",
    }

    def __init__(self, plugin: DataSourcePlugin, num_posts: int = 100):
        """Initialize with a data source plugin."""
        self.plugin = plugin
        self.num_posts = num_posts

    def _extract_topics_from_posts(
        self, posts: list[RawPost]
    ) -> tuple[dict[str, list[tuple[RawPost, float]]], dict[str, set[str]]]:
        """Extract topics from posts and track authors."""
        topic_posts: dict[str, list[tuple[RawPost, float]]] = defaultdict(list)
        topic_authors: dict[str, set[str]] = defaultdict(set)

        for post in posts:
            topics = extract_topics(post.title, post.content)
            for slug, relevance in topics:
                topic_posts[slug].append((post, relevance))
                topic_authors[slug].add(post.author)

        return topic_posts, topic_authors

    def _build_cooccurrence_graph(
        self,
        topic_posts: dict[str, list[tuple[RawPost, float]]],
        topic_authors: dict[str, set[str]],
    ) -> list[TopicGraphData]:
        """Build co-occurrence graph data from topic posts."""
        cooccurrence: dict[tuple[str, str], int] = defaultdict(int)
        post_topics: dict[str, list[str]] = defaultdict(list)

        for slug, post_list in topic_posts.items():
            for post, _ in post_list:
                post_topics[post.id].append(slug)

        for _post_id, slugs in post_topics.items():
            for i, slug_a in enumerate(slugs):
                for slug_b in slugs[i + 1 :]:
                    key: tuple[str, str] = (
                        (slug_a, slug_b) if slug_a < slug_b else (slug_b, slug_a)
                    )
                    cooccurrence[key] += 1

        graph_data = []
        for (topic_a, topic_b), count in cooccurrence.items():
            shared_authors = topic_authors[topic_a] & topic_authors[topic_b]
            graph_data.append(
                TopicGraphData(
                    topic_a=topic_a,
                    topic_b=topic_b,
                    shared_posts=count,
                    shared_authors=len(shared_authors),
                )
            )

        return graph_data

    def _assign_ranks(self, topics: list[ComputedTopic]) -> list[ComputedTopic]:
        """Assign both mention and pulse ranks to topics."""
        by_mentions = sorted(topics, key=lambda t: t.mention_count, reverse=True)
        for i, topic in enumerate(by_mentions):
            topic.mention_rank = i + 1

        by_pulse = sorted(topics, key=lambda t: t.pulse_score, reverse=True)
        for i, topic in enumerate(by_pulse):
            topic.pulse_rank = i + 1

        return by_pulse

    def compute_pulse(self) -> list[ComputedTopic]:
        """Compute pulse scores from the configured data source."""
        posts = self.plugin.fetch_posts(limit=self.num_posts)
        if not posts:
            logger.warning(
                f"No posts fetched from {self.plugin.name} (requested {self.num_posts})"
            )
            return []

        topic_posts, topic_authors = self._extract_topics_from_posts(posts)
        if not topic_posts:
            logger.info(
                f"No topics extracted from {len(posts)} posts - check topic patterns"
            )
            return []

        logger.info(
            f"Computing pulse for {len(topic_posts)} topics from {len(posts)} posts"
        )

        graph_data = self._build_cooccurrence_graph(topic_posts, topic_authors)

        # Build both undirected and directed graphs for different centrality measures
        undirected, node_indices = build_topic_graph(graph_data)
        directed = build_directed_graph(graph_data, node_indices)

        # Compute all centrality metrics using appropriate graph types
        centrality_by_idx = compute_all_centrality(undirected, directed)

        idx_to_topic = {idx: slug for slug, idx in node_indices.items()}
        centrality = {
            idx_to_topic[idx]: metrics
            for idx, metrics in centrality_by_idx.items()
            if idx in idx_to_topic
        }

        max_authors = len({p.author for p in posts})
        computed_topics: list[ComputedTopic] = []

        for slug, post_list in topic_posts.items():
            mention_count = len(post_list)
            unique_authors = len(topic_authors[slug])

            topic_centrality = centrality.get(slug, {})
            eigenvector = topic_centrality.get("eigenvector", 0.0)
            betweenness = topic_centrality.get("betweenness", 0.0)
            pagerank = topic_centrality.get("pagerank", 0.0)

            avg_mentions = len(posts) / max(len(topic_posts), 1)
            velocity = mention_count / max(avg_mentions, 1)

            pulse = compute_pulse_score(
                velocity=velocity,
                eigenvector_centrality=eigenvector,
                betweenness_centrality=betweenness,
                unique_authors=unique_authors,
                max_authors=max(max_authors, 1),
                pagerank=pagerank,
            )

            sorted_posts = sorted(post_list, key=lambda x: x[0].score, reverse=True)
            sample_posts = [
                SamplePostData(
                    id=post.id,
                    title=post.title,
                    url=post.url,
                    score=post.score,
                    comment_count=post.comment_count,
                )
                for post, _ in sorted_posts[:3]
            ]

            computed_topics.append(
                ComputedTopic(
                    slug=slug,
                    label=self.TOPIC_LABELS.get(slug, slug.title()),
                    pulse_score=pulse,
                    velocity=velocity,
                    mention_count=mention_count,
                    unique_authors=unique_authors,
                    centrality=eigenvector,
                    sample_posts=sample_posts,
                )
            )

        return self._assign_ranks(computed_topics)


def compute_live_pulse(
    num_stories: int = 100,
    plugin: DataSourcePlugin | None = None,
) -> list[ComputedTopic]:
    """Compute live pulse scores from a data source."""
    if plugin is None:
        plugin = HackerNewsPlugin()

    service = PulseComputeService(plugin=plugin, num_posts=num_stories)
    return service.compute_pulse()
