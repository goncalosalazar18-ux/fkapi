"""Tests for Type_K auto-categorization in scraping service."""

from unittest.mock import Mock, patch

from django.test import TestCase

from core.models import Brand, Club, Season, Type_K
from core.parsers import KitPageData
from core.services.scraping_service import ScrapingService


class ScrapingServiceTypeKTests(TestCase):
    """Test Type_K auto-categorization in scraping service."""

    def setUp(self):
        """Set up test data."""
        self.season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.club = Club.objects.create(slug="test-club", name="Test Club")
        self.brand = Brand.objects.create(slug="test-brand", name="Test Brand")

    @patch('core.services.scraping_service.ClubsService.handle_club_changes')
    @patch('core.scrapers._get_or_create_brand')
    @patch('core.scrapers.get_season')
    @patch('core.services.scraping_service.KitsService.create_or_update_kit')
    def test_new_type_k_auto_categorized(self, mock_create_kit, mock_get_season, mock_brand, mock_club):
        """Test that new Type_K is automatically categorized when created during scraping."""
        mock_club.return_value = self.club
        mock_brand.return_value = self.brand
        mock_get_season.return_value = self.season
        mock_create_kit.return_value = (Mock(), True)

        # Create KitPageData with a new type name
        data = KitPageData(
            team_name="Test Club",
            team_slug="test-club",
            kit_type="Training Home",  # New type that should be categorized
            brand_slug="test-brand",
            brand_name="Test Brand",
            season_text="2024-25",
            rating=8.5,
            main_img_url="https://example.com/kit.jpg",
            design="Plain",
            colors_str="Blue / White",
            competitions_html="Premier League",
        )

        # Process kit data
        ScrapingService.process_kit_data(data, "test-kit-slug", None, use_proxy=False)

        # Verify Type_K was created and categorized
        type_k = Type_K.objects.get(name="Training Home")
        self.assertEqual(type_k.category, "training")
        self.assertEqual(type_k.category_order, 4)
        self.assertFalse(type_k.is_goalkeeper)
        self.assertEqual(type_k.order_priority, 1)  # Home has priority 1

    @patch('core.services.scraping_service.ClubsService.handle_club_changes')
    @patch('core.scrapers._get_or_create_brand')
    @patch('core.scrapers.get_season')
    @patch('core.services.scraping_service.KitsService.create_or_update_kit')
    def test_existing_type_k_not_recategorized(self, mock_create_kit, mock_get_season, mock_brand, mock_club):
        """Test that existing Type_K is not recategorized."""
        mock_club.return_value = self.club
        mock_brand.return_value = self.brand
        mock_get_season.return_value = self.season
        mock_create_kit.return_value = (Mock(), True)

        # Create existing Type_K with custom category
        existing_type = Type_K.objects.create(
            name="Custom Type",
            category="match",
            category_order=1,
            order_priority=999,
            is_goalkeeper=False
        )

        # Create KitPageData with existing type name
        data = KitPageData(
            team_name="Test Club",
            team_slug="test-club",
            kit_type="Custom Type",
            brand_slug="test-brand",
            brand_name="Test Brand",
            season_text="2024-25",
            rating=8.5,
            main_img_url="https://example.com/kit.jpg",
            design="Plain",
            colors_str="Blue / White",
            competitions_html="Premier League",
        )

        # Process kit data
        ScrapingService.process_kit_data(data, "test-kit-slug", None, use_proxy=False)

        # Verify Type_K was not recategorized
        existing_type.refresh_from_db()
        self.assertEqual(existing_type.category, "match")
        self.assertEqual(existing_type.category_order, 1)
        self.assertEqual(existing_type.order_priority, 999)

    @patch('core.services.scraping_service.ClubsService.handle_club_changes')
    @patch('core.scrapers._get_or_create_brand')
    @patch('core.scrapers.get_season')
    @patch('core.services.scraping_service.KitsService.create_or_update_kit')
    def test_gk_type_k_categorized(self, mock_create_kit, mock_get_season, mock_brand, mock_club):
        """Test that GK types are correctly identified and categorized."""
        mock_club.return_value = self.club
        mock_brand.return_value = self.brand
        mock_get_season.return_value = self.season
        mock_create_kit.return_value = (Mock(), True)

        data = KitPageData(
            team_name="Test Club",
            team_slug="test-club",
            kit_type="GK Home",
            brand_slug="test-brand",
            brand_name="Test Brand",
            season_text="2024-25",
            rating=8.5,
            main_img_url="https://example.com/kit.jpg",
            design="Plain",
            colors_str="Blue / White",
            competitions_html="Premier League",
        )

        ScrapingService.process_kit_data(data, "test-kit-slug", None, use_proxy=False)

        type_k = Type_K.objects.get(name="GK Home")
        self.assertEqual(type_k.category, "match")
        self.assertTrue(type_k.is_goalkeeper)
        self.assertEqual(type_k.order_priority, 1)
