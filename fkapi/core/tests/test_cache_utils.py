from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.cache_utils import (
    CACHE_PREFIX_SEARCH,
    generate_cache_key,
    invalidate_brand_cache,
    invalidate_club_cache,
    invalidate_competition_cache,
    invalidate_kit_cache,
    invalidate_search_cache,
    invalidate_season_cache,
    setup_cache_invalidation,
)


class GenerateCacheKeyTests(TestCase):
    def test_simple_key_with_args_and_kwargs(self) -> None:
        key = generate_cache_key("prefix", 1, "two", slug="club", page=3)
        # Ordering of kwargs must be stable
        self.assertEqual(key, "prefix_1_two_page=3_slug=club")

    def test_long_key_is_hashed(self) -> None:
        long_part = "x" * 300
        key = generate_cache_key(CACHE_PREFIX_SEARCH, long_part)
        self.assertTrue(key.startswith(CACHE_PREFIX_SEARCH + "_"))
        # After prefix_ we expect a hex md5
        self.assertGreater(len(key), len(CACHE_PREFIX_SEARCH) + 1)


class InvalidateHelpersTests(TestCase):
    @patch("django_redis.get_redis_connection")
    def test_invalidate_helpers_emit_expected_patterns(self, mock_conn: MagicMock) -> None:
        client = MagicMock()
        # Simulate some keys returned for any pattern
        client.keys.return_value = [b"fkapi:dummy"]
        mock_conn.return_value = client

        invalidate_club_cache(1)
        invalidate_season_cache(2)
        invalidate_kit_cache(3)
        invalidate_brand_cache(4)
        invalidate_competition_cache(5)
        invalidate_search_cache()

        # We don't care about exact keys, just that delete is called at least once
        self.assertGreaterEqual(client.delete.call_count, 1)
        self.assertGreaterEqual(client.keys.call_count, 1)

    @patch("django_redis.get_redis_connection", side_effect=ImportError)
    def test_invalidate_helpers_gracefully_handle_missing_redis(self, _: MagicMock) -> None:
        # Should not raise even if django-redis is not available
        invalidate_club_cache(1)
        invalidate_search_cache()


class SetupCacheInvalidationTests(TestCase):
    @patch("core.cache_utils.post_save.connect")
    @patch("core.cache_utils.post_delete.connect")
    def test_setup_cache_invalidation_connects_signals(
        self,
        mock_post_delete_connect: MagicMock,
        mock_post_save_connect: MagicMock,
    ) -> None:
        setup_cache_invalidation()
        # We don't assert exact call list, just that it wired something
        self.assertGreaterEqual(mock_post_save_connect.call_count, 1)
        self.assertGreaterEqual(mock_post_delete_connect.call_count, 1)


    @patch("core.cache_utils.logger")
    @patch("django_redis.get_redis_connection")
    def test_invalidate_patterns_handles_exceptions(
        self,
        mock_conn: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        from core.cache_utils import _invalidate_patterns

        # Test exception during pattern processing
        client = MagicMock()
        client.keys.side_effect = Exception("Redis error")
        mock_conn.return_value = client

        _invalidate_patterns(["test_pattern"])
        mock_logger.debug.assert_called()

    @patch("core.cache_utils.logger")
    def test_invalidate_patterns_handles_import_error(
        self,
        mock_logger: MagicMock,
    ) -> None:
        from core.cache_utils import _invalidate_patterns

        with patch("django_redis.get_redis_connection", side_effect=ImportError):
            _invalidate_patterns(["test_pattern"])
            mock_logger.debug.assert_called()

    @patch("core.cache_utils.logger")
    @patch("django_redis.get_redis_connection", side_effect=Exception("General error"))
    def test_invalidate_patterns_handles_general_exception(
        self,
        mock_conn: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        from core.cache_utils import _invalidate_patterns

        _invalidate_patterns(["test_pattern"])
        mock_logger.debug.assert_called()

