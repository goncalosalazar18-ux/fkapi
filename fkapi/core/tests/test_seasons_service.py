from django.test import TestCase

from core.models import Season
from core.services.seasons_service import MAX_YEAR, MIN_YEAR, SeasonsService, get_max_season_span


class SeasonsServiceTests(TestCase):
    def test_get_max_season_span_threshold(self) -> None:
        """get_max_season_span should switch span at 1960."""
        self.assertEqual(get_max_season_span(1959), 20)
        self.assertEqual(get_max_season_span(1960), 2)
        self.assertEqual(get_max_season_span(2024), 2)

    def test_find_problematic_seasons_flags_all_issue_types(self) -> None:
        """find_problematic_seasons should classify seasons into all problem buckets."""
        # Invalid first year (non numeric)
        Season.objects.create(year="XXXX", first_year="XXXX", second_year=None)

        # First year out of range
        Season.objects.create(year="1700", first_year=str(MIN_YEAR - 10), second_year=None)

        # Invalid second year
        Season.objects.create(year="2024-XX", first_year="2024", second_year="XX24")

        # Second year out of range
        Season.objects.create(year="2500-01", first_year="2500", second_year=str(MAX_YEAR + 1))

        # Second year before first year
        Season.objects.create(year="2024-23", first_year="2024", second_year="2023")

        # Excessive span (modern season, span > 2)
        Season.objects.create(year="2000-05", first_year="2000", second_year="2005")

        # Excessive span (old season, span > 20)
        Season.objects.create(year="1930-60", first_year="1930", second_year="1960")

        # Year format mismatch (single-year season)
        Season.objects.create(year="2024", first_year="2023", second_year=None)

        # Year format mismatch (two-year season)
        Season.objects.create(year="2023-2026", first_year="2023", second_year="2024")

        problems = SeasonsService.find_problematic_seasons()

        self.assertGreaterEqual(len(problems["invalid_first_year"]), 1)
        self.assertGreaterEqual(len(problems["invalid_second_year"]), 1)
        self.assertGreaterEqual(len(problems["second_year_before_first"]), 1)
        self.assertGreaterEqual(len(problems["excessive_year_span"]), 2)
        self.assertGreaterEqual(len(problems["year_format_mismatch"]), 2)
        self.assertGreaterEqual(len(problems["out_of_range"]), 2)

    def test_validate_year_helper(self) -> None:
        """_validate_year should accept 4‑digit years and reject others."""
        valid, year_int = SeasonsService._validate_year("2024")
        self.assertTrue(valid)
        self.assertEqual(year_int, 2024)

        valid, year_int = SeasonsService._validate_year("  1999 ")
        self.assertTrue(valid)
        self.assertEqual(year_int, 1999)

        for value in ("", "   ", "20A4", "123", "abcd"):
            valid, year_int = SeasonsService._validate_year(value)
            self.assertFalse(valid)
            self.assertIsNone(year_int)

    def test_check_year_format_consistency_helper(self) -> None:
        """_check_year_format_consistency should validate year against first/second year."""
        # Single‑year season
        s1 = Season(year="2024", first_year="2024", second_year=None)
        self.assertIsNone(SeasonsService._check_year_format_consistency(s1))

        s2 = Season(year="2025", first_year="2024", second_year=None)
        self.assertIsNotNone(SeasonsService._check_year_format_consistency(s2))

        # Two‑year formats
        s3 = Season(year="2023-2024", first_year="2023", second_year="2024")
        s4 = Season(year="2023-24", first_year="2023", second_year="2024")
        self.assertIsNone(SeasonsService._check_year_format_consistency(s3))
        self.assertIsNone(SeasonsService._check_year_format_consistency(s4))

        s5 = Season(year="2023-25", first_year="2023", second_year="2024")
        self.assertIsNotNone(SeasonsService._check_year_format_consistency(s5))

    def test_get_season_statistics(self) -> None:
        """get_season_statistics should return sensible aggregates."""
        # Single‑year season
        Season.objects.create(year="2024", first_year="2024", second_year=None)
        # Two‑year seasons
        Season.objects.create(year="2023-24", first_year="2023", second_year="2024")
        Season.objects.create(year="2025-26", first_year="2025", second_year="2026")

        stats = SeasonsService.get_season_statistics()

        self.assertEqual(stats["total_seasons"], 3)
        self.assertEqual(stats["seasons_single_year"], 1)
        self.assertEqual(stats["seasons_with_second_year"], 2)
        self.assertEqual(stats["min_year"], 2023)
        self.assertEqual(stats["max_year"], 2025)

