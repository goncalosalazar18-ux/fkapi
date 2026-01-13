"""Tests for middleware."""
import pytest
from django.test import RequestFactory, Client
from django.core.cache import cache
from unittest.mock import Mock

from core.middleware import rate_limit_middleware, _get_client_ip, _get_limit_from_settings


@pytest.fixture
def rf():
    """Request factory for creating test requests."""
    return RequestFactory()


@pytest.fixture
def mock_get_response():
    """Mock get_response function."""
    return Mock(return_value=Mock(status_code=200))


@pytest.mark.django_db
def test_get_client_ip_default(rf):
    """Test client IP extraction without X-Forwarded-For."""
    request = rf.get("/api/test")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    ip = _get_client_ip(request)
    assert ip == "192.168.1.1"


@pytest.mark.django_db
def test_get_client_ip_with_xff(rf, settings):
    """Test client IP extraction with X-Forwarded-For when enabled."""
    settings.TRUST_X_FORWARDED_FOR = True
    request = rf.get("/api/test", HTTP_X_FORWARDED_FOR="10.0.0.1, 192.168.1.1")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    ip = _get_client_ip(request)
    assert ip == "10.0.0.1"


@pytest.mark.django_db
def test_rate_limit_middleware_allows_requests(rf, mock_get_response, settings):
    """Test that rate limiting allows requests under the limit."""
    settings.API_RATE_LIMIT = {"RATE": "100/hour", "CACHE_PREFIX": "ratelimit"}
    cache.clear()
    
    middleware = rate_limit_middleware(mock_get_response)
    request = rf.get("/api/test")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    
    response = middleware(request)
    assert response.status_code == 200
    assert mock_get_response.called


@pytest.mark.django_db
def test_rate_limit_middleware_blocks_excessive_requests(rf, mock_get_response, settings):
    """Test that rate limiting blocks requests over the limit."""
    settings.API_RATE_LIMIT = {"RATE": "2/hour", "CACHE_PREFIX": "ratelimit"}
    cache.clear()
    
    middleware = rate_limit_middleware(mock_get_response)
    request = rf.get("/api/test")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    
    # Make requests up to the limit
    middleware(request)
    middleware(request)
    
    # This should be blocked
    response = middleware(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_rate_limit_middleware_ignores_non_api_paths(rf, mock_get_response, settings):
    """Test that rate limiting only applies to API paths."""
    settings.API_RATE_LIMIT = {"RATE": "1/hour", "CACHE_PREFIX": "ratelimit"}
    cache.clear()
    
    middleware = rate_limit_middleware(mock_get_response)
    request = rf.get("/admin/")
    request.META["REMOTE_ADDR"] = "192.168.1.1"
    
    # Should not be rate limited
    response = middleware(request)
    assert response.status_code == 200
