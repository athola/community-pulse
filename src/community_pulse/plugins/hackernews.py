"""Hacker News data source plugin.

Fetches posts from the official Hacker News Firebase API.
Documentation: https://github.com/HackerNews/API
"""

import logging
from datetime import datetime, timezone
from time import time
from typing import Any, Literal, cast

import httpx

from community_pulse.plugins.base import RawPost

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ITEM_URL = "https://news.ycombinator.com/item?id="


class HackerNewsPlugin:
    """Hacker News data source plugin.

    Fetches stories from the HN top stories feed using their Firebase API.
    Converts HN items to normalized RawPost format.

    Implements in-memory caching to reduce API calls:
    - Story IDs cached for 5 minutes (300 seconds)
    - Individual items cached for 2 minutes (120 seconds)

    Usage (recommended - context manager for automated cleanup):
        with HackerNewsPlugin() as plugin:
            posts = plugin.fetch_posts(limit=100)
            for post in posts:
                print(f"{post.title} by {post.author}")

    Alternative (manual cleanup required):
        plugin = HackerNewsPlugin()
        try:
            posts = plugin.fetch_posts(limit=100)
        finally:
            plugin.close()
    """

    name: str = "hackernews"

    def __init__(
        self,
        timeout: float = 30.0,
        story_ids_cache_ttl: float = 300.0,
        item_cache_ttl: float = 120.0,
    ):
        """Initialize with HTTP client settings and cache configuration.

        Args:
            timeout: HTTP read timeout in seconds
            story_ids_cache_ttl: Cache TTL for story IDs in seconds (default: 300)
            item_cache_ttl: Cache TTL for individual items in seconds (default: 120)

        """
        self.client = httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0)
        )
        self._cache: dict[str, tuple[float, Any]] = {}
        self._story_ids_cache_ttl = story_ids_cache_ttl
        self._item_cache_ttl = item_cache_ttl

    def __enter__(self) -> "HackerNewsPlugin":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> Literal[False]:
        """Context manager exit - performs cleanup."""
        self.close()
        return False

    def close(self) -> None:
        """Explicitly close the HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

    def __del__(self) -> None:
        """Clean up HTTP client."""
        self.close()

    def _get_cached(self, key: str, ttl: float) -> Any | None:
        """Retrieve value from cache if not expired.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            Cached value if present and not expired, None otherwise

        """
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time() - timestamp < ttl:
                logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                logger.debug(f"Cache expired for key: {key}")
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Store value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache

        """
        self._cache[key] = (time(), value)
        logger.debug(f"Cached value for key: {key}")

    def clear_cache(self) -> None:
        """Clear all cached data.

        Useful for testing or forcing fresh data fetches.
        """
        self._cache.clear()
        logger.debug("Cache cleared")

    def _fetch_story_ids(self, endpoint: str = "topstories") -> list[int]:
        """Fetch story IDs from a specific endpoint.

        Results are cached for story_ids_cache_ttl seconds (default: 300).

        Args:
            endpoint: API endpoint name (e.g., "topstories", "newstories")

        Returns:
            List of story IDs (empty list if HN API is unavailable)

        """
        cache_key = f"story_ids:{endpoint}"

        # Check cache first
        cached = self._get_cached(cache_key, self._story_ids_cache_ttl)
        if cached is not None:
            return cast(list[int], cached)

        # Fetch fresh data with error handling
        try:
            resp = self.client.get(f"{HN_API_BASE}/{endpoint}.json")
            resp.raise_for_status()
            result: list[int] = resp.json()

            # Store in cache
            self._set_cached(cache_key, result)

            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HN API error fetching {endpoint}: HTTP {e.response.status_code}. "
                "Service may be temporarily unavailable."
            )
            return []
        except httpx.RequestError as e:
            logger.error(
                f"Network error fetching {endpoint} from HN API: {e}. "
                "Check internet connectivity."
            )
            return []
        except ValueError as e:
            logger.error(f"Invalid JSON response from HN API for {endpoint}: {e}")
            return []

    def _fetch_item(self, item_id: int) -> dict[str, Any] | None:
        """Fetch a single HN item by ID.

        Results are cached for item_cache_ttl seconds (default: 120).

        Args:
            item_id: HN item ID

        Returns:
            Item data dict or None if error occurs

        """
        cache_key = f"item:{item_id}"

        # Check cache first
        cached = self._get_cached(cache_key, self._item_cache_ttl)
        if cached is not None:
            return cast(dict[str, Any], cached)

        # Fetch fresh data
        try:
            resp = self.client.get(f"{HN_API_BASE}/item/{item_id}.json")
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()

            # Store in cache
            self._set_cached(cache_key, result)

            return result
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP error fetching item {item_id}: {e.response.status_code}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching item {item_id}: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON decode error for item {item_id}: {e}")
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
