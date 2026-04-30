from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse


class ForecastTests(TestCase):
    @patch("forecast.services.requests.get")
    def test_forecast_workspace_omits_summary_cards_container(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "temperature": {
                "time": [1_700_000_000_000],
                "value": [12.5],
            },
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        page = self.client.get(reverse("forecast:index"))

        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'id="forecastSummary"')
        self.assertNotContains(page, "forecast/icons/favicon.svg")

    @patch("forecast.services.requests.get")
    def test_forecast_api_returns_normalized_payload(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "temperature": {
                "time": [1_700_000_000_000],
                "value": [12.5],
            },
            "cloud_cover_total": {
                "time": [1_700_000_000_000],
                "value": [30],
            },
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        api_response = self.client.get(reverse("forecast:api"))

        self.assertEqual(api_response.status_code, 200)
        payload = api_response.json()
        self.assertEqual(payload["providers"][0]["status"], "ok")
        self.assertTrue(payload["series_groups"])
        self.assertEqual(payload["summary"]["point_count"], 2)

    @patch("forecast.services.requests.get")
    def test_forecast_api_handles_provider_failure(self, mock_get):
        mock_get.side_effect = OSError("down")

        api_response = self.client.get(reverse("forecast:api"))

        self.assertEqual(api_response.status_code, 503)
        payload = api_response.json()
        self.assertEqual(payload["providers"][0]["status"], "error")
        self.assertTrue(payload["warnings"])

    @patch("forecast.services.requests.get")
    def test_forecast_api_returns_qualitative_overview_states(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "cloud_cover_total": {
                "time": [1_700_000_000_000],
                "value": [75],
            },
            "total_precipitation": {
                "time": [1_700_000_000_000],
                "value": [0.0],
            },
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        api_response = self.client.get(reverse("forecast:api"))

        self.assertEqual(api_response.status_code, 200)
        payload = api_response.json()
        self.assertEqual(payload["overview_states"]["cloud"]["state"], "Cloudy")
        self.assertEqual(payload["overview_states"]["rain"]["state"], "Dry")
        self.assertEqual(payload["overview_states"]["rain"]["detail"], "0 mm latest precipitation")
