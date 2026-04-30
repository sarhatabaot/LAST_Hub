import json

from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import service
from .commands import get_spec, parse_base


# These endpoints expose the controller as an internal service. CSRF is
# disabled because the only callers are server-to-server (the hub's
# controller_client). Authentication is the next thing to add when the
# controller moves out of localhost.


def _backend():
    return service.get_backend()


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}")


def _normalize_units(payload):
    units = payload.get("units")
    if units in (None, "", []):
        return None
    if not isinstance(units, list):
        raise ValueError("units must be a list of integers")
    resolved = []
    for u in units:
        try:
            resolved.append(int(u))
        except (TypeError, ValueError):
            raise ValueError("units must be integers")
    return resolved


@require_GET
def status_view(request):
    state = _backend().status()
    return JsonResponse({
        "backend": getattr(settings, "CONTROLLER_BACKEND", "mock"),
        "state": state,
        "events": service.recent_events(20),
    })


def _units_from_body(request):
    body = _json_body(request)
    return body, _normalize_units(body)


@csrf_exempt
@require_POST
def open_view(request):
    try:
        _, units = _units_from_body(request)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    label = f"observatory.open units={units or 'all'}"
    service.dispatch(label, _backend().open_observatory, units)
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def close_view(request):
    try:
        _, units = _units_from_body(request)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    label = f"observatory.close units={units or 'all'}"
    service.dispatch(label, _backend().close_observatory, units)
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def abort_view(request):
    try:
        _, units = _units_from_body(request)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    label = f"observatory.abort units={units or 'all'}"
    result = service.dispatch(label, _backend().abort, units)
    return JsonResponse({"ok": True, "abort_set": result})


@csrf_exempt
@require_POST
def command_view(request):
    try:
        body = _json_body(request)
        command = body.get("command")
        if not command or not isinstance(command, str):
            raise ValueError("command (string) is required")
        units = _normalize_units(body)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    spec = get_spec(command)
    if spec is None:
        return JsonResponse(
            {"ok": False, "error": f"Unknown command: {parse_base(command)!r}"},
            status=400,
        )

    # Catalog is authoritative for channel/wait. The body can override only by
    # explicitly supplying both fields (advanced HTTP callers; the UI doesn't
    # surface these).
    channel = (body.get("channel") or spec["channel"]).lower()
    wait = bool(body["wait"]) if "wait" in body else spec["wait"]

    backend = _backend()
    if channel == "messenger":
        fn = backend.query if wait else backend.send
    elif channel == "responder":
        fn = backend.query_callback if wait else backend.send_callback
    else:
        return HttpResponseBadRequest("channel must be 'messenger' or 'responder'")

    label = f"{channel}.{'query' if wait else 'send'} {command} units={units or 'all'}"
    result = service.dispatch(label, fn, command, units)
    return JsonResponse({"ok": True, "result": result})
