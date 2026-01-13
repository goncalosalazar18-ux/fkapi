import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden


def _get_client_ip(request):
    """Return client IP safely.

    By default, use REMOTE_ADDR. If TRUST_X_FORWARDED_FOR=True, use the first
    IP from X-Forwarded-For.
    """
    if getattr(settings, 'TRUST_X_FORWARDED_FOR', False):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            # XFF may contain multiple IPs: client, proxy1, proxy2, ...
            return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _get_limit_from_settings():
    conf = getattr(settings, 'API_RATE_LIMIT', {})
    rate_str = conf.get('RATE', '100/hour')
    try:
        max_requests = int(str(rate_str).split('/')[0])
    except Exception:
        max_requests = 100
    prefix = conf.get('CACHE_PREFIX', 'ratelimit')
    return max_requests, prefix


def rate_limit_middleware(get_response):
    """
    Middleware to implement rate limiting for API endpoints.
    """
    def middleware(request):
        if request.path.startswith('/api/'):
            ip = _get_client_ip(request)
            max_requests, prefix = _get_limit_from_settings()

            # Create cache key
            cache_key = f"{prefix}_{ip}"

            # Get current request count and timestamp
            request_data = cache.get(cache_key, {'count': 0, 'timestamp': time.time()})

            # Reset count if an hour has passed
            current_time = time.time()
            if current_time - request_data['timestamp'] > 3600:  # 3600 seconds = 1 hour
                request_data = {'count': 0, 'timestamp': current_time}

            # Check if rate limit is exceeded
            if request_data['count'] >= max_requests:
                return HttpResponseForbidden('Rate limit exceeded. Please try again later.')

            # Update request count
            request_data['count'] += 1
            cache.set(cache_key, request_data, 3600)

        response = get_response(request)
        return response

    return middleware
