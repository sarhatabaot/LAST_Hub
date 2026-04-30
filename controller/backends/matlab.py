from .base import ControllerBackend


class MatlabBackend(ControllerBackend):
    """Placeholder for the real backend. The plan (see CONTROLLER_REFERENCE.md)
    is to start one `matlab.engine` session at boot, hold the engine handle
    for the process lifetime, and dispatch every command through
    ``eng.eval("S.send(...)")`` etc. Not implemented yet — pick
    CONTROLLER_BACKEND=mock until the engine integration lands."""

    name = "matlab"

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "MatlabBackend is not implemented yet. "
            "Set CONTROLLER_BACKEND=mock for development."
        )

    def status(self): raise NotImplementedError
    def query(self, command, units=None): raise NotImplementedError
    def send(self, command, units=None): raise NotImplementedError
    def query_callback(self, command, units=None): raise NotImplementedError
    def send_callback(self, command, units=None): raise NotImplementedError
    def abort(self, units=None): raise NotImplementedError
    def open_observatory(self, units=None): raise NotImplementedError
    def close_observatory(self, units=None): raise NotImplementedError
