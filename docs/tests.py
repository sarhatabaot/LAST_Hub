from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings
from django.urls import reverse


class DocsTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        (root / "01-overview.md").write_text("# Overview\nSafe startup guide.\n", encoding="utf-8")
        (root / "ops").mkdir()
        (root / "ops" / "02-nightly.md").write_text(
            "# Nightly Ops\nUse this procedure to open and close the observatory.\n",
            encoding="utf-8",
        )
        self.override = override_settings(MANUAL_DOCS_ROOT=root)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.temp_dir.cleanup()

    def test_docs_index_renders_filesystem_markdown(self):
        response = self.client.get(reverse("docs:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overview")
        self.assertContains(response, "Safe startup guide")

    def test_docs_detail_missing_slug_returns_404(self):
        response = self.client.get(reverse("docs:detail", args=["missing-page"]))

        self.assertEqual(response.status_code, 404)

    def test_docs_search_matches_body_text(self):
        response = self.client.get(reverse("docs:index"), {"q": "open and close"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nightly Ops")
        self.assertContains(response, "open and close the observatory")

    def test_pygments_stylesheet_supports_dark_theme(self):
        stylesheet = Path(__file__).resolve().parent.parent / "hub" / "static" / "hub" / "css" / "pygments.css"
        css = stylesheet.read_text(encoding="utf-8")

        self.assertIn("@media (prefers-color-scheme: dark)", css)
        self.assertIn("--code-bg", css)
