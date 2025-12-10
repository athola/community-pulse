"""Base protocol for data source plugins."""

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class RawPost:
    """Normalized post data from any community platform.

    This is the common format that all plugins convert their API data to.
    The pulse computation service works with RawPosts regardless of source.
    """

    id: str
    title: str
    content: str
    author: str
    url: str
    score: int
    comment_count: int
    posted_at: datetime | None = None
    metadata: dict | None = None  # Platform-specific extra data


@runtime_checkable
class DataSourcePlugin(Protocol):
    """Protocol for community data source plugins.

    Implement this to add support for a new platform (Reddit, Discord, etc.)
    """

    name: str  # Unique identifier for this plugin

    @abstractmethod
    def fetch_posts(self, limit: int = 100) -> list[RawPost]:
        """Fetch posts from the community platform."""
        ...

    def get_post_url(self, post_id: str) -> str:
        """Generate URL for a specific post.

        Override if URL format is complex or requires auth.
        """
        return f"#{post_id}"  # Default placeholder
