import logging
import time
from collections import defaultdict
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger("performance")
db_logger = logging.getLogger("django.db.backends")


def _get_client_ip(request):
    """Return client IP safely.

    By default, use REMOTE_ADDR. If TRUST_X_FORWARDED_FOR=True, use the first
    IP from X-Forwarded-For.
    """
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            # XFF may contain multiple IPs: client, proxy1, proxy2, ...
            return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_limit_from_settings():
    conf = getattr(settings, "API_RATE_LIMIT", {})
    rate_str = conf.get("RATE", "100/hour")
    try:
        max_requests = int(str(rate_str).split("/")[0])
    except Exception:
        max_requests = 100
    prefix = conf.get("CACHE_PREFIX", "ratelimit")
    return max_requests, prefix


def rate_limit_middleware(get_response):
    """
    Middleware to implement rate limiting for API endpoints.
    """

    def middleware(request):
        if request.path.startswith("/api/"):
            ip = _get_client_ip(request)
            max_requests, prefix = _get_limit_from_settings()

            # Create cache key
            cache_key = f"{prefix}_{ip}"

            # Get current request count and timestamp
            request_data = cache.get(cache_key, {"count": 0, "timestamp": time.time()})

            # Reset count if an hour has passed
            current_time = time.time()
            if current_time - request_data["timestamp"] > 3600:  # 3600 seconds = 1 hour
                request_data = {"count": 0, "timestamp": current_time}

            # Check if rate limit is exceeded
            if request_data["count"] >= max_requests:
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")

            # Update request count
            request_data["count"] += 1
            cache.set(cache_key, request_data, 3600)

        response = get_response(request)
        return response

    return middleware


def performance_monitoring_middleware(get_response):
    """
    Middleware to log response times, database queries, and API usage statistics.
    """

    def middleware(request):
        start_time = time.time()

        queries_available = settings.DEBUG and hasattr(connection, "queries")
        if queries_available:
            initial_queries = len(connection.queries)
        else:
            initial_queries = 0

        response = get_response(request)

        duration = time.time() - start_time

        if queries_available:
            total_queries = len(connection.queries) - initial_queries
        else:
            total_queries = 0

        path = request.path
        method = request.method
        status_code = response.status_code if hasattr(response, "status_code") else 200

        slow_query_threshold = getattr(settings, "SLOW_QUERY_THRESHOLD", 0.5)
        slow_response_threshold = getattr(settings, "SLOW_RESPONSE_THRESHOLD", 1.0)

        if queries_available and total_queries > 0:
            query_times = [float(q.get("time", 0)) for q in connection.queries[initial_queries:]]
            total_query_time = sum(query_times)
            slow_queries = [
                connection.queries[initial_queries + i] for i, t in enumerate(query_times) if t > slow_query_threshold
            ]

            if slow_queries:
                for query in slow_queries:
                    db_logger.warning(
                        f"Slow query detected ({query.get('time', 0)}s): {query.get('sql', '')[:200]}",
                        extra={
                            "path": path,
                            "method": method,
                            "duration": query.get("time", 0),
                        },
                    )

            if getattr(settings, "LOG_DB_QUERIES", False):
                db_logger.info(
                    f"DB queries: {total_queries} queries in {total_query_time:.3f}s",
                    extra={
                        "path": path,
                        "method": method,
                        "query_count": total_queries,
                        "total_query_time": total_query_time,
                    },
                )

        if duration > slow_response_threshold:
            performance_logger.warning(
                f"Slow response: {method} {path} took {duration:.3f}s (status: {status_code})",
                extra={
                    "path": path,
                    "method": method,
                    "duration": duration,
                    "status_code": status_code,
                    "query_count": total_queries,
                },
            )
        else:
            performance_logger.info(
                f"{method} {path} - {duration:.3f}s (status: {status_code}, queries: {total_queries})",
                extra={
                    "path": path,
                    "method": method,
                    "duration": duration,
                    "status_code": status_code,
                    "query_count": total_queries,
                },
            )

        if path.startswith("/api/"):
            _track_api_usage(request, response, duration, total_queries)

        if hasattr(response, "headers"):
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            if total_queries > 0:
                response.headers["X-Query-Count"] = str(total_queries)
        elif hasattr(response, "__setitem__"):
            try:
                response["X-Response-Time"] = f"{duration:.3f}s"
                if total_queries > 0:
                    response["X-Query-Count"] = str(total_queries)
            except (TypeError, KeyError):
                pass

        return response

    return middleware


def _track_api_usage(request: Any, response: Any, duration: float, query_count: int) -> None:
    """
    Track API usage statistics in cache.
    """
    try:
        path = request.path
        method = request.method
        status_code = getattr(response, "status_code", 200)

        stats_key = "api_usage_stats"
        cached_stats = cache.get(stats_key, {})

        if not cached_stats:
            stats = defaultdict(
                lambda: {
                    "count": 0,
                    "total_duration": 0.0,
                    "total_queries": 0,
                    "status_codes": defaultdict(int),
                }
            )
        else:
            stats = defaultdict(
                lambda: {
                    "count": 0,
                    "total_duration": 0.0,
                    "total_queries": 0,
                    "status_codes": defaultdict(int),
                },
                cached_stats,
            )
            for key, value in cached_stats.items():
                if "status_codes" in value:
                    stats[key]["status_codes"] = defaultdict(int, value["status_codes"])
                else:
                    stats[key].update(value)

        endpoint_key = f"{method} {path}"
        stats[endpoint_key]["count"] += 1
        stats[endpoint_key]["total_duration"] += duration
        stats[endpoint_key]["total_queries"] += query_count
        stats[endpoint_key]["status_codes"][status_code] += 1

        stats_dict = {}
        for key, value in stats.items():
            stats_dict[key] = {
                "count": value["count"],
                "total_duration": value["total_duration"],
                "total_queries": value["total_queries"],
                "status_codes": dict(value["status_codes"]),
            }

        cache.set(stats_key, stats_dict, timeout=3600)
    except Exception as e:
        logger.error(f"Error tracking API usage: {str(e)}")
