"""Caching behavior tests for HackerNewsPlugin.

Tests verify that the in-memory cache:
- Reduces redundant API calls
- Respects TTL for story IDs (5 minutes / 300 seconds)
- Respects TTL for items (2 minutes / 120 seconds)
- Can be cleared manually
- Handles cache hits and misses correctly
"""

import logging
from time import sleep, time
from unittest.mock import Mock, patch

import httpx

from community_pulse.plugins.hackernews import HackerNewsPlugin


class TestCacheInfrastructure:
    """Test basic cache infrastructure."""

    def test_cache_initialized_empty(self) -> None:
        """Test that cache starts empty."""
        plugin = HackerNewsPlugin()
        assert len(plugin._cache) == 0

    def test_cache_ttl_configuration(self) -> None:
        """Test that cache TTL values are configurable."""
        plugin = HackerNewsPlugin(
            timeout=30.0, story_ids_cache_ttl=600.0, item_cache_ttl=180.0
        )
        assert plugin._story_ids_cache_ttl == 600.0
        assert plugin._item_cache_ttl == 180.0

    def test_default_cache_ttl_values(self) -> None:
        """Test default cache TTL values."""
        plugin = HackerNewsPlugin()
        assert plugin._story_ids_cache_ttl == 300.0  # 5 minutes
        assert plugin._item_cache_ttl == 120.0  # 2 minutes

    def test_clear_cache_empties_cache(self) -> None:
        """Test that clear_cache removes all cached data."""
        plugin = HackerNewsPlugin()

        # Add some data to cache
        plugin._set_cached("key1", "value1")
        plugin._set_cached("key2", "value2")
        assert len(plugin._cache) == 2

        # Clear cache
        plugin.clear_cache()
        assert len(plugin._cache) == 0

    def test_clear_cache_logs_debug_message(self, caplog) -> None:
        """Test that clear_cache logs a debug message."""
        plugin = HackerNewsPlugin()
        plugin._set_cached("key1", "value1")

        with caplog.at_level(logging.DEBUG):
            plugin.clear_cache()

        assert "Cache cleared" in caplog.text


class TestCacheHelperMethods:
    """Test _get_cached and _set_cached helper methods."""

    def test_set_cached_stores_value_with_timestamp(self) -> None:
        """Test that _set_cached stores value with current timestamp."""
        plugin = HackerNewsPlugin()
        before = time()

        plugin._set_cached("test_key", "test_value")

        assert "test_key" in plugin._cache
        timestamp, value = plugin._cache["test_key"]
        assert value == "test_value"
        assert before <= timestamp <= time()

    def test_set_cached_logs_debug_message(self, caplog) -> None:
        """Test that _set_cached logs a debug message."""
        plugin = HackerNewsPlugin()

        with caplog.at_level(logging.DEBUG):
            plugin._set_cached("test_key", "test_value")

        assert "Cached value for key: test_key" in caplog.text

    def test_get_cached_returns_none_for_missing_key(self) -> None:
        """Test that _get_cached returns None for non-existent key."""
        plugin = HackerNewsPlugin()
        result = plugin._get_cached("nonexistent", 60.0)
        assert result is None

    def test_get_cached_returns_value_within_ttl(self) -> None:
        """Test that _get_cached returns value when not expired."""
        plugin = HackerNewsPlugin()
        plugin._set_cached("test_key", "test_value")

        result = plugin._get_cached("test_key", 60.0)  # 60 second TTL
        assert result == "test_value"

    def test_get_cached_returns_none_after_ttl(self) -> None:
        """Test that _get_cached returns None after TTL expires."""
        plugin = HackerNewsPlugin()

        # Set cache with past timestamp (simulating expired cache)
        expired_timestamp = time() - 10.0  # 10 seconds ago
        plugin._cache["test_key"] = (expired_timestamp, "test_value")

        # Try to get with 5 second TTL (should be expired)
        result = plugin._get_cached("test_key", 5.0)
        assert result is None

    def test_get_cached_logs_cache_hit(self, caplog) -> None:
        """Test that _get_cached logs debug message on cache hit."""
        plugin = HackerNewsPlugin()
        plugin._set_cached("test_key", "test_value")

        with caplog.at_level(logging.DEBUG):
            plugin._get_cached("test_key", 60.0)

        assert "Cache hit for key: test_key" in caplog.text

    def test_get_cached_logs_cache_expired(self, caplog) -> None:
        """Test that _get_cached logs debug message when cache expired."""
        plugin = HackerNewsPlugin()

        # Set expired cache entry
        expired_timestamp = time() - 10.0
        plugin._cache["test_key"] = (expired_timestamp, "test_value")

        with caplog.at_level(logging.DEBUG):
            plugin._get_cached("test_key", 5.0)

        assert "Cache expired for key: test_key" in caplog.text


class TestStoryIDsCaching:
    """Test caching behavior for _fetch_story_ids."""

    def test_fetch_story_ids_caches_result(self) -> None:
        """Test that _fetch_story_ids caches the result."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = [1, 2, 3, 4, 5]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # First call should fetch from API
            result = plugin._fetch_story_ids("topstories")

            assert result == [1, 2, 3, 4, 5]
            assert "story_ids:topstories" in plugin._cache

    def test_fetch_story_ids_uses_cache_on_second_call(self) -> None:
        """Test that second call uses cache instead of API."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = [1, 2, 3, 4, 5]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # First call
            result1 = plugin._fetch_story_ids("topstories")
            assert mock_get.call_count == 1

            # Second call should use cache
            result2 = plugin._fetch_story_ids("topstories")
            assert mock_get.call_count == 1  # Still only 1 call
            assert result1 == result2

    def test_fetch_story_ids_separate_cache_per_endpoint(self) -> None:
        """Test that different endpoints have separate cache entries."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()

        def json_side_effect():
            # Return different data based on URL
            if "topstories" in mock_response.url:
                return [1, 2, 3]
            else:
                return [4, 5, 6]

        mock_response.json.side_effect = json_side_effect

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # Mock URL for different endpoints
            mock_response.url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            plugin._fetch_story_ids("topstories")

            mock_response.url = "https://hacker-news.firebaseio.com/v0/newstories.json"
            plugin._fetch_story_ids("newstories")

            # Should have 2 separate cache entries
            assert "story_ids:topstories" in plugin._cache
            assert "story_ids:newstories" in plugin._cache

    def test_fetch_story_ids_respects_ttl(self) -> None:
        """Test that cached story IDs expire after TTL."""
        # Use short TTL for testing
        plugin = HackerNewsPlugin(story_ids_cache_ttl=0.1)  # 100ms

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = [1, 2, 3]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # First call
            plugin._fetch_story_ids("topstories")
            assert mock_get.call_count == 1

            # Wait for cache to expire
            sleep(0.15)

            # Second call should fetch fresh data
            plugin._fetch_story_ids("topstories")
            assert mock_get.call_count == 2

    def test_fetch_story_ids_cache_survives_multiple_accesses(self) -> None:
        """Test that cache works correctly for multiple successive accesses."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = [1, 2, 3, 4, 5]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # Multiple calls
            for _ in range(5):
                result = plugin._fetch_story_ids("topstories")
                assert result == [1, 2, 3, 4, 5]

            # Should only have made 1 API call
            assert mock_get.call_count == 1


class TestItemCaching:
    """Test caching behavior for _fetch_item."""

    def test_fetch_item_caches_result(self) -> None:
        """Test that _fetch_item caches the result."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"id": 123, "type": "story", "title": "Test"}

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            result = plugin._fetch_item(123)

            assert result == {"id": 123, "type": "story", "title": "Test"}
            assert "item:123" in plugin._cache

    def test_fetch_item_uses_cache_on_second_call(self) -> None:
        """Test that second call uses cache instead of API."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"id": 456, "type": "story", "title": "Test"}

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # First call
            result1 = plugin._fetch_item(456)
            assert mock_get.call_count == 1

            # Second call should use cache
            result2 = plugin._fetch_item(456)
            assert mock_get.call_count == 1  # Still only 1 call
            assert result1 == result2

    def test_fetch_item_separate_cache_per_id(self) -> None:
        """Test that different item IDs have separate cache entries."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = [
            {"id": 1, "title": "Item 1"},
            {"id": 2, "title": "Item 2"},
        ]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            result1 = plugin._fetch_item(1)
            result2 = plugin._fetch_item(2)

            # Should have 2 separate cache entries
            assert "item:1" in plugin._cache
            assert "item:2" in plugin._cache
            assert result1 is not None
            assert result2 is not None
            assert result1["id"] == 1
            assert result2["id"] == 2

    def test_fetch_item_respects_ttl(self) -> None:
        """Test that cached items expire after TTL."""
        # Use short TTL for testing
        plugin = HackerNewsPlugin(item_cache_ttl=0.1)  # 100ms

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"id": 789, "title": "Test"}

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # First call
            plugin._fetch_item(789)
            assert mock_get.call_count == 1

            # Wait for cache to expire
            sleep(0.15)

            # Second call should fetch fresh data
            plugin._fetch_item(789)
            assert mock_get.call_count == 2

    def test_fetch_item_does_not_cache_none_on_error(self) -> None:
        """Test that None results from errors are not cached."""
        plugin = HackerNewsPlugin()

        # Simulate an error
        with patch.object(plugin.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            # First call returns None
            result1 = plugin._fetch_item(999)
            assert result1 is None
            assert "item:999" not in plugin._cache

            # Set up successful response for second call
            mock_response = Mock(spec=httpx.Response)
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {"id": 999, "title": "Success"}
            mock_get.side_effect = None
            mock_get.return_value = mock_response

            # Second call should fetch successfully
            result2 = plugin._fetch_item(999)
            assert result2 == {"id": 999, "title": "Success"}


class TestCacheIntegration:
    """Test cache behavior in integrated scenarios."""

    def test_fetch_posts_benefits_from_item_cache(self) -> None:
        """Test that fetch_posts reuses cached items."""
        plugin = HackerNewsPlugin()

        # Pre-populate item cache
        item_data = {
            "id": 1,
            "type": "story",
            "by": "testuser",
            "time": 1704067200,
            "title": "Cached Story",
            "score": 100,
        }
        plugin._set_cached("item:1", item_data)

        # Mock story IDs but not item fetch
        with patch.object(plugin, "_fetch_story_ids") as mock_fetch_ids:
            mock_fetch_ids.return_value = [1]

            # Mock the client to verify it's not called for cached item
            with patch.object(plugin.client, "get") as mock_get:
                posts = plugin.fetch_posts(limit=1)

                # Should have 1 post from cache
                assert len(posts) == 1
                assert posts[0].id == "1"
                assert posts[0].title == "Cached Story"

                # Client should not be called for item
                # (only for story IDs if not cached).
                # Since we mocked _fetch_story_ids, client.get
                # should not be called at all
                assert mock_get.call_count == 0

    def test_clear_cache_forces_fresh_fetch(self) -> None:
        """Test that clearing cache forces fresh API calls."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = [1, 2, 3]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # First call
            plugin._fetch_story_ids("topstories")
            assert mock_get.call_count == 1

            # Clear cache
            plugin.clear_cache()

            # Next call should fetch again
            plugin._fetch_story_ids("topstories")
            assert mock_get.call_count == 2

    def test_context_manager_preserves_cache(self) -> None:
        """Test that using context manager doesn't clear cache."""
        with HackerNewsPlugin() as plugin:
            plugin._set_cached("test_key", "test_value")
            assert len(plugin._cache) == 1

        # Cache should still exist after context exit
        # (though the plugin itself is closed)

    def test_multiple_plugins_have_separate_caches(self) -> None:
        """Test that different plugin instances have separate caches."""
        plugin1 = HackerNewsPlugin()
        plugin2 = HackerNewsPlugin()

        plugin1._set_cached("key1", "value1")
        plugin2._set_cached("key2", "value2")

        # Each plugin should only have its own cache entry
        assert "key1" in plugin1._cache
        assert "key2" not in plugin1._cache

        assert "key2" in plugin2._cache
        assert "key1" not in plugin2._cache


class TestCachePerformance:
    """Test that caching improves performance."""

    def test_cache_reduces_api_calls_significantly(self) -> None:
        """Test that cache dramatically reduces API calls."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"id": 1, "title": "Test"}

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # Fetch same item 100 times
            for _ in range(100):
                plugin._fetch_item(1)

            # Should only make 1 API call due to cache
            assert mock_get.call_count == 1

    def test_cache_handles_mixed_hits_and_misses(self) -> None:
        """Test cache with mix of cache hits and misses."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()

        call_count = 0

        def json_side_effect():
            nonlocal call_count
            call_count += 1
            return {"id": call_count, "title": f"Item {call_count}"}

        mock_response.json.side_effect = json_side_effect

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            # Fetch items: 1, 2, 1, 3, 2, 1
            plugin._fetch_item(1)  # Miss
            plugin._fetch_item(2)  # Miss
            plugin._fetch_item(1)  # Hit
            plugin._fetch_item(3)  # Miss
            plugin._fetch_item(2)  # Hit
            plugin._fetch_item(1)  # Hit

            # Should only make 3 API calls (for IDs 1, 2, 3)
            assert mock_get.call_count == 3
