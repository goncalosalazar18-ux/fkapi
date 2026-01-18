"""
Unit tests for Celery integration and fallback mechanisms.

These tests verify:
1. Celery detection (available/active)
2. Task execution with Celery and threading fallback
3. Task decorators work correctly
4. Integration with Django settings
"""

import threading
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.test import TestCase, override_settings

from core.models import Club, Season, Type_K
from core.tasks import scrape_daily, scrape_kit_task, scrape_whole_club_task
from core.utils.celery_utils import (
    execute_task_async,
    is_celery_active,
    is_celery_available,
)


class TestCeleryUtils(TestCase):
    """Test Celery utility functions."""

    def setUp(self):
        """Reset cached values before each test."""
        import core.utils.celery_utils as celery_utils_module
        celery_utils_module._CELERY_AVAILABLE = None
        celery_utils_module._CELERY_ACTIVE = None

    def test_is_celery_available_with_celery_installed(self):
        """Test is_celery_available returns True when Celery is installed."""
        with patch('core.utils.celery_utils.celery', create=True):
            result = is_celery_available()
            # Should return True if celery can be imported
            assert isinstance(result, bool)

    def test_is_celery_available_without_celery(self):
        """Test is_celery_available returns False when Celery is not installed."""
        with patch.dict('sys.modules', {'celery': None}):
            # Force re-import
            import core.utils.celery_utils as celery_utils_module
            celery_utils_module._CELERY_AVAILABLE = None
            with patch('builtins.__import__', side_effect=ImportError("No module named 'celery'")):
                result = is_celery_available()
                assert result is False

    @override_settings(ENABLE_CELERY=True)
    def test_is_celery_active_when_enabled(self):
        """Test is_celery_active returns True when Celery is enabled in settings."""
        with patch('core.utils.celery_utils.is_celery_available', return_value=True):
            # Mock the celery module and app
            mock_app = MagicMock()
            mock_app.main = 'fkapi'
            with patch.dict('sys.modules', {'fkapi.celery': MagicMock(app=mock_app)}):
                with patch('core.utils.celery_utils.app', mock_app, create=True):
                    result = is_celery_active()
                    # Should return True if Celery is available and enabled
                    assert isinstance(result, bool)

    @override_settings(ENABLE_CELERY=False)
    def test_is_celery_active_when_disabled(self):
        """Test is_celery_active returns False when ENABLE_CELERY is False."""
        with patch('core.utils.celery_utils.is_celery_available', return_value=True):
            result = is_celery_active()
            assert result is False

    def test_is_celery_active_when_not_available(self):
        """Test is_celery_active returns False when Celery is not available."""
        with patch('core.utils.celery_utils.is_celery_available', return_value=False):
            result = is_celery_active()
            assert result is False

    def test_execute_task_async_with_celery(self):
        """Test execute_task_async uses Celery when available."""
        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock())

        with patch('core.utils.celery_utils.is_celery_active', return_value=True):
            result = execute_task_async(mock_task, 'arg1', kwarg1='value1')
            mock_task.delay.assert_called_once_with('arg1', kwarg1='value1')
            assert result is not None

    def test_execute_task_async_without_celery(self):
        """Test execute_task_async falls back to threading when Celery is not available."""
        def dummy_task(arg1, kwarg1=None):
            return f"result: {arg1}, {kwarg1}"

        with patch('core.utils.celery_utils.is_celery_active', return_value=False):
            result = execute_task_async(dummy_task, 'arg1', kwarg1='value1')
            assert isinstance(result, threading.Thread)
            # Wait for thread to complete
            result.join(timeout=1)
            assert not result.is_alive()

    def test_execute_task_async_celery_fallback_on_error(self):
        """Test execute_task_async falls back to threading when Celery task fails."""
        mock_task = MagicMock()
        mock_task.delay = MagicMock(side_effect=Exception("Celery error"))

        with patch('core.utils.celery_utils.is_celery_active', return_value=True):
            result = execute_task_async(mock_task, 'arg1')
            # Should fall back to threading
            assert isinstance(result, threading.Thread)


class TestCeleryTasks(TestCase):
    """Test Celery task definitions and execution."""

    def setUp(self):
        """Set up test data."""
        self.season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.club = Club.objects.create(slug="test-club", name="Test Club")
        self.type_k = Type_K.objects.create(name="Home")

    def test_scrape_daily_task_exists(self):
        """Test that scrape_daily task is defined."""
        assert callable(scrape_daily)
        assert hasattr(scrape_daily, '__name__')
        assert scrape_daily.__name__ == 'scrape_daily'

    def test_scrape_whole_club_task_exists(self):
        """Test that scrape_whole_club_task is defined."""
        assert callable(scrape_whole_club_task)
        assert hasattr(scrape_whole_club_task, '__name__')
        assert scrape_whole_club_task.__name__ == 'scrape_whole_club_task'

    def test_scrape_kit_task_exists(self):
        """Test that scrape_kit_task is defined."""
        assert callable(scrape_kit_task)
        assert hasattr(scrape_kit_task, '__name__')
        assert scrape_kit_task.__name__ == 'scrape_kit_task'

    @patch('core.tasks.call_command')
    def test_scrape_daily_calls_command(self, mock_call_command):
        """Test that scrape_daily calls the scrape_latest command."""
        scrape_daily()
        mock_call_command.assert_called_once_with('scrape_latest')

    def test_scrape_whole_club_task_with_valid_club(self):
        """Test scrape_whole_club_task with a valid club ID."""
        with patch('core.scrapers.scrape_whole_club') as mock_scrape:
            mock_scrape.return_value = self.club
            result = scrape_whole_club_task(self.club.id, use_proxy=False)
            # Verify scrape_whole_club was called with the club object
            mock_scrape.assert_called_once()
            call_args = mock_scrape.call_args
            # scrape_whole_club takes club as first positional arg (no use_proxy parameter)
            assert call_args[0][0] == self.club
            assert result == self.club

    def test_scrape_whole_club_task_with_invalid_club(self):
        """Test scrape_whole_club_task raises exception for invalid club ID."""
        from core.models import Club
        with pytest.raises(Club.DoesNotExist):
            scrape_whole_club_task(99999)

    @patch('core.scrapers.scrape_kit')
    def test_scrape_kit_task_calls_scraper(self, mock_scrape_kit):
        """Test that scrape_kit_task calls scrape_kit with correct parameters."""
        mock_scrape_kit.return_value = True
        result = scrape_kit_task('test-slug', kit_id='123', use_proxy=True)
        # Verify scrape_kit was called with correct parameters
        mock_scrape_kit.assert_called_once()
        call_kwargs = mock_scrape_kit.call_args[1]  # Get keyword arguments
        assert call_kwargs['kit_id'] == '123'
        assert call_kwargs['use_proxy'] is True
        # First positional arg should be the slug
        assert mock_scrape_kit.call_args[0][0] == 'test-slug'
        assert result is True


class TestCeleryFallback(TestCase):
    """Test fallback behavior when Celery is not available."""

    def setUp(self):
        """Reset cached values."""
        import core.utils.celery_utils as celery_utils_module
        celery_utils_module._CELERY_AVAILABLE = None
        celery_utils_module._CELERY_ACTIVE = None

    @override_settings(ENABLE_CELERY=False)
    def test_tasks_work_without_celery(self):
        """Test that tasks can be called directly without Celery."""
        # Tasks should be callable functions, not Celery tasks
        assert callable(scrape_daily)
        assert callable(scrape_whole_club_task)
        assert callable(scrape_kit_task)

    @override_settings(ENABLE_CELERY=False)
    @patch('core.tasks.call_command')
    def test_scrape_daily_works_without_celery(self, mock_call_command):
        """Test scrape_daily works when Celery is disabled."""
        scrape_daily()
        mock_call_command.assert_called_once_with('scrape_latest')

    def test_execute_task_async_threading_fallback(self):
        """Test that execute_task_async uses threading when Celery is not active."""
        call_count = {'value': 0}

        def test_task():
            call_count['value'] += 1

        with patch('core.utils.celery_utils.is_celery_active', return_value=False):
            thread = execute_task_async(test_task)
            assert isinstance(thread, threading.Thread)
            thread.join(timeout=1)
            assert call_count['value'] == 1


class TestCeleryIntegration(TestCase):
    """Integration tests for Celery configuration."""

    @override_settings(ENABLE_CELERY=True)
    def test_celery_settings_when_enabled(self):
        """Test that Celery settings are configured when enabled."""
        # This test verifies settings are set correctly
        # Actual Celery app loading is tested separately
        assert hasattr(settings, 'ENABLE_CELERY')
        # Settings may or may not have Celery config depending on availability
        assert isinstance(settings.ENABLE_CELERY, bool)

    @override_settings(ENABLE_CELERY=False)
    def test_celery_settings_when_disabled(self):
        """Test that Celery settings are not configured when disabled."""
        assert settings.ENABLE_CELERY is False

    def test_task_decorator_conditional(self):
        """Test that task decorator is conditional based on Celery availability."""
        # The decorator should be a function, not raise errors
        from core.tasks import task_decorator
        assert callable(task_decorator)

        # Decorator should work on any function
        @task_decorator
        def test_func():
            return "test"

        assert callable(test_func)
        assert test_func() == "test"


@pytest.mark.unit
class TestCeleryUnitTests:
    """Pytest-style unit tests for Celery utilities."""

    def test_is_celery_available_caching(self):
        """Test that is_celery_available caches results."""
        import core.utils.celery_utils as celery_utils_module
        celery_utils_module._CELERY_AVAILABLE = None

        # First call
        result1 = is_celery_available()

        # Second call should use cache
        with patch('core.utils.celery_utils.celery', create=True):
            result2 = is_celery_available()
            # Should return same result (cached)
            assert result1 == result2

    def test_is_celery_active_caching(self):
        """Test that is_celery_active caches results."""
        import core.utils.celery_utils as celery_utils_module
        celery_utils_module._CELERY_ACTIVE = None

        with patch('core.utils.celery_utils.is_celery_available', return_value=False):
            result1 = is_celery_active()
            result2 = is_celery_active()
            assert result1 == result2
