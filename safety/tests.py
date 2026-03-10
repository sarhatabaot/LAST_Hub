from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse


class SafetyTests(TestCase):
    @patch("safety.services.requests.get")
    def test_safety_page_renders(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "safe": True,
            "reasons": {
                "passed": ["Roof closed"],
                "failed": [],
            },
            "reason_metrics": {
                "passed": [],
                "failed": [],
            },
            "stale_sensors": [],
            "evaluated_at": "2026-03-10T00:00:00+00:00",
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        page = self.client.get(reverse("safety:index"))

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "SAFE")

