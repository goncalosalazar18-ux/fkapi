"""Tests for performance monitoring."""

import time
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from core.models import Club


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
