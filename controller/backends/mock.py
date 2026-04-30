import time
from threading import RLock

from .base import ControllerBackend


class MockBackend(ControllerBackend):
    """In-memory pretend superunit. Useful for developing the UI and the
    HTTP surface without a MATLAB licence."""

    name = "mock"

    def __init__(self, n_units=4, settle_seconds=0.05):
        self._lock = RLock()
        self._n = max(1, int(n_units))
        self._settle = float(settle_seconds)
        self._general_status = ["disconnected"] * self._n
        self._executing = [""] * self._n
        self._abort = [False] * self._n

    def _resolve(self, units):
        if not units:
            return list(range(self._n))
        resolved = []
        for u in units:
            try:
                idx = int(u) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= idx < self._n:
                resolved.append(idx)
        return resolved

    def status(self):
        with self._lock:
            return {
                "units": list(range(1, self._n + 1)),
                "general_status": list(self._general_status),
                "command_executing": list(self._executing),
                "abort_activity": list(self._abort),
            }

    def query(self, command, units=None):
        idx = self._resolve(units)
        return [f"<mock query: {command}>" for _ in idx]

    def send(self, command, units=None):
        with self._lock:
            for i in self._resolve(units):
                if not self._executing[i]:
                    self._executing[i] = command

    def query_callback(self, command, units=None):
        return self.query(command, units)

    def send_callback(self, command, units=None):
        with self._lock:
            for i in self._resolve(units):
                self._executing[i] = command

    def abort(self, units=None):
        with self._lock:
            resolved = self._resolve(units)
            for i in resolved:
                self._abort[i] = True
                self._executing[i] = ""
            return [self._abort[i] for i in resolved]

    def open_observatory(self, units=None):
        indices = self._resolve(units)
        with self._lock:
            for i in indices:
                self._general_status[i] = "powering up..."
                self._executing[i] = "Unit.operateUnit"
                self._abort[i] = False
        time.sleep(self._settle)
        with self._lock:
            for i in indices:
                self._general_status[i] = "initialized"
                self._executing[i] = ""

    def close_observatory(self, units=None):
        indices = self._resolve(units)
        with self._lock:
            for i in indices:
                self._general_status[i] = "shutting down..."
                self._executing[i] = "Unit.shutdown"
        time.sleep(self._settle)
        with self._lock:
            for i in indices:
                self._general_status[i] = "disconnected"
                self._executing[i] = ""
