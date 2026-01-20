# Standard library imports
import logging
import os
import re
from contextlib import contextmanager
from typing import Any

# Third-party imports
import requests
from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Path, Query, Schema
from ninja_apikey.security import APIKeyAuth

from core.cache_utils import generate_cache_key

# Local imports
from core.exceptions import (
    ClubNotFoundError,
    InvalidSeasonError,
    KitNotFoundError,
    RateLimitExceededError,
    ScrapingError,
    ValidationError,
)
from core.models import Brand, Club, Competition, Kit, Season
from core.serializers import (
    BrandJsonSchema,
    ClubJsonSchema,
    ClubSerializer,
    ColorJsonSchema,
    CompetitionJsonSchema,
    KitJsonSchema,
    KitSerializer,
    SeasonJsonSchema,
    SeasonSerializer,
    TypeJsonSchema,
)


# Create a simple serializer for the search results
class KitSearchResult(Schema):
    id: int
    name: str
    main_img_url: str
    team_name: str
    season_year: str


# Enable API key authentication if configured
_api_auth = APIKeyAuth() if os.getenv("DJANGO_API_ENABLE_AUTH", "False").lower() in ("1", "true", "yes") else None

api = NinjaAPI(
    title="Football Kit Archive API",
    description="""
    Comprehensive REST API for managing and retrieving football kit information from around the world.

    This API provides access to a vast database of football kits, including:
    - Club information with logos and country data
    - Kit details with images, brands, and design information
    - Season and competition data
    - Advanced search capabilities with fuzzy matching
    - Color and design analysis

    ## Features

    - **Advanced Search**: Trigram-based fuzzy search for clubs, kits, and brands
    - **Accent-Insensitive**: Find "Málaga" by searching "Malaga"
    - **Caching**: Responses are cached for optimal performance
    - **Pagination**: Efficient pagination for large result sets
    - **Rate Limiting**: Built-in protection against abuse

    ## Authentication
    API key authentication is optional and can be enabled by setting `DJANGO_API_ENABLE_AUTH=True`.
    When enabled, include your API key in the request header:
    ```
    X-API-Key: your-api-key-here
    ```

    ## Rate Limiting
    The API is rate-limited to 100 requests per hour per IP address by default.
    Rate limit can be configured via `API_RATE_LIMIT_RATE` environment variable.
    When rate limit is exceeded, you will receive a 403 Forbidden response.

    ## Pagination
    Endpoints that return lists support pagination via query parameters:
    - `page`: Page number (default: 1)
    - `page_size`: Number of items per page (default: 20, max: 100)

    ## Error Responses
    The API uses standard HTTP status codes:
    - `200 OK`: Successful request
    - `400 Bad Request`: Invalid request parameters
    - `401 Unauthorized`: Missing or invalid API key (if authentication enabled)
    - `403 Forbidden`: Rate limit exceeded
    - `404 Not Found`: Resource not found
    - `500 Internal Server Error`: Server error

    Error responses follow this format:
    ```json
    {
        "detail": "Error message description"
    }
    ```

    ## Base URL
    All endpoints are prefixed with `/api/`

    ## Additional Documentation

    📚 **Complete Project Documentation**: http://localhost:8000/docs/

    For comprehensive project documentation including setup guides, ethical scraping practices, troubleshooting, and architecture, visit the link above.

    This includes:
    - Getting Started guide with ethical scraping practices
    - Troubleshooting common issues and solutions
    - Architecture and system design diagrams
    - Celery setup for background tasks
    - API usage examples and endpoint catalog

    All documentation is also available in the repository's `docs/` directory.
    """,
    version="1.0.0",
    auth=_api_auth,
    csrf=False,  # Disable CSRF for API endpoints
    openapi_extra={
        "info": {
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "externalDocs": {
            "description": "📚 Complete Project Documentation - Setup guides, scraping practices, troubleshooting, and architecture",
            "url": "http://localhost:8000/docs/"
        },
        "tags": [
            {
                "name": "System",
                "description": "System endpoints for health checks, metrics, and monitoring"
            },
            {
                "name": "Clubs",
                "description": "Operations related to football clubs: search, retrieve, and manage club data"
            },
            {
                "name": "Kits",
                "description": "Operations related to football kits: search, retrieve complete kit information"
            },
            {
                "name": "Seasons",
                "description": "Operations related to football seasons: search and retrieve season data"
            },
            {
                "name": "Brands",
                "description": "Operations related to kit brands (Adidas, Nike, Puma, etc.)"
            },
            {
                "name": "Competitions",
                "description": "Operations related to football competitions and leagues"
            },
            {
                "name": "Testing",
                "description": "Testing and development endpoints"
            }
        ]
    }
)


# Error handlers
@api.exception_handler(ScrapingError)
def scraping_error_handler(request: HttpRequest, exc: ScrapingError) -> Any:
    """Handle scraping-related errors."""
    if isinstance(exc, KitNotFoundError):
        return api.create_response(request, {"detail": str(exc)}, status=404)
    elif isinstance(exc, ClubNotFoundError):
        return api.create_response(request, {"detail": str(exc)}, status=404)
    elif isinstance(exc, InvalidSeasonError):
        return api.create_response(request, {"detail": str(exc)}, status=400)
    elif isinstance(exc, ValidationError):
        return api.create_response(request, {"detail": str(exc)}, status=400)
    elif isinstance(exc, RateLimitExceededError):
        return api.create_response(request, {"detail": str(exc)}, status=403)
    else:
        return api.create_response(request, {"detail": str(exc)}, status=500)


@api.exception_handler(Exception)
def custom_exception_handler(request: HttpRequest, exc: Exception) -> Any:
    """Handle all other exceptions."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {type(exc).__name__}", exc_info=True)

    if settings.DEBUG:
        detail = str(exc)
    else:
        detail = "An internal server error occurred. Please try again later."

    return api.create_response(request, {"detail": detail}, status=500)


@api.get("/health", summary="Health Check", tags=["System"], description="""
    Check if the API and database are functioning correctly.

    **Response:**
    - `200 OK`: API and database are healthy
    - `503 Service Unavailable`: Database connection failed

    **Example Response:**
    ```json
    {
        "status": "healthy",
        "timestamp": "2026-01-13T12:00:00Z",
        "database": "connected",
        "cache": "connected"
    }
    ```
    """)
def health_check(request: HttpRequest) -> dict[str, Any]:
    """
    Check if the API and database are functioning correctly.
    """
    from datetime import datetime

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        Club.objects.count()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = "disconnected"
        health_status["error"] = str(e)
        return api.create_response(request, health_status, status=503)

    try:
        cache.set("health_check_test", "ok", 10)
        cache.get("health_check_test")
        health_status["cache"] = "connected"
    except Exception as e:
        health_status["cache"] = "disconnected"
        health_status["cache_error"] = str(e)

    return health_status


@api.get(
    "/docs/info",
    summary="Project Documentation Information",
    tags=["System"],
    description="""
    Get information about the project and links to documentation.

    Returns:
    - Project overview and description
    - Links to all available documentation
    - Setup guides and tutorials
    - Ethical scraping guidelines
    - Troubleshooting resources
    - Architecture and design documents
    """,
    response=dict
)
def get_documentation_info(request: HttpRequest) -> dict[str, Any]:
    """
    Get project documentation information and links.
    """
    from pathlib import Path

    # Get repository root (assuming we're in fkapi/fkapi/)
    repo_root = Path(__file__).parent.parent.parent
    docs_dir = repo_root / "docs"

    # Check if docs exist
    docs_available = docs_dir.exists()

    return {
        "project": {
            "name": "Football Kit Archive API",
            "version": "1.0.0",
            "description": "Comprehensive REST API for managing and retrieving football kit information"
        },
        "documentation": {
            "available": docs_available,
            "base_path": str(docs_dir) if docs_available else None,
            "guides": {
                "getting_started": {
                    "title": "Getting Started Guide",
                    "description": "Complete setup guide from scratch, including initial database population and ethical scraping practices",
                    "file": "GETTING_STARTED.md"
                },
                "celery_setup": {
                    "title": "Celery Setup Guide",
                    "description": "Optional: Guide to setting up Celery for background tasks (recommended for production)",
                    "file": "CELERY_SETUP.md"
                },
                "troubleshooting": {
                    "title": "Troubleshooting Guide",
                    "description": "Common issues and solutions for setup, scraping, API, and database problems",
                    "file": "troubleshooting.md"
                },
                "architecture": {
                    "title": "Architecture Documentation",
                    "description": "System architecture, design decisions, and data flow diagrams",
                    "file": "architecture.md"
                },
                "developer_onboarding": {
                    "title": "Developer Onboarding",
                    "description": "Guide for new developers joining the project",
                    "file": "developer-onboarding.md"
                },
                "ethical_scraping": {
                    "title": "Ethical Scraping Practices",
                    "description": "Guidelines for responsible web scraping: robots.txt, rate limiting, Terms of Service",
                    "note": "See GETTING_STARTED.md section 'Legal and Ethical Reminders'"
                }
            },
            "api_documentation": {
                "interactive": "/api/docs",
                "openapi_schema": "/api/openapi.json",
                "endpoint_catalog": "docs/api/endpoint-catalog.md",
                "usage_examples": "docs/api/usage-examples.md"
            },
            "quick_links": {
                "repository": "See repository root for full documentation",
                "docs_directory": "docs/",
                "api_docs": "http://localhost:8000/api/docs"
            }
        },
        "ethical_scraping_reminders": {
            "important": "Always scrape responsibly",
            "guidelines": [
                "Check robots.txt before scraping",
                "Review Terms of Service",
                "Use proper User-Agent with contact info",
                "Respect rate limits (minimum 2 seconds between requests)",
                "Only scrape what you need",
                "Don't overload servers",
                "Handle errors gracefully",
                "Monitor your scraping activity",
                "Give attribution when displaying data"
            ],
            "legal_note": "Web scraping may be subject to legal restrictions. Always ensure you have permission to scrape the target website."
        }
    }


@api.get("/metrics", summary="API Usage Metrics", tags=["System"], description="""
    Get API usage statistics and performance metrics.

    **Response:**
    - `200 OK`: Returns API usage statistics

    **Example Response:**
    ```json
    {
        "endpoints": {
            "GET /api/kits": {
                "count": 150,
                "avg_duration": 0.234,
                "avg_queries": 3.2,
                "status_codes": {"200": 148, "404": 2}
            }
        }
    }
    ```
    """)
def get_metrics(request: HttpRequest) -> dict[str, Any]:
    """
    Get API usage statistics and performance metrics.
    """

    stats_key = 'api_usage_stats'
    stats = cache.get(stats_key, {})

    metrics = {
        "endpoints": {},
    }

    for endpoint, data in stats.items():
        count = data.get('count', 0)
        total_duration = data.get('total_duration', 0.0)
        total_queries = data.get('total_queries', 0)

        metrics["endpoints"][endpoint] = {
            "count": count,
            "avg_duration": round(total_duration / count, 3) if count > 0 else 0.0,
            "avg_queries": round(total_queries / count, 2) if count > 0 else 0,
            "status_codes": dict(data.get('status_codes', {})),
        }

    return metrics


@contextmanager
def db_connection() -> Any:
    """Context manager for database connections."""
    try:
        yield
    finally:
        connection.close()


def _is_postgresql() -> bool:
    """Check if the database is PostgreSQL."""
    return connection.vendor == "postgresql"


def _search_filter(field: str, keyword: str) -> Q:
    """Create a search filter that works with both PostgreSQL and SQLite."""
    if _is_postgresql():
        return Q(**{f"{field}__trigram_word_similar": keyword})
    else:
        return Q(**{f"{field}__icontains": keyword})


def _unaccent_filter(field: str, value: str) -> Q:
    """Create an unaccent filter that works with both PostgreSQL and SQLite."""
    if _is_postgresql():
        return Q(**{f"{field}__unaccent__icontains": value})
    else:
        return Q(**{f"{field}__icontains": value})


@api.get(
    "/clubs/{club_id}/kits",
    response=list[KitSerializer],
    summary="Get Club Kits",
    description="""
    Retrieve all kits for a specific club.

    This is a nested resource endpoint following REST conventions.
    Alternative: Use `/api/kits?club={club_id}` for more flexible filtering.

    **Query Parameters:**
    - `season` (optional): Filter kits by season ID
    - `page` (optional): Page number for pagination
    - `page_size` (optional): Number of items per page

    Returns a list of kits for the specified club.
    """,
    tags=["Clubs"],
)
def get_club_kits(
    request: HttpRequest,
    club_id: int = Path(..., description="Club ID", example=1),
    season: int | None = Query(None, description="Filter by season ID", example=1),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Items per page", ge=1, le=100),
) -> list[KitSerializer]:
    """
    Get all kits for a specific club.

    Args:
        request: The HTTP request
        club_id (int): ID of the club
        season (int, optional): Filter by season ID
        page (int): Page number for pagination
        page_size (int): Number of items per page

    Returns:
        List[KitSerializer]: List of kits for the club

    Raises:
        ClubNotFoundError: If the club with the given ID is not found
    """
    from django.conf import settings
    from django.core.paginator import Paginator

    try:
        club = Club.objects.get(id=club_id)
    except Club.DoesNotExist as e:
        raise ClubNotFoundError(f"club-{club_id}", f"Club with ID {club_id} not found") from e

    cache_key = generate_cache_key("club_kits", club_id, "season", season, "page", page, "page_size", page_size)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    kits_query = Kit.objects.filter(team=club).select_related("team", "season", "brand", "type")

    if season:
        kits_query = kits_query.filter(season__id=season)

    paginator = Paginator(kits_query, page_size)
    page_obj = paginator.get_page(page)
    kits = list(page_obj)

    cache.set(cache_key, kits, timeout=settings.CACHE_TIMEOUT_MEDIUM)
    return kits


@api.get(
    "/clubs/search",
    response=list[ClubSerializer],
    summary="Search Clubs",
    description="""
    Search for clubs using a keyword. The search is performed on both club names and slugs
    using trigram word similarity.

    Returns up to 10 results ordered by ID.
    """,
    tags=["Clubs"],
)
def search_clubs(
    request: HttpRequest,
    keyword: str = Query(..., description="Keyword to search for in club names and slugs", example="manchester"),
) -> list[ClubSerializer]:
    """
    Search for clubs using a keyword.

    Args:
        request: The HTTP request
        keyword (str): Search term for club names and slugs

    Returns:
        List[ClubSerializer]: List of matching clubs, limited to 10 results
    """
    from django.conf import settings

    cache_key = generate_cache_key("search_clubs", keyword)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    with transaction.atomic():
        clubs = list(Club.objects.filter(
            _search_filter("name", keyword) | _search_filter("slug", keyword)
        ).order_by("id")[:10])
        cache.set(cache_key, clubs, timeout=settings.CACHE_TIMEOUT_MEDIUM)
        return clubs


@api.get(
    "/brands/search",
    response=list[BrandJsonSchema],
    summary="Search Brands",
    description="""
    Search for brands by name or slug using trigram similarity.
    Returns up to 10 matched brands ordered by ID.
    """,
    tags=["Brands"],
)
def search_brands(
    request: HttpRequest, keyword: str = Query(..., description="Keyword to search for in brand names or slugs", example="adidas")
) -> list[BrandJsonSchema]:
    """
    Search for brands using a keyword.

    Args:
        request: The HTTP request
        keyword (str): Search term for brand names or slugs

    Returns:
        List[BrandJsonSchema]: List of matching brands, limited to 10 results
    """
    from django.conf import settings

    cache_key = generate_cache_key("search_brands", keyword)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    brands = Brand.objects.filter(
        _search_filter("name", keyword) | _search_filter("slug", keyword)
    ).order_by("id")[:10]

    result = [
        BrandJsonSchema(
            id=b.id,
            name=b.name,
            slug=b.slug,
            logo=b.logo,
            logo_dark=getattr(b, "logo_dark", None) if hasattr(b, "logo_dark") else None,
        )
        for b in brands
    ]
    cache.set(cache_key, result, timeout=settings.CACHE_TIMEOUT_MEDIUM)
    return result


@api.get(
    "/competitions/search",
    response=list[CompetitionJsonSchema],
    summary="Search Competitions",
    description="""
    Search for competitions by name or slug using trigram similarity.
    Returns up to 10 matched competitions ordered by ID.
    """,
    tags=["Competitions"],
)
def search_competitions(
    request: HttpRequest,
    keyword: str = Query(..., description="Keyword to search for in competition names or slugs", example="premier"),
) -> list[CompetitionJsonSchema]:
    """
    Search for competitions using a keyword.

    Args:
        request: The HTTP request
        keyword (str): Search term for competition names or slugs

    Returns:
        List[CompetitionJsonSchema]: List of matching competitions, limited to 10 results
    """
    from django.conf import settings

    cache_key = generate_cache_key("search_competitions", keyword)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    competitions = Competition.objects.filter(
        _search_filter("name", keyword) | _search_filter("slug", keyword)
    ).order_by("id")[:10]

    competition_logo_default = "https://www.footballkitarchive.com/static/logos/not_found.png"
    result = [
        CompetitionJsonSchema(
            id=c.id,
            name=c.name,
            slug=c.slug,
            logo=c.logo if c.logo else competition_logo_default,
            logo_dark=getattr(c, "logo_dark", None) if hasattr(c, "logo_dark") else None,
            country=c.country.code if hasattr(c, "country") and c.country else None,
        )
        for c in competitions
    ]
    cache.set(cache_key, result, timeout=settings.CACHE_TIMEOUT_MEDIUM)
    return result


# Available colors for filtering (hardcoded list)
AVAILABLE_COLORS = [
    "White",
    "Red",
    "Blue",
    "Black",
    "Yellow",
    "Green",
    "Sky blue",
    "Navy",
    "Orange",
    "Gray",
    "Claret",
    "Purple",
    "Pink",
    "Brown",
    "Gold",
    "Silver",
    "Off-white",
]

# Available designs for filtering (hardcoded list - matches DB format)
AVAILABLE_DESIGNS = [
    "Plain",
    "Stripes",
    "Graphic",
    "Chest band",
    "Contrasting sleeves",
    "Pinstripes",
    "Hoops",
    "Single stripe",
    "Half-and-half",
    "Sash",
    "Chevron",
    "Checkers",
    "Gradient",
    "Diagonal",
    "Cross",
    "Quarters",
]

# Pre-computed strings for Query descriptions (to avoid function calls in defaults)
AVAILABLE_COLORS_STR = ', '.join(AVAILABLE_COLORS)
AVAILABLE_DESIGNS_STR = ', '.join(AVAILABLE_DESIGNS)

# Query objects for list_kits endpoint (to avoid function calls in argument defaults)
_QUERY_CLUB = Query(None, description="Filter by club ID", example=1)
_QUERY_SEASON = Query(None, description="Filter by season ID", example=1)
_QUERY_COUNTRY = Query(None, description="Filter by club country (ISO 2-letter code)", example="ES")
_QUERY_PRIMARY_COLOR = Query(None, description=f"Filter by primary color. Options: {AVAILABLE_COLORS_STR}", example="Red")
_QUERY_SECONDARY_COLOR = Query(None, description=f"Filter by secondary color(s). Can specify multiple. Options: {AVAILABLE_COLORS_STR}", example=["White", "Blue"])
_QUERY_DESIGN = Query(None, description=f"Filter by design pattern. Options: {AVAILABLE_DESIGNS_STR}", example="Stripes")
_QUERY_YEAR = Query(None, description="Filter by year (searches in first_year and second_year)", example=2024)
_QUERY_FIRST_YEAR = Query(None, description="Filter by season first year", example=2024)
_QUERY_SECOND_YEAR = Query(None, description="Filter by season second year (use with first_year for exact match)", example=2025)
_QUERY_PAGE = Query(1, description="Page number", ge=1)
_QUERY_PAGE_SIZE = Query(20, description="Items per page", ge=1, le=100)


@api.get(
    "/kits",
    response=list[KitSerializer],
    summary="List Kits",
    description=f"""
    Retrieve kits with advanced filtering options.

    **Filtering Parameters:**

    **Basic Filters:**
    - `club` (int, optional): Filter kits by club ID
    - `season` (int, optional): Filter kits by season ID
    - `country` (str, optional): Filter kits by club country (ISO 2-letter code, e.g., "ES", "GB", "FR")

    **Color Filters:**
    - `primary_color` (str, optional): Filter by primary color name. Available options: {AVAILABLE_COLORS_STR}
    - `secondary_color` (str, optional): Filter by secondary color name. Can be specified multiple times. Available options: {AVAILABLE_COLORS_STR}

    **Design Filter:**
    - `design` (str, optional): Filter by design pattern. Available options: {AVAILABLE_DESIGNS_STR}

    **Year/Season Filters:**
    - `year` (int, optional): Filter by year. Searches in both first_year and second_year of seasons (e.g., 2024 matches "2024-25" and "2023-24")
    - `first_year` (int, optional): Filter by season first year (e.g., 2024 for "2024-25")
    - `second_year` (int, optional): Filter by season second year (e.g., 2025 for "2024-25"). Use with `first_year` for exact season match

    **Pagination:**
    - `page` (int, default: 1): Page number
    - `page_size` (int, default: 20, max: 100): Number of items per page

    **Examples:**
    - Get all kits: `/api/kits`
    - Get kits for a specific club: `/api/kits?club=1`
    - Get kits by primary color: `/api/kits?primary_color=Red`
    - Get kits by secondary color: `/api/kits?secondary_color=White&secondary_color=Blue`
    - Get kits by design: `/api/kits?design=Stripes`
    - Get kits by year: `/api/kits?year=2024`
    - Get kits by exact season: `/api/kits?first_year=2024&second_year=2025`
    - Get kits by country: `/api/kits?country=ES`
    - Combined filters: `/api/kits?primary_color=Red&year=2024&country=ES&design=Stripes`

    The kits are returned in a list, containing all kit details including images,
    competitions, and ratings.
    """,
    tags=["Kits"],
)
def list_kits(
    request: HttpRequest,
    club: int | None = _QUERY_CLUB,
    season: int | None = _QUERY_SEASON,
    country: str | None = _QUERY_COUNTRY,
    primary_color: str | None = _QUERY_PRIMARY_COLOR,
    secondary_color: list[str] | None = _QUERY_SECONDARY_COLOR,
    design: str | None = _QUERY_DESIGN,
    year: int | None = _QUERY_YEAR,
    first_year: int | None = _QUERY_FIRST_YEAR,
    second_year: int | None = _QUERY_SECOND_YEAR,
    page: int = _QUERY_PAGE,
    page_size: int = _QUERY_PAGE_SIZE,
) -> list[KitSerializer]:
    """
    List kits with advanced filtering options.

    Args:
        request: The HTTP request
        club: Filter by club ID
        season: Filter by season ID
        country: Filter by club country (ISO 2-letter code)
        primary_color: Filter by primary color name
        secondary_color: Filter by secondary color name(s) - can be multiple
        design: Filter by design pattern
        year: Filter by year (searches in first_year and second_year)
        first_year: Filter by season first year
        second_year: Filter by season second year
        page: Page number for pagination
        page_size: Number of items per page

    Returns:
        List[KitSerializer]: List of kits matching the criteria
    """
    from django.conf import settings
    from django.core.paginator import Paginator

    from core.models import Color

    cache_key = generate_cache_key(
        "kits",
        "club", club,
        "season", season,
        "country", country,
        "primary_color", primary_color,
        "secondary_color", secondary_color,
        "design", design,
        "year", year,
        "first_year", first_year,
        "second_year", second_year,
        "page", page,
        "page_size", page_size,
    )
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    kits_query = Kit.objects.select_related("team", "season", "brand", "type", "primary_color").prefetch_related("secondary_color")

    if club:
        kits_query = kits_query.filter(team__id=club)
    if season:
        kits_query = kits_query.filter(season__id=season)
    if country:
        kits_query = kits_query.filter(team__country=country.upper())
    if primary_color:
        if primary_color not in AVAILABLE_COLORS:
            raise ValidationError(
                f"Invalid primary_color '{primary_color}'. Available options: {', '.join(AVAILABLE_COLORS)}"
            )
        try:
            color_obj = Color.objects.get(name=primary_color)
            kits_query = kits_query.filter(primary_color=color_obj)
        except Color.DoesNotExist:
            kits_query = kits_query.none()
    if secondary_color:
        invalid_colors = [c for c in secondary_color if c not in AVAILABLE_COLORS]
        if invalid_colors:
            raise ValidationError(
                f"Invalid secondary_color(s): {', '.join(invalid_colors)}. Available options: {', '.join(AVAILABLE_COLORS)}"
            )
        color_objs = list(Color.objects.filter(name__in=secondary_color))
        if len(color_objs) == len(secondary_color):
            for color_obj in color_objs:
                kits_query = kits_query.filter(secondary_color=color_obj)
            kits_query = kits_query.distinct()
        else:
            kits_query = kits_query.none()
    if design:
        design_normalized = design.strip()
        if design_normalized not in AVAILABLE_DESIGNS:
            raise ValidationError(
                f"Invalid design '{design}'. Available options: {', '.join(AVAILABLE_DESIGNS)}"
            )
        kits_query = kits_query.filter(design=design_normalized)
    if year:
        kits_query = kits_query.filter(
            Q(season__first_year=str(year)) | Q(season__second_year=str(year))
        )
    if first_year:
        kits_query = kits_query.filter(season__first_year=str(first_year))
    if second_year:
        kits_query = kits_query.filter(season__second_year=str(second_year))

    paginator = Paginator(kits_query, page_size)
    page_obj = paginator.get_page(page)
    kits = list(page_obj)

    cache.set(cache_key, kits, timeout=settings.CACHE_TIMEOUT_MEDIUM)
    return kits


@api.get(
    "/seasons",
    response=list[SeasonSerializer],
    summary="Get Club Seasons",
    description="""
    Retrieve all available seasons for a specific club.

    Returns a list of seasons sorted by year in descending order (most recent first).
    Each season includes year information and related metadata.
    """,
    tags=["Seasons"],
)
def get_seasons(request: HttpRequest, id: int = Query(..., description="Club ID", example=1)) -> list[SeasonSerializer]:
    """
    Get all available seasons for a club.

    Args:
        request: The HTTP request
        id (int): ID of the club

    Returns:
        List[SeasonSerializer]: List of seasons sorted by year (descending)

    Raises:
        ClubNotFoundError: If the club with the given ID is not found
    """
    from django.conf import settings

    cache_key = generate_cache_key("season", "club", id)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    try:
        club = Club.objects.get(id=id)
    except Club.DoesNotExist as e:
        raise ClubNotFoundError(f"club-{id}", f"Club with ID {id} not found") from e
    kits = Kit.objects.filter(team=club).select_related("season").distinct("season")
    seasons = sorted([kit.season for kit in kits], key=lambda x: x.year, reverse=True)
    cache.set(cache_key, seasons, timeout=settings.CACHE_TIMEOUT_LONG)
    return seasons


@api.get(
    "/seasons/search",
    response=list[SeasonSerializer],
    summary="Search Seasons",
    description="""
    Search for seasons by year. Supports partial year matching.

    Examples:
    - "2025" will match "2025", "2024-25", "2025-26"
    - "2025-" will match "2024-25", "2025-26"
    - "2020-21" will match exactly "2020-21"

    Returns up to 10 matching seasons sorted by year (descending).
    """,
    tags=["Seasons"],
)
def search_seasons(
    request: HttpRequest, keyword: str = Query(..., description="Year or partial year to search for", example="2025")
) -> list[SeasonSerializer]:
    """
    Search for seasons by year.

    Args:
        request: The HTTP request
        keyword (str): Year or partial year to search for (e.g., "2025", "2025-", "2020-21")

    Returns:
        List[SeasonSerializer]: List of matching seasons, limited to 10 results
    """
    if not keyword:
        return []

    keyword = keyword.strip()

    if not keyword:
        return []

    from django.conf import settings

    cache_key = generate_cache_key("search_seasons", keyword)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    year_query = Q()

    if keyword.endswith("-"):
        year_prefix = keyword[:-1]
        if year_prefix.isdigit() and len(year_prefix) == 4:
            year_int = int(year_prefix)
            year_short = str(year_int)[-2:]
            prev_year = year_int - 1

            year_query = Q(year__exact=f"{prev_year}-{year_short}") | Q(year__startswith=f"{year_int}-")
        else:
            year_query = Q(year__startswith=keyword)
    elif "-" in keyword:
        if keyword.count("-") == 1:
            parts = keyword.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                year_query = Q(year__exact=keyword)
            else:
                year_query = Q(year__exact=keyword) | Q(year__startswith=keyword)
        else:
            year_query = Q(year__exact=keyword)
    elif keyword.isdigit():
        year_int = int(keyword)
        if len(keyword) == 4:
            year_short = str(year_int)[-2:]
            prev_year = year_int - 1
            next_year = year_int + 1
            next_year_short = str(next_year)[-2:]

            year_query = (
                Q(year__exact=str(year_int))
                | Q(year__startswith=f"{prev_year}-{year_short}")
                | Q(year__startswith=f"{year_int}-{next_year_short}")
            )
        else:
            year_query = Q(year__icontains=keyword)
    else:
        year_query = Q(year__icontains=keyword)

    seasons = Season.objects.filter(year_query).order_by("-year")[:10]
    result = list(seasons)

    cache.set(cache_key, result, timeout=settings.CACHE_TIMEOUT_MEDIUM)

    return result


@api.get(
    "/kits/search",
    response=list[KitSearchResult],
    summary="Search Kits by Name and Year",
    description="""
    Search for kits using a keyword and optionally a year.

    The search uses a two-tier approach for optimal results:
    1. First shows exact matches (accent-insensitive)
    2. Then shows approximate matches using trigram similarity

    This provides:
    - Accent-insensitive searches (e.g., "Málaga" and "Malaga" return the same results)
    - Approximate matching for typos and spelling variations
    - Partial word matching

    Year matching is precise and supports these formats:
    - "Barcelona Third 2024" will match "2023-24" and "2024-25" seasons
    - "Real Madrid Home 2025" will match "2024-25" season
    - "Málaga 2003" will match "2002-03" and "2003-04" seasons

    Results are limited to 10 items, with exact matches shown first.
    """,
    tags=["Kits"],
)
def search_kits(request: HttpRequest, keyword: str | None = Query(None, description="Search query", example="Málaga 2003")) -> list[KitSearchResult]:
    from django.conf import settings

    search_query = keyword
    if not search_query:
        return []

    cache_key = generate_cache_key("search_kits", search_query)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    # Extract year from query if present
    year_match = re.search(r"\b(19|20)\d{2}\b", search_query)
    year = None
    search_terms = search_query

    if year_match:
        year = year_match.group(0)
        # Remove year from search terms
        search_terms = search_query.replace(year, "").strip()

    # Base query
    base_kits = Kit.objects.select_related("team", "season").all()

    # Apply year filter first if present
    if year:
        year_int = int(year)
        year_short = str(year_int)[-2:]
        prev_year = year_int - 1

        year_query = (
            Q(season__year__exact=str(year_int))
            | Q(season__year__exact=f"{prev_year}-{year_short}")
            | Q(season__year__exact=f"{year_int}-{str(year_int + 1)[-2:]}")
        )

        base_kits = base_kits.filter(year_query)

    # Apply optimized name search
    if search_terms:
        # Split search terms
        terms = search_terms.split()

        # First try: simple icontains search (fastest)
        simple_matches = base_kits.filter(_unaccent_filter("name", search_terms))[:20]

        if simple_matches.exists():
            kits = simple_matches
        else:
            # Second try: individual terms with AND logic
            term_matches = base_kits
            for term in terms:
                if len(term) > 2:  # Only search terms longer than 2 characters
                    term_matches = term_matches.filter(_unaccent_filter("name", term))

            if term_matches.exists():
                kits = term_matches[:20]
            else:
                # Third try: individual terms with OR logic
                or_query = Q()
                for term in terms:
                    if len(term) > 2:
                        or_query |= _unaccent_filter("name", term)

                if or_query:
                    kits = base_kits.filter(or_query)[:20]
                else:
                    kits = base_kits.none()
    else:
        kits = base_kits

    # Get top 10 results and convert to list to avoid lazy evaluation issues
    kits_list = list(kits[:10])

    # Format results
    results = []
    for kit in kits_list:
        results.append(
            {
                "id": kit.id,
                "name": kit.name,
                "main_img_url": kit.main_img_url,
                "team_name": kit.team.name,
                "season_year": kit.season.year,
            }
        )
    cache.set(cache_key, results, timeout=settings.CACHE_TIMEOUT_MEDIUM)
    return results


@api.get(
    "/kits/{kit_id}",
    response=KitJsonSchema,
    summary="Get Kit by ID",
    description="""
    Retrieve comprehensive information about a specific kit by its ID.

    Returns complete kit information including:
    - Basic kit details (name, slug)
    - Complete team information (ID, name, slug, logos)
    - Full season information (ID, year, first_year, second_year)
    - Detailed competition information (ID, name, slug, logos)
    - Kit type details (ID, name)
    - Complete brand information (ID, name, slug, logos)
    - Design information
    - Color information (primary and secondary colors)
    - Image URLs
    """,
    tags=["Kits"],
)
def get_kit(request: HttpRequest, kit_id: int = Path(..., description="Kit ID", example=1)) -> KitJsonSchema:
    """
    Get detailed information for a specific kit.

    Args:
        request: The HTTP request
        kit_id (int): ID of the kit

    Returns:
        KitJsonSchema: Detailed kit information

    Raises:
        KitNotFoundError: If the kit with the given ID is not found
    """
    from django.conf import settings

    cache_key = generate_cache_key("kit_json", kit_id)
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    try:
        kit = get_object_or_404(Kit.objects.select_related("team", "season", "brand", "type", "primary_color").prefetch_related("competition", "secondary_color"), id=kit_id)
    except Exception as e:
        if 'not found' in str(e).lower() or 'does not exist' in str(e).lower():
            raise KitNotFoundError(f"kit-{kit_id}", f"Kit with ID {kit_id} not found") from e
        raise
    competition_logo_default = "https://www.footballkitarchive.com/static/logos/not_found.png"

    # Prepare primary color if available
    primary_color = None
    if kit.primary_color:
        primary_color = ColorJsonSchema(name=kit.primary_color.name, color=kit.primary_color.color)

    # Prepare secondary colors if available
    secondary_colors = []
    if kit.secondary_color.exists():
        secondary_colors = [ColorJsonSchema(name=color.name, color=color.color) for color in kit.secondary_color.all()]

    # Get country information if available
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
    return result


@api.get(
    "/kit-json/{kit_id}",
    response=KitJsonSchema,
    summary="Get Kit by ID (Legacy)",
    description="""
    **⚠️ Deprecated**: This endpoint is maintained for backward compatibility.
    Please use `/api/kits/{kit_id}` instead.

    Retrieve comprehensive information about a specific kit by its ID.
    """,
    tags=["Kits"],
    deprecated=True,
)
def get_kit_json_legacy(request: HttpRequest, kit_id: int = Path(..., description="Kit ID", example=1)) -> KitJsonSchema:
    """Legacy endpoint - redirects to get_kit."""
    return get_kit(request, kit_id)


@api.get(
    "/send-kit/{kit_id}",
    summary="Send Kit to External API",
    description="""
    Send kit information to an external API endpoint.

    Formats and sends the kit data to a specified external endpoint (http://localhost:8888/api/kits/).
    Includes all kit details, team information, and related metadata.
    """,
    tags=["Kits"],
)
def send_kit(request: HttpRequest, kit_id: int = Path(..., description="Kit ID", example=1)) -> JsonResponse:
    """
    Send kit information to an external API.

    Args:
        request: The HTTP request
        kit_id (int): ID of the kit to send

    Returns:
        JsonResponse: Success message and API response or error details

    Raises:
        KitNotFoundError: If the kit is not found
        RequestException: If there's an error sending data to the external API
    """
    try:
        kit = Kit.objects.select_related("team", "season", "brand", "type", "primary_color").prefetch_related("competition", "secondary_color").get(id=kit_id)
    except Kit.DoesNotExist as e:
        raise KitNotFoundError(f"kit-{kit_id}", f"Kit with ID {kit_id} not found") from e
        competition_logo_default = "https://www.footballkitarchive.com/static/logos/not_found.png"
        formatted_competitions = [
            CompetitionJsonSchema(
                id=comp.id,
                name=comp.name,
                slug=comp.slug,
                logo=comp.logo if comp.logo else competition_logo_default,
                logo_dark=comp.logo_dark,
                country=comp.country.code if hasattr(comp, "country") and comp.country else None,
            )
            for comp in kit.competition.all()
        ]

        # Prepare primary color if available
        primary_color = None
        if kit.primary_color:
            primary_color = ColorJsonSchema(name=kit.primary_color.name, color=kit.primary_color.color)

        # Prepare secondary colors if available
        secondary_colors = []
        if kit.secondary_color.exists():
            secondary_colors = [
                ColorJsonSchema(name=color.name, color=color.color) for color in kit.secondary_color.all()
            ]

        # Get country information if available
        country_code = None
        country_name = None
        if hasattr(kit.team, "country") and kit.team.country:
            country_code = kit.team.country.code
            country_name = kit.team.country.name

        formatted_kit = KitJsonSchema(
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
                country_name=country_name,
            ),
            season=SeasonJsonSchema(
                id=kit.season.id,
                year=kit.season.year,
                first_year=kit.season.first_year,
                second_year=kit.season.second_year,
            ),
            competition=formatted_competitions,
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

        response = requests.post(
            "http://localhost:8888/api/kits/", json=formatted_kit.dict(), timeout=15
        )
        response.raise_for_status()

        return JsonResponse({"message": "Kit sent successfully", "response": response.json()})
    except requests.RequestException as e:
        return JsonResponse({"error": f"Error sending data to the API: {str(e)}"}, status=500)


@api.get(
    "/test-search",
    summary="Test Search Functionality",
    description="""
    Test endpoint to verify search functionality with specific examples.
    Tests the search with "burinam" to see if it finds "buriram".
    """,
    tags=["Testing"],
)
def test_search(request: HttpRequest) -> JsonResponse:
    """
    Test endpoint to verify search functionality.
    """
    from django.contrib.postgres.search import TrigramSimilarity

    # Test data
    test_cases = [
        ("burinam", "buriram"),
        ("manchester", "manchester"),
        ("barcelona", "barcelona"),
    ]

    results = {}

    for search_term, expected_match in test_cases:
        # Get all kits
        all_kits = Kit.objects.all()

        # Calculate similarity for each kit
        kits_with_similarity = (
            all_kits.annotate(similarity=TrigramSimilarity("name", search_term))
            .filter(similarity__gt=0.1)
            .order_by("-similarity")[:5]
        )

        # Format results
        kit_results = []
        for kit in kits_with_similarity:
            kit_results.append(
                {"id": kit.id, "name": kit.name, "similarity": float(kit.similarity), "team": kit.team.name}
            )

        results[search_term] = {
            "expected_match": expected_match,
            "found_kits": kit_results,
            "best_match": kit_results[0] if kit_results else None,
        }

    return JsonResponse(
        {
            "test_results": results,
            "message": 'Search test completed. Check if "burinam" finds "buriram" with good similarity.',
        }
    )


@api.get(
    "/random-kits/",
    summary="Get Random Kits",
    description="""
    Retrieve a paginated list of random kits.

    **Pagination Parameters:**
    - `page` (int, default: 1): Page number
    - `page_size` (int, default: 20, max: 100): Number of items per page

    **Response Format:**
    ```json
    {
        "kits": [
            {
                "id": 1,
                "name": "Manchester United 2024-25 Home Kit",
                "slug": "manchester-united-2024-25-home-kit",
                "main_img_url": "https://...",
                "team_name": "Manchester United",
                "season_year": "2024-25",
                "type_name": "Home",
                "brand_name": "Adidas",
                "rating": 8.5,
                "colors": "Red / White",
                "design": "Classic design"
            }
        ],
        "pagination": {
            "current_page": 1,
            "total_pages": 50,
            "total_count": 1000,
            "has_next": true,
            "has_previous": false,
            "next_page": 2,
            "previous_page": null
        }
    }
    ```

    **Example Usage:**
    - Get first page: `/api/random-kits/?page=1&page_size=20`
    - Get second page: `/api/random-kits/?page=2&page_size=20`
    """,
    tags=["Kits"],
)
def get_random_kits(request: HttpRequest, page: int = Query(1, description="Page number", ge=1), page_size: int = Query(20, description="Items per page", ge=1, le=100)) -> dict[str, Any]:
    """
    Get random kits with pagination.
    """
    from django.core.paginator import Paginator

    # Get random kits that have main images
    kits = Kit.objects.filter(main_img_url__isnull=False, main_img_url__gt="").select_related("team", "season", "type", "brand", "primary_color").prefetch_related("secondary_color").order_by("?")

    # Paginate results
    paginator = Paginator(kits, page_size)
    page_obj = paginator.get_page(page)

    # Serialize kits
    kits_data = []
    for kit in page_obj:
        secondary_color_name = None
        if kit.secondary_color.exists():
            secondary_colors = list(kit.secondary_color.all())
            if secondary_colors:
                secondary_color_name = secondary_colors[0].name

        kits_data.append(
            {
                "id": kit.id,
                "name": kit.name,
                "slug": kit.slug,
                "main_img_url": kit.main_img_url,
                "team_name": kit.team.name if kit.team else None,
                "season_year": kit.season.year if kit.season else None,
                "type_name": kit.type.name if kit.type else None,
                "brand_name": kit.brand.name if kit.brand else None,
                "rating": float(kit.rating) if kit.rating else None,
                "colors": f"{kit.primary_color.name} / {secondary_color_name}"
                if kit.primary_color and secondary_color_name
                else (kit.primary_color.name if kit.primary_color else None),
                "design": kit.design,
            }
        )

    return {
        "kits": kits_data,
        "pagination": {
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
        },
    }


@api.get(
    "/random-clubs/",
    summary="Get Random Clubs",
    description="""
    Retrieve a paginated list of random clubs.

    **Pagination Parameters:**
    - `page` (int, default: 1): Page number
    - `page_size` (int, default: 20, max: 100): Number of items per page

    **Response Format:**
    ```json
    {
        "clubs": [
            {
                "id": 1,
                "name": "Manchester United",
                "slug": "manchester-united-kits",
                "logo": "https://...",
                "country": "GB",
                "kit_count": 150
            }
        ],
        "pagination": {
            "current_page": 1,
            "total_pages": 25,
            "total_count": 500,
            "has_next": true,
            "has_previous": false,
            "next_page": 2,
            "previous_page": null
        }
    }
    ```

    **Example Usage:**
    - Get first page: `/api/random-clubs/?page=1&page_size=20`
    - Get second page: `/api/random-clubs/?page=2&page_size=20`
    """,
    tags=["Clubs"],
)
def get_random_clubs(request: HttpRequest, page: int = Query(1, description="Page number", ge=1), page_size: int = Query(20, description="Items per page", ge=1, le=100)) -> dict[str, Any]:
    """
    Get random clubs with pagination.
    """
    from django.core.paginator import Paginator

    try:
        from django.db.models import Count

        # Get clubs that have logos and exclude default logo
        clubs = (
            Club.objects.filter(logo__isnull=False, logo__gt="")
            .exclude(logo="https://www.footballkitarchive.com/static/logos/not_found.png")
            .annotate(kit_count=Count("kit"))
            .order_by("?")
        )

        # Paginate results
        paginator = Paginator(clubs, page_size)
        page_obj = paginator.get_page(page)

        # Serialize clubs
        clubs_data = []
        for club in page_obj:
            clubs_data.append(
                {
                    "id": club.id,
                    "name": club.name,
                    "slug": club.slug,
                    "logo": club.logo,
                    "country": str(club.country) if club.country else None,
                    "kit_count": club.kit_count,
                }
            )

        return {
            "clubs": clubs_data,
            "pagination": {
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
                "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
            },
        }
    except Exception as e:
        return {
            "clubs": [],
            "pagination": {
                "current_page": 1,
                "total_pages": 0,
                "total_count": 0,
                "has_next": False,
                "has_previous": False,
                "next_page": None,
                "previous_page": None,
            },
            "error": str(e),
        }


