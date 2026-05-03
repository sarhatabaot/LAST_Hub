import json
import logging
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


_DATA_DIR = Path(__file__).resolve().parent / "data"
_STREAMS_PATH = _DATA_DIR / "streams.json"
_WEBCAMS_PATH = _DATA_DIR / "webcams.json"
_PRESETS_PATH = _DATA_DIR / "presets.json"

_DEFAULT_ORIGIN = "http://10.23.1.25/mediamtx"

logger = logging.getLogger(__name__)

_origin = _DEFAULT_ORIGIN
_registry = {}
_presets = []


def _security_id(path):
    return f"security:{path}"


def _webcam_id(host, suffix):
    return f"webcam:{host}:{suffix}"


def _read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImproperlyConfigured(f"Cannot read {path}: {exc}") from exc


def _load_security_streams():
    parsed = _read_json(_STREAMS_PATH)
    if parsed is None:
        logger.warning("Cameras streams config missing: %s", _STREAMS_PATH)
        return _DEFAULT_ORIGIN, []

    mediamtx = parsed.get("mediamtx") or {}
    origin = mediamtx.get("origin", _DEFAULT_ORIGIN)
    if not isinstance(origin, str):
        raise ImproperlyConfigured('cameras: "mediamtx.origin" must be a string')

    streams_raw = parsed.get("streams")
    if not isinstance(streams_raw, list):
        raise ImproperlyConfigured('cameras: "streams" must be a list')

    streams = []
    for idx, entry in enumerate(streams_raw):
        if not isinstance(entry, dict):
            raise ImproperlyConfigured(f"cameras: stream {idx} must be an object")
        path = entry.get("path")
        description = entry.get("description")
        if not isinstance(path, str) or not path:
            raise ImproperlyConfigured(f'cameras: stream {idx} missing valid "path"')
        if not isinstance(description, str) or not description:
            raise ImproperlyConfigured(f'cameras: stream {idx} missing valid "description"')
        streams.append({
            "id": _security_id(path),
            "kind": "security",
            "path": path,
            "label": description,
        })

    return origin, streams


def _load_webcams():
    parsed = _read_json(_WEBCAMS_PATH)
    if parsed is None:
        logger.warning("Cameras webcams config missing: %s", _WEBCAMS_PATH)
        return []

    if not isinstance(parsed, list):
        raise ImproperlyConfigured('cameras: webcams.json must be a list')

    webcams = []
    for idx, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            raise ImproperlyConfigured(f"cameras: webcam {idx} must be an object")
        host = entry.get("host")
        port = entry.get("port")
        suffix = entry.get("suffix")
        description = entry.get("description")
        if not isinstance(host, str) or not host:
            raise ImproperlyConfigured(f'cameras: webcam {idx} missing valid "host"')
        if not isinstance(port, int):
            raise ImproperlyConfigured(f'cameras: webcam {idx} missing valid "port"')
        if not isinstance(suffix, str) or not suffix:
            raise ImproperlyConfigured(f'cameras: webcam {idx} missing valid "suffix"')
        if not isinstance(description, str) or not description:
            raise ImproperlyConfigured(f'cameras: webcam {idx} missing valid "description"')

        webcams.append({
            "id": _webcam_id(host, suffix),
            "kind": "webcam",
            "host": host,
            "port": port,
            "suffix": suffix,
            "label": description,
        })
    return webcams


def get_webcam_hosts():
    return {cam["host"] for cam in _registry.values() if cam["kind"] == "webcam"}


def _load_presets(registry):
    parsed = _read_json(_PRESETS_PATH)
    if parsed is None:
        logger.warning("Cameras presets config missing: %s", _PRESETS_PATH)
        return []

    if not isinstance(parsed, list) or not parsed:
        raise ImproperlyConfigured('cameras: presets.json must be a non-empty list')

    presets = []
    seen_keys = set()
    for idx, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            raise ImproperlyConfigured(f"cameras: preset {idx} must be an object")
        key = entry.get("key")
        name = entry.get("name")
        if not isinstance(key, str) or not key:
            raise ImproperlyConfigured(f'cameras: preset {idx} missing valid "key"')
        if key in seen_keys:
            raise ImproperlyConfigured(f'cameras: preset key "{key}" is duplicated')
        seen_keys.add(key)
        if not isinstance(name, str) or not name:
            raise ImproperlyConfigured(f'cameras: preset "{key}" missing valid "name"')

        groups_raw = entry.get("groups")
        cameras_raw = entry.get("cameras")
        if groups_raw is not None and cameras_raw is not None:
            raise ImproperlyConfigured(f'cameras: preset "{key}" must use either "groups" or "cameras", not both')

        if groups_raw is not None:
            if not isinstance(groups_raw, list):
                raise ImproperlyConfigured(f'cameras: preset "{key}" "groups" must be a list')
            groups = []
            for gidx, group in enumerate(groups_raw):
                gname = group.get("name") if isinstance(group, dict) else None
                gcams = group.get("cameras") if isinstance(group, dict) else None
                if not isinstance(gname, str) or not gname:
                    raise ImproperlyConfigured(f'cameras: preset "{key}" group {gidx} missing valid "name"')
                if not isinstance(gcams, list):
                    raise ImproperlyConfigured(f'cameras: preset "{key}" group {gidx} "cameras" must be a list')
                groups.append({"name": gname, "cameras": _resolve_camera_ids(key, gcams, registry)})
            presets.append({"key": key, "name": name, "groups": groups})
        else:
            if not isinstance(cameras_raw, list):
                raise ImproperlyConfigured(f'cameras: preset "{key}" "cameras" must be a list')
            presets.append({
                "key": key,
                "name": name,
                "groups": [{"name": None, "cameras": _resolve_camera_ids(key, cameras_raw, registry)}],
            })

    return presets


def _resolve_camera_ids(preset_key, ids, registry):
    resolved = []
    for cam_id in ids:
        if not isinstance(cam_id, str):
            raise ImproperlyConfigured(f'cameras: preset "{preset_key}" has a non-string camera id')
        if cam_id not in registry:
            raise ImproperlyConfigured(f'cameras: preset "{preset_key}" references unknown camera id "{cam_id}"')
        resolved.append(registry[cam_id])
    return resolved


def load_all():
    """Load streams + webcams + presets and validate cross-references."""
    global _origin, _registry, _presets

    origin, security = _load_security_streams()
    webcams = _load_webcams()

    registry = {}
    for cam in security + webcams:
        registry[cam["id"]] = cam

    presets = _load_presets(registry)

    _origin = origin.rstrip("/")
    _registry = registry
    _presets = presets

    logger.info(
        "Cameras loaded: %d security, %d webcams, %d presets",
        len(security),
        len(webcams),
        len(presets),
    )
    return presets


def get_origin():
    return _origin


def get_presets():
    return _presets


def get_preset(key):
    for preset in _presets:
        if preset["key"] == key:
            return preset
    return None
