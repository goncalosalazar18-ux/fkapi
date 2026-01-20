"""
Management command to warm up the cache with frequently accessed data.

This command pre-populates the cache with:
- Popular club seasons
- Recent kits
- Popular search queries
- Top clubs and brands
"""

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models import Count

from core.cache_utils import generate_cache_key
from core.models import Brand, Club, Kit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command to warm up the cache."""

    help = "Warm up the cache with frequently accessed data"

    def add_arguments(self, parser: Any) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--clubs",
            type=int,
            default=50,
            help="Number of top clubs to cache (default: 50)",
        )
        parser.add_argument(
            "--kits",
            type=int,
            default=100,
            help="Number of recent kits to cache (default: 100)",
        )
        parser.add_argument(
            "--seasons",
            action="store_true",
            help="Cache seasons for top clubs",
        )
        parser.add_argument(
            "--search",
            action="store_true",
            help="Cache popular search queries",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the cache warming command."""
        self.stdout.write(self.style.SUCCESS("Starting cache warming..."))

        clubs_count = options["clubs"]
        kits_count = options["kits"]
        cache_seasons = options["seasons"]
        cache_search = options["search"]

        cached_items = 0

        if cache_seasons:
            cached_items += self._cache_club_seasons(clubs_count)

        cached_items += self._cache_popular_kits(kits_count)
        cached_items += self._cache_top_clubs(clubs_count)
        cached_items += self._cache_top_brands()

        if cache_search:
            cached_items += self._cache_popular_searches()

        self.stdout.write(
            self.style.SUCCESS(f"Cache warming completed. Cached {cached_items} items.")
        )

    def _cache_club_seasons(self, limit: int) -> int:
        """Cache seasons for top clubs."""
        self.stdout.write("Caching club seasons...")
        cached = 0

        top_clubs = (
            Club.objects.annotate(kit_count=Count("kit"))
            .filter(kit_count__gt=0)
            .order_by("-kit_count")[:limit]
        )

        for club in top_clubs:
            cache_key = generate_cache_key("season", "club", club.id)
            if cache.get(cache_key) is None:
                try:
                    kits = Kit.objects.filter(team=club).select_related("season").distinct("season")
                    seasons = sorted([kit.season for kit in kits], key=lambda x: x.year, reverse=True)
                    cache.set(cache_key, seasons, timeout=settings.CACHE_TIMEOUT_LONG)
                    cached += 1
                except Exception as e:
                    logger.error(f"Error caching seasons for club {club.id}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"  Cached seasons for {cached} clubs"))
        return cached

    def _cache_popular_kits(self, limit: int) -> int:
        """Cache popular/recent kits."""
        self.stdout.write("Caching popular kits...")
        cached = 0

        popular_kits = Kit.objects.select_related("team", "season", "brand", "type").order_by("-id")[:limit]

        for kit in popular_kits:
            cache_key = generate_cache_key("kit_json", kit.id)
            if cache.get(cache_key) is None:
                try:
                    from core.serializers import (
                        BrandJsonSchema,
                        ClubJsonSchema,
                        ColorJsonSchema,
                        CompetitionJsonSchema,
                        KitJsonSchema,
                        SeasonJsonSchema,
                        TypeJsonSchema,
                    )

                    kit = Kit.objects.select_related("team", "season", "brand", "type", "primary_color").prefetch_related("competition", "secondary_color").get(id=kit.id)
                    competition_logo_default = "https://www.footballkitarchive.com/static/logos/not_found.png"

                    primary_color = None
                    if kit.primary_color:
                        primary_color = ColorJsonSchema(name=kit.primary_color.name, color=kit.primary_color.color)

                    secondary_colors = []
                    if kit.secondary_color.exists():
                        secondary_colors = [ColorJsonSchema(name=color.name, color=color.color) for color in kit.secondary_color.all()]

                    country_code = None
                    if hasattr(kit.team, "country") and kit.team.country:
                        country_code = kit.team.country.code

                    result = KitJsonSchema(
                        name=kit.name,
                        slug=kit.slug,
                        team=ClubJsonSchema(
                            id=kit.team.id,
                            id_fka=kit.team.id_fka,
                            name=kit.team.name,
                            slug=kit.team.slug,
                            logo=kit.team.logo,
                            logo_dark=kit.team.logo_dark,
                            country=country_code,
                        ),
                        season=SeasonJsonSchema(
                            id=kit.season.id,
                            year=kit.season.year,
                            first_year=kit.season.first_year,
                            second_year=kit.season.second_year,
                        ),
                        competition=[
                            CompetitionJsonSchema(
                                id=c.id,
                                name=c.name,
                                slug=c.slug,
                                logo=c.logo if c.logo else competition_logo_default,
                                logo_dark=c.logo_dark,
                                country=c.country.code if hasattr(c, "country") and c.country else None,
                            )
                            for c in kit.competition.all()
                        ],
                        type=TypeJsonSchema(id=kit.type.id, name=kit.type.name),
                        brand=BrandJsonSchema(
                            id=kit.brand.id,
                            name=kit.brand.name,
                            slug=kit.brand.slug,
                            logo=kit.brand.logo,
                            logo_dark=kit.brand.logo_dark,
                        ),
                        design=kit.design,
                        primary_color=primary_color,
                        secondary_color=secondary_colors,
                        main_img_url=kit.main_img_url,
                    )
                    cache.set(cache_key, result, timeout=settings.CACHE_TIMEOUT_LONG)
                    cached += 1
                except Exception as e:
                    logger.error(f"Error caching kit {kit.id}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"  Cached {cached} kits"))
        return cached

    def _cache_top_clubs(self, limit: int) -> int:
        """Cache top clubs by kit count."""
        self.stdout.write("Caching top clubs...")
        cached = 0

        top_clubs = (
            Club.objects.annotate(kit_count=Count("kit"))
            .filter(kit_count__gt=0)
            .order_by("-kit_count")[:limit]
        )

        for club in top_clubs:
            cache_key = generate_cache_key("club", "top", club.id)
            cache.set(
                cache_key,
                {
                    "id": club.id,
                    "name": club.name,
                    "slug": club.slug,
                    "kit_count": club.kit_count,
                },
                timeout=settings.CACHE_TIMEOUT_LONG,
            )
            cached += 1

        self.stdout.write(self.style.SUCCESS(f"  Cached {cached} clubs"))
        return cached

    def _cache_top_brands(self) -> int:
        """Cache top brands by kit count."""
        self.stdout.write("Caching top brands...")
        cached = 0

        top_brands = (
            Brand.objects.annotate(kit_count=Count("kit"))
            .filter(kit_count__gt=0)
            .order_by("-kit_count")[:20]
        )

        for brand in top_brands:
            cache_key = generate_cache_key("brand", "top", brand.id)
            cache.set(
                cache_key,
                {
                    "id": brand.id,
                    "name": brand.name,
                    "slug": brand.slug,
                    "kit_count": brand.kit_count,
                },
                timeout=settings.CACHE_TIMEOUT_LONG,
            )
            cached += 1

        self.stdout.write(self.style.SUCCESS(f"  Cached {cached} brands"))
        return cached

    def _cache_popular_searches(self) -> int:
        """Cache popular search queries."""
        self.stdout.write("Caching popular searches...")
        cached = 0

        popular_searches = [
            "Barcelona",
            "Real Madrid",
            "Manchester United",
            "Liverpool",
            "Arsenal",
            "Chelsea",
            "Manchester City",
            "Bayern Munich",
            "PSG",
            "Juventus",
            "AC Milan",
            "Inter Milan",
            "2024",
            "2023",
            "2022",
            "adidas",
            "nike",
            "puma",
        ]

        for search_term in popular_searches:
            try:
                cache_key = generate_cache_key("search_clubs", search_term.lower())
                if cache.get(cache_key) is None:

                    from core.models import Club
                    from fkapi.api import _search_filter

                    clubs = list(Club.objects.filter(
                        _search_filter("name", search_term.lower()) | _search_filter("slug", search_term.lower())
                    ).order_by("id")[:10])
                    if clubs:
                        cache.set(cache_key, clubs, timeout=settings.CACHE_TIMEOUT_MEDIUM)
                        cached += 1

                cache_key = generate_cache_key("search_kits", search_term.lower())
                if cache.get(cache_key) is None:
                    from core.models import Kit
                    from fkapi.api import _unaccent_filter

                    base_kits = Kit.objects.select_related("team", "season").all()
                    kits = base_kits.filter(_unaccent_filter("name", search_term.lower()))[:10]
                    kits_list = list(kits)
                    if kits_list:
                        results = [
                            {
                                "id": kit.id,
                                "name": kit.name,
                                "main_img_url": kit.main_img_url,
                                "team_name": kit.team.name,
                                "season_year": kit.season.year,
                            }
                            for kit in kits_list
                        ]
                        cache.set(cache_key, results, timeout=settings.CACHE_TIMEOUT_MEDIUM)
                        cached += 1
            except Exception as e:
                logger.error(f"Error caching search for '{search_term}': {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"  Cached {cached} search queries"))
        return cached
