# Standard library imports
import hashlib
import os
import re
from contextlib import contextmanager
from typing import Any

# Third-party imports
import requests
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Path, Query, Schema
from ninja_apikey.security import APIKeyAuth

# Local imports
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
    API for managing and retrieving football kit information.

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
    """,
    version="1.0.0",
    auth=_api_auth,
    csrf=False,  # Disable CSRF for API endpoints
)


# Error handlers
@api.exception_handler(Exception)
def custom_exception_handler(request: HttpRequest, exc: Exception) -> Any:
    return api.create_response(request, {"detail": str(exc)}, status=500)


@api.get("/health", summary="Health Check", tags=["System"], description="""
    Check if the API and database are functioning correctly.

    **Response:**
    - `200 OK`: API and database are healthy
    - `503 Service Unavailable`: Database connection failed

    **Example Response:**
    ```json
    {
        "status": "healthy",
        "timestamp": "2026-01-13T12:00:00Z"
    }
    ```
    """)
def health_check(request: HttpRequest) -> dict[str, Any]:
    """
    Check if the API and database are functioning correctly.
    """
    from datetime import datetime
    try:
        # Simple database check
        Club.objects.count()
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return api.create_response(request, {"status": "unhealthy", "error": str(e)}, status=503)


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
    with transaction.atomic():
        clubs = Club.objects.filter(
            _search_filter("name", keyword) | _search_filter("slug", keyword)
        ).order_by("id")[:10]
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
    brands = Brand.objects.filter(
        _search_filter("name", keyword) | _search_filter("slug", keyword)
    ).order_by("id")[:10]

    # Explicitly serialize as list of dicts in case BrandJsonSchema is a pydantic/ninja schema
    return [
        BrandJsonSchema(
            id=b.id,
            name=b.name,
            slug=b.slug,
            logo=b.logo,
            logo_dark=getattr(b, "logo_dark", None) if hasattr(b, "logo_dark") else None,
        )
        for b in brands
    ]


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
    competitions = Competition.objects.filter(
        _search_filter("name", keyword) | _search_filter("slug", keyword)
    ).order_by("id")[:10]

    competition_logo_default = "https://www.footballkitarchive.com/static/logos/not_found.png"
    return [
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


@api.get(
    "/kits",
    response=list[KitSerializer],
    summary="Get Club Kits by Season",
    description="""
    Retrieve all kits for a specific club in a specific season.

    The kits are returned in a list, containing all kit details including images,
    competitions, and ratings.
    """,
    tags=["Kits"],
)
def get_kits(
    request: HttpRequest,
    club: int = Query(..., description="Club ID", example=1),
    season: int = Query(..., description="Season ID", example=1),
) -> list[KitSerializer]:
    """
    Get all kits for a club in a specific season.

    Args:
        request: The HTTP request
        club (int): ID of the club
        season (int): ID of the season

    Returns:
        List[KitSerializer]: List of kits matching the criteria
    """
    kits = Kit.objects.filter(season__id=season, team__id=club)
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
        Club.DoesNotExist: If the club with the given ID is not found
    """
    club = Club.objects.get(id=id)
    kits = Kit.objects.filter(team=club).select_related("season").distinct("season")
    seasons = sorted([kit.season for kit in kits], key=lambda x: x.year, reverse=True)
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

    cache_key = f"season_search_{hashlib.md5(keyword.encode()).hexdigest()}"
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

    cache.set(cache_key, result, timeout=3600)

    return result


@api.get(
    "/kit-json/{kit_id}",
    response=KitJsonSchema,
    summary="Get Complete Kit Details",
    description="""
    Retrieve comprehensive information about a specific kit.

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
def get_kit_json(request: HttpRequest, kit_id: int = Path(..., description="Kit ID", example=1)) -> KitJsonSchema:
    """
    Get detailed information for a specific kit.

    Args:
        request: The HTTP request
        kit_id (int): ID of the kit

    Returns:
        KitJsonSchema: Detailed kit information

    Raises:
        Http404: If the kit with the given ID is not found
    """
    kit = get_object_or_404(Kit, id=kit_id)
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

    return KitJsonSchema(
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
        Http404: If the kit is not found
        RequestException: If there's an error sending data to the external API
    """
    try:
        kit = Kit.objects.get(id=kit_id)
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
    except Kit.DoesNotExist:
        return JsonResponse({"error": "Kit not found"}, status=404)
    except requests.RequestException as e:
        return JsonResponse({"error": f"Error sending data to the API: {str(e)}"}, status=500)


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
    search_query = keyword
    if not search_query:
        return []

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
    return results


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
    kits = Kit.objects.filter(main_img_url__isnull=False, main_img_url__gt="").order_by("?")

    # Paginate results
    paginator = Paginator(kits, page_size)
    page_obj = paginator.get_page(page)

    # Serialize kits
    kits_data = []
    for kit in page_obj:
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
                "colors": f"{kit.primary_color.name} / {kit.secondary_color.name}"
                if kit.primary_color and kit.secondary_color
                else None,
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
        # Get clubs that have logos and exclude default logo
        clubs = (
            Club.objects.filter(logo__isnull=False, logo__gt="")
            .exclude(logo="https://www.footballkitarchive.com/static/logos/not_found.png")
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
                    "kit_count": club.kit_set.count(),
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


@api.get("/merge-suggestions/")
def get_merge_suggestions(request: HttpRequest, threshold: float = 0.70, limit: int = 50) -> dict[str, Any]:
    """
    Get suggestions for merging duplicate clubs based on improved similarity algorithm.
    Filters out clubs with words like "femenino", "sub", "filial", etc.
    Uses normalized names, multiple similarity metrics, and logo matching.
    """
    import re
    from difflib import SequenceMatcher

    from django.db.models import Count

    def normalize_name(name: str) -> str:
        """Normalize club name by removing common prefixes and suffixes"""
        name = name.lower().strip()
        original_name = name

        prefixes = [
            "fc ",
            "cf ",
            "cfc ",
            "sc ",
            "ac ",
            "ud ",
            "cd ",
            "sd ",
            "rcd ",
            "rc ",
            "real ",
            "athletic ",
            "atletico ",
            "atlético ",
            "deportivo ",
            "sporting ",
            "club ",
            "football club ",
            "futbol club ",
            "soccer club ",
            "tsv ",
            "as ",
        ]

        suffixes = [" fc", " cf", " cfc", " sc", " ac", " ud", " cd", " sd", " rcd", " rc"]

        for prefix in sorted(prefixes, key=len, reverse=True):
            if name.startswith(prefix):
                name = name[len(prefix) :].strip()
                break

        for suffix in sorted(suffixes, key=len, reverse=True):
            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()
                break

        name = re.sub(r"\s+", " ", name)

        if not name:
            return original_name

        return name

    def remove_exclusion_words(name: str) -> str:
        """Remove exclusion words from name for comparison"""
        exclude_words = [
            "beleza",
            "gloriosas",
            "futsal",
            "beach",
            "indoor",
            "femenino",
            "femenina",
            "frauen",
            "women",
            "woman",
        ]
        words = name.split()
        filtered_words = [w for w in words if not any(ex in w for ex in exclude_words)]
        return " ".join(filtered_words).strip()

    def calculate_similarity(name1: str, name2: str, logo1: str | None, logo2: str | None) -> float:
        """Calculate multiple similarity scores and combine them"""
        name1_lower = name1.lower()
        name2_lower = name2.lower()

        norm1 = normalize_name(name1)
        norm2 = normalize_name(name2)

        scores = {}

        scores["exact_match"] = 1.0 if name1_lower == name2_lower else 0.0
        scores["normalized_exact"] = 1.0 if norm1 == norm2 else 0.0

        scores["normalized_ratio"] = SequenceMatcher(None, norm1, norm2).ratio()
        scores["original_ratio"] = SequenceMatcher(None, name1_lower, name2_lower).ratio()

        if norm1 and norm2:
            if norm1 in norm2 or norm2 in norm1:
                if len(norm1) > 5 and len(norm2) > 5:
                    scores["contains"] = 0.95
                else:
                    scores["contains"] = 0.85
            else:
                scores["contains"] = 0.0
        else:
            scores["contains"] = 0.0

        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1 and words2:
            common_words = words1.intersection(words2)
            total_words = words1.union(words2)
            scores["word_overlap"] = len(common_words) / len(total_words) if total_words else 0.0
        else:
            scores["word_overlap"] = 0.0

        def get_logo_filename(logo_url):
            """Extract filename from logo URL for comparison"""
            if not logo_url or logo_url == "https://www.footballkitarchive.com/static/logos/not_found.png":
                return None
            try:
                from urllib.parse import unquote, urlparse

                parsed = urlparse(logo_url)
                path = unquote(parsed.path)
                filename = path.split("/")[-1]
                filename_base = filename.split("?")[0].split("&")[0]
                return filename_base.lower()
            except Exception:
                return None

        logo1_file = get_logo_filename(logo1)
        logo2_file = get_logo_filename(logo2)

        if logo1_file and logo2_file and logo1_file == logo2_file:
            scores["logo_match"] = 0.3
        elif (
            logo1
            and logo2
            and logo1 == logo2
            and logo1 != "https://www.footballkitarchive.com/static/logos/not_found.png"
        ):
            scores["logo_match"] = 0.3
        else:
            scores["logo_match"] = 0.0

        if len(norm1) >= 3 and len(norm2) >= 3:
            if norm1.startswith(norm2[:3]) or norm2.startswith(norm1[:3]):
                scores["prefix_match"] = 0.1
            else:
                scores["prefix_match"] = 0.0
        else:
            scores["prefix_match"] = 0.0

        base_score = (
            scores["exact_match"] * 0.25
            + scores["normalized_exact"] * 0.2
            + scores["normalized_ratio"] * 0.2
            + scores["original_ratio"] * 0.1
            + scores["contains"] * 0.15
            + scores["word_overlap"] * 0.15
        )

        logo_boost = 0.0
        if scores["logo_match"] > 0:
            logo_boost = scores["logo_match"]
            if scores["normalized_ratio"] > 0.3:
                logo_boost += 0.2
            if scores["contains"] > 0:
                logo_boost += 0.15
            if scores["word_overlap"] > 0.3:
                logo_boost += 0.15

        final_score = min(base_score + logo_boost + scores["prefix_match"], 1.0)

        return min(final_score, 1.0), scores

    try:
        exclude_keywords = [
            "femenino",
            "femenina",
            "frauen",
            "women",
            "woman",
            "sub-",
            "sub ",
            "sub19",
            "sub-19",
            "sub 19",
            "sub20",
            "sub-20",
            "sub 20",
            "sub21",
            "sub-21",
            "sub 21",
            "filial",
            "b team",
            "b-team",
            "reserve",
            "reserves",
            "youth",
            "academy",
            "u19",
            "u20",
            "u21",
            "u23",
            "u-19",
            "u-20",
            "u-21",
            "u-23",
            "beleza",
            "gloriosas",
            "futsal",
            "beach",
            "indoor",
        ]

        all_clubs = Club.objects.annotate(kit_count=Count("kit")).all()

        filtered_clubs = []
        excluded_clubs = []

        for club in all_clubs:
            name_lower = club.name.lower()

            should_exclude = False
            for keyword in exclude_keywords:
                if keyword in name_lower:
                    should_exclude = True
                    break

            if not should_exclude:
                filtered_clubs.append(club)
            else:
                excluded_clubs.append(club)

        suggestions = []
        processed_pairs = set()

        total_comparisons = len(filtered_clubs) * (len(filtered_clubs) - 1) // 2
        max_comparisons = 100000

        if total_comparisons > max_comparisons:
            filtered_clubs = filtered_clubs[: int((max_comparisons * 2) ** 0.5) + 1]

        for i, club1 in enumerate(filtered_clubs):
            for club2 in filtered_clubs[i + 1 :]:
                pair_key = tuple(sorted([club1.id, club2.id]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                if club1.country and club2.country and club1.country != club2.country:
                    continue

                norm1 = normalize_name(club1.name)
                norm2 = normalize_name(club2.name)

                norm1_in_norm2 = norm1 in norm2 if norm1 and norm2 else False
                norm2_in_norm1 = norm2 in norm1 if norm1 and norm2 else False

                similarity, scores = calculate_similarity(club1.name, club2.name, club1.logo, club2.logo)

                should_include = False
                if norm1_in_norm2 or norm2_in_norm1:
                    should_include = True
                elif similarity >= threshold:
                    should_include = True
                elif scores["normalized_ratio"] > 0.5 and scores["word_overlap"] > 0.3:
                    should_include = True
                elif scores["contains"] > 0 and scores["normalized_ratio"] > 0.4:
                    should_include = True

                if should_include:
                    suggestions.append(
                        {
                            "club1": {
                                "id": club1.id,
                                "name": club1.name,
                                "slug": club1.slug,
                                "kit_count": club1.kit_count,
                                "logo": club1.logo,
                                "country": str(club1.country) if club1.country else None,
                            },
                            "club2": {
                                "id": club2.id,
                                "name": club2.name,
                                "slug": club2.slug,
                                "kit_count": club2.kit_count,
                                "logo": club2.logo,
                                "country": str(club2.country) if club2.country else None,
                            },
                            "similarity": round(similarity, 3),
                            "total_kits": club1.kit_count + club2.kit_count,
                            "scores": {
                                "normalized_ratio": round(scores["normalized_ratio"], 3),
                                "word_overlap": round(scores["word_overlap"], 3),
                                "logo_match": scores["logo_match"] > 0,
                            },
                        }
                    )

                    if len(suggestions) >= limit * 2:
                        break

            if len(suggestions) >= limit * 2:
                break

        for club1 in filtered_clubs:
            for club2 in excluded_clubs:
                pair_key = tuple(sorted([club1.id, club2.id]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                if club1.country and club2.country and club1.country != club2.country:
                    continue

                norm1 = normalize_name(club1.name)
                norm2 = normalize_name(club2.name)

                clean1 = remove_exclusion_words(norm1)
                clean2 = remove_exclusion_words(norm2)

                norm1_in_norm2 = norm1 in norm2 if norm1 and norm2 else False
                norm2_in_norm1 = norm2 in norm1 if norm1 and norm2 else False
                clean1_in_clean2 = clean1 in clean2 if clean1 and clean2 else False
                clean2_in_clean1 = clean2 in clean1 if clean1 and clean2 else False

                similarity, scores = calculate_similarity(club1.name, club2.name, club1.logo, club2.logo)

                clean_similarity = SequenceMatcher(None, clean1, clean2).ratio() if clean1 and clean2 else 0.0

                should_include = False
                if norm1_in_norm2 or norm2_in_norm1:
                    should_include = True
                elif clean1_in_clean2 or clean2_in_clean1:
                    should_include = True
                elif clean_similarity > 0.35:
                    should_include = True
                elif similarity >= threshold * 0.5:
                    should_include = True
                elif scores["normalized_ratio"] > 0.3:
                    should_include = True
                elif scores["word_overlap"] > 0.3:
                    should_include = True
                elif scores["contains"] > 0 and clean_similarity > 0.2:
                    should_include = True
                elif scores["original_ratio"] > 0.35:
                    should_include = True
                elif len(clean1) > 5 and len(clean2) > 5:
                    words1 = set(clean1.split())
                    words2 = set(clean2.split())
                    if words1 and words2:
                        common = words1.intersection(words2)
                        if len(common) >= 2:
                            should_include = True

                if should_include:
                    norm1 = normalize_name(club1.name)
                    norm2 = normalize_name(club2.name)

                    clean1 = remove_exclusion_words(norm1)
                    clean2 = remove_exclusion_words(norm2)

                    norm1_in_norm2 = norm1 in norm2 if norm1 and norm2 else False
                    norm2_in_norm1 = norm2 in norm1 if norm1 and norm2 else False
                    clean1_in_clean2 = clean1 in clean2 if clean1 and clean2 else False
                    clean2_in_clean1 = clean2 in clean1 if clean1 and clean2 else False

                    similarity, scores = calculate_similarity(club1.name, club2.name, club1.logo, club2.logo)

                    clean_similarity = SequenceMatcher(None, clean1, clean2).ratio() if clean1 and clean2 else 0.0

                    should_include = False
                    if norm1_in_norm2 or norm2_in_norm1:
                        should_include = True
                    elif clean1_in_clean2 or clean2_in_clean1:
                        should_include = True
                    elif clean_similarity > 0.5:
                        should_include = True
                    elif similarity >= threshold:
                        should_include = True
                    elif scores["logo_match"] > 0:
                        if scores["normalized_ratio"] > 0.25:
                            should_include = True
                        elif scores["word_overlap"] > 0.25:
                            should_include = True
                        elif scores["contains"] > 0:
                            should_include = True
                        elif clean_similarity > 0.4:
                            should_include = True
                        elif scores["original_ratio"] > 0.4:
                            should_include = True

                    if should_include:
                        suggestions.append(
                            {
                                "club1": {
                                    "id": club1.id,
                                    "name": club1.name,
                                    "slug": club1.slug,
                                    "kit_count": club1.kit_count,
                                    "logo": club1.logo,
                                    "country": str(club1.country) if club1.country else None,
                                },
                                "club2": {
                                    "id": club2.id,
                                    "name": club2.name,
                                    "slug": club2.slug,
                                    "kit_count": club2.kit_count,
                                    "logo": club2.logo,
                                    "country": str(club2.country) if club2.country else None,
                                },
                                "similarity": round(similarity, 3),
                                "total_kits": club1.kit_count + club2.kit_count,
                                "scores": {
                                    "normalized_ratio": round(scores["normalized_ratio"], 3),
                                    "word_overlap": round(scores["word_overlap"], 3),
                                    "logo_match": scores["logo_match"] > 0,
                                },
                            }
                        )

                        if len(suggestions) >= limit * 2:
                            break

            if len(suggestions) >= limit * 2:
                break

        suggestions.sort(key=lambda x: x["total_kits"], reverse=True)
        suggestions = suggestions[:limit]

        return {"suggestions": suggestions, "total": len(suggestions), "threshold": threshold}
    except Exception as e:
        return {"suggestions": [], "total": 0, "error": str(e)}


@api.post("/merge-clubs/")
def merge_clubs(request: HttpRequest, source_id: int = Query(...), target_id: int = Query(...)) -> dict[str, Any]:
    """
    Merge two clubs. Moves all kits from source to target and deletes source.
    """
    from django.db import transaction

    try:
        source_club = Club.objects.get(id=source_id)
        target_club = Club.objects.get(id=target_id)

        if source_club.id == target_club.id:
            return {"success": False, "error": "Cannot merge a club with itself"}

        source_kits = source_club.kit_set.all()
        source_kit_count = source_kits.count()

        with transaction.atomic():
            source_kits.update(team=target_club)

            if not target_club.logo and source_club.logo:
                target_club.logo = source_club.logo
            if not target_club.logo_dark and source_club.logo_dark:
                target_club.logo_dark = source_club.logo_dark
            if not target_club.country and source_club.country:
                target_club.country = source_club.country
            if not target_club.id_fka and source_club.id_fka:
                target_club.id_fka = source_club.id_fka

            target_club.save()
            source_club.delete()

        return {
            "success": True,
            "message": f"Successfully merged {source_kit_count} kits from {source_club.name} to {target_club.name}",
            "merged_kits": source_kit_count,
            "target_club": {
                "id": target_club.id,
                "name": target_club.name,
                "slug": target_club.slug,
            },
        }
    except Club.DoesNotExist as e:
        return {"success": False, "error": f"Club not found: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
