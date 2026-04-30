from abc import ABC, abstractmethod


class ControllerBackend(ABC):
    """The thing that actually talks to (or pretends to talk to) the
    superunit MATLAB session. Mirrors the dispatch primitives described in
    CONTROLLER_REFERENCE.md plus a couple of high-level shortcuts.

    Implementations must be safe to call from a single thread at a time;
    the controller service serialises calls behind a process-wide lock.
    """

    name = "base"

    @abstractmethod
    def status(self):
        """Return a dict with at least:
          - general_status: list[str], one per unit (Unit.GeneralStatus)
          - command_executing: list[str], one per unit (S.commandExecuting)
          - abort_activity: list[bool], one per unit (Unit.AbortActivity)
          - units: list[int], 1-based unit ids
        """

    @abstractmethod
    def query(self, command, units=None):
        """Messenger query — wait for a reply. Returns a list, one per unit."""

    @abstractmethod
    def send(self, command, units=None):
        """Messenger send — fire-and-forget; refuses if a unit is busy."""

    @abstractmethod
    def query_callback(self, command, units=None):
        """Responder query — works mid-exposure. Returns a list."""

    @abstractmethod
    def send_callback(self, command, units=None):
        """Responder send — works mid-exposure. No reply."""

    @abstractmethod
    def abort(self, units=None):
        """Set the abort flag on each unit (Responder)."""

    @abstractmethod
    def open_observatory(self, units=None):
        """High-level open on the requested units (None = all). Mapped to
        Unit.connect / operateUnit on the real backend."""

    @abstractmethod
    def close_observatory(self, units=None):
        """High-level close on the requested units (None = all). Mapped to
        Unit.shutdown on the real backend."""
