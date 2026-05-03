from django.test import TestCase
from django.urls import reverse


class HubRoutesTests(TestCase):
    def test_overview_renders(self):
        response = self.client.get(reverse("hub_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations dashboard")
        self.assertContains(response, "Cloud state")
        self.assertContains(response, "Rain state")
        self.assertNotContains(response, "Quick launch")
        self.assertNotContains(response, "Secondary resources")
        self.assertContains(response, "overview-snippet-chip-unsafe")

    def test_resources_renders(self):
        response = self.client.get(reverse("hub_resources"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resources and legacy links")

    def test_operations_renders(self):
        response = self.client.get(reverse("hub_operations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mission Control")

    def test_zorg_redirects_to_external_page(self):
        response = self.client.get(reverse("zorg"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "http://10.23.1.25/")

    def test_base_template_uses_htmx_2(self):
        response = self.client.get(reverse("hub_overview"))

        self.assertContains(response, "https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js")
