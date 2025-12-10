"""Pulse computation service - runs analysis on community data via plugins."""

from collections import defaultdict
from dataclasses import dataclass, field

from community_pulse.analysis.graph import (
    TopicGraphData,
    build_topic_graph,
    compute_centrality,
)
from community_pulse.analysis.velocity import compute_pulse_score
from community_pulse.ingest.topic_extractor import extract_topics
from community_pulse.plugins.base import DataSourcePlugin, RawPost


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
    """Service to compute pulse scores from any community data source.

    Uses the plugin system to fetch data, then runs the core analysis:
    1. Extract topics from posts
    2. Build co-occurrence graph
    3. Compute centrality metrics
    4. Calculate pulse scores using weighted formula
    5. Compare to simple mention-count ranking

    The algorithm is identical regardless of data source.
    """

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

    def compute_pulse(self) -> list[ComputedTopic]:  # noqa: PLR0912
        """Compute pulse scores from the configured data source."""
        # Step 1: Fetch posts via plugin
        posts = self.plugin.fetch_posts(limit=self.num_posts)
        if not posts:
            return []

        # Step 2: Extract topics from each post
        topic_posts: dict[str, list[tuple[RawPost, float]]] = defaultdict(list)
        topic_authors: dict[str, set[str]] = defaultdict(set)

        for post in posts:
            topics = extract_topics(post.title, post.content)
            for slug, relevance in topics:
                topic_posts[slug].append((post, relevance))
                topic_authors[slug].add(post.author)

        if not topic_posts:
            return []

        # Step 3: Build co-occurrence graph
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

        # Build graph data
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

        # Step 4: Compute centrality
        graph, node_indices = build_topic_graph(graph_data)
        centrality_by_idx = compute_centrality(graph)

        # Map node indices back to topic slugs
        idx_to_topic = {idx: slug for slug, idx in node_indices.items()}
        centrality = {
            idx_to_topic[idx]: metrics
            for idx, metrics in centrality_by_idx.items()
            if idx in idx_to_topic
        }

        # Step 5: Compute pulse scores
        max_authors = len({p.author for p in posts})
        computed_topics: list[ComputedTopic] = []

        for slug, post_list in topic_posts.items():
            mention_count = len(post_list)
            unique_authors = len(topic_authors[slug])

            # Get centrality (default 0 if topic not in graph)
            topic_centrality = centrality.get(slug, {})
            eigenvector = topic_centrality.get("eigenvector", 0.0)
            betweenness = topic_centrality.get("betweenness", 0.0)

            # Velocity: for POC, use mention count relative to average
            # In production, would compare to historical baseline
            avg_mentions = len(posts) / max(len(topic_posts), 1)
            velocity = mention_count / max(avg_mentions, 1)

            # Compute pulse score using our formula
            pulse = compute_pulse_score(
                velocity=velocity,
                eigenvector_centrality=eigenvector,
                betweenness_centrality=betweenness,
                unique_authors=unique_authors,
                max_authors=max(max_authors, 1),
            )

            # Get sample posts (top by score)
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

        # Step 6: Rank by both methods for comparison
        by_mentions = sorted(
            computed_topics, key=lambda t: t.mention_count, reverse=True
        )
        for i, topic in enumerate(by_mentions):
            topic.mention_rank = i + 1

        by_pulse = sorted(computed_topics, key=lambda t: t.pulse_score, reverse=True)
        for i, topic in enumerate(by_pulse):
            topic.pulse_rank = i + 1

        return by_pulse


def compute_live_pulse(
    num_stories: int = 100,
    plugin: DataSourcePlugin | None = None,
) -> list[ComputedTopic]:
    """Compute live pulse scores from a data source."""
    if plugin is None:
        # Lazy import to avoid circular dependency
        from community_pulse.plugins.hackernews import (  # noqa: PLC0415
            HackerNewsPlugin,
        )

        plugin = HackerNewsPlugin()

    service = PulseComputeService(plugin=plugin, num_posts=num_stories)
    return service.compute_pulse()
