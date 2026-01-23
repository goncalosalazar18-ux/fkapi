"""Tests for Type_K auto-categorization in scrapers."""

from unittest.mock import Mock, patch

from django.test import TestCase

from core.models import Brand, Club, Season, Type_K
from core.scrapers import _process_kit


class ScrapersTypeKTests(TestCase):
    """Test Type_K auto-categorization in scrapers."""

    def setUp(self):
        """Set up test data."""
        self.season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.club = Club.objects.create(slug="test-club", name="Test Club")
        self.brand = Brand.objects.create(slug="test-brand", name="Test Brand")

    @patch("core.scrapers.scrape_kit_lite")
    def test_new_type_k_auto_categorized_in_process_kit(self, mock_scrape_kit):
        """Test that new Type_K is automatically categorized in _process_kit."""
        mock_scrape_kit.return_value = Mock()

        # Create mock BeautifulSoup element
        from bs4 import BeautifulSoup

        html = """
        <div>
            <a href="/test-kit-slug/123/"></a>
            <div class="kit-season">2024-25 Training Home</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        kit_element = soup.find("div")

        # Process kit
        _process_kit(kit_element, self.club, self.season, self.brand)

        # Verify Type_K was created and categorized
        type_k = Type_K.objects.get(name="Training Home")
        self.assertEqual(type_k.category, "training")
        self.assertEqual(type_k.category_order, 4)
        self.assertFalse(type_k.is_goalkeeper)
        self.assertEqual(type_k.order_priority, 1)

    @patch("core.scrapers.scrape_kit_lite")
    def test_existing_type_k_not_recategorized_in_process_kit(self, mock_scrape_kit):
        """Test that existing Type_K is not recategorized in _process_kit."""
        mock_scrape_kit.return_value = Mock()

        # Create existing Type_K with custom category
        existing_type = Type_K.objects.create(
            name="Custom Type", category="match", category_order=1, order_priority=999, is_goalkeeper=False
        )

        # Create mock BeautifulSoup element
        from bs4 import BeautifulSoup

        html = """
        <div>
            <a href="/test-kit-slug/123/"></a>
            <div class="kit-season">2024-25 Custom Type</div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        kit_element = soup.find("div")

        # Process kit
        _process_kit(kit_element, self.club, self.season, self.brand)

        # Verify Type_K was not recategorized
        existing_type.refresh_from_db()
        self.assertEqual(existing_type.category, "match")
        self.assertEqual(existing_type.category_order, 1)
        self.assertEqual(existing_type.order_priority, 999)
