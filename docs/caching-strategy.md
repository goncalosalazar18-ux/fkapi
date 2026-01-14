# Caching Strategy

## Overview

The FKApi project uses Redis as the caching backend to improve performance by reducing database queries and API response times. Redis is configured but was not fully utilized until this implementation.

## Cache Configuration

### Redis Setup

The cache is configured in `fkapi/settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'fkapi',
        'TIMEOUT': 3600,  # Default timeout: 1 hour
    }
}
```

### Cache Timeouts

Different cache timeouts are defined for different types of data:

- `CACHE_TIMEOUT_SHORT`: 300 seconds (5 minutes) - For frequently changing data
- `CACHE_TIMEOUT_MEDIUM`: 1800 seconds (30 minutes) - For search results and queries
- `CACHE_TIMEOUT_LONG`: 3600 seconds (1 hour) - For relatively static data
- `CACHE_TIMEOUT_VERY_LONG`: 86400 seconds (24 hours) - For very static data

## Cached Endpoints

### API Endpoints with Caching

1. **GET /api/seasons** - Club seasons
   - Cache key: `season_club_{club_id}`
   - Timeout: 1 hour
   - Invalidated when: Club or Kit changes

2. **GET /api/kits** - Club kits by season
   - Cache key: `kit_club_{club_id}_season_{season_id}`
   - Timeout: 30 minutes
   - Invalidated when: Kit, Club, or Season changes

3. **GET /api/kit-json/{kit_id}** - Complete kit details
   - Cache key: `kit_json_{kit_id}`
   - Timeout: 1 hour
   - Invalidated when: Kit changes

4. **GET /api/clubs/search** - Search clubs
   - Cache key: `search_clubs_{keyword}`
   - Timeout: 30 minutes
   - Invalidated when: Club changes

5. **GET /api/brands/search** - Search brands
   - Cache key: `search_brands_{keyword}`
   - Timeout: 30 minutes
   - Invalidated when: Brand changes

6. **GET /api/competitions/search** - Search competitions
   - Cache key: `search_competitions_{keyword}`
   - Timeout: 30 minutes
   - Invalidated when: Competition changes

7. **GET /api/seasons/search** - Search seasons
   - Cache key: `search_seasons_{keyword}`
   - Timeout: 30 minutes
   - Invalidated when: Season changes

8. **GET /api/kits/search** - Search kits
   - Cache key: `search_kits_{keyword}`
   - Timeout: 30 minutes
   - Invalidated when: Kit changes

## Cache Invalidation Strategy

### Automatic Invalidation

Cache invalidation is handled automatically through Django signals in `core/cache_utils.py`:

- **Club changes**: Invalidates all club-related cache entries
- **Season changes**: Invalidates all season-related cache entries
- **Kit changes**: Invalidates kit-specific cache and related club/season caches
- **Brand changes**: Invalidates brand-related cache entries
- **Competition changes**: Invalidates competition-related cache entries

### Manual Invalidation

You can manually invalidate cache using utility functions:

```python
from core.cache_utils import (
    invalidate_club_cache,
    invalidate_season_cache,
    invalidate_kit_cache,
    invalidate_brand_cache,
    invalidate_competition_cache,
    invalidate_search_cache,
)

# Invalidate cache for a specific club
invalidate_club_cache(club_id=1)

# Invalidate all search caches
invalidate_search_cache()
```

## Cache Key Generation

Cache keys are generated using the `generate_cache_key()` function in `core/cache_utils.py`:

```python
from core.cache_utils import generate_cache_key

# Generate a cache key
cache_key = generate_cache_key("kit", "club", 1, "season", 2)
# Result: "kit_club_1_season_2"
```

The function:
- Takes a prefix and variable arguments
- Creates consistent, readable cache keys
- Automatically hashes long keys (>200 chars) to prevent Redis key length issues

## Cache Warming

### Management Command

A management command is provided to pre-populate the cache with frequently accessed data:

```bash
python manage.py warm_cache
```

### Options

- `--clubs N`: Cache seasons for top N clubs (default: 50)
- `--kits N`: Cache N recent kits (default: 100)
- `--seasons`: Cache seasons for top clubs
- `--search`: Cache popular search queries

### Examples

```bash
# Cache seasons for top 100 clubs
python manage.py warm_cache --seasons --clubs 100

# Cache 200 recent kits
python manage.py warm_cache --kits 200

# Cache everything including popular searches
python manage.py warm_cache --seasons --search
```

### Scheduled Warming

Consider adding cache warming to your Celery beat schedule in `settings.py`:

```python
CELERY_BEAT_SCHEDULE = {
    'scrape_daily': {
        'task': 'core.tasks.scrape_daily',
        'schedule': crontab(hour=0, minute=0),
    },
    'warm_cache': {
        'task': 'core.tasks.warm_cache_task',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM
    },
}
```

## Performance Considerations

### Query Optimization

Cached endpoints use optimized queries with `select_related()` and `prefetch_related()` to minimize database hits:

```python
Kit.objects.select_related("team", "season", "brand", "type").prefetch_related("competition", "secondary_color")
```

### Cache Hit Rate Monitoring

Monitor cache hit rates to optimize timeout values. Low hit rates may indicate:
- Timeouts too short
- Cache invalidation too frequent
- Need for cache warming

### Memory Management

Redis memory usage should be monitored. Consider:
- Setting max memory limits in Redis config
- Using Redis eviction policies (e.g., `allkeys-lru`)
- Monitoring cache size and adjusting timeouts

## Best Practices

1. **Always use cache keys consistently** - Use `generate_cache_key()` for all cache operations
2. **Set appropriate timeouts** - Match timeout to data change frequency
3. **Invalidate on updates** - Ensure cache invalidation signals are working
4. **Monitor cache performance** - Track hit rates and adjust as needed
5. **Warm cache after deployments** - Run cache warming after major data changes
6. **Test cache behavior** - Verify cache invalidation works correctly

## Troubleshooting

### Cache Not Working

1. Verify Redis is running: `redis-cli ping`
2. Check Redis connection in Django: `python manage.py shell` → `from django.core.cache import cache; cache.set('test', 'value'); cache.get('test')`
3. Verify `django-redis` is installed: `pip list | grep django-redis`

### Stale Data

1. Check cache invalidation signals are connected
2. Verify model save/delete signals are firing
3. Manually invalidate cache if needed
4. Check cache timeout values

### High Memory Usage

1. Reduce cache timeouts
2. Implement cache size limits
3. Use Redis eviction policies
4. Monitor and clean up unused cache keys

## Future Improvements

Potential enhancements to the caching strategy:

1. **Cache versioning** - Add version numbers to cache keys for easier invalidation
2. **Cache statistics** - Add metrics for cache hit/miss rates
3. **Conditional caching** - Cache based on request headers (e.g., user-specific data)
4. **Cache compression** - Compress large cache values to save memory
5. **Distributed caching** - Use Redis Cluster for high availability
6. **Cache warming automation** - Automatically warm cache based on access patterns
