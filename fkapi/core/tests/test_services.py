"""
Tests for service layer.
"""

from django.test import TestCase

from core.models import Brand, Club, Kit, Season, Type_K
from core.services.clubs_service import ClubsService
from core.services.kits_service import KitsService


class TestKitsService(TestCase):
    """Test KitsService functionality."""

    def setUp(self):
        """Set up test data."""
        self.season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.club = Club.objects.create(slug="test-club", name="Test Club")
        self.brand = Brand.objects.create(slug="test-brand", name="Test Brand")
        self.type_k = Type_K.objects.create(name="Home")
        self.kit = Kit.objects.create(
            slug="test-kit",
            name="Test Kit",
            team=self.club,
            season=self.season,
            type=self.type_k,
            brand=self.brand,
            main_img_url="https://example.com/kit.jpg",
            rating=8.5,
        )

    def test_process_competitions_html(self):
        """Test processing competitions from HTML."""
        competitions_html = '<a href="/premier-league-kits/">Premier League</a>'
        KitsService.process_competitions(self.kit, competitions_html, "test-kit")

        self.assertEqual(self.kit.competition.count(), 1)
        competition = self.kit.competition.first()
        self.assertEqual(competition.name, "Premier League")
        self.assertEqual(competition.slug, "premier-league-kits")

    def test_process_competitions_plain_text(self):
        """Test processing competitions from plain text."""
        competitions_html = "Premier League"
        KitsService.process_competitions(self.kit, competitions_html, "test-kit")

        self.assertEqual(self.kit.competition.count(), 1)
        competition = self.kit.competition.first()
        self.assertEqual(competition.name, "Premier League")

    def test_process_competitions_multiple(self):
        """Test processing multiple competitions."""
        competitions_html = "Premier League·Champions League"
        KitsService.process_competitions(self.kit, competitions_html, "test-kit")

        self.assertEqual(self.kit.competition.count(), 2)
        competition_names = [c.name for c in self.kit.competition.all()]
        self.assertIn("Premier League", competition_names)
        self.assertIn("Champions League", competition_names)

    def test_process_colors(self):
        """Test processing colors with various scenarios."""
        from core.models import Color

        # Create test colors
        white = Color.objects.create(name="White", color="#FFFFFF")
        blue = Color.objects.create(name="Blue", color="#0000FF")
        red = Color.objects.create(name="Red", color="#FF0000")
        green = Color.objects.create(name="Green", color="#008000")

        # Test single color
        KitsService.process_colors(self.kit, "Blue")
        self.kit.refresh_from_db()
        self.assertEqual(self.kit.primary_color, blue)
        self.assertEqual(self.kit.secondary_color.count(), 0)

        # Test with one secondary color
        KitsService.process_colors(self.kit, "Red / White")
        self.kit.refresh_from_db()
        self.assertEqual(self.kit.primary_color, red)
        self.assertIn(white, self.kit.secondary_color.all())

        # Test with two secondary colors
        KitsService.process_colors(self.kit, "White / Blue / Red")
        self.kit.refresh_from_db()
        self.assertEqual(self.kit.primary_color, white)
        self.assertIn(blue, self.kit.secondary_color.all())
        self.assertIn(red, self.kit.secondary_color.all())

        # Test with three secondary colors
        KitsService.process_colors(self.kit, "Green / Blue / Red / White")
        self.kit.refresh_from_db()
        self.assertEqual(self.kit.primary_color, green)
        self.assertIn(blue, self.kit.secondary_color.all())
        self.assertIn(red, self.kit.secondary_color.all())
        self.assertIn(white, self.kit.secondary_color.all())
        self.assertEqual(self.kit.secondary_color.count(), 3)

    def test_create_or_update_kit_new(self):
        """Test creating a new kit."""
        new_season = Season.objects.create(year="2023-24", first_year="2023", second_year="2024")
        kit, created = KitsService.create_or_update_kit(
            slug="new-kit",
            kit_name="New Kit",
            team=self.club,
            season=new_season,
            type_k=self.type_k,
            brand=self.brand,
            rating=9.0,
            main_img_url="https://example.com/new-kit.jpg",
        )

        self.assertTrue(created)
        self.assertEqual(kit.name, "New Kit")
        self.assertEqual(kit.slug, "new-kit")

    def test_create_or_update_kit_existing(self):
        """Test updating an existing kit."""
        # Use the kit from setUp which has team, season, type already set
        kit, created = KitsService.create_or_update_kit(
            slug="test-kit-updated",
            kit_name="Updated Kit",
            team=self.club,
            season=self.season,
            type_k=self.type_k,
            brand=self.brand,
            rating=8.0,
            main_img_url="https://example.com/updated.jpg",
            design="Striped",
        )

        self.assertFalse(created)
        self.assertEqual(kit.id, self.kit.id)
        self.kit.refresh_from_db()
        self.assertEqual(self.kit.design, "Striped")


class TestClubsService(TestCase):
    """Test ClubsService functionality."""

    def setUp(self):
        """Set up test data."""
        self.club = Club.objects.create(slug="test-club", name="Test Club")

    def test_handle_club_changes_existing_by_slug(self):
        """Test handling club changes when club exists by slug."""
        club = ClubsService.handle_club_changes("test-club", "Test Club")

        self.assertEqual(club.id, self.club.id)
        self.assertEqual(club.name, "Test Club")

    def test_handle_club_changes_name_update(self):
        """Test updating club name when slug matches."""
        club = ClubsService.handle_club_changes("test-club", "Updated Club Name")

        self.assertEqual(club.id, self.club.id)
        self.assertEqual(club.name, "Updated Club Name")

    def test_handle_club_changes_existing_by_name(self):
        """Test handling club changes when club exists by name but different slug."""
        club = ClubsService.handle_club_changes("new-slug", "Test Club")

        self.assertEqual(club.id, self.club.id)
        self.assertEqual(club.slug, "new-slug")
        self.assertEqual(club.name, "Test Club")
