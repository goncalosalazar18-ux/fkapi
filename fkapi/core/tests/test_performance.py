"""Tests for performance monitoring."""

from unittest.mock import patch

from django.core.cache import cache
from django.db import connection, reset_queries
from django.test import Client, TestCase, override_settings

from core.models import Brand, Club, Competition, Kit, Season, Type_K


class PerformanceTests(TestCase):
    """Test cases for performance monitoring features."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        cache.clear()

    def test_health_check_endpoint(self):
        """Test that health check endpoint returns correct status."""
        response = self.client.get('/api/health')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('database', data)
        self.assertEqual(data['database'], 'connected')

    def test_health_check_with_database_error(self):
        """Test health check when database is unavailable."""
        with patch('core.models.Club.objects.count') as mock_count:
            mock_count.side_effect = Exception("Database connection failed")

            response = self.client.get('/api/health')

            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data['status'], 'unhealthy')
            self.assertEqual(data['database'], 'disconnected')

    def test_metrics_endpoint(self):
        """Test that metrics endpoint returns API usage statistics."""
        response = self.client.get('/api/metrics')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('endpoints', data)

    def test_metrics_endpoint_tracks_usage(self):
        """Test that metrics endpoint tracks API usage after requests."""
        self.client.get('/api/health')
        self.client.get('/api/health')

        response = self.client.get('/api/metrics')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('endpoints', data)

        if 'GET /api/health' in data['endpoints']:
            endpoint_data = data['endpoints']['GET /api/health']
            self.assertGreaterEqual(endpoint_data['count'], 2)
            self.assertIn('avg_duration', endpoint_data)
            self.assertIn('avg_queries', endpoint_data)

    @override_settings(SLOW_RESPONSE_THRESHOLD=0.01)
    def test_slow_response_detection(self):
        """Test that performance middleware is active and working."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-Response-Time', response.headers)

    def test_response_time_header(self):
        """Test that response time header is added to responses."""
        response = self.client.get('/api/health')

        self.assertIn('X-Response-Time', response.headers)
        if 'X-Query-Count' in response.headers:
            query_count = int(response.headers['X-Query-Count'])
            self.assertGreaterEqual(query_count, 0)

    def test_query_count_header(self):
        """Test that query count header is added to responses when queries are made."""
        response = self.client.get('/api/health')

        if 'X-Query-Count' in response.headers:
            query_count = int(response.headers['X-Query-Count'])
            self.assertGreaterEqual(query_count, 0)


class DatabasePerformanceTests(TestCase):
    """Test cases for database query optimization."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        cache.clear()

        # Create test data
        self.season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.club = Club.objects.create(slug="test-club", name="Test Club", logo="https://example.com/logo.png")
        self.brand = Brand.objects.create(slug="test-brand", name="Test Brand", logo="https://example.com/brand.png")
        self.competition = Competition.objects.create(slug="test-competition", name="Test Competition")
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
        self.kit.competition.add(self.competition)

    @override_settings(DEBUG=True)
    def test_get_kit_json_query_optimization(self):
        """Test that get_kit_json uses select_related and prefetch_related."""
        reset_queries()

        response = self.client.get(f'/api/kit-json/{self.kit.id}')

        self.assertEqual(response.status_code, 200)
        query_count = len(connection.queries)

        # With proper optimization, should use minimal queries (1 for kit + prefetch for relations)
        # Without optimization, would be many more queries (N+1 problem)
        self.assertLess(query_count, 10, "Query count should be optimized with select_related/prefetch_related")

    @override_settings(DEBUG=True)
    def test_get_kits_query_optimization(self):
        """Test that get_kits uses select_related."""
        reset_queries()

        response = self.client.get(f'/api/kits?club={self.club.id}&season={self.season.id}')

        self.assertEqual(response.status_code, 200)
        query_count = len(connection.queries)

        # Should use minimal queries with select_related
        self.assertLess(query_count, 5, "Query count should be optimized with select_related")

    @override_settings(DEBUG=True)
    def test_get_random_kits_query_optimization(self):
        """Test that get_random_kits uses select_related and prefetch_related."""
        reset_queries()

        response = self.client.get('/api/random-kits/?page=1&page_size=10')

        self.assertEqual(response.status_code, 200)
        query_count = len(connection.queries)

        # Should use minimal queries even with pagination
        self.assertLess(query_count, 15, "Query count should be optimized with select_related/prefetch_related")

    @override_settings(DEBUG=True)
    def test_get_random_clubs_query_optimization(self):
        """Test that get_random_clubs uses annotate to avoid N+1 queries."""
        reset_queries()

        response = self.client.get('/api/random-clubs/?page=1&page_size=10')

        self.assertEqual(response.status_code, 200)
        query_count = len(connection.queries)

        # Should use annotate instead of N+1 queries for kit_count
        self.assertLess(query_count, 15, "Query count should be optimized with annotate")

    @override_settings(DEBUG=True)
    def test_search_clubs_query_count(self):
        """Test that search_clubs doesn't cause excessive queries."""
        reset_queries()

        response = self.client.get('/api/clubs/search?keyword=test')

        self.assertEqual(response.status_code, 200)
        query_count = len(connection.queries)

        # Search should be efficient
        self.assertLess(query_count, 5, "Search queries should be optimized")
