"""
Cache utility functions for managing cache keys and invalidation.

This module provides utilities for:
- Generating consistent cache keys
- Invalidating cache based on model changes
- Cache key prefixes and patterns
"""

import hashlib
import logging
from typing import Any

from django.db.models.signals import post_delete, post_save

from core.models import Brand, Club, Competition, Kit, Season

logger = logging.getLogger(__name__)


# Cache key prefixes
CACHE_PREFIX_CLUB = "club"
CACHE_PREFIX_SEASON = "season"
CACHE_PREFIX_KIT = "kit"
CACHE_PREFIX_BRAND = "brand"
CACHE_PREFIX_COMPETITION = "competition"
CACHE_PREFIX_SEARCH = "search"


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate a consistent cache key from prefix and arguments.

    Args:
        prefix: Cache key prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        str: Generated cache key
    """
    parts = [prefix]
    parts.extend(str(arg) for arg in args)
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        parts.extend(f"{k}={v}" for k, v in sorted_kwargs)
    key_string = "_".join(parts)
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}_{key_hash}"
    return key_string


def invalidate_club_cache(club_id: int) -> None:
    """
    Invalidate all cache entries related to a specific club.

    Args:
        club_id: ID of the club
    """
    patterns = [
        f"{CACHE_PREFIX_CLUB}_{club_id}_*",
        f"{CACHE_PREFIX_SEASON}_club_{club_id}_*",
        f"{CACHE_PREFIX_KIT}_club_{club_id}_*",
        f"{CACHE_PREFIX_SEARCH}_club_{club_id}_*",
    ]
    _invalidate_patterns(patterns)


def invalidate_season_cache(season_id: int) -> None:
    """
    Invalidate all cache entries related to a specific season.

    Args:
        season_id: ID of the season
    """
    patterns = [
        f"{CACHE_PREFIX_SEASON}_{season_id}_*",
        f"{CACHE_PREFIX_KIT}_season_{season_id}_*",
        f"{CACHE_PREFIX_SEARCH}_season_{season_id}_*",
    ]
    _invalidate_patterns(patterns)


def invalidate_kit_cache(kit_id: int) -> None:
    """
    Invalidate all cache entries related to a specific kit.

    Args:
        kit_id: ID of the kit
    """
    patterns = [
        f"{CACHE_PREFIX_KIT}_{kit_id}_*",
        f"{CACHE_PREFIX_SEARCH}_kit_{kit_id}_*",
    ]
    _invalidate_patterns(patterns)


def invalidate_brand_cache(brand_id: int) -> None:
    """
    Invalidate all cache entries related to a specific brand.

    Args:
        brand_id: ID of the brand
    """
    patterns = [
        f"{CACHE_PREFIX_BRAND}_{brand_id}_*",
        f"{CACHE_PREFIX_SEARCH}_brand_{brand_id}_*",
    ]
    _invalidate_patterns(patterns)


def invalidate_competition_cache(competition_id: int) -> None:
    """
    Invalidate all cache entries related to a specific competition.

    Args:
        competition_id: ID of the competition
    """
    patterns = [
        f"{CACHE_PREFIX_COMPETITION}_{competition_id}_*",
        f"{CACHE_PREFIX_SEARCH}_competition_{competition_id}_*",
    ]
    _invalidate_patterns(patterns)


def invalidate_search_cache() -> None:
    """
    Invalidate all search-related cache entries.
    """
    patterns = [
        f"{CACHE_PREFIX_SEARCH}_*",
    ]
    _invalidate_patterns(patterns)


def invalidate_user_collection_cache(userid: int) -> None:
    """
    Invalidate cache entry for a specific user collection.

    Args:
        userid: User ID from FootballKitArchive
    """
    from django.core.cache import cache

    cache_key = generate_cache_key("user_collection", userid)
    cache.delete(cache_key)
    logger.info(f"Invalidated user collection cache for userid: {userid}")


def _invalidate_patterns(patterns: list[str]) -> None:
    """
    Invalidate cache entries matching the given patterns.

    Note: Redis doesn't support wildcard deletion directly.
    This is a simplified version. For production, consider using
    django-redis's delete_pattern method or iterate through keys.

    Args:
        patterns: List of cache key patterns to invalidate
    """
    try:
        from django_redis import get_redis_connection

        redis_client = get_redis_connection("default")
        for pattern in patterns:
            try:
                keys = redis_client.keys(f"fkapi:{pattern}")
                if keys:
                    redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
            except Exception as pattern_error:
                logger.debug(f"Pattern invalidation not supported for pattern {pattern}: {str(pattern_error)}")
    except ImportError:
        logger.debug("django-redis not available, skipping pattern-based invalidation")
    except Exception as e:
        logger.debug(f"Cache pattern invalidation not supported: {str(e)}")


_MODEL_INVALIDATORS = {
    Club: invalidate_club_cache,
    Season: invalidate_season_cache,
    Kit: invalidate_kit_cache,
    Brand: invalidate_brand_cache,
    Competition: invalidate_competition_cache,
}


def _invalidate_kit_related(kit: Kit) -> None:
    if kit.team:
        invalidate_club_cache(kit.team.id)
    if kit.season:
        invalidate_season_cache(kit.season.id)


def setup_cache_invalidation() -> None:
    """
    Set up signal handlers for automatic cache invalidation on model changes.
    """

    def invalidate_on_save(sender, instance, **kwargs):
        invalidation_fn = _MODEL_INVALIDATORS.get(type(instance))
        if invalidation_fn is not None:
            invalidation_fn(instance.id)
        if type(instance) is Kit:
            _invalidate_kit_related(instance)

    def invalidate_on_delete(sender, instance, **kwargs):
        invalidation_fn = _MODEL_INVALIDATORS.get(type(instance))
        if invalidation_fn is not None:
            invalidation_fn(instance.id)

    for model in (Club, Season, Kit, Brand, Competition):
        post_save.connect(invalidate_on_save, sender=model)
        post_delete.connect(invalidate_on_delete, sender=model)

    logger.info("Cache invalidation signals configured")
