from unittest.mock import MagicMock, patch

from django.test import TestCase

from core import tasks
from core.models import Club


class TasksTests(TestCase):
    @patch("core.tasks.call_command")
    def test_scrape_daily_calls_management_command(self, mock_call: MagicMock) -> None:
        tasks.scrape_daily()
        mock_call.assert_called_once_with("scrape_latest")

    @patch("core.scrapers.scrape_whole_club")
    def test_scrape_whole_club_task_happy_path(self, mock_scrape: MagicMock) -> None:
        club = Club.objects.create(slug="club", name="Club")
        mock_scrape.return_value = club

        result = tasks.scrape_whole_club_task(club.id, use_proxy=False)

        mock_scrape.assert_called_once()
        self.assertEqual(result, club)

    def test_scrape_whole_club_task_invalid_club_raises(self) -> None:
        with self.assertRaises(Club.DoesNotExist):
            tasks.scrape_whole_club_task(9999)

    @patch("core.scrapers.scrape_kit")
    def test_scrape_kit_task_success_returns_dict(self, mock_scrape: MagicMock) -> None:
        class DummyKit:
            id = 123

        mock_scrape.return_value = DummyKit()

        result = tasks.scrape_kit_task("slug-test", kit_id="abc", use_proxy=True)

        mock_scrape.assert_called_once()
        self.assertEqual(result["success"], True)
        self.assertEqual(result["kit_id"], 123)
        self.assertEqual(result["slug"], "slug-test")

    @patch("core.scrapers.scrape_kit", return_value=None)
    def test_scrape_kit_task_failure_returns_false_dict(self, _: MagicMock) -> None:
        result = tasks.scrape_kit_task("slug-fail")
        self.assertEqual(result["success"], False)
        self.assertEqual(result["slug"], "slug-fail")

    @patch("django.core.cache.cache")
    @patch("core.scrapers.scrape_user_collection_api")
    def test_scrape_user_collection_task_success(self, mock_scrape: MagicMock, mock_cache: MagicMock) -> None:
        """Test successful user collection scraping task."""
        mock_data = {
            "success": True,
            "entries": [{"id": 1, "kit": {"id": 10}}],
            "total_entries": 1,
            "pages_scraped": 1,
        }
        mock_scrape.return_value = mock_data

        result = tasks.scrape_user_collection_task(123)

        mock_scrape.assert_called_once_with(123)
        mock_cache.set.assert_called_once()
        # Check cache key and timeout
        # cache.set is called with positional args (key, value) and keyword arg (timeout=...)
        call_args = mock_cache.set.call_args
        cache_key = call_args[0][0]
        cached_data = call_args[0][1]
        timeout = call_args.kwargs.get("timeout")
        self.assertIn("user_collection", cache_key)
        self.assertIn("123", cache_key)
        self.assertEqual(timeout, 604800)  # 1 week
        self.assertEqual(cached_data, mock_data)
        # Check result
        self.assertEqual(result["success"], True)
        self.assertEqual(result["userid"], 123)
        self.assertEqual(result["entries_count"], 1)

    @patch("core.scrapers.scrape_user_collection_api")
    def test_scrape_user_collection_task_failure(self, mock_scrape: MagicMock) -> None:
        """Test user collection scraping task failure."""
        from core.exceptions import ScrapingError

        mock_scrape.side_effect = ScrapingError("API error")

        with self.assertRaises(ScrapingError):
            tasks.scrape_user_collection_task(123)
