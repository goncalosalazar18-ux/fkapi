"""
Custom Prometheus metrics.

Defines metrics for tracking user collection scrapes, cache usage, etc.
Not all of these are used yet, but they're here when we need them.
"""

from prometheus_client import Counter, Gauge, Histogram

# User Collection Scraping Metrics
user_collection_scrapes_total = Counter(
    'fkapi_user_collection_scrapes_total',
    'Total number of user collection scrapes',
    ['userid', 'status']  # status: success, error, filtered
)

user_collection_scrape_duration_seconds = Histogram(
    'fkapi_user_collection_scrape_duration_seconds',
    'Time spent scraping user collections',
    ['userid'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

user_collection_entries_scraped = Histogram(
    'fkapi_user_collection_entries_scraped',
    'Number of entries scraped per collection',
    ['userid'],
    buckets=[0, 10, 50, 100, 200, 500, 1000, 2000]
)

user_collection_entries_filtered = Counter(
    'fkapi_user_collection_entries_filtered_total',
    'Total number of entries filtered out',
    ['filter_reason']  # filter_reason: custom_fields, etc.
)

# Cache Metrics
cache_entries = Gauge(
    'fkapi_cache_entries',
    'Number of entries in cache',
    ['cache_type']  # cache_type: user_collection, etc.
)

cache_hits = Counter(
    'fkapi_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

cache_misses = Counter(
    'fkapi_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

# Celery Task Metrics (in addition to default Celery metrics)
celery_task_duration_seconds = Histogram(
    'fkapi_celery_task_duration_seconds',
    'Duration of Celery tasks',
    ['task_name', 'status'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# API Endpoint Metrics (in addition to django-prometheus defaults)
api_endpoint_requests = Counter(
    'fkapi_api_endpoint_requests_total',
    'Total API endpoint requests',
    ['endpoint', 'method', 'status_code']
)

api_endpoint_duration_seconds = Histogram(
    'fkapi_api_endpoint_duration_seconds',
    'API endpoint response time',
    ['endpoint', 'method'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)
