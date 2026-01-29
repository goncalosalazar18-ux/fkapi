"""
Constants used throughout the application.

This module centralizes all magic strings and constants to improve maintainability
and follow the DRY principle.
"""

# Scraping constants
BASE_URL = "https://www.footballkitarchive.com"
DEFAULT_LOGO_URL = f"{BASE_URL}/static/logos/not_found.png"

# HTML class names and selectors
FACT_TABLE_CLASS = "fact-table"
TOP_IMAGE_CLASS = "top-image"
KIT_CONTAINER_CLASS = "kit-container"
KIT_CLASS = "kit"
KIT_SEASON_CLASS = "kit-season"
COLLECTION_CONTAINER_CLASS = "collection-container"
SECTION_DETAILS_CLASS = "section-details"

# Field labels for fact table
FIELD_TEAM = "team"
FIELD_SEASON = "season"
FIELD_TYPE = "type"
FIELD_KIT_TYPE = "kit type"
FIELD_BRAND = "brand"
FIELD_COLORS = "colors"
FIELD_DESIGN = "design"
FIELD_LEAGUE = "league"
FIELD_RATING = "rating"

# HTML element IDs
RATING_SPAN_ID = "rating"
RATING_DETAILS_ID = "rating-details-no"

# Season constants
CURRENT_SEASON_YEAR = "2024"
CURRENT_CENTURY = "20"

# URL patterns
LATEST_PAGE_URL = "/latest/?p="
USER_PAGE_URL = "/user/{username}?p="

# File names for logging
TEAM_SLUG_CHANGES_LOG = "team_slug_changes.log"

# Brand slug suffix
BRAND_SLUG_SUFFIX = "-kits"

# Color separators
COLOR_SEPARATOR_SLASH = " / "
COLOR_SEPARATOR_COMMA = ", "
COMPETITION_SEPARATOR = "·"

# HTTP status codes
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_NOT_FOUND = 404

# Scraper messages and parsers
MSG_403_RETRY_PROXY = "Received 403 status code. Retrying with a new proxy."
HTML_PARSER = "html.parser"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2

# Competition slug suffix
COMPETITION_SLUG_SUFFIX = "-kits"
