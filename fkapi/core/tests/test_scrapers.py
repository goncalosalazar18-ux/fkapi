from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup
from django.db import transaction
from django.test import TestCase

from core.models import Brand, Club, Color, Competition, Kit, Season, Type_K
from core.scrapers import (
    _get_or_create_brand,
    _process_kit,
    get_current_season,
    get_season,
    get_season_e,
    scrape_brand,
    scrape_club_details,
    scrape_competition,
    scrape_kit,
    scrape_kit_lite,
    scrape_lastest,
    scrape_latest_pages,
    scrape_whole_club,
)

# Create your tests here.

class ScraperTests(TestCase):
    """Test cases for scraping functions."""

    def setUp(self):
        """Set up test data."""
        # Create base season
        self.current_season = Season.objects.create(
            year="2024-25",
            first_year="2024",
            second_year="2025"
        )

        # Create test clubs
        self.club = Club.objects.create(
            slug="fc-copenhagen-kits",
            name="FC Copenhagen"
        )

        # Create test brand
        self.brand, _ = Brand.objects.get_or_create(
            slug="adidas-kits",
            defaults={'name': "adidas"}
        )

        # Create test competitions
        self.competition = Competition.objects.create(
            slug="superliga-kits",
            name="Superliga"
        )

        # Create test type
        self.type_k, _ = Type_K.objects.get_or_create(
            name="Third"
        )

    @patch('core.scrapers.http_get')
    def test_scrape_kit(self, mock_http_get):
        """Test scrape_kit function with real season formats from the website."""
        test_cases = [
            {
                "slug": "fc-copenhagen-2024-25-third-1-kit",
                "html_season": "2024-25",
                "expected": {
                    "year": "2024-25",
                    "first_year": "2024",
                    "second_year": "2025"
                }
            },
            {
                "slug": "manchester-united-2024-home-kit",
                "html_season": "2024",
                "expected": {
                    "year": "2024",
                    "first_year": "2024",
                    "second_year": None
                }
            }
        ]

        for case in test_cases:
            with self.subTest(season=case["html_season"]):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = f"""
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/12/28/WoFwCr2Yv42ZmE6.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/12/28/WoFwCr2Yv42ZmE6.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr>
                                        <td>Team</td>
                                        <td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td>
                                    </tr>
                                    <tr>
                                        <td>Season</td>
                                        <td>{case["html_season"]}</td>
                                    </tr>
                                    <tr>
                                        <td>Type</td>
                                        <td>Third</td>
                                    </tr>
                                    <tr>
                                        <td>Design</td>
                                        <td>Striped</td>
                                    </tr>
                                    <tr>
                                        <td>Colors</td>
                                        <td>Blue / White</td>
                                    </tr>
                                    <tr>
                                        <td>Brand</td>
                                        <td><a href="/adidas-kits/">adidas</a></td>
                                    </tr>
                                    <tr>
                                        <td>League</td>
                                        <td>
                                            <a href="/danish-superliga-kits/">Danish Superliga</a>
                                            ·
                                            <a href="/conference-league-kits/">Conference League</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>Rating</td>
                                        <td>
                                            <div class="rating-container">
                                                <div class="rating-details">
                                                    <span id="rating">4.42</span>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """
                mock_http_get.return_value = mock_response

                Club.objects.get_or_create(
                    slug="fc-copenhagen-kits",
                    defaults={'name': "FC Copenhagen"}
                )
                Color.objects.get_or_create(name="Blue", defaults={'color': "#0000FF"})
                Color.objects.get_or_create(name="White", defaults={'color': "#FFFFFF"})

                kit = scrape_kit(case["slug"])

                self.assertIsNotNone(kit)
                self.assertEqual(kit.season.year, case["expected"]["year"])
                self.assertEqual(kit.season.first_year, case["expected"]["first_year"])
                self.assertEqual(kit.season.second_year, case["expected"]["second_year"])
                self.assertEqual(kit.design, "Striped")
                self.assertEqual(kit.primary_color.name, "Blue")
                self.assertEqual(kit.secondary_color.first().name, "White")

    @patch('core.scrapers.http_get')
    def test_scrape_kit_errors(self, mock_http_get):
        """Test scrape_kit error handling."""
        test_cases = [
            {
                "name": "404 error",
                "status_code": 404,
                "html": """
                    <div class="main-header">
                        <h1><span class="main-title">404 Not Found</span></h1>
                    </div>
                    <div class="content-c">
                        The requested page could not be found.
                    </div>
                """,
                "expected": None
            },
            {
                "name": "No rating",
                "status_code": 200,
                "html": """
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/12/28/test.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/12/28/test.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr>
                                        <td>Team</td>
                                        <td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td>
                                    </tr>
                                    <tr>
                                        <td>Season</td>
                                        <td>2024-25</td>
                                    </tr>
                                    <tr>
                                        <td>Type</td>
                                        <td>Third</td>
                                    </tr>
                                    <tr>
                                        <td>Brand</td>
                                        <td><a href="/adidas-kits/">adidas</a></td>
                                    </tr>
                                    <tr>
                                        <td>League</td>
                                        <td><a href="/superliga-kits/">Superliga</a></td>
                                    </tr>
                                    <tr>
                                        <td>Rating</td>
                                        <td>
                                            <div class="rating-container">
                                                <div class="rating-details">
                                                    <span id="rating"></span>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """,
                "expected": 0.0  # Should default to 0 when no rating
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_http_get.return_value = mock_response

                # Ensure we have the test club in the database
                Club.objects.get_or_create(
                    slug="fc-copenhagen-kits",
                    defaults={'name': "FC Copenhagen"}
                )

                kit = scrape_kit("test-kit")
                if case["expected"] is None:
                    self.assertIsNone(kit)
                else:
                    self.assertIsNotNone(kit)
                    self.assertEqual(kit.rating, case["expected"])

    @patch('core.scrapers.http_get')
    def test_scrape_kit_season_formats(self, mock_http_get):
        """Test scraping different season formats."""
        test_cases = [
            {
                "name": "Single year season",
                "html": """
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/12/28/test.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/12/28/test.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr>
                                        <td>Team</td>
                                        <td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td>
                                    </tr>
                                    <tr>
                                        <td>Season</td>
                                        <td>2025</td>
                                    </tr>
                                    <tr>
                                        <td>Type</td>
                                        <td>Third</td>
                                    </tr>
                                    <tr>
                                        <td>Brand</td>
                                        <td><a href="/adidas-kits/">adidas</a></td>
                                    </tr>
                                    <tr>
                                        <td>League</td>
                                        <td><a href="/superliga-kits/">Superliga</a></td>
                                    </tr>
                                    <tr>
                                        <td>Rating</td>
                                        <td>
                                            <div class="rating-container">
                                                <div class="rating-details">
                                                    <span id="rating">4.5</span>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """,
                "expected": "2025"
            },
            {
                "name": "Two year season",
                "html": """
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/12/28/test.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/12/28/test.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr>
                                        <td>Team</td>
                                        <td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td>
                                    </tr>
                                    <tr>
                                        <td>Season</td>
                                        <td>2024-25</td>
                                    </tr>
                                    <tr>
                                        <td>Type</td>
                                        <td>Third</td>
                                    </tr>
                                    <tr>
                                        <td>Brand</td>
                                        <td><a href="/adidas-kits/">adidas</a></td>
                                    </tr>
                                    <tr>
                                        <td>League</td>
                                        <td><a href="/superliga-kits/">Superliga</a></td>
                                    </tr>
                                    <tr>
                                        <td>Rating</td>
                                        <td>
                                            <div class="rating-container">
                                                <div class="rating-details">
                                                    <span id="rating">4.5</span>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """,
                "expected": "2024-25"
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = case["html"]
                mock_http_get.return_value = mock_response

                Club.objects.get_or_create(
                    slug="fc-copenhagen-kits",
                    defaults={'name': "FC Copenhagen"}
                )

                kit = scrape_kit("test-kit")
                self.assertIsNotNone(kit, f"Kit should not be None for case {case['name']}")
                self.assertEqual(kit.season.year, case["expected"], f"Season year mismatch for case {case['name']}")

    @patch('core.scrapers.http_get')
    def test_scrape_kit_competitions(self, mock_http_get):
        """Test scraping competitions."""
        test_cases = [
            {
                "name": "Single competition",
                "html": """
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/12/28/test.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/12/28/test.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr><td>Team</td><td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td></tr>
                                    <tr><td>Season</td><td>2024-25</td></tr>
                                    <tr><td>Type</td><td>Third</td></tr>
                                    <tr><td>Brand</td><td><a href="/adidas-kits/">adidas</a></td></tr>
                                    <tr><td>League</td><td><a href="/superliga-kits/">Superliga</a></td></tr>
                                    <tr><td>Rating</td><td>
                                        <div class="rating-container">
                                            <div class="rating-details">
                                                <span id="rating">4.42</span>
                                            </div>
                                        </div>
                                    </td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """,
                "expected": ["Superliga"]
            },
            {
                "name": "Multiple competitions",
                "html": """
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/12/28/test.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/12/28/test.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr><td>Team</td><td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td></tr>
                                    <tr><td>Season</td><td>2024-25</td></tr>
                                    <tr><td>Type</td><td>Third</td></tr>
                                    <tr><td>Brand</td><td><a href="/adidas-kits/">adidas</a></td></tr>
                                    <tr><td>League</td><td>
                                        <a href="/superliga-kits/">Superliga</a> ·
                                        <a href="/champions-league-kits/">Champions League</a>
                                    </td></tr>
                                    <tr><td>Rating</td><td>
                                        <div class="rating-container">
                                            <div class="rating-details">
                                                <span id="rating">4.42</span>
                                            </div>
                                        </div>
                                    </td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """,
                "expected": ["Superliga", "Champions League"]
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = case["html"]
                mock_http_get.return_value = mock_response

                Club.objects.get_or_create(
                    slug="fc-copenhagen-kits",
                    defaults={'name': "FC Copenhagen"}
                )

                kit = scrape_kit("test-kit")
                self.assertIsNotNone(kit)
                competition_names = [comp.name for comp in kit.competition.all()]
                self.assertEqual(sorted(competition_names), sorted(case["expected"]))

    def test_get_current_season(self):
        """Test get_current_season function."""
        # Test successful retrieval
        season = get_current_season()
        self.assertEqual(season.year, "2024-25")
        self.assertEqual(season.first_year, "2024")
        self.assertEqual(season.second_year, "2025")

        # Test season not found
        with transaction.atomic():
            Season.objects.all().delete()
            with self.assertRaises(Season.DoesNotExist):
                get_current_season()

    def test_get_season(self):
        """Test get_season function with different formats."""
        test_cases = [
            ("2024", {
                "year": "2024",
                "first_year": "2024",
                "second_year": None
            }),
            ("2023-24", {
                "year": "2023-24",
                "first_year": "2023",
                "second_year": "2024"
            }),
            ("1999-00", {
                "year": "1999-00",
                "first_year": "1999",
                "second_year": "2000"
            }),
            ("1934-35", {
                "year": "1934-35",
                "first_year": "1934",
                "second_year": "1935"
            })
        ]

        for input_year, expected in test_cases:
            with self.subTest(input_year=input_year):
                season = get_season(input_year)
                self.assertEqual(season.year, expected["year"])
                self.assertEqual(season.first_year, expected["first_year"])
                self.assertEqual(season.second_year, expected["second_year"])

    def test_get_season_e(self):
        """Test get_season_e function with different formats."""
        test_cases = [
            ("2024", {
                "year": "2024",
                "first_year": "2024",
                "second_year": None
            }),
            ("2023-2024", {
                "year": "2023-2024",
                "first_year": "2023",
                "second_year": "2024"
            }),
            ("1999-00", {
                "year": "1999-00",
                "first_year": "1999",
                "second_year": "2000"
            }),
            ("1934-35", {
                "year": "1934-35",
                "first_year": "1934",
                "second_year": "1935"
            })
        ]

        for input_year, expected in test_cases:
            with self.subTest(input_year=input_year):
                season = get_season_e(input_year)
                self.assertEqual(season.year, expected["year"])
                self.assertEqual(season.first_year, expected["first_year"])
                self.assertEqual(season.second_year, expected["second_year"])

    @patch('core.scrapers.http_get')
    def test_scrape_competition(self, mock_http_get):
        """Test scraping competition details."""
        test_cases = [
            {
                "name": "Successful scrape",
                "status_code": 200,
                "html": """
                    <div class="main-header">
                        <span class="main-title">Premier League</span>
                    </div>
                """,
                "slug": "premier-league-kits",
                "expected": {
                    "name": "Premier League",
                    "slug": "premier-league-kits"
                }
            },
            {
                "name": "404 error",
                "status_code": 404,
                "html": "<html></html>",
                "slug": "nonexistent-league-kits",
                "expected": None
            },
            {
                "name": "403 error",
                "status_code": 403,
                "html": "<html></html>",
                "slug": "blocked-league-kits",
                "expected": None
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_response.raise_for_status = Mock()
                if case["status_code"] >= 400:
                    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
                mock_http_get.return_value = mock_response

                competition = scrape_competition(case["slug"])

                if case["expected"] is None:
                    self.assertIsNone(competition)
                else:
                    self.assertIsNotNone(competition)
                    self.assertEqual(competition.name, case["expected"]["name"])
                    self.assertEqual(competition.slug, case["expected"]["slug"])

    @patch('core.scrapers.http_get')
    def test_scrape_brand(self, mock_http_get):
        """Test scraping brand details."""
        test_cases = [
            {
                "name": "Successful scrape",
                "status_code": 200,
                "html": """
                    <div class="main-header">
                        <span class="main-title">Nike Football Kit History</span>
                        <img data-src="logos/nike.png"/>
                    </div>
                """,
                "slug": "nike-kits",
                "expected": {
                    "name": "Nike",
                    "slug": "nike-kits",
                    "has_logo": True
                }
            },
            {
                "name": "No logo",
                "status_code": 200,
                "html": """
                    <div class="main-header">
                        <span class="main-title">Adidas Football Kit History</span>
                    </div>
                """,
                "slug": "adidas-kits",
                "expected": {
                    "name": "Adidas",
                    "slug": "adidas-kits",
                    "has_logo": False
                }
            },
            {
                "name": "404 error",
                "status_code": 404,
                "html": "<html></html>",
                "slug": "nonexistent-brand-kits",
                "expected": None
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                Brand.objects.filter(slug=case["slug"]).delete()

                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_response.raise_for_status = Mock()
                if case["status_code"] >= 400:
                    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
                mock_http_get.return_value = mock_response

                brand = scrape_brand(case["slug"])

                if case["expected"] is None:
                    self.assertIsNone(brand)
                else:
                    self.assertIsNotNone(brand)
                    self.assertEqual(brand.name.lower(), case["expected"]["name"].lower())
                    self.assertEqual(brand.slug.lower(), case["expected"]["slug"].lower())
                    if case["expected"]["has_logo"]:
                        self.assertTrue(brand.logo.endswith("nike.png"))
                    else:
                        self.assertTrue(brand.logo.endswith("not_found.png"))

    @patch('core.scrapers._process_kit')
    @patch('core.scrapers.http_get')
    def test_scrape_whole_club(self, mock_http_get, mock_process_kit):
        """Test scraping all kits for a club."""
        test_cases = [
            {
                "name": "Successful scrape",
                "status_code": 200,
                "html": """
                    <div class="archive-content-container">
                        <div class="collection-container">
                            <h3>2024-25</h3>
                            <ul class="section-details">
                                <li><a href="/adidas-kits/">adidas</a></li>
                            </ul>
                            <div class="kit">
                                <a href="/fc-copenhagen-2024-25-home-kit/">
                                    <img src="kit1.jpg"/>
                                </a>
                                <div class="kit-season">Home</div>
                            </div>
                            <div class="kit">
                                <a href="/fc-copenhagen-2024-25-away-kit/">
                                    <img src="kit2.jpg"/>
                                </a>
                                <div class="kit-season">Away</div>
                            </div>
                        </div>
                    </div>
                """,
                "expected": {
                    "seasons": 1,
                    "kits": 2
                }
            },
            {
                "name": "No kits found",
                "status_code": 200,
                "html": """
                    <div class="archive-content-container">
                    </div>
                """,
                "expected": {
                    "seasons": 0,
                    "kits": 0
                }
            },
            {
                "name": "404 error",
                "status_code": 404,
                "html": "<html></html>",
                "expected": None
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_http_get.return_value = mock_response
                mock_process_kit.return_value = Mock()

                result = scrape_whole_club(self.club)

                if case["expected"] is None:
                    self.assertIsNone(result)
                else:
                    self.assertIsNotNone(result)
                    self.assertEqual(result, self.club)

    def test_get_or_create_brand(self):
        """Test _get_or_create_brand function."""
        # Test getting existing brand
        brand = _get_or_create_brand("adidas-kits")
        self.assertEqual(brand.name, "adidas")
        self.assertEqual(brand.slug, "adidas-kits")

        # Test creating new brand when scraping fails
        with patch('core.scrapers.scrape_brand') as mock_scrape:
            mock_scrape.side_effect = ValueError("Logo image not found")
            brand = _get_or_create_brand("new-brand-kits")
            self.assertEqual(brand.name, "New Brand")
            self.assertEqual(brand.slug, "new-brand-kits")

    @patch('core.scrapers.requests.get')
    def test_process_kit(self, mock_get):
        """Test _process_kit function."""
        test_cases = [
            {
                "name": "Valid kit",
                "html": """
                    <div class="kit" id="243162">
                        <a href="/bayern-munchen-2024-25-home-kit/">
                            <div class="kit-image-container">
                                <img class="lazyload entered loaded" data-src="https://cdn.footballkitarchive.com/2024/05/06/test.jpg" src="https://cdn.footballkitarchive.com/2024/05/06/test.jpg" data-ll-status="loaded">
                                <div class="kit-image-container-ratio-fix"></div>
                            </div>
                            <div class="kit-teamname">Bayern München</div>
                            <div class="kit-season" title="2024-25 Home Kit">2024-25 Home</div>
                        </a>
                        <button class="toggle-collection-button" onclick="toggleCollection(event)" data-id="243162" data-in-collection="">
                            <svg class="in-collection-check" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                        </button>
                    </div>
                """,
                "expected": {
                    "type": "Home",
                    "should_create": True
                }
            },
            {
                "name": "No link",
                "html": """
                    <div class="kit" id="243162">
                        <div class="kit-image-container">
                            <img class="lazyload" data-src="test.jpg" src="test.jpg">
                            <div class="kit-image-container-ratio-fix"></div>
                        </div>
                        <div class="kit-teamname">Bayern München</div>
                        <div class="kit-season" title="2024-25 Home Kit">2024-25 Home</div>
                    </div>
                """,
                "expected": None
            },
            {
                "name": "No kit-season div",
                "html": """
                    <div class="kit" id="243162">
                        <a href="/bayern-munchen-2024-25-home-kit/">
                            <div class="kit-image-container">
                                <img class="lazyload" data-src="test.jpg" src="test.jpg">
                                <div class="kit-image-container-ratio-fix"></div>
                            </div>
                            <div class="kit-teamname">Bayern München</div>
                        </a>
                    </div>
                """,
                "expected": None
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                soup = BeautifulSoup(case["html"], 'html.parser')
                kit_element = soup.find("div", class_="kit")

                # Mock scrape_kit_lite response
                if case["expected"] and case["expected"]["should_create"]:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.text = """
                        <div class="top-container">
                            <table class="fact-table">
                                <tbody>
                                    <tr>
                                        <td>Team</td>
                                        <td><a href="/bayern-munchen-kits/">Bayern München</a></td>
                                    </tr>
                                    <tr>
                                        <td>Season</td>
                                        <td>2024-25</td>
                                    </tr>
                                    <tr>
                                        <td>Type</td>
                                        <td>Home</td>
                                    </tr>
                                    <tr>
                                        <td>Brand</td>
                                        <td><a href="/adidas-kits/">adidas</a></td>
                                    </tr>
                                    <tr>
                                        <td>League</td>
                                        <td><a href="/bundesliga-kits/">Bundesliga</a></td>
                                    </tr>
                                    <tr>
                                        <td>Rating</td>
                                        <td>
                                            <div class="rating-container">
                                                <div class="rating-details">
                                                    <span id="rating">4.5</span>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <img class="top-image" data-src="test.jpg"/>
                    """
                    mock_get.return_value = mock_response

                result = _process_kit(kit_element, self.club, self.current_season, self.brand)

                if case["expected"] is None:
                    self.assertIsNone(result)
                elif case["expected"]["should_create"]:
                    self.assertIsNotNone(result)
                    self.assertEqual(result.type.name, case["expected"]["type"])

    @patch('core.scrapers.http_get')
    def test_scrape_kit_lite(self, mock_http_get):
        """Test scrape_kit_lite function."""
        test_cases = [
            {
                "name": "Successful scrape",
                "status_code": 200,
                "html": """
                    <div class="top-container">
                        <table class="fact-table">
                            <tr>
                                <td>Team</td>
                                <td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td>
                            </tr>
                            <tr>
                                <td>Season</td>
                                <td>2024-25</td>
                            </tr>
                            <tr>
                                <td>Type</td>
                                <td>Third</td>
                            </tr>
                            <tr>
                                <td>Design</td>
                                <td>Striped</td>
                            </tr>
                            <tr>
                                <td>Colors</td>
                                <td>Blue / White</td>
                            </tr>
                            <tr>
                                <td>Brand</td>
                                <td><a href="/adidas-kits/">adidas</a></td>
                            </tr>
                            <tr>
                                <td>League</td>
                                <td><a href="/superliga-kits/">Superliga</a></td>
                            </tr>
                            <tr>
                                <td>Rating</td>
                                <td>
                                    <div class="rating-container">
                                        <div class="rating-details">
                                            <span id="rating">4.5</span>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </table>
                        <img class="top-image" data-src="test.jpg"/>
                    </div>
                """,
                "expected": {
                    "rating": 4.5,
                    "has_image": True,
                    "design": "Striped",
                    "colors": "Blue / White"
                }
            },
            {
                "name": "No rating",
                "status_code": 200,
                "html": """
                    <div class="top-container">
                        <table class="fact-table">
                            <tr>
                                <td>Team</td>
                                <td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td>
                            </tr>
                            <tr>
                                <td>Season</td>
                                <td>2024-25</td>
                            </tr>
                            <tr>
                                <td>Type</td>
                                <td>Third</td>
                            </tr>
                            <tr>
                                <td>Brand</td>
                                <td><a href="/adidas-kits/">adidas</a></td>
                            </tr>
                            <tr>
                                <td>League</td>
                                <td><a href="/superliga-kits/">Superliga</a></td>
                            </tr>
                            <tr>
                                <td>Rating</td>
                                <td>
                                    <div class="rating-container">
                                        <div class="rating-details">
                                            <span id="rating"></span>
                                            <span id="rating-details-no">no votes</span>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </table>
                        <img class="top-image" data-src="test.jpg"/>
                    </div>
                """,
                "expected": {
                    "rating": 0.0,
                    "has_image": True
                }
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Reset mock before each test case
                mock_http_get.reset_mock()

                # Set up a new mock response
                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_http_get.return_value = mock_response

                # Delete any existing kits to ensure clean state
                Kit.objects.filter(team=self.club, season=self.current_season, type=self.type_k).delete()

                # Create colors if needed
                if "colors" in case["expected"]:
                    Color.objects.get_or_create(name="Blue", defaults={'color': "#0000FF"})
                    Color.objects.get_or_create(name="White", defaults={'color': "#FFFFFF"})

                result = scrape_kit_lite(
                    "test-kit",
                    self.brand,
                    self.current_season,
                    self.type_k,
                    self.club
                )

                if case["expected"] is None:
                    self.assertIsNone(result)
                else:
                    self.assertIsNotNone(result)
                    self.assertAlmostEqual(float(result.rating), case["expected"]["rating"], places=2)
                    if case["expected"]["has_image"]:
                        self.assertEqual(result.main_img_url, "test.jpg")

    @patch('core.scrapers.http_get')
    def test_scrape_club_details_full(self, mock_http_get):
        """Test scraping club details with full HTML response."""
        test_cases = [
            {
                "name": "Full club page",
                "status_code": 200,
                "html": """
                    <div class="main-header">
                        <img class="lazyload entered loaded" src="/static/logos/teams/6302.png?v=1660006928&amp;s=128"
                             data-src="/static/logos/teams/6302.png?v=1660006928&amp;s=128" data-ll-status="loaded">
                        <span class="main-title">Loja Club Deportivo Kit History</span>
                        <div class="button-set">
                            <a class="button" href="/spanish-division-honor-andalucia-gr-2-kits/">Spanish División Honor Andalucía Gr. 2</a>
                            <a class="button" href="/kedeke-kits/">Kedeke</a>
                        </div>
                    </div>
                """,
                "slug": "loja-club-deportivo-kits",
                "expected": {
                    "name": "Loja Club Deportivo",
                    "logo": "https://www.footballkitarchive.com/static/logos/teams/6302.png?v=1660006928&s=128"
                }
            },
            {
                "name": "Missing logo",
                "status_code": 200,
                "html": """
                    <div class="main-header">
                        <span class="main-title">Loja Club Deportivo Kit History</span>
                    </div>
                """,
                "slug": "loja-club-deportivo-kits",
                "expected": {
                    "name": "Loja Club Deportivo",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png"
                }
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                Club.objects.filter(slug=case["slug"]).delete()

                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_response.raise_for_status = Mock()
                mock_http_get.return_value = mock_response

                club = scrape_club_details(case["slug"])

                self.assertIsNotNone(club)
                self.assertEqual(club.name, case["expected"]["name"])
                self.assertEqual(club.logo, case["expected"]["logo"])

    @patch('core.scrapers.http_get')
    def test_scrape_kit_full(self, mock_http_get):
        """Test scraping kit details with full HTML response."""
        test_cases = [
            {
                "name": "Full kit page",
                "status_code": 200,
                "html": """
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/02/04/Y3Zty9oc0wBF39R.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/02/04/Y3Zty9oc0wBF39R.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr>
                                        <td>Team</td>
                                        <td><a href="/loja-club-deportivo-kits/">Loja Club Deportivo</a></td>
                                    </tr>
                                    <tr>
                                        <td>Season</td>
                                        <td>2023-24</td>
                                    </tr>
                                    <tr>
                                        <td>Type</td>
                                        <td>Home</td>
                                    </tr>
                                    <tr>
                                        <td>Design</td>
                                        <td>Striped</td>
                                    </tr>
                                    <tr>
                                        <td>Colors</td>
                                        <td>Red / White</td>
                                    </tr>
                                    <tr>
                                        <td>Brand</td>
                                        <td><a href="/kedeke-kits/">Kedeke</a></td>
                                    </tr>
                                    <tr>
                                        <td>League</td>
                                        <td>
                                            <a href="/spanish-division-honor-andalucia-gr-2-kits/">Spanish División Honor Andalucía Gr. 2</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>Rating</td>
                                        <td>
                                            <div class="rating-container">
                                                <div class="rating-details">
                                                    <span id="rating">4.67</span>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """,
                "slug": "loja-club-deportivo-2023-24-home-kit",
                "expected": {
                    "team_name": "Loja Club Deportivo",
                    "season": "2023-24",
                    "type": "Home",
                    "brand": "Kedeke",
                    "rating": 4.67,
                    "main_img_url": "https://cdn.footballkitarchive.com/2024/02/04/Y3Zty9oc0wBF39R.jpg"
                }
            },
            {
                "name": "No rating",
                "status_code": 200,
                "html": """
                    <div class="top-container">
                        <div class="top-container-col top-container-col-image">
                            <div class="top-container-img-container">
                                <a href="https://cdn.footballkitarchive.com/2024/02/04/test.jpg">
                                    <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/02/04/test.jpg"/>
                                </a>
                            </div>
                        </div>
                        <div class="top-container-col">
                            <table class="fact-table">
                                <tbody>
                                    <tr>
                                        <td>Team</td>
                                        <td><a href="/loja-club-deportivo-kits/">Loja Club Deportivo</a></td>
                                    </tr>
                                    <tr>
                                        <td>Season</td>
                                        <td>2023-24</td>
                                    </tr>
                                    <tr>
                                        <td>Type</td>
                                        <td>Home</td>
                                    </tr>
                                    <tr>
                                        <td>Brand</td>
                                        <td><a href="/kedeke-kits/">Kedeke</a></td>
                                    </tr>
                                    <tr>
                                        <td>League</td>
                                        <td>
                                            <a href="/spanish-division-honor-andalucia-gr-2-kits/">Spanish División Honor Andalucía Gr. 2</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>Rating</td>
                                        <td>
                                            <div class="rating-container">
                                                <div class="rating-details">
                                                    <span id="rating"></span>
                                                    <span id="rating-details-no">no votes</span>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                """,
                "slug": "loja-club-deportivo-2023-24-home-kit",
                "expected": {
                    "team_name": "Loja Club Deportivo",
                    "season": "2023-24",
                    "type": "Home",
                    "brand": "Kedeke",
                    "rating": 0.0,
                    "main_img_url": "https://cdn.footballkitarchive.com/2024/02/04/test.jpg"
                }
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Clean up any existing objects first
                Club.objects.filter(slug="loja-club-deportivo-kits").delete()
                Brand.objects.filter(slug="kedeke-kits").delete()

                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_http_get.return_value = mock_response

                # Create required objects
                Club.objects.create(
                    slug="loja-club-deportivo-kits",
                    name=case["expected"]["team_name"]
                )
                Brand.objects.create(
                    slug="kedeke-kits",
                    name=case["expected"]["brand"]
                )

                # Create colors if needed
                Color.objects.get_or_create(name="Red", defaults={'color': "#FF0000"})
                Color.objects.get_or_create(name="White", defaults={'color': "#FFFFFF"})

                kit = scrape_kit(case["slug"])

                self.assertIsNotNone(kit)
                self.assertEqual(kit.team.name, case["expected"]["team_name"])
                self.assertEqual(kit.season.year, case["expected"]["season"])
                self.assertEqual(kit.type.name, case["expected"]["type"])
                self.assertEqual(kit.brand.name, case["expected"]["brand"])
                self.assertEqual(kit.rating, case["expected"]["rating"])
                self.assertEqual(kit.main_img_url, case["expected"]["main_img_url"])

    @patch('core.scrapers.scrape_kit')
    @patch('core.scrapers.http_get')
    def test_scrape_lastest(self, mock_http_get, mock_scrape_kit):
        """Test scraping latest kits page."""
        test_cases = [
            {
                "name": "Successful scrape",
                "status_code": 200,
                "html": """
                    <div class="kit-container">
                        <div class="kit">
                            <a href="/fc-copenhagen-2024-25-home-kit/">
                                <img src="kit1.jpg"/>
                            </a>
                        </div>
                        <div class="kit">
                            <a href="/fc-copenhagen-2024-25-away-kit/">
                                <img src="kit2.jpg"/>
                            </a>
                        </div>
                    </div>
                """,
                "expected": True
            },
            {
                "name": "Empty page",
                "status_code": 200,
                "html": """
                    <div class="kit-container">
                    </div>
                """,
                "expected": True
            },
            {
                "name": "404 error",
                "status_code": 404,
                "html": "<html></html>",
                "expected": False
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                mock_response = Mock()
                mock_response.status_code = case["status_code"]
                mock_response.text = case["html"]
                mock_http_get.return_value = mock_response
                mock_scrape_kit.return_value = Mock()

                result = scrape_lastest(1)
                self.assertEqual(result, case["expected"])

    @patch('core.scrapers.scrape_lastest')
    def test_scrape_latest_pages(self, mock_scrape_latest):
        """Test scraping multiple latest kit pages."""
        test_cases = [
            {
                "name": "All successful",
                "pages": [True, True, True],
                "expected": (3, 0)
            },
            {
                "name": "Some failures",
                "pages": [True, False, True],
                "expected": (2, 1)
            },
            {
                "name": "All failures",
                "pages": [False, False, False],
                "expected": (0, 3)
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                mock_scrape_latest.side_effect = case["pages"]

                success, failure = scrape_latest_pages(
                    page_start=1,
                    page_end=len(case["pages"]),
                    delay=0  # No delay for testing
                )

                self.assertEqual((success, failure), case["expected"])

        # Test invalid page range
        with self.assertRaises(ValueError):
            scrape_latest_pages(page_start=2, page_end=1)

    @patch('core.scrapers.http_get')
    def test_design_extraction(self, mock_http_get):
        """Test that the design field is correctly extracted and saved."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
            <div class="top-container">
                <div class="top-container-col top-container-col-image">
                    <div class="top-container-img-container">
                        <a href="https://cdn.footballkitarchive.com/2024/12/28/WoFwCr2Yv42ZmE6.jpg">
                            <img class="top-image" data-src="https://cdn.footballkitarchive.com/2024/12/28/WoFwCr2Yv42ZmE6.jpg"/>
                        </a>
                    </div>
                </div>
                <div class="top-container-col">
                    <table class="fact-table">
                        <tbody>
                            <tr>
                                <td>Team</td>
                                <td><a href="/fc-copenhagen-kits/">FC Copenhagen</a></td>
                            </tr>
                            <tr>
                                <td>Season</td>
                                <td>2024-25</td>
                            </tr>
                            <tr>
                                <td>Type</td>
                                <td>Third</td>
                            </tr>
                            <tr>
                                <td>Design</td>
                                <td>Hoops</td>
                            </tr>
                            <tr>
                                <td>Colors</td>
                                <td>Blue / White</td>
                            </tr>
                            <tr>
                                <td>Brand</td>
                                <td><a href="/adidas-kits/">adidas</a></td>
                            </tr>
                            <tr>
                                <td>League</td>
                                <td>
                                    <a href="/danish-superliga-kits/">Danish Superliga</a>
                                </td>
                            </tr>
                            <tr>
                                <td>Rating</td>
                                <td>
                                    <div class="rating-container">
                                        <div class="rating-details">
                                            <span id="rating">4.42</span>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        """
        mock_http_get.return_value = mock_response

        Color.objects.get_or_create(name="Blue", defaults={'color': "#0000FF"})
        Color.objects.get_or_create(name="White", defaults={'color': "#FFFFFF"})

        Club.objects.get_or_create(
            name="FC Copenhagen",
            slug="fc-copenhagen-kits"
        )

        kit = scrape_kit("fc-copenhagen-2024-25-third-kit")

        self.assertIsNotNone(kit)
        self.assertEqual(kit.design, "Hoops")
        self.assertEqual(kit.primary_color.name, "Blue")
        self.assertEqual(kit.secondary_color.first().name, "White")
