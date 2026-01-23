"""
Comprehensive parser tests for extracting kit information from HTML.
These tests ensure the HTML parsing functionality works correctly.
"""

from bs4 import BeautifulSoup
from django.test import TestCase

from core.parsers import extract_fact_table, parse_kit_page


class TestFactTableParser(TestCase):
    """Test the fact table parser functionality."""

    def test_extract_valid_fact_table(self):
        """Test extracting facts from a valid fact table."""
        html = """
        <html><body>
        <table class="fact-table">
            <tbody>
                <tr><td>Team</td><td><a href="/arsenal-kits/">Arsenal</a></td></tr>
                <tr><td>Season</td><td>2024-25</td></tr>
                <tr><td>Kit Type</td><td>Home</td></tr>
                <tr><td>Design</td><td>Striped</td></tr>
                <tr><td>Colors</td><td>Red / White</td></tr>
                <tr><td>Brand</td><td><a href="/adidas-kits/">adidas</a></td></tr>
                <tr><td>League</td><td><a href="/premier-league-kits/">Premier League</a></td></tr>
                <tr><td>Rating</td><td><span id="rating">4.42</span></td></tr>
            </tbody>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("team"), "Arsenal")
        self.assertEqual(fact_table.get_text("Season"), "2024-25")
        self.assertEqual(fact_table.get_text("kit type"), "Home")
        self.assertEqual(fact_table.get_text("Design"), "Striped")
        self.assertEqual(fact_table.get_text("Brand"), "adidas")
        self.assertEqual(fact_table.get_text("League"), "Premier League")

    def test_extract_fact_table_case_insensitive(self):
        """Test that fact table extraction is case insensitive."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>TEAM</td><td>Manchester United</td></tr>
                <tr><td>season</td><td>2023-24</td></tr>
                <tr><td>Kit Type</td><td>Away</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("team"), "Manchester United")
        self.assertEqual(fact_table.get_text("season"), "2023-24")

    def test_extract_fact_table_special_characters(self):
        """Test extracting facts with special characters in text."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Team</td><td><a href="/fc-bucuresti-kits/">FC București</a></td></tr>
                <tr><td>Colors</td><td>Dark Red / Light Blue</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("team"), "FC București")
        self.assertEqual(fact_table.get_text("colors"), "Dark Red / Light Blue")

    def test_extract_fact_table_missing_fields(self):
        """Test extracting facts with missing optional fields."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Team</td><td>Arsenal</td></tr>
                <tr><td>Season</td><td>2024-25</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("team"), "Arsenal")
        self.assertEqual(fact_table.get_text("season"), "2024-25")
        # Missing fields should return None
        self.assertIsNone(fact_table.get_text("brand"))

    def test_extract_fact_table_no_table(self):
        """Test handling HTML without a fact table."""
        html = """
        <html><body>
            <div>No fact table here</div>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        with self.assertRaises(ValueError):
            extract_fact_table(soup)


class TestColorExtraction(TestCase):
    """Test color extraction from HTML."""

    def test_extract_single_color(self):
        """Test extracting a single color."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Colors</td><td>Red</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("colors"), "Red")

    def test_extract_multiple_colors(self):
        """Test extracting multiple colors."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Colors</td><td>Red / White / Black</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        colors = fact_table.get_text("colors")
        self.assertIn("Red", colors)
        self.assertIn("White", colors)
        self.assertIn("Black", colors)

    def test_extract_colors_with_various_separators(self):
        """Test extracting colors with different separators."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Colors</td><td>Red, White, Black</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        colors = fact_table.get_text("colors")
        self.assertIn("Red", colors)
        self.assertIn("White", colors)
        self.assertIn("Black", colors)


class TestSeasonParsing(TestCase):
    """Test season format parsing."""

    def test_season_two_year_format(self):
        """Test parsing two-year season format."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Season</td><td>2024-25</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("season"), "2024-25")

    def test_season_single_year_format(self):
        """Test parsing single year season format."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Season</td><td>2024</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("season"), "2024")

    def test_season_with_special_characters(self):
        """Test parsing season with special characters."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Season</td><td>2024/25</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        season = fact_table.get_text("season")
        self.assertEqual(season, "2024/25")


class TestRatingExtraction(TestCase):
    """Test rating extraction from HTML."""

    def test_extract_rating_from_span(self):
        """Test extracting rating from span element."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Rating</td><td><span id="rating">4.5</span></td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("rating"), "4.5")

    def test_extract_rating_plain_text(self):
        """Test extracting rating from plain text."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Rating</td><td>4.75</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("rating"), "4.75")

    def test_extract_rating_decimal_precision(self):
        """Test extracting rating with decimal precision."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>Rating</td><td><span id="rating">4.33</span></td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("rating"), "4.33")


class TestCompetitionExtraction(TestCase):
    """Test competition extraction from HTML."""

    def test_extract_competition_from_link(self):
        """Test extracting competition from a link."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>League</td><td><a href="/premier-league-kits/">Premier League</a></td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("league"), "Premier League")

    def test_extract_multiple_competitions(self):
        """Test handling kits with multiple competitions."""
        html = """
        <table class="fact-table">
            <tbody>
                <tr><td>League</td><td>Premier League</td></tr>
                <tr><td>European Competition</td><td>Champions League</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        fact_table = extract_fact_table(soup)

        self.assertEqual(fact_table.get_text("league"), "Premier League")
        self.assertEqual(fact_table.get_text("european competition"), "Champions League")


class TestParseKitPage(TestCase):
    """Test complete kit page parsing."""

    def test_parse_complete_kit_page(self):
        """Test parsing a complete kit page."""
        html = """
        <html><body>
        <img class="top-image" src="https://example.com/kit.jpg" />
        <span id="rating">4.5</span>
        <table class="fact-table">
            <tbody>
                <tr><td>Team</td><td><a href="/arsenal-kits/">Arsenal</a></td></tr>
                <tr><td>Season</td><td>2024-25</td></tr>
                <tr><td>Kit Type</td><td>Home</td></tr>
                <tr><td>Design</td><td>Striped</td></tr>
                <tr><td>Colors</td><td>Red / White</td></tr>
                <tr><td>Brand</td><td><a href="/adidas-kits/">adidas</a></td></tr>
                <tr><td>League</td><td><a href="/premier-league-kits/">Premier League</a></td></tr>
            </tbody>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        data = parse_kit_page(soup)

        self.assertEqual(data.team_name, "Arsenal")
        self.assertEqual(data.team_slug, "arsenal-kits")
        self.assertEqual(data.season_text, "2024-25")
        self.assertEqual(data.rating, 4.5)
        self.assertEqual(data.main_img_url, "https://example.com/kit.jpg")
        self.assertEqual(data.kit_type, "Home")
        self.assertEqual(data.brand_name, "adidas")
        self.assertEqual(data.brand_slug, "adidas-kits")
        self.assertEqual(data.design, "Striped")
        self.assertEqual(data.colors_str, "Red / White")
        self.assertIn("Premier League", data.competitions_html)
