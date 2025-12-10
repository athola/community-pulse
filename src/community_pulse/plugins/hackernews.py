"""Hacker News data source plugin.

Fetches posts from the official Hacker News Firebase API.
Documentation: https://github.com/HackerNews/API
"""

from datetime import datetime, timezone

import httpx

from community_pulse.plugins.base import RawPost

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ITEM_URL = "https://news.ycombinator.com/item?id="


class HackerNewsPlugin:
    """Hacker News data source plugin.

    Fetches stories from the HN top stories feed using their Firebase API.
    Converts HN items to normalized RawPost format.

    Usage:
        plugin = HackerNewsPlugin()
        posts = plugin.fetch_posts(limit=100)
        for post in posts:
            print(f"{post.title} by {post.author}")
            print(f"  {post.url}")
    """

    name: str = "hackernews"

    def __init__(self, timeout: float = 30.0):
        """Initialize with HTTP client settings."""
        self.client = httpx.Client(timeout=timeout)

    def __del__(self) -> None:
        """Clean up HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

    def _fetch_story_ids(self, endpoint: str = "topstories") -> list[int]:
        """Fetch story IDs from a specific endpoint."""
        resp = self.client.get(f"{HN_API_BASE}/{endpoint}.json")
        resp.raise_for_status()
        result: list[int] = resp.json()
        return result

    def _fetch_item(self, item_id: int) -> dict | None:
        """Fetch a single HN item by ID."""
        try:
            resp = self.client.get(f"{HN_API_BASE}/item/{item_id}.json")
            resp.raise_for_status()
            result: dict = resp.json()
            return result
        except Exception:
            return None

    def fetch_posts(self, limit: int = 100) -> list[RawPost]:
        """Fetch top stories from Hacker News."""
        story_ids = self._fetch_story_ids("topstories")[:limit]
        posts: list[RawPost] = []

        for story_id in story_ids:
            item = self._fetch_item(story_id)
            if not item:
                continue

            # Skip deleted, dead, or non-story items
            if item.get("deleted") or item.get("dead"):
                continue
            if item.get("type") != "story":
                continue

            # Convert to RawPost
            post = RawPost(
                id=str(item["id"]),
                title=item.get("title", "Untitled"),
                content=item.get("text", ""),  # Only present for Ask HN/Show HN
                author=item.get("by", "anonymous"),
                url=self.get_post_url(str(item["id"])),
                score=item.get("score", 0),
                comment_count=item.get("descendants", 0),
                posted_at=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc)
                if item.get("time")
                else None,
                metadata={
                    "type": item.get("type"),
                    "external_url": item.get("url"),  # Link to external article
                },
            )
            posts.append(post)

        return posts

    def get_post_url(self, post_id: str) -> str:
        """Generate HN discussion URL for a post."""
        return f"{HN_ITEM_URL}{post_id}"
