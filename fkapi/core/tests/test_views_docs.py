from django.http import Http404
from django.test import Client, TestCase
from django.urls import reverse

from core.views_docs import docs_view


class DocsViewsTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_docs_index_renders_readme(self) -> None:
        """GET /docs/ should render the README markdown via core/docs.html."""
        response = self.client.get(reverse("docs_index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/docs.html")
        # Basic sanity checks on context
        self.assertIn("content", response.context)
        self.assertIn("title", response.context)
        self.assertIn("doc_files", response.context)

    def test_docs_view_with_subpath(self) -> None:
        """GET /docs/api/endpoint-catalog should render an existing API doc."""
        response = self.client.get(reverse("docs_view", args=["api/endpoint-catalog"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/docs.html")
        # Ensure we actually converted some markdown to HTML
        self.assertIn("content", response.context)
        html = response.context["content"]
        self.assertIsInstance(html, str)
        self.assertNotEqual(html.strip(), "")

    def test_docs_view_raises_404_for_excluded_dir(self) -> None:
        """Docs under excluded directories (like tmp) should 404."""
        with self.assertRaises(Http404):
            docs_view(None, "tmp/AGENT_PROMPT_TEMPLATE")
