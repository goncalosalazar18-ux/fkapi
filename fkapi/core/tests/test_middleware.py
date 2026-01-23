"""Tests for middleware."""

import time
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from core.middleware import (
    _get_client_ip,
    performance_monitoring_middleware,
    rate_limit_middleware,
)


class MiddlewareTests(TestCase):
    """Test cases for middleware functions."""

    def setUp(self):
        """Set up test fixtures."""
        from django.http import HttpResponse

        self.rf = RequestFactory()
        self.mock_get_response = Mock(return_value=HttpResponse())
        cache.clear()

    def test_get_client_ip_default(self):
        """Test client IP extraction without X-Forwarded-For."""
        request = self.rf.get("/api/test")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        ip = _get_client_ip(request)
        self.assertEqual(ip, "192.168.1.1")

    @override_settings(TRUST_X_FORWARDED_FOR=True)
    def test_get_client_ip_with_xff(self):
        """Test client IP extraction with X-Forwarded-For when enabled."""
        request = self.rf.get("/api/test", HTTP_X_FORWARDED_FOR="10.0.0.1, 192.168.1.1")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        ip = _get_client_ip(request)
        self.assertEqual(ip, "10.0.0.1")

    @override_settings(API_RATE_LIMIT={"RATE": "100/hour", "CACHE_PREFIX": "ratelimit"})
    def test_rate_limit_middleware_allows_requests(self):
        """Test that rate limiting allows requests under the limit."""
        cache.clear()
        middleware = rate_limit_middleware(self.mock_get_response)
        request = self.rf.get("/api/test")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.mock_get_response.called)

    @override_settings(API_RATE_LIMIT={"RATE": "2/hour", "CACHE_PREFIX": "ratelimit"})
    def test_rate_limit_middleware_blocks_excessive_requests(self):
        """Test that rate limiting blocks requests over the limit."""
        cache.clear()
        middleware = rate_limit_middleware(self.mock_get_response)
        request = self.rf.get("/api/test")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Make requests up to the limit
        middleware(request)
        middleware(request)

        # This should be blocked
        response = middleware(request)
        self.assertEqual(response.status_code, 403)

    @override_settings(API_RATE_LIMIT={"RATE": "1/hour", "CACHE_PREFIX": "ratelimit"})
    def test_rate_limit_middleware_ignores_non_api_paths(self):
        """Test that rate limiting only applies to API paths."""
        cache.clear()
        middleware = rate_limit_middleware(self.mock_get_response)
        request = self.rf.get("/admin/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Should not be rate limited
        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(SLOW_RESPONSE_THRESHOLD=0.01)
    def test_performance_middleware_logs_response_time(self):
        """Test that performance middleware logs response time."""
        with patch("core.middleware.performance_logger") as mock_logger:
            middleware = performance_monitoring_middleware(self.mock_get_response)
            request = self.rf.get("/api/test")

            response = middleware(request)

            self.assertEqual(response.status_code, 200)
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            self.assertIn("/api/test", str(call_args))

    @override_settings(SLOW_RESPONSE_THRESHOLD=0.01)
    def test_performance_middleware_tracks_slow_responses(self):
        """Test that performance middleware detects slow responses."""
        from django.http import HttpResponse

        with patch("core.middleware.performance_logger") as mock_logger:

            def slow_response(request):
                time.sleep(0.02)
                return HttpResponse()

            middleware = performance_monitoring_middleware(slow_response)
            request = self.rf.get("/api/test")

            response = middleware(request)

            self.assertEqual(response.status_code, 200)
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            self.assertIn("Slow response", str(call_args))

    @override_settings(SLOW_QUERY_THRESHOLD=0.01, LOG_DB_QUERIES=True, DEBUG=True)
    def test_performance_middleware_tracks_queries(self):
        """Test that performance middleware tracks database queries."""
        with patch("core.middleware.db_logger"):
            middleware = performance_monitoring_middleware(self.mock_get_response)
            request = self.rf.get("/api/test")

            response = middleware(request)

            self.assertEqual(response.status_code, 200)
            self.assertIn("X-Response-Time", response.headers)

    def test_performance_middleware_adds_response_headers(self):
        """Test that performance middleware adds response time header."""
        middleware = performance_monitoring_middleware(self.mock_get_response)
        request = self.rf.get("/api/test")

        response = middleware(request)

        self.assertIn("X-Response-Time", response.headers)
        if "X-Query-Count" in response.headers:
            query_count = int(response.headers["X-Query-Count"])
            self.assertGreaterEqual(query_count, 0)

    def test_performance_middleware_tracks_api_usage(self):
        """Test that performance middleware tracks API usage statistics."""
        from django.core.cache import cache as django_cache

        django_cache.clear()
        middleware = performance_monitoring_middleware(self.mock_get_response)
        request = self.rf.get("/api/kits")

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

        stats = django_cache.get("api_usage_stats", {})
        self.assertIn("GET /api/kits", stats)

    @override_settings(API_RATE_LIMIT={"RATE": "invalid", "CACHE_PREFIX": "ratelimit"})
    def test_rate_limit_middleware_handles_invalid_rate_format(self):
        """Test that rate limiting handles invalid rate format gracefully."""
        cache.clear()
        middleware = rate_limit_middleware(self.mock_get_response)
        request = self.rf.get("/api/test")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(API_RATE_LIMIT={"RATE": "100/hour", "CACHE_PREFIX": "ratelimit"})
    def test_rate_limit_middleware_resets_after_hour(self):
        """Test that rate limit resets after an hour."""
        cache.clear()
        middleware = rate_limit_middleware(self.mock_get_response)
        request = self.rf.get("/api/test")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        cache_key = "ratelimit_192.168.1.1"
        old_timestamp = time.time() - 3700
        cache.set(cache_key, {"count": 100, "timestamp": old_timestamp}, 3600)

        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=True, SLOW_QUERY_THRESHOLD=0.01)
    def test_performance_middleware_logs_slow_queries(self):
        """Test that performance middleware logs slow queries."""
        from django.http import HttpResponse

        mock_connection = Mock()
        # Start with empty queries, then add one after get_response
        mock_connection.queries = []

        def get_response_with_slow_query(request):
            # Add query after get_response is called
            mock_connection.queries.append({"sql": "SELECT * FROM test", "time": "0.02"})
            return HttpResponse()

        with patch("core.middleware.db_logger") as mock_db_logger:
            with patch("core.middleware.connection", mock_connection):
                middleware = performance_monitoring_middleware(get_response_with_slow_query)
                request = self.rf.get("/api/test")

                response = middleware(request)
                self.assertEqual(response.status_code, 200)
                mock_db_logger.warning.assert_called()

    @override_settings(DEBUG=True, LOG_DB_QUERIES=True)
    def test_performance_middleware_logs_db_queries_when_enabled(self):
        """Test that performance middleware logs DB queries when LOG_DB_QUERIES is enabled."""
        from django.http import HttpResponse

        mock_connection = Mock()
        # Start with empty queries, then add one after get_response
        mock_connection.queries = []

        def get_response_with_queries(request):
            # Add query after get_response is called
            mock_connection.queries.append({"sql": "SELECT * FROM test", "time": "0.001"})
            return HttpResponse()

        with patch("core.middleware.db_logger") as mock_db_logger:
            with patch("core.middleware.connection", mock_connection):
                middleware = performance_monitoring_middleware(get_response_with_queries)
                request = self.rf.get("/api/test")

                response = middleware(request)
                self.assertEqual(response.status_code, 200)
                mock_db_logger.info.assert_called()

    def test_performance_middleware_handles_response_with_setitem(self):
        """Test that performance middleware handles responses with __setitem__."""

        class DictLikeResponse:
            def __init__(self):
                self._headers = {}

            def __setitem__(self, key, value):
                self._headers[key] = value

            def __getitem__(self, key):
                return self._headers[key]

        dict_response = DictLikeResponse()
        mock_get_response = Mock(return_value=dict_response)

        middleware = performance_monitoring_middleware(mock_get_response)
        request = self.rf.get("/api/test")

        response = middleware(request)
        self.assertIn("X-Response-Time", response._headers)

    def test_performance_middleware_handles_track_api_usage_exception(self):
        """Test that _track_api_usage handles exceptions gracefully."""

        with patch("core.middleware.cache.set", side_effect=Exception("Cache error")):
            with patch("core.middleware.logger") as mock_logger:
                middleware = performance_monitoring_middleware(self.mock_get_response)
                request = self.rf.get("/api/test")

                response = middleware(request)
                self.assertEqual(response.status_code, 200)
                mock_logger.error.assert_called()

    def test_performance_middleware_tracks_api_usage_with_existing_stats(self):
        """Test that _track_api_usage handles existing cached stats."""
        from django.core.cache import cache as django_cache

        django_cache.clear()
        existing_stats = {
            "GET /api/kits": {"count": 5, "total_duration": 0.5, "total_queries": 10, "status_codes": {200: 5}}
        }
        django_cache.set("api_usage_stats", existing_stats, 3600)

        middleware = performance_monitoring_middleware(self.mock_get_response)
        request = self.rf.get("/api/kits")

        response = middleware(request)
        self.assertEqual(response.status_code, 200)

        stats = django_cache.get("api_usage_stats", {})
        self.assertIn("GET /api/kits", stats)
        self.assertGreater(stats["GET /api/kits"]["count"], 5)
