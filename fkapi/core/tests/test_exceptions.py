"""
Unit tests for custom exception classes.

This module tests the custom exception classes defined in core.exceptions.
"""


from core.exceptions import (
    ClubNotFoundError,
    InvalidSeasonError,
    KitNotFoundError,
    RateLimitExceededError,
    ScrapingError,
)


class TestScrapingError:
    """Test cases for ScrapingError base exception."""

    def test_scraping_error_with_message(self):
        """Test ScrapingError with only a message."""
        error = ScrapingError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.slug is None

    def test_scraping_error_with_slug(self):
        """Test ScrapingError with message and slug."""
        error = ScrapingError("Test error", "test-slug")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.slug == "test-slug"


class TestKitNotFoundError:
    """Test cases for KitNotFoundError."""

    def test_kit_not_found_error_default_message(self):
        """Test KitNotFoundError with default message."""
        error = KitNotFoundError("test-kit-slug")
        assert str(error) == "Kit not found: test-kit-slug"
        assert error.message == "Kit not found: test-kit-slug"
        assert error.slug == "test-kit-slug"
        assert isinstance(error, ScrapingError)

    def test_kit_not_found_error_custom_message(self):
        """Test KitNotFoundError with custom message."""
        error = KitNotFoundError("test-kit-slug", "Custom error message")
        assert str(error) == "Custom error message"
        assert error.message == "Custom error message"
        assert error.slug == "test-kit-slug"


class TestClubNotFoundError:
    """Test cases for ClubNotFoundError."""

    def test_club_not_found_error_default_message(self):
        """Test ClubNotFoundError with default message."""
        error = ClubNotFoundError("test-club-slug")
        assert str(error) == "Club not found: test-club-slug"
        assert error.message == "Club not found: test-club-slug"
        assert error.slug == "test-club-slug"
        assert isinstance(error, ScrapingError)

    def test_club_not_found_error_custom_message(self):
        """Test ClubNotFoundError with custom message."""
        error = ClubNotFoundError("test-club-slug", "Custom error message")
        assert str(error) == "Custom error message"
        assert error.message == "Custom error message"
        assert error.slug == "test-club-slug"


class TestInvalidSeasonError:
    """Test cases for InvalidSeasonError."""

    def test_invalid_season_error_default_message(self):
        """Test InvalidSeasonError with default message."""
        error = InvalidSeasonError("2023-24")
        assert str(error) == "Invalid season format: 2023-24"
        assert error.message == "Invalid season format: 2023-24"
        assert error.slug == "2023-24"
        assert isinstance(error, ScrapingError)

    def test_invalid_season_error_custom_message(self):
        """Test InvalidSeasonError with custom message."""
        error = InvalidSeasonError("2023-24", "Custom error message")
        assert str(error) == "Custom error message"
        assert error.message == "Custom error message"
        assert error.slug == "2023-24"


class TestRateLimitExceededError:
    """Test cases for RateLimitExceededError."""

    def test_rate_limit_exceeded_error_default_message(self):
        """Test RateLimitExceededError with default message."""
        error = RateLimitExceededError()
        assert str(error) == "Rate limit exceeded. Please try again later."
        assert error.message == "Rate limit exceeded. Please try again later."
        assert error.slug is None
        assert isinstance(error, ScrapingError)

    def test_rate_limit_exceeded_error_custom_message(self):
        """Test RateLimitExceededError with custom message."""
        error = RateLimitExceededError("Custom rate limit message")
        assert str(error) == "Custom rate limit message"
        assert error.message == "Custom rate limit message"
        assert error.slug is None


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_scraping_error(self):
        """Test that all custom exceptions inherit from ScrapingError."""
        assert issubclass(KitNotFoundError, ScrapingError)
        assert issubclass(ClubNotFoundError, ScrapingError)
        assert issubclass(InvalidSeasonError, ScrapingError)
        assert issubclass(RateLimitExceededError, ScrapingError)

    def test_all_exceptions_inherit_from_exception(self):
        """Test that all custom exceptions inherit from Exception."""
        assert issubclass(ScrapingError, Exception)
        assert issubclass(KitNotFoundError, Exception)
        assert issubclass(ClubNotFoundError, Exception)
        assert issubclass(InvalidSeasonError, Exception)
        assert issubclass(RateLimitExceededError, Exception)
