"""Process-local controller service.

Holds the singleton backend instance, the single-writer lock, and a small
in-memory event log so the UI can show "what's running now". When the
controller is split into its own process later, the lock graduates to Redis
without changing the dispatch shape — see CONTROLLER_REFERENCE.md.
"""
import threading
import time
from collections import deque
from datetime import datetime, timezone

from django.conf import settings

from .backends.base import ControllerBackend
from .backends.mock import MockBackend


_LOCK = threading.RLock()
_BACKEND_LOCK = threading.Lock()
_BACKEND = None
_EVENTS = deque(maxlen=200)


def _make_backend():
    name = getattr(settings, "CONTROLLER_BACKEND", "mock").strip().lower()
    if name == "mock":
        n = int(getattr(settings, "CONTROLLER_MOCK_UNITS", 4))
        return MockBackend(n_units=n)
    if name == "matlab":
        from .backends.matlab import MatlabBackend
        return MatlabBackend()
    raise ValueError(f"Unknown CONTROLLER_BACKEND={name!r}")


def get_backend() -> ControllerBackend:
    global _BACKEND
    if _BACKEND is None:
        with _BACKEND_LOCK:
            if _BACKEND is None:
                _BACKEND = _make_backend()
    return _BACKEND


def reset_backend_for_testing():
    """Drop the cached backend so the next get_backend() rebuilds it."""
    global _BACKEND
    with _BACKEND_LOCK:
        _BACKEND = None
    _EVENTS.clear()


def emit(kind, message, **extra):
    _EVENTS.appendleft({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "message": message,
        **extra,
    })


def recent_events(limit=50):
    return list(_EVENTS)[: max(0, int(limit))]


def dispatch(label, fn, *args, **kwargs):
    """Run a backend call under the single-writer lock with event logging.

    All client-visible commands go through here so the event log is the
    audit trail of every command the controller has issued.
    """
    emit("dispatch", label)
    started = time.monotonic()
    with _LOCK:
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            emit("error", f"{label}: {exc}")
            raise
    emit("ok", f"{label} ({time.monotonic() - started:.2f}s)")
    return result
