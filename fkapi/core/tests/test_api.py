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
            rating=4.5,
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

    def test_search_seasons_priority_ordering(self):
        """Test season search endpoint returns results in correct priority order."""
        # Clear cache to ensure fresh results
        from django.core.cache import cache

        cache.clear()

        # Create test seasons for priority testing (using get_or_create to avoid conflicts)
        season_exact, _ = Season.objects.get_or_create(
            year="2025", defaults={"first_year": "2025", "second_year": None}
        )
        season_starts_with, _ = Season.objects.get_or_create(
            year="2025-26", defaults={"first_year": "2025", "second_year": "2026"}
        )
        season_ends_with, _ = Season.objects.get_or_create(
            year="2024-25", defaults={"first_year": "2024", "second_year": "2025"}
        )
        season_contains, _ = Season.objects.get_or_create(
            year="2025-27", defaults={"first_year": "2025", "second_year": "2027"}
        )

        response = self.client.get("/api/seasons/search", {"keyword": "2025"})
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

        # Extract years from response
        years = [season["year"] for season in data]

        # Verify priority order: exact match first, then starts with, then ends with, then contains
        if "2025" in years:
            exact_index = years.index("2025")
            # Exact match should be first
            self.assertEqual(exact_index, 0, "Exact match '2025' should be first")

        if "2025-26" in years and "2024-25" in years:
            starts_index = years.index("2025-26")
            ends_index = years.index("2024-25")
            # "2025-26" (starts with) should come before "2024-25" (ends with)
            self.assertLess(
                starts_index,
                ends_index,
                "'2025-26' (first_year='2025') should come before '2024-25' (second_year='2025')",
            )

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

    def test_get_kits_bulk_success(self):
        """Test bulk kits endpoint with valid slugs."""
        # Create additional test kits
        kit2 = Kit.objects.create(
            slug="test-kit-2",
            name="Test Kit 2",
            team=self.club,
            season=self.season,
            type=self.type_k,
            brand=self.brand,
            main_img_url="https://example.com/kit2.jpg",
            rating=4.0,
        )

        response = self.client.get("/api/kits/bulk", {"slugs": f"{self.kit.slug},{kit2.slug}"})
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content}")
        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        # Verify structure
        kit_data = data[0]
        self.assertIn("name", kit_data)
        self.assertIn("team", kit_data)
        self.assertIn("season", kit_data)
        self.assertIn("brand", kit_data)
        self.assertIn("main_img_url", kit_data)

        # Verify team structure
        self.assertIn("name", kit_data["team"])
        self.assertIn("logo", kit_data["team"])
        self.assertIn("logo_dark", kit_data["team"])
        self.assertIn("country", kit_data["team"])

        # Verify season structure
        self.assertIn("year", kit_data["season"])

        # Verify brand structure
        self.assertIn("name", kit_data["brand"])
        self.assertIn("logo", kit_data["brand"])
        self.assertIn("logo_dark", kit_data["brand"])

    def test_get_kits_bulk_minimum_validation(self):
        """Test bulk kits endpoint rejects less than 2 kits."""
        response = self.client.get("/api/kits/bulk", {"slugs": self.kit.slug})
        # Django Ninja may return 400 or 422 for validation errors
        self.assertIn(response.status_code, [400, 422])
        data = response.json()
        self.assertIn("detail", data)

    def test_get_kits_bulk_maximum_validation(self):
        """Test bulk kits endpoint rejects more than 30 kits."""
        # Create 31 slugs
        slugs = ",".join([f"test-kit-{i}" for i in range(31)])
        response = self.client.get("/api/kits/bulk", {"slugs": slugs})
        # Django Ninja may return 400 or 422 for validation errors
        self.assertIn(response.status_code, [400, 422])
        data = response.json()
        self.assertIn("detail", data)

    def test_get_kits_bulk_with_urls(self):
        """Test bulk kits endpoint accepts full URLs."""
        kit2 = Kit.objects.create(
            slug="test-kit-2",
            name="Test Kit 2",
            team=self.club,
            season=self.season,
            type=self.type_k,
            brand=self.brand,
            main_img_url="https://example.com/kit2.jpg",
            rating=4.0,
        )

        # Test with full URLs
        url1 = f"https://www.footballkitarchive.com/{self.kit.slug}"
        url2 = f"https://www.footballkitarchive.com/{kit2.slug}/"
        response = self.client.get("/api/kits/bulk", {"slugs": f"{url1},{url2}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_get_kits_bulk_mixed_slugs_and_urls(self):
        """Test bulk kits endpoint accepts mix of slugs and URLs."""
        kit2 = Kit.objects.create(
            slug="test-kit-2",
            name="Test Kit 2",
            team=self.club,
            season=self.season,
            type=self.type_k,
            brand=self.brand,
            main_img_url="https://example.com/kit2.jpg",
            rating=4.0,
        )

        url1 = f"https://www.footballkitarchive.com/{self.kit.slug}"
        response = self.client.get("/api/kits/bulk", {"slugs": f"{url1},{kit2.slug}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_get_kits_bulk_preserves_order(self):
        """Test bulk kits endpoint preserves input order."""
        kit2 = Kit.objects.create(
            slug="test-kit-2",
            name="Test Kit 2",
            team=self.club,
            season=self.season,
            type=self.type_k,
            brand=self.brand,
            main_img_url="https://example.com/kit2.jpg",
            rating=3.5,
        )
        kit3 = Kit.objects.create(
            slug="test-kit-3",
            name="Test Kit 3",
            team=self.club,
            season=self.season,
            type=self.type_k,
            brand=self.brand,
            main_img_url="https://example.com/kit3.jpg",
            rating=3.5,
        )

        # Request in specific order
        slugs = f"{kit3.slug},{self.kit.slug},{kit2.slug}"
        response = self.client.get("/api/kits/bulk", {"slugs": slugs})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)

        # Verify order is preserved
        self.assertEqual(data[0]["name"], "Test Kit 3")
        self.assertEqual(data[1]["name"], "Test Kit")
        self.assertEqual(data[2]["name"], "Test Kit 2")

    def test_get_kits_bulk_handles_missing_kits(self):
        """Test bulk kits endpoint handles non-existent kits gracefully."""
        # Include one valid and one invalid slug
        response = self.client.get("/api/kits/bulk", {"slugs": f"{self.kit.slug},non-existent-kit"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should return only the valid kit
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Test Kit")

    def test_get_kits_bulk_maximum_allowed(self):
        """Test bulk kits endpoint accepts exactly 30 kits."""
        # Create additional kits (we already have self.kit)
        kits = []
        for i in range(2, 32):  # Create 30 more kits (total 31, but we'll use 30)
            kit = Kit.objects.create(
                slug=f"test-kit-{i}",
                name=f"Test Kit {i}",
                team=self.club,
                season=self.season,
                type=self.type_k,
                brand=self.brand,
                main_img_url=f"https://example.com/kit{i}.jpg",
                rating=3.5,
            )
            kits.append(kit)

        # Create slug list with exactly 30 kits (self.kit + 29 from kits)
        slugs = ",".join([self.kit.slug] + [kit.slug for kit in kits[:29]])
        response = self.client.get("/api/kits/bulk", {"slugs": slugs})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 30)
