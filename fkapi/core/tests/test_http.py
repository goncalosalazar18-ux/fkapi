from unittest.mock import ANY, MagicMock, patch

from django.test import SimpleTestCase

from core import http


class HttpUtilsTests(SimpleTestCase):
    @patch("core.http.requests.Session")
    def test_get_session_merges_default_and_custom_headers(self, mock_session_cls: MagicMock) -> None:
        session = MagicMock()
        session.headers = {}
        mock_session_cls.return_value = session

        result = http.get_session(headers={"X-Test": "1"})

        self.assertIs(result, session)
        session.mount.assert_called_once_with("https://", ANY)
        # Custom header merged
        self.assertEqual(session.headers["X-Test"], "1")

    @patch("core.http.get_session")
    def test_http_get_uses_provided_session_and_does_not_mutate_headers(self, mock_get_session: MagicMock) -> None:
        session = MagicMock()
        session.headers = {"Base": "value"}
        mock_get_session.return_value = session

        http.http_get("https://example.com", session=session, headers={"X-Test": "1"})

        # The call should use merged headers but not change session.headers
        session.get.assert_called_once()
        called_headers = session.get.call_args.kwargs["headers"]
        self.assertEqual(called_headers["X-Test"], "1")
        self.assertEqual(called_headers["Base"], "value")
        self.assertNotIn("X-Test", session.headers)

    @patch("core.http.get_proxy", return_value={"http": "http://proxy"})
    @patch("core.http.get_session")
    def test_http_get_uses_proxy_when_requested(
        self,
        mock_get_session: MagicMock,
        _: MagicMock,
    ) -> None:
        session = MagicMock()
        session.headers = {}
        mock_get_session.return_value = session

        http.http_get("https://example.com", use_proxy=True)

        session.get.assert_called_once()
        called_kwargs = session.get.call_args.kwargs
        self.assertEqual(called_kwargs["proxies"], {"http": "http://proxy"})
