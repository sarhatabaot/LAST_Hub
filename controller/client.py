import requests
from django.conf import settings


def _controller_endpoint(action):
    base_url = (settings.CONTROLLER_API_BASE_URL or "").strip()
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/observatory/{action}"


def send_action(action, timeout=5):
    endpoint = _controller_endpoint(action)
    if not endpoint:
        return False, "Controller API is not configured."

    try:
        response = requests.post(endpoint, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Controller request failed: {exc}"

    return True, "Controller acknowledged the request."


def open_observatory():
    return send_action("open")


def close_observatory():
    return send_action("close")
