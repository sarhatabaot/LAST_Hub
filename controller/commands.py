"""Catalog of MATLAB commands the controller will accept.

Anything whose base identifier isn't listed here is rejected. The base is
everything up to the first ``(``, so ``Unit.takeExposure([1 2],10,5)``
matches the catalog entry ``Unit.takeExposure``.

Each entry's ``channel`` and ``wait`` are the natural dispatch defaults —
the ones you'd pick if the only thing you knew was the command name.
``args`` is metadata for the UI's Brigadier-style completer; the server
only validates membership, not arity.

See CONTROLLER_REFERENCE.md for the channel-selection rules.
"""

# channel: "messenger" (long, interruptible) | "responder" (fast, mid-exposure-safe)
# wait:    True (query, returns a value) | False (send/sendCallback, no reply)
# args:    list of {name, summary, example, suggestions?} — UI hints only.
COMMAND_CATALOG = [
    # Lifecycle / orchestration -- long, blocking.
    {"base": "Unit.connect",              "channel": "messenger", "wait": False, "summary": "Connect hardware", "args": []},
    {"base": "Unit.disconnect",           "channel": "messenger", "wait": False, "summary": "Disconnect hardware", "args": []},
    {"base": "Unit.shutdown",             "channel": "messenger", "wait": False, "summary": "Shutdown sequence", "args": []},
    {"base": "Unit.operateUnit",          "channel": "messenger", "wait": False, "summary": "Connect + flats + focus", "args": []},
    {"base": "Unit.nightRun",             "channel": "messenger", "wait": False, "summary": "operateUnit + observeAskingTargets", "args": []},
    {"base": "Unit.observeAskingTargets", "channel": "messenger", "wait": False, "summary": "Scheduler-fed observing loop", "args": []},
    {"base": "Unit.takeExposure",         "channel": "messenger", "wait": False, "summary": "takeExposure(cams, expTime, N, ...)", "args": [
        {"name": "cams",    "summary": "Camera indices",          "example": "[1 2 3 4]"},
        {"name": "expTime", "summary": "Exposure time (seconds)", "example": "10"},
        {"name": "N",       "summary": "Number of exposures",     "example": "5"},
    ]},
    {"base": "Unit.takeDarks",            "channel": "messenger", "wait": False, "summary": "takeDarks(expTime, N, ...)", "args": [
        {"name": "expTime", "summary": "Exposure time (seconds)", "example": "10"},
        {"name": "N",       "summary": "Number of darks",         "example": "5"},
    ]},
    {"base": "Unit.takeTwilightFlats",    "channel": "messenger", "wait": False, "summary": "takeTwilightFlats(...)", "args": []},
    {"base": "Unit.focusTel3",            "channel": "messenger", "wait": False, "summary": "focusTel3(itel, ...) — adaptive focus", "args": [
        {"name": "itel", "summary": "Telescope index (1-4)", "example": "1", "suggestions": ["1", "2", "3", "4"]},
    ]},
    {"base": "Unit.acquirePointingModel", "channel": "messenger", "wait": False, "summary": "acquirePointingModel(...)", "args": []},

    # State / readiness -- fast queries.
    {"base": "Unit.GeneralStatus", "channel": "responder", "wait": True, "summary": "Current status string", "args": []},
    {"base": "Unit.AbortActivity", "channel": "responder", "wait": True, "summary": "Abort flag (logical)", "args": []},
    {"base": "Unit.MountPower",    "channel": "responder", "wait": True, "summary": "Mount power state", "args": []},
    {"base": "Unit.CameraPower",   "channel": "responder", "wait": True, "summary": "Camera power state", "args": []},
    {"base": "Unit.Temperature",   "channel": "responder", "wait": True, "summary": "Camera temperatures", "args": []},
    {"base": "Unit.readyToExpose", "channel": "responder", "wait": True, "summary": "[Ready, Status] readyToExpose(...)", "args": []},
    {"base": "Unit.fullStatus",    "channel": "responder", "wait": True, "summary": "[Operable, Status, Failures] fullStatus(...)", "args": []},
    {"base": "Unit.isConnected",   "channel": "responder", "wait": True, "summary": "Connection state", "args": []},
    {"base": "Unit.checkWholeUnit","channel": "responder", "wait": True, "summary": "Full self-check", "args": []},
    {"base": "Unit.checkMount",    "channel": "responder", "wait": True, "summary": "Mount self-check", "args": []},
    {"base": "Unit.checkCamera",   "channel": "responder", "wait": True, "summary": "Camera self-check", "args": []},
    {"base": "Unit.checkFocuser",  "channel": "responder", "wait": True, "summary": "Focuser self-check", "args": []},
    {"base": "Unit.checkSwitches", "channel": "responder", "wait": True, "summary": "Power-switch self-check", "args": []},

    # Recovery -- responder so it works on busy sessions.
    {"base": "Unit.abort",           "channel": "responder", "wait": False, "summary": "Set abort flag", "args": []},
    {"base": "Unit.reconnectCamera", "channel": "responder", "wait": False, "summary": "reconnectCamera(camnum, power, recreate)", "args": [
        {"name": "camnum",   "summary": "Camera number (1-4)",         "example": "1",    "suggestions": ["1", "2", "3", "4"]},
        {"name": "power",    "summary": "Power-cycle the camera",      "example": "true", "suggestions": ["true", "false"]},
        {"name": "recreate", "summary": "Recreate the camera object",  "example": "true", "suggestions": ["true", "false"]},
    ]},

    # Hardware setup -- idempotent prep.
    {"base": "Unit.setCameraTemperature", "channel": "messenger", "wait": False, "summary": "setCameraTemperature(itel)", "args": [
        {"name": "itel", "summary": "Telescope index (1-4)", "example": "1", "suggestions": ["1", "2", "3", "4"]},
    ]},
    {"base": "Unit.setNominalFocuserPos", "channel": "messenger", "wait": False, "summary": "setNominalFocuserPos(itel)", "args": [
        {"name": "itel", "summary": "Telescope index (1-4)", "example": "1", "suggestions": ["1", "2", "3", "4"]},
    ]},
]


_BY_BASE = {entry["base"]: entry for entry in COMMAND_CATALOG}


def parse_base(command):
    """Return the dotted identifier prefix of a MATLAB command string.

    ``Unit.takeExposure([1 2],10,5)`` -> ``Unit.takeExposure``
    ``Unit.GeneralStatus;``           -> ``Unit.GeneralStatus``
    """
    if not isinstance(command, str):
        return ""
    text = command.strip().rstrip(";").strip()
    paren = text.find("(")
    if paren >= 0:
        text = text[:paren]
    return text.strip()


def get_spec(command):
    return _BY_BASE.get(parse_base(command))


def is_allowed(command):
    return parse_base(command) in _BY_BASE
