from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse

from safety.services import fetch_safety_status


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

    @patch("safety.services.requests.get")
    def test_safety_page_preserves_structured_metric_label_with_numbers(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "safe": False,
            "reasons": {
                "passed": [],
                "failed": [],
            },
            "reason_metrics": {
                "passed": [],
                "failed": [
                    {
                        "label": "Davis Wind Speed Max 15/min",
                        "value": 15.0,
                        "threshold": 14.5,
                        "operator": "<=",
                        "unit": "/min",
                    }
                ],
            },
            "stale_sensors": [],
            "evaluated_at": "2026-03-10T00:00:00+00:00",
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        page = self.client.get(reverse("safety:index"))

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'data-metric-label="Davis Wind Speed Max 15/min"')
        self.assertContains(page, 'data-metric-threshold="14.5"')
        self.assertNotContains(page, "No threshold metadata")

    @patch("safety.services.requests.get")
    def test_safety_page_attaches_two_sided_range_metadata_from_reason_text(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "safe": False,
            "reasons": {
                "passed": [],
                "failed": ["Sun Horizon: 0 < value < 12 deg"],
            },
            "reason_metrics": {
                "passed": [],
                "failed": [
                    {
                        "label": "Sun Horizon",
                        "value": 12.0,
                        "threshold": 12.0,
                        "operator": "<=",
                        "unit": "deg",
                    }
                ],
            },
            "stale_sensors": [],
            "evaluated_at": "2026-03-10T00:00:00+00:00",
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        page = self.client.get(reverse("safety:index"))

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'data-metric-range-min="0.0"')
        self.assertContains(page, 'data-metric-range-max="12.0"')

    @patch("safety.services.requests.get")
    def test_fetch_safety_status_preserves_structured_range_context(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "safe": False,
            "reasons": {
                "passed": [],
                "failed": ["5 < value < 14.5 /min"],
            },
            "reason_metrics": {
                "passed": [],
                "failed": [
                    {
                        "label": "Davis Wind Speed Max 15/min",
                        "value": 15.0,
                        "threshold": 14.5,
                        "operator": "<=",
                        "unit": "/min",
                    }
                ],
            },
            "stale_sensors": [],
            "evaluated_at": "2026-03-10T00:00:00+00:00",
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        payload = fetch_safety_status()

        self.assertEqual(payload["failed_reason_metrics"][0]["label"], "Davis Wind Speed Max 15/min")
        self.assertEqual(payload["failed_reason_metrics"][0]["range_min"], 5.0)
        self.assertEqual(payload["failed_reason_metrics"][0]["range_max"], 14.5)
