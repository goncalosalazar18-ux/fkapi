"""Tests for API endpoints."""

from django.test import Client, TestCase

from core.models import Brand, Club, Competition, Kit, Season, Type_K


class APITests(TestCase):
    """Test cases for API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create test season
        self.season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")

        # Create test club
        self.club = Club.objects.create(slug="test-club", name="Test Club", logo="https://example.com/logo.png")

        # Create test brand
        self.brand = Brand.objects.create(slug="test-brand", name="Test Brand", logo="https://example.com/brand.png")

        # Create test competition
        self.competition = Competition.objects.create(slug="test-competition", name="Test Competition")

        # Create test type
        self.type_k = Type_K.objects.create(name="Home")

        # Create test kit
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
        self.kit.competition.add(self.competition)

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn(data["status"], ["healthy", "unhealthy"])

    def test_search_clubs(self):
        """Test club search endpoint."""
        response = self.client.get("/api/clubs/search", {"keyword": "test"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        if data:
            self.assertIn("id", data[0])
            self.assertIn("name", data[0])

    def test_search_brands(self):
        """Test brand search endpoint."""
        response = self.client.get("/api/brands/search", {"keyword": "test"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_search_competitions(self):
        """Test competition search endpoint."""
        response = self.client.get("/api/competitions/search", {"keyword": "test"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_search_seasons(self):
        """Test season search endpoint."""
        response = self.client.get("/api/seasons/search", {"keyword": "2024"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_get_kit_json(self):
        """Test get kit details endpoint."""
        response = self.client.get(f"/api/kits/{self.kit.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("name", data)
        self.assertIn("team", data)
        self.assertIn("season", data)
        self.assertIn("type", data)

        # Verify Type_K fields are included
        type_data = data["type"]
        self.assertIn("id", type_data)
        self.assertIn("name", type_data)
        self.assertIn("category", type_data)
        self.assertIn("category_order", type_data)
        self.assertIn("order_priority", type_data)
        self.assertIn("is_goalkeeper", type_data)

        # Verify values match the model (refresh to get latest values)
        self.type_k.refresh_from_db()
        # Verify all required fields are present and match model
        self.assertIsInstance(type_data["id"], int)
        self.assertEqual(type_data["name"], self.type_k.name)
        self.assertEqual(type_data["category"], self.type_k.category)
        self.assertEqual(type_data["category_order"], self.type_k.category_order)
        self.assertEqual(type_data["order_priority"], self.type_k.order_priority)
        self.assertEqual(type_data["is_goalkeeper"], self.type_k.is_goalkeeper)

    def test_get_random_kits(self):
        """Test random kits endpoint with pagination."""
        response = self.client.get("/api/random-kits/", {"page": 1, "page_size": 20})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("kits", data)
        self.assertIn("pagination", data)
        self.assertIn("current_page", data["pagination"])

    def test_get_random_clubs(self):
        """Test random clubs endpoint with pagination."""
        response = self.client.get("/api/random-clubs/", {"page": 1, "page_size": 20})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("clubs", data)
        self.assertIn("pagination", data)

    def test_search_kits(self):
        """Test kit search endpoint."""
        response = self.client.get("/api/kits/search", {"keyword": "test"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
