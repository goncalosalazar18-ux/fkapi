"""
Service for season validation and correction logic.
"""

import logging
import re
from typing import Any

from core.models import Season

logger = logging.getLogger(__name__)

# Constants for validation
MIN_YEAR = 1800
MAX_YEAR = 2100
# Maximum years between first_year and second_year
# For modern seasons (after 1960), max span is 2 years
# For older seasons (before 1960), allow larger spans (up to 20 years)
# This handles cases like "1937-49" or "1956-59" which were common in older football
def get_max_season_span(first_year_int: int) -> int:
    """Get maximum allowed season span based on the first year."""
    return 20 if first_year_int < 1960 else 2


class SeasonsService:
    """Service for managing season validation and correction."""

    @staticmethod
    def find_problematic_seasons() -> dict[str, list[dict[str, Any]]]:
        """
        Find all seasons with problematic data.

        Returns:
            Dictionary with problem types as keys and lists of problematic seasons as values
        """
        problems: dict[str, list[dict[str, Any]]] = {
            "invalid_first_year": [],
            "invalid_second_year": [],
            "second_year_before_first": [],
            "excessive_year_span": [],
            "year_format_mismatch": [],
            "out_of_range": [],
        }

        seasons = Season.objects.all().select_related().prefetch_related("kit_set")

        for season in seasons:
            # Validate first_year
            first_year_valid, first_year_int = SeasonsService._validate_year(season.first_year)
            if not first_year_valid:
                problems["invalid_first_year"].append({
                    "season": season,
                    "issue": f"first_year '{season.first_year}' is not a valid year",
                    "kit_count": season.kit_set.count(),
                })
                continue

            # Check if first_year is out of reasonable range
            if first_year_int < MIN_YEAR or first_year_int > MAX_YEAR:
                problems["out_of_range"].append({
                    "season": season,
                    "issue": f"first_year '{season.first_year}' is out of range ({MIN_YEAR}-{MAX_YEAR})",
                    "kit_count": season.kit_set.count(),
                })

            # Validate second_year if present
            if season.second_year:
                second_year_valid, second_year_int = SeasonsService._validate_year(season.second_year)
                if not second_year_valid:
                    problems["invalid_second_year"].append({
                        "season": season,
                        "issue": f"second_year '{season.second_year}' is not a valid year",
                        "kit_count": season.kit_set.count(),
                    })
                    continue

                # Check if second_year is out of reasonable range
                if second_year_int < MIN_YEAR or second_year_int > MAX_YEAR:
                    problems["out_of_range"].append({
                        "season": season,
                        "issue": f"second_year '{season.second_year}' is out of range ({MIN_YEAR}-{MAX_YEAR})",
                        "kit_count": season.kit_set.count(),
                    })

                # Check if second_year is before first_year
                if second_year_int < first_year_int:
                    problems["second_year_before_first"].append({
                        "season": season,
                        "issue": f"second_year '{season.second_year}' ({second_year_int}) is before first_year '{season.first_year}' ({first_year_int})",
                        "year_span": first_year_int - second_year_int,
                        "kit_count": season.kit_set.count(),
                    })

                # Check if year span is excessive
                year_span = second_year_int - first_year_int
                max_span = get_max_season_span(first_year_int)
                if year_span > max_span:
                    problems["excessive_year_span"].append({
                        "season": season,
                        "issue": f"Year span is {year_span} years (max allowed: {max_span})",
                        "year_span": year_span,
                        "kit_count": season.kit_set.count(),
                    })

            # Check if year format matches first_year/second_year
            year_format_issue = SeasonsService._check_year_format_consistency(season)
            if year_format_issue:
                problems["year_format_mismatch"].append({
                    "season": season,
                    "issue": year_format_issue,
                    "kit_count": season.kit_set.count(),
                })

        return problems

    @staticmethod
    def _validate_year(year_str: str) -> tuple[bool, int | None]:
        """
        Validate if a year string is a valid year.

        Args:
            year_str: Year string to validate

        Returns:
            Tuple of (is_valid, year_int or None)
        """
        if not year_str or not year_str.strip():
            return False, None

        # Check if it's a 4-digit number
        if not re.match(r'^\d{4}$', year_str.strip()):
            return False, None

        try:
            year_int = int(year_str.strip())
            return True, year_int
        except ValueError:
            return False, None

    @staticmethod
    def _check_year_format_consistency(season: Season) -> str | None:
        """
        Check if the year field format is consistent with first_year and second_year.

        Args:
            season: Season object to check

        Returns:
            Error message if inconsistent, None if consistent
        """
        year = season.year.strip()
        first_year = season.first_year.strip()

        # Single year format (e.g., "2024")
        if not season.second_year:
            if year != first_year:
                return f"year '{year}' doesn't match first_year '{first_year}' (expected single year format)"
            return None

        # Two-year format (e.g., "2023-24" or "2023-2024")
        second_year = season.second_year.strip()

        # Check if year matches expected format
        # Expected formats: "2023-24", "2023-2024", "2023-25"
        expected_patterns = [
            f"{first_year}-{second_year}",  # Full format: 2023-2024
            f"{first_year}-{second_year[2:]}",  # Short format: 2023-24
        ]

        if year not in expected_patterns:
            # Check if it's close but has wrong second year
            if "-" in year:
                parts = year.split("-")
                if len(parts) == 2:
                    return f"year '{year}' format doesn't match first_year '{first_year}' and second_year '{second_year}'"
            return f"year '{year}' format doesn't match two-year format with first_year '{first_year}' and second_year '{second_year}'"

        return None

    @staticmethod
    def get_season_statistics() -> dict[str, Any]:
        """
        Get statistics about seasons in the database.

        Returns:
            Dictionary with statistics
        """
        total_seasons = Season.objects.count()
        seasons_with_second_year = Season.objects.exclude(second_year__isnull=True).exclude(second_year="").count()
        seasons_single_year = total_seasons - seasons_with_second_year

        # Get year range
        seasons_with_valid_first = Season.objects.filter(first_year__regex=r'^\d{4}$')
        if seasons_with_valid_first.exists():
            first_years = [int(s.first_year) for s in seasons_with_valid_first if s.first_year.isdigit()]
            if first_years:
                min_year = min(first_years)
                max_year = max(first_years)
            else:
                min_year = None
                max_year = None
        else:
            min_year = None
            max_year = None

        return {
            "total_seasons": total_seasons,
            "seasons_with_second_year": seasons_with_second_year,
            "seasons_single_year": seasons_single_year,
            "min_year": min_year,
            "max_year": max_year,
        }
