from django.test import TestCase
from django.urls import reverse


class HubRoutesTests(TestCase):
    def test_overview_renders(self):
        response = self.client.get(reverse("hub_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operations dashboard")

    def test_resources_renders(self):
        response = self.client.get(reverse("hub_resources"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resources and legacy links")

    def test_operations_redirects_to_checklist(self):
        response = self.client.get(reverse("operations"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("checklist:index"))
