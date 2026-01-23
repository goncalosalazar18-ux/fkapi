"""
Tests for Django models.
"""

from django.test import TestCase

from core.models import Brand, Club, Color, Competition, Kit, Season, Type_K


class TestSeasonModel(TestCase):
    """Test Season model."""

    def test_create_season(self):
        """Test creating a season model."""
        season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.assertEqual(season.year, "2024-25")
        self.assertEqual(season.first_year, "2024")
        self.assertEqual(season.second_year, "2025")

    def test_season_str(self):
        """Test season string representation."""
        season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.assertEqual(str(season), "2024-25")


class TestClubModel(TestCase):
    """Test Club model."""

    def test_create_club(self):
        """Test creating a club model."""
        club = Club.objects.create(name="Arsenal", slug="arsenal-kits")
        self.assertEqual(club.name, "Arsenal")
        self.assertEqual(club.slug, "arsenal-kits")

    def test_club_str(self):
        """Test club string representation."""
        club = Club.objects.create(name="Arsenal", slug="arsenal-kits")
        self.assertEqual(str(club), "Arsenal")


class TestBrandModel(TestCase):
    """Test Brand model."""

    def test_create_brand(self):
        """Test creating a brand model."""
        brand = Brand.objects.create(name="adidas", slug="adidas-kits")
        self.assertEqual(brand.name, "adidas")
        self.assertEqual(brand.slug, "adidas-kits")

    def test_brand_str(self):
        """Test brand string representation."""
        brand = Brand.objects.create(name="adidas", slug="adidas-kits")
        self.assertEqual(str(brand), "adidas")


class TestCompetitionModel(TestCase):
    """Test Competition model."""

    def test_create_competition(self):
        """Test creating a competition model."""
        comp = Competition.objects.create(name="Premier League", slug="premier-league-kits")
        self.assertEqual(comp.name, "Premier League")
        self.assertEqual(comp.slug, "premier-league-kits")

    def test_competition_str(self):
        """Test competition string representation."""
        comp = Competition.objects.create(name="Premier League", slug="premier-league-kits")
        self.assertEqual(str(comp), "Premier League")


class TestTypeKModel(TestCase):
    """Test Type_K model."""

    def test_create_type(self):
        """Test creating a kit type model."""
        kit_type = Type_K.objects.create(name="Home")
        self.assertEqual(kit_type.name, "Home")
        self.assertEqual(kit_type.category, "match")
        self.assertEqual(kit_type.category_order, 1)
        self.assertFalse(kit_type.is_goalkeeper)

    def test_type_str(self):
        """Test type string representation."""
        kit_type = Type_K.objects.create(name="Home")
        self.assertEqual(str(kit_type), "Home")

    def test_type_defaults(self):
        """Test Type_K default values."""
        kit_type = Type_K.objects.create(name="Test")
        self.assertEqual(kit_type.category, "match")
        self.assertEqual(kit_type.category_order, 1)
        self.assertEqual(kit_type.order_priority, 999)
        self.assertFalse(kit_type.is_goalkeeper)

    def test_type_goalkeeper(self):
        """Test Type_K goalkeeper detection."""
        gk_type = Type_K.objects.create(name="GK Home", is_goalkeeper=True)
        self.assertTrue(gk_type.is_goalkeeper)

        normal_type = Type_K.objects.create(name="Home", is_goalkeeper=False)
        self.assertFalse(normal_type.is_goalkeeper)

    def test_type_ordering(self):
        """Test Type_K ordering by category and priority."""
        # Create types in different categories
        match_home = Type_K.objects.create(name="Home", category="match", category_order=1, order_priority=1)
        match_away = Type_K.objects.create(name="Away", category="match", category_order=1, order_priority=2)
        prematch = Type_K.objects.create(name="Pre-match Home", category="prematch", category_order=2, order_priority=1)

        # Query should be ordered correctly
        types = list(Type_K.objects.all())
        self.assertEqual(types[0], match_home)
        self.assertEqual(types[1], match_away)
        self.assertEqual(types[2], prematch)


class TestColorModel(TestCase):
    """Test Color model."""

    def test_create_color(self):
        """Test creating a color model."""
        color = Color.objects.create(name="Red", color="#FF0000")
        self.assertEqual(color.name, "Red")
        self.assertEqual(color.color, "#FF0000")

    def test_color_str(self):
        """Test color string representation."""
        color = Color.objects.create(name="Red", color="#FF0000")
        self.assertEqual(str(color), "Red")


class TestKitModel(TestCase):
    """Test Kit model."""

    def test_create_complete_kit(self):
        """Test creating a complete kit with all relationships."""
        # Create all related objects
        season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        brand = Brand.objects.create(name="adidas", slug="adidas-kits")
        competition = Competition.objects.create(name="Premier League", slug="premier-league-kits")
        kit_type = Type_K.objects.create(name="Home")
        primary_color = Color.objects.create(name="Red", color="#FF0000")
        secondary_color = Color.objects.create(name="White", color="#FFFFFF")
        club = Club.objects.create(name="Arsenal", slug="arsenal-kits")

        # Create the kit
        kit = Kit.objects.create(
            name="Arsenal 2024-25 Home",
            slug="arsenal-2024-25-home-kit",
            team=club,
            season=season,
            type=kit_type,
            brand=brand,
            main_img_url="https://example.com/kit.jpg",
            rating=4.5,
            primary_color=primary_color,
            design="Striped",
        )

        # Add relationships
        kit.competition.add(competition)
        kit.secondary_color.add(secondary_color)

        # Verify the kit
        self.assertEqual(kit.name, "Arsenal 2024-25 Home")
        self.assertEqual(kit.team, club)
        self.assertEqual(kit.season, season)
        self.assertEqual(kit.type, kit_type)
        self.assertEqual(kit.brand, brand)
        self.assertEqual(kit.rating, 4.5)
        self.assertEqual(kit.primary_color, primary_color)
        self.assertEqual(kit.design, "Striped")

        # Verify relationships
        self.assertEqual(kit.competition.count(), 1)
        self.assertIn(competition, kit.competition.all())
        self.assertEqual(kit.secondary_color.count(), 1)
        self.assertIn(secondary_color, kit.secondary_color.all())

    def test_kit_str(self):
        """Test kit string representation."""
        season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        brand = Brand.objects.create(name="adidas", slug="adidas-kits")
        kit_type = Type_K.objects.create(name="Home")
        club = Club.objects.create(name="Arsenal", slug="arsenal-kits")

        kit = Kit.objects.create(
            name="Arsenal 2024-25 Home",
            slug="arsenal-2024-25-home-kit",
            team=club,
            season=season,
            type=kit_type,
            brand=brand,
            main_img_url="https://example.com/kit.jpg",
            rating=4.5,
        )

        self.assertEqual(str(kit), "Arsenal 2024-25 Home")
