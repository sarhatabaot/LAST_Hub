import logging

import requests
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from . import services


logger = logging.getLogger(__name__)

# HLS segments and MJPEG streams both use stream=True. The connect/read budget
# is generous because MJPEG responses are open-ended.
_UPSTREAM_TIMEOUT = (5, 30)


def index(request):
    presets = services.get_presets()
    if not presets:
        return render(request, "cameras/index.html", {"camera_config": None, "presets": []})

    requested_key = request.GET.get("preset")
    selected = services.get_preset(requested_key) if requested_key else None
    if selected is None:
        selected = presets[0]

    proxy_base = reverse("cameras:index") + "stream/"
    stream_timeout_ms = 3 * 60 * 1000

    presets_payload = []
    for preset in presets:
        groups_payload = []
        camera_count = 0
        for group in preset["groups"]:
            cameras = []
            for cam in group["cameras"]:
                if cam["kind"] == "webcam":
                    src = reverse(
                        "cameras:webcam_proxy",
                        args=[cam["host"], cam["port"], cam["suffix"]],
                    )
                    cameras.append({**cam, "src": src})
                else:
                    cameras.append(cam)
                camera_count += 1
            groups_payload.append({"name": group["name"], "cameras": cameras})
        presets_payload.append({
            "key": preset["key"],
            "name": preset["name"],
            "camera_count": camera_count,
            "groups": groups_payload,
        })

    selected_payload = next(p for p in presets_payload if p["key"] == selected["key"])

    return render(
        request,
        "cameras/index.html",
        {
            "camera_config": {
                "proxy_base": proxy_base,
                "selected_key": selected["key"],
                "presets": presets_payload,
                "stream_timeout_ms": stream_timeout_ms,
            },
            "presets": [{"key": p["key"], "name": p["name"]} for p in presets],
            "selected_key": selected["key"],
            "camera_count": selected_payload["camera_count"],
            "auto_stop_label": "3 min",
        },
    )


@require_GET
def proxy(request, suffix):
    if ".." in suffix.split("/") or suffix.startswith("/"):
        return HttpResponseBadRequest("Invalid stream path")

    upstream_url = f"{services.get_origin()}/{suffix}"
    auth = None
    if settings.MEDIAMTX_USERNAME or settings.MEDIAMTX_PASSWORD:
        auth = (settings.MEDIAMTX_USERNAME, settings.MEDIAMTX_PASSWORD)

    return _stream_upstream(upstream_url, auth=auth)


@require_GET
def webcam_proxy(request, host, port, suffix):
    if ".." in suffix.split("/") or suffix.startswith("/"):
        return HttpResponseBadRequest("Invalid stream path")

    upstream_url = services.get_webcam_upstream(host, port, suffix)
    if upstream_url is None:
        return HttpResponseBadRequest("Unknown webcam")

    return _stream_upstream(upstream_url)


def _stream_upstream(upstream_url, auth=None):
    try:
        upstream = requests.get(
            upstream_url,
            auth=auth,
            stream=True,
            timeout=_UPSTREAM_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("Cameras proxy: upstream error for %s: %s", upstream_url, exc)
        return HttpResponse(f"Upstream error: {exc}", status=502)

    def streamer():
        try:
            for chunk in upstream.iter_content(8192):
                yield chunk
        finally:
            upstream.close()

    response = StreamingHttpResponse(
        streamer(),
        status=upstream.status_code,
        content_type=upstream.headers.get("Content-Type", "application/octet-stream"),
    )
    if "Cache-Control" in upstream.headers:
        response["Cache-Control"] = upstream.headers["Cache-Control"]
    return response
