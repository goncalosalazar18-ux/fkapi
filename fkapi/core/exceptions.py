"""
Custom exception classes for the FKApi application.

This module provides standardized exception classes for better error handling
and more informative error messages throughout the application.
"""


class ScrapingError(Exception):
    """Base exception for scraping-related errors."""

    def __init__(self, message: str, slug: str | None = None):
        """
        Initialize a ScrapingError.

        Args:
            message: Error message describing what went wrong
            slug: Optional slug or identifier related to the error
        """
        self.message = message
        self.slug = slug
        super().__init__(self.message)


class KitNotFoundError(ScrapingError):
    """Raised when a kit is not found on the source."""

    def __init__(self, slug: str, message: str | None = None):
        """
        Initialize a KitNotFoundError.

        Args:
            slug: The kit slug that was not found
            message: Optional custom error message
        """
        if message is None:
            message = f"Kit not found: {slug}"
        super().__init__(message, slug)


class ClubNotFoundError(ScrapingError):
    """Raised when a club is not found on the source."""

    def __init__(self, slug: str, message: str | None = None):
        """
        Initialize a ClubNotFoundError.

        Args:
            slug: The club slug that was not found
            message: Optional custom error message
        """
        if message is None:
            message = f"Club not found: {slug}"
        super().__init__(message, slug)


class InvalidSeasonError(ScrapingError):
    """Raised when a season format is invalid or cannot be parsed."""

    def __init__(self, season_slug: str, message: str | None = None):
        """
        Initialize an InvalidSeasonError.

        Args:
            season_slug: The season slug that is invalid
            message: Optional custom error message
        """
        if message is None:
            message = f"Invalid season format: {season_slug}"
        super().__init__(message, season_slug)


class RateLimitExceededError(ScrapingError):
    """Raised when the rate limit for API requests is exceeded."""

    def __init__(self, message: str | None = None):
        """
        Initialize a RateLimitExceededError.

        Args:
            message: Optional custom error message
        """
        if message is None:
            message = "Rate limit exceeded. Please try again later."
        super().__init__(message, None)
