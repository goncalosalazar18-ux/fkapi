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


def _is_ip_whitelisted(ip: str) -> bool:
    """Check if an IP address is in the rate limit whitelist."""
    whitelist = getattr(settings, "API_RATE_LIMIT_WHITELIST", [])
    return ip in whitelist if whitelist else False


def rate_limit_middleware(get_response):
    """
    Middleware to implement rate limiting for API endpoints.
    """

    def middleware(request):
        if request.path.startswith("/api/"):
            ip = _get_client_ip(request)

            if _is_ip_whitelisted(ip):
                response = get_response(request)
                return response

            max_requests, prefix = _get_limit_from_settings()

            cache_key = f"{prefix}_{ip}"

            request_data = cache.get(cache_key, {"count": 0, "timestamp": time.time()})

            current_time = time.time()
            if current_time - request_data["timestamp"] > 3600:
                request_data = {"count": 0, "timestamp": current_time}

            if request_data["count"] >= max_requests:
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")

            request_data["count"] += 1
            cache.set(cache_key, request_data, 3600)

        response = get_response(request)
        return response

    return middleware


def _get_initial_query_state() -> tuple[bool, int]:
    queries_available = settings.DEBUG and hasattr(connection, "queries")
    initial_queries = len(connection.queries) if queries_available else 0
    return queries_available, initial_queries


def _log_slow_queries(
    path: str, method: str, initial_queries: int, query_times: list[float], slow_query_threshold: float
) -> None:
    slow_queries = [
        connection.queries[initial_queries + i] for i, t in enumerate(query_times) if t > slow_query_threshold
    ]
    for query in slow_queries:
        db_logger.warning(
            f"Slow query detected ({query.get('time', 0)}s): {query.get('sql', '')[:200]}",
            extra={"path": path, "method": method, "duration": query.get("time", 0)},
        )


def _log_response_time(
    path: str,
    method: str,
    status_code: int,
    duration: float,
    total_queries: int,
    slow_response_threshold: float,
) -> None:
    extra = {
        "path": path,
        "method": method,
        "duration": duration,
        "status_code": status_code,
        "query_count": total_queries,
    }
    if duration > slow_response_threshold:
        performance_logger.warning(
            f"Slow response: {method} {path} took {duration:.3f}s (status: {status_code})", extra=extra
        )
    else:
        performance_logger.info(
            f"{method} {path} - {duration:.3f}s (status: {status_code}, queries: {total_queries})", extra=extra
        )


def _add_performance_headers(response: Any, duration: float, total_queries: int) -> None:
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


def performance_monitoring_middleware(get_response):
    """
    Middleware to log response times, database queries, and API usage statistics.
    """

    def middleware(request):
        start_time = time.time()
        queries_available, initial_queries = _get_initial_query_state()
        response = get_response(request)
        duration = time.time() - start_time
        total_queries = (len(connection.queries) - initial_queries) if queries_available else 0
        path, method = request.path, request.method
        status_code = getattr(response, "status_code", 200)
        slow_query_threshold = getattr(settings, "SLOW_QUERY_THRESHOLD", 0.5)
        slow_response_threshold = getattr(settings, "SLOW_RESPONSE_THRESHOLD", 1.0)

        if queries_available and total_queries > 0:
            query_times = [float(q.get("time", 0)) for q in connection.queries[initial_queries:]]
            _log_slow_queries(path, method, initial_queries, query_times, slow_query_threshold)
            if getattr(settings, "LOG_DB_QUERIES", False):
                total_query_time = sum(query_times)
                db_logger.info(
                    f"DB queries: {total_queries} queries in {total_query_time:.3f}s",
                    extra={
                        "path": path,
                        "method": method,
                        "query_count": total_queries,
                        "total_query_time": total_query_time,
                    },
                )

        _log_response_time(path, method, status_code, duration, total_queries, slow_response_threshold)
        if path.startswith("/api/"):
            _track_api_usage(request, response, duration, total_queries)
        _add_performance_headers(response, duration, total_queries)
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
