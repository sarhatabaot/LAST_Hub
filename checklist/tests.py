from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from hub.models import OperationalChecklistState


class ChecklistTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("operator", password="secret12345")

    def test_checklist_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse("checklist:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Observation Checklist")

    def test_toggle_requires_login(self):
        response = self.client.post(reverse("checklist:toggle"), {"item_key": "weather_reviewed", "checked": "on"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("/hub/accounts/login/", response.url)

    def test_authenticated_user_can_toggle_item(self):
        self.client.login(username="operator", password="secret12345")

        response = self.client.post(reverse("checklist:toggle"), {"item_key": "weather_reviewed", "checked": "on"})

        self.assertEqual(response.status_code, 302)
        state = OperationalChecklistState.objects.get(pk=1)
        self.assertTrue(state.items["weather_reviewed"])

    def test_open_is_blocked_until_complete(self):
        self.client.login(username="operator", password="secret12345")

        response = self.client.post(reverse("checklist:open"))

        self.assertEqual(response.status_code, 302)
        state = OperationalChecklistState.objects.get(pk=1)
        self.assertEqual(state.last_action_status, OperationalChecklistState.ACTION_STATUS_SKIPPED)

    def test_close_resets_checklist(self):
        self.client.login(username="operator", password="secret12345")
        state, _ = OperationalChecklistState.objects.get_or_create(pk=1, defaults={"items": {}})
        state.items = {
            "safety_status_green": True,
            "weather_reviewed": True,
            "systems_reachable": True,
            "data_path_verified": True,
            "team_notified": True,
        }
        state.save(update_fields=["items", "updated_at"])

        response = self.client.post(reverse("checklist:close"))

        self.assertEqual(response.status_code, 302)
        state.refresh_from_db()
        self.assertFalse(any(state.items.values()))
        self.assertEqual(state.last_action, OperationalChecklistState.ACTION_CLOSE)

