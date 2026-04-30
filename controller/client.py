import requests
from django.conf import settings


def _base_url():
    base = (settings.CONTROLLER_API_BASE_URL or "").strip()
    return base.rstrip("/") if base else ""


def _endpoint(path):
    base = _base_url()
    if not base:
        return None
    return f"{base}/{path.lstrip('/')}"


def _request(method, path, *, json=None, timeout=5):
    endpoint = _endpoint(path)
    if not endpoint:
        return False, None, "Controller API is not configured."

    try:
        response = requests.request(method, endpoint, json=json, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, None, f"Controller request failed: {exc}"

    payload = None
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = None
    return True, payload, "Controller acknowledged the request."


def send_action(action, units=None, timeout=5):
    body = {"units": units} if units is not None else None
    ok, _, message = _request("POST", f"observatory/{action}", json=body, timeout=timeout)
    return ok, message


def open_observatory(units=None):
    return send_action("open", units=units)


def close_observatory(units=None):
    return send_action("close", units=units)


def get_status(timeout=3):
    ok, payload, message = _request("GET", "observatory/status", timeout=timeout)
    if not ok:
        return None, message
    return payload, ""


def send_command(command, channel="messenger", wait=True, units=None, timeout=15):
    body = {"command": command, "channel": channel, "wait": wait}
    if units is not None:
        body["units"] = units
    ok, payload, message = _request("POST", "command", json=body, timeout=timeout)
    if not ok:
        return None, message
    return payload, ""


def abort(units=None, timeout=5):
    body = {"units": units} if units is not None else {}
    ok, payload, message = _request("POST", "observatory/abort", json=body, timeout=timeout)
    if not ok:
        return None, message
    return payload, ""
