"""Tests for middleware."""

from unittest.mock import Mock

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from core.middleware import _get_client_ip, rate_limit_middleware


class MiddlewareTests(TestCase):
    """Test cases for middleware functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.rf = RequestFactory()
        self.mock_get_response = Mock(return_value=Mock(status_code=200))
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
