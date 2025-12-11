"""HTTP error handling tests for HackerNewsPlugin.

Tests focus on increasing coverage for error handling paths in:
- _fetch_item() HTTP status errors (lines 74-82)
- Timeout exceptions
- JSON decode errors
- Network errors
- Context manager cleanup (lines 44, 48-49)
"""

import logging
from unittest.mock import Mock, patch

import httpx

from community_pulse.plugins.hackernews import HackerNewsPlugin


class TestHTTPStatusErrors:
    """Test HTTP status error handling in _fetch_item()."""

    def test_fetch_item_404_returns_none(self, caplog) -> None:
        """Test that 404 errors return None and log warning."""
        plugin = HackerNewsPlugin()

        # Create mock response with 404 status
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.url = "https://hacker-news.firebaseio.com/v0/item/12345.json"

        # Create the exception
        status_error = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = status_error

            with caplog.at_level(logging.WARNING):
                result = plugin._fetch_item(12345)

            assert result is None
            assert "HTTP error fetching item 12345" in caplog.text
            assert "404" in caplog.text

    def test_fetch_item_500_returns_none(self, caplog) -> None:
        """Test that 500 errors return None and log warning."""
        plugin = HackerNewsPlugin()

        # Create mock response with 500 status
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.url = "https://hacker-news.firebaseio.com/v0/item/67890.json"

        status_error = httpx.HTTPStatusError(
            "Internal Server Error", request=Mock(), response=mock_response
        )

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = status_error

            with caplog.at_level(logging.WARNING):
                result = plugin._fetch_item(67890)

            assert result is None
            assert "HTTP error fetching item 67890" in caplog.text
            assert "500" in caplog.text

    def test_fetch_item_403_returns_none(self, caplog) -> None:
        """Test that 403 errors return None and log warning."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.url = "https://hacker-news.firebaseio.com/v0/item/11111.json"

        status_error = httpx.HTTPStatusError(
            "Forbidden", request=Mock(), response=mock_response
        )

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = status_error

            with caplog.at_level(logging.WARNING):
                result = plugin._fetch_item(11111)

            assert result is None
            assert "HTTP error fetching item 11111" in caplog.text
            assert "403" in caplog.text


class TestTimeoutErrors:
    """Test timeout handling in _fetch_item()."""

    def test_fetch_item_timeout_returns_none(self, caplog) -> None:
        """Test that timeout exceptions return None and log error."""
        plugin = HackerNewsPlugin()

        timeout_error = httpx.TimeoutException("Read timeout")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.side_effect = timeout_error

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(99999)

            assert result is None
            assert "Request error fetching item 99999" in caplog.text

    def test_fetch_item_read_timeout_returns_none(self, caplog) -> None:
        """Test that read timeout returns None and logs error."""
        plugin = HackerNewsPlugin()

        read_timeout = httpx.ReadTimeout("Read operation timed out")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.side_effect = read_timeout

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(88888)

            assert result is None
            assert "Request error fetching item 88888" in caplog.text

    def test_timeout_configuration(self) -> None:
        """Test that timeout is configurable via constructor."""
        custom_timeout = 60.0
        plugin = HackerNewsPlugin(timeout=custom_timeout)

        # Verify timeout settings
        assert plugin.client.timeout.read == custom_timeout
        assert plugin.client.timeout.connect == 5.0
        assert plugin.client.timeout.write == 5.0
        assert plugin.client.timeout.pool == 5.0


class TestJSONDecodeErrors:
    """Test JSON decode error handling."""

    def test_fetch_item_malformed_json_returns_none(self, caplog) -> None:
        """Test that malformed JSON returns None and logs error."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()  # No HTTP error
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(77777)

            assert result is None
            assert "JSON decode error for item 77777" in caplog.text

    def test_fetch_item_empty_response_body(self, caplog) -> None:
        """Test that empty response body is handled gracefully."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = ValueError("Expecting value")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(66666)

            assert result is None
            assert "JSON decode error for item 66666" in caplog.text

    def test_fetch_item_json_decode_error(self, caplog) -> None:
        """Test specific JSONDecodeError handling."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        # ValueError is the base class for json.JSONDecodeError
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(55555)

            assert result is None
            assert "JSON decode error for item 55555" in caplog.text


class TestNetworkErrors:
    """Test network error handling."""

    def test_fetch_item_connection_refused(self, caplog) -> None:
        """Test that connection refused returns None and logs error."""
        plugin = HackerNewsPlugin()

        connect_error = httpx.ConnectError("Connection refused")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.side_effect = connect_error

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(44444)

            assert result is None
            assert "Request error fetching item 44444" in caplog.text

    def test_fetch_item_connection_timeout(self, caplog) -> None:
        """Test that connection timeout returns None and logs error."""
        plugin = HackerNewsPlugin()

        connect_timeout = httpx.ConnectTimeout("Connection timed out")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.side_effect = connect_timeout

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(33333)

            assert result is None
            assert "Request error fetching item 33333" in caplog.text

    def test_fetch_item_network_error(self, caplog) -> None:
        """Test generic network error handling."""
        plugin = HackerNewsPlugin()

        network_error = httpx.NetworkError("Network unreachable")

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.side_effect = network_error

            with caplog.at_level(logging.ERROR):
                result = plugin._fetch_item(22222)

            assert result is None
            assert "Request error fetching item 22222" in caplog.text


class TestContextManager:
    """Test context manager functionality and cleanup."""

    def test_context_manager_enter_returns_self(self) -> None:
        """Test that __enter__ returns self."""
        plugin = HackerNewsPlugin()
        with plugin as p:
            assert p is plugin

    def test_context_manager_exit_closes_client(self) -> None:
        """Test that __exit__ calls close()."""
        plugin = HackerNewsPlugin()

        # Spy on the close method using unittest.mock
        from unittest.mock import patch  # noqa: PLC0415

        with patch.object(plugin, "close", wraps=plugin.close) as mock_close:
            with plugin:
                pass
            mock_close.assert_called_once()

    def test_context_manager_exit_returns_false(self) -> None:
        """Test that __exit__ returns False (doesn't suppress exceptions)."""
        plugin = HackerNewsPlugin()
        result = plugin.__exit__(None, None, None)
        assert result is False

    def test_close_method_closes_http_client(self) -> None:
        """Test that close() method closes the HTTP client."""
        plugin = HackerNewsPlugin()

        # Mock the client's close method
        with patch.object(plugin.client, "close") as mock_close:
            plugin.close()
            mock_close.assert_called_once()

    def test_close_method_handles_missing_client(self) -> None:
        """Test that close() handles missing client gracefully."""
        plugin = HackerNewsPlugin()
        del plugin.client

        # Should not raise an error
        plugin.close()

    def test_context_manager_with_exception(self) -> None:
        """Test that context manager cleans up even when exception occurs."""
        plugin = HackerNewsPlugin()

        with patch.object(plugin.client, "close") as mock_close:
            try:
                with plugin:
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # close() should still have been called
            mock_close.assert_called_once()

    def test_destructor_calls_close(self) -> None:
        """Test that __del__ calls close()."""
        plugin = HackerNewsPlugin()

        with patch.object(plugin.client, "close") as mock_close:
            plugin.__del__()
            mock_close.assert_called_once()


class TestFetchPostsErrorHandling:
    """Test error handling in fetch_posts() method."""

    def test_fetch_posts_skips_failed_items(self, caplog) -> None:
        """Test that fetch_posts() skips items that fail to fetch."""
        plugin = HackerNewsPlugin()

        # Mock _fetch_story_ids to return test IDs
        test_ids = [1, 2, 3, 4, 5]
        with patch.object(plugin, "_fetch_story_ids") as mock_fetch_ids:
            mock_fetch_ids.return_value = test_ids

            # Mock _fetch_item to fail for some items
            def mock_fetch_item(item_id):
                if item_id in [2, 4]:  # Fail for items 2 and 4
                    return None
                return {
                    "id": item_id,
                    "type": "story",
                    "by": f"user{item_id}",
                    "time": 1704067200,
                    "title": f"Story {item_id}",
                    "score": 10 * item_id,
                }

            with patch.object(plugin, "_fetch_item") as mock_item:
                mock_item.side_effect = mock_fetch_item

                posts = plugin.fetch_posts(limit=5)

                # Should only get 3 posts (1, 3, 5)
                assert len(posts) == 3
                assert posts[0].id == "1"
                assert posts[1].id == "3"
                assert posts[2].id == "5"

    def test_fetch_posts_handles_all_failed_items(self) -> None:
        """Test fetch_posts when all items fail to fetch."""
        plugin = HackerNewsPlugin()

        test_ids = [1, 2, 3]
        with patch.object(plugin, "_fetch_story_ids") as mock_fetch_ids:
            mock_fetch_ids.return_value = test_ids

            # All items fail
            with patch.object(plugin, "_fetch_item") as mock_item:
                mock_item.return_value = None

                posts = plugin.fetch_posts(limit=3)

                assert len(posts) == 0

    def test_fetch_posts_skips_deleted_items(self) -> None:
        """Test that fetch_posts skips deleted items."""
        plugin = HackerNewsPlugin()

        test_ids = [1, 2, 3]
        with patch.object(plugin, "_fetch_story_ids") as mock_fetch_ids:
            mock_fetch_ids.return_value = test_ids

            def mock_fetch_item(item_id):
                if item_id == 2:
                    return {"id": item_id, "deleted": True}
                return {
                    "id": item_id,
                    "type": "story",
                    "by": f"user{item_id}",
                    "time": 1704067200,
                    "title": f"Story {item_id}",
                    "score": 10,
                }

            with patch.object(plugin, "_fetch_item") as mock_item:
                mock_item.side_effect = mock_fetch_item

                posts = plugin.fetch_posts(limit=3)

                # Should skip deleted item 2
                assert len(posts) == 2
                assert posts[0].id == "1"
                assert posts[1].id == "3"

    def test_fetch_posts_skips_dead_items(self) -> None:
        """Test that fetch_posts skips dead items."""
        plugin = HackerNewsPlugin()

        test_ids = [1, 2, 3]
        with patch.object(plugin, "_fetch_story_ids") as mock_fetch_ids:
            mock_fetch_ids.return_value = test_ids

            def mock_fetch_item(item_id):
                if item_id == 2:
                    return {"id": item_id, "dead": True, "type": "story"}
                return {
                    "id": item_id,
                    "type": "story",
                    "by": f"user{item_id}",
                    "time": 1704067200,
                    "title": f"Story {item_id}",
                    "score": 10,
                }

            with patch.object(plugin, "_fetch_item") as mock_item:
                mock_item.side_effect = mock_fetch_item

                posts = plugin.fetch_posts(limit=3)

                # Should skip dead item 2
                assert len(posts) == 2
                assert posts[0].id == "1"
                assert posts[1].id == "3"

    def test_fetch_posts_skips_non_story_items(self) -> None:
        """Test that fetch_posts skips non-story items."""
        plugin = HackerNewsPlugin()

        test_ids = [1, 2, 3]
        with patch.object(plugin, "_fetch_story_ids") as mock_fetch_ids:
            mock_fetch_ids.return_value = test_ids

            def mock_fetch_item(item_id):
                item_type = "comment" if item_id == 2 else "story"
                return {
                    "id": item_id,
                    "type": item_type,
                    "by": f"user{item_id}",
                    "time": 1704067200,
                    "title": f"Story {item_id}" if item_type == "story" else None,
                    "text": "Comment text" if item_type == "comment" else None,
                    "score": 10,
                }

            with patch.object(plugin, "_fetch_item") as mock_item:
                mock_item.side_effect = mock_fetch_item

                posts = plugin.fetch_posts(limit=3)

                # Should skip comment item 2
                assert len(posts) == 2
                assert posts[0].id == "1"
                assert posts[1].id == "3"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_fetch_item_with_mixed_errors(self, caplog) -> None:
        """Test multiple different errors in sequence."""
        plugin = HackerNewsPlugin()

        errors = [
            httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=Mock(status_code=404)
            ),
            httpx.TimeoutException("Timeout"),
            ValueError("JSON error"),
            httpx.ConnectError("Connection failed"),
        ]

        for i, error in enumerate(errors):
            with patch.object(plugin.client, "get") as mock_get:
                if isinstance(error, httpx.HTTPStatusError):
                    mock_get.return_value.raise_for_status.side_effect = error
                elif isinstance(error, ValueError):
                    mock_response = Mock()
                    mock_response.raise_for_status = Mock()
                    mock_response.json.side_effect = error
                    mock_get.return_value = mock_response
                else:
                    mock_get.side_effect = error

                result = plugin._fetch_item(1000 + i)
                assert result is None

    def test_plugin_reusability_after_errors(self) -> None:
        """Test that plugin can be reused after encountering errors."""
        plugin = HackerNewsPlugin()

        # First call fails
        with patch.object(plugin.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")
            result1 = plugin._fetch_item(1)
            assert result1 is None

        # Second call succeeds
        with patch.object(plugin.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "id": 2,
                "type": "story",
                "title": "Test",
            }
            mock_get.return_value = mock_response

            result2 = plugin._fetch_item(2)
            assert result2 is not None
            assert result2["id"] == 2

    def test_fetch_posts_with_zero_limit(self) -> None:
        """Test fetch_posts with limit=0."""
        plugin = HackerNewsPlugin()

        with patch.object(plugin, "_fetch_story_ids") as mock_fetch_ids:
            mock_fetch_ids.return_value = [1, 2, 3, 4, 5]

            posts = plugin.fetch_posts(limit=0)

            assert len(posts) == 0


class TestFetchStoryIds:
    """Test _fetch_story_ids method to achieve 100% coverage."""

    def test_fetch_story_ids_success(self) -> None:
        """Test successful fetching of story IDs."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = [1, 2, 3, 4, 5]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            story_ids = plugin._fetch_story_ids("topstories")

            assert story_ids == [1, 2, 3, 4, 5]
            mock_get.assert_called_once_with(
                "https://hacker-news.firebaseio.com/v0/topstories.json"
            )

    def test_fetch_story_ids_different_endpoint(self) -> None:
        """Test fetching from different endpoint."""
        plugin = HackerNewsPlugin()

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = [10, 20, 30]

        with patch.object(plugin.client, "get") as mock_get:
            mock_get.return_value = mock_response

            story_ids = plugin._fetch_story_ids("newstories")

            assert story_ids == [10, 20, 30]
            mock_get.assert_called_once_with(
                "https://hacker-news.firebaseio.com/v0/newstories.json"
            )
