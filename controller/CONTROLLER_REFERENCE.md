# `superunit` Controller Reference

A reference for building a controller (CLI, web, etc.) on top of `obs.superunit`.
Covers the orchestration model, the dispatch primitives, and the vocabulary of
remote commands the controller will send.

## Conceptual model

A `superunit` is a **local orchestrator object**. It does not contain hardware.
It owns a fleet of `obs.util.SpawnedMatlab` sessions — one per host listed in
`UnitHosts` — and each spawned MATLAB session contains a `unitCS` object
conventionally named `Unit`. The superunit's job is to push command *strings*
to those sessions and, optionally, collect results.

```
controller (CLI/web)  →  superunit (local MATLAB)  →  RemoteUnits(i)  →  Unit  (unitCS on lastNN)
                                                                          │
                                                                          ├── Mount, Camera{}, Focuser{}, PowerSwitch{}
                                                                          └── Slave(j) (more spawned MATLABs per camera group)
```

Two transport channels exist between superunit and each remote `Unit`:

- **Messenger** — a *Listener* on the remote side. Used for long, interruptible
  work (`takeExposure`, `focusTel3`, etc.). The remote can be aborted because
  it polls `Unit.AbortActivity`.
- **Responder** — always runs in a callback. Used for fast, uninterruptible
  queries/pokes (status, abort flag, GeneralStatus). A Responder query is the
  only way to talk to a session whose Messenger is currently busy.

That distinction drives every dispatch method below.

## Properties (configuration surface)

Set these *before* calling `connect`/`spawn`. Most are pushed down to every
`RemoteUnits(i)` automatically by setters at
[superunit.m:48-96](superunit.m#L48-L96).

| Property | Type | Notes |
|---|---|---|
| `Id` | char | Optional id, defaults from constructor arg |
| `UnitHosts` | cell of char | E.g. `{'last01w','last02w'}`. Setting this builds `RemoteUnits`. |
| `UnitTerminal` | char | `xterm` / `gnome-terminal` / `desktop` / `silentx` / `none`. Validated by `validTermType`. |
| `SlaveTerminals` | char | Same options, applied to slaves spawned *inside* each unit. |
| `RemoteUnits` | array of `obs.util.SpawnedMatlab` | One per host. Built by `set.UnitHosts`. |
| `Logging` | logical | Must set BEFORE connect. Propagates to all RemoteUnits. |
| `LoggingDir` | char | Must set BEFORE connect. |

## Lifecycle methods

All four take an optional `units` numeric index vector. Empty/missing = all.

### `spawn(S, units)` — [superunit.m:102](superunit.m#L102)

Launches a fresh MATLAB on each host, then connects, then sends
`Unit=obs.unitCS('NN');` and queues a slave-terminal config command.
**No return value.** Errors are caught and reported via `S.reportError`. Use
this when sessions don't already exist.

### `res = connect(S, units)` — [superunit.m:134](superunit.m#L134)

Reconnects to *already-spawned* remote sessions (e.g. after the controller
restarts but the MATLABs are still alive). Also turns on
`MasterMessenger.PushPropertyChanges=true` so status updates flow back.
**Returns:** logical vector `res`, one per requested unit.

### `disconnect(S, units)` — [superunit.m:149](superunit.m#L149)

Drops the local Messenger/Responder handles. **Hardware stays on**, remote
MATLABs keep running. Another client can pick them up. No return value.

### `terminate(S, units)` — [superunit.m:159](superunit.m#L159)

Kills the remote MATLAB sessions. Destructive — use sparingly.

## Command dispatch (the core of your controller)

Pick the method by answering two questions: *do I need a reply?* and *is the
remote possibly busy?*

| Method | Channel | Waits for reply? | Refuses if busy? | Use when |
|---|---|---|---|---|
| `res = query(S, command, units)` | Messenger | yes (serial) | no (will block) | Reading values when remote is idle |
| `send(S, command, units)` | Messenger | no | **yes** (skips & warns) | Fire-and-forget long commands |
| `sendEnqueue(S, command, units)` | Messenger | no | no (queues in UDP buffer — fragile) | Force-queue follow-up commands |
| `res = queryCallback(S, command, units)` | Responder | yes (serial) | no (Responder is independent) | Status checks even mid-exposure |
| `sendCallback(S, command, units)` | Responder | no | no | Setting flags (e.g. abort) on a busy unit |

`command` is always a **char array of MATLAB code** evaluated in the remote
workspace, e.g. `'Unit.takeExposure([1 2],10,5)'` or `'Unit.Mount.RA'`.

`units` is empty (= all) or a numeric index vector into `RemoteUnits`.

**Return shape:** `query` and `queryCallback` return a `1×N cell`, one entry
per unit, holding whatever the evaluated expression returned (or empty on
error). The other three return nothing.

[superunit.m:167-287](superunit.m#L167-L287) has the full bodies; note the
busy-check in `send` at [superunit.m:199](superunit.m#L199) — it calls
`commandExecuting` and silently refuses if the unit is mid-command.

### `cexec = commandExecuting(S, units)` — [superunit.m:289](superunit.m#L289)

Cell array of currently-executing command strings (one per unit). Empty cell
entry = unit is free for a Messenger command. **Note:** "free for Messenger"
doesn't guarantee the Responder is free — Responder commands are
uninterruptible.

### `success = abortActivity(S, units)` — [superunit.m:305](superunit.m#L305)

Sends `Unit.abort;` over the Responder, then queries `Unit.AbortActivity`.
Returns the cell of bools (true = abort flag is set on remote). The remote
must be running code that periodically checks `Unit.AbortActivity` for the
abort to take effect.

### `success = connectResponders(S, units)` — [superunit.m:323](superunit.m#L323)

Last-resort: rebuild only the Responder when the Messenger is hopelessly
stuck. Returns logical array.

## Static helpers

- `id = superunit.hostUnitId(address)` — extracts the integer unit id from
  `lastNN` or `10.23.x.x`. Returns 0 as fallback.
- `valid = superunit.validTermType(termtype)` — coerces user input to one of
  the five legal terminal types.

## Domain helper

- `plotFocusData(S, units)` — pulls `Unit.FocusData` from the per-host
  **Redis cache** (port 6379, key `unitCS.set.FocusData:NN`) and plots it.
  Useful as a template: there's a side channel (Redis) for harvesting state
  without sending callbacks. See [plotFocusData.m](plotFocusData.m).

## What you'll typically send through `send` / `query`

Your controller's "actions" are mostly thin wrappers that build a command
string and pick the right dispatch method. The vocabulary on the remote side
comes from the `unitCS` methods in [../@unitCS/](../@unitCS/):

**High-level orchestration (long, blocking — use `send`):**

- `Unit.connect` / `Unit.disconnect` / `Unit.shutdown`
- `Unit.operateUnit(...)` — connect + flats + focus
- `Unit.nightRun(...)` — wraps operateUnit + observeAskingTargets
- `Unit.observeAskingTargets(...)` — runs a scheduler-fed observing loop
- `Unit.takeExposure(cams, expTime, N, ...)`, `Unit.takeDarks(...)`, `Unit.takeTwilightFlats(...)`
- `Unit.focusTel3(itel, ...)` — adaptive focus
- `Unit.acquirePointingModel(...)`

**State / readiness (fast — use `query` if idle, `queryCallback` if not sure):**

- `Unit.GeneralStatus` (string: `"disconnected"`, `"initialized"`, `"powering up..."`, `"shutting down..."`, etc.)
- `Unit.AbortActivity` (logical)
- `Unit.MountPower`, `Unit.CameraPower`, `Unit.Temperature`
- `Unit.readyToExpose(...)` → `[Ready, Status]`
- `Unit.fullStatus(...)` → `[OperableComponents, ComponentStatus, FailureReasons]`
- `Unit.isConnected` → logical
- `Unit.checkWholeUnit / checkMount / checkCamera / checkFocuser / checkSwitches` (all return `[ok, remedy, ...]`)

**Recovery (use `sendCallback` so it works on busy sessions):**

- `Unit.abort;` (already wrapped by `abortActivity`)
- `Unit.reconnectCamera(camnum, power, recreate)`

**Hardware setup (idempotent, run before observation):**

- `Unit.setCameraTemperature(itel)`
- `Unit.setNominalFocuserPos(itel)`

The `arguments` blocks at the top of each `.m` file in `@unitCS` give you the
exact parameter names/defaults — that's your controller's API surface.

## Suggested controller patterns

1. **Status poll loop** — every few seconds,
   `queryCallback('Unit.GeneralStatus')` and `commandExecuting()` for each
   unit. These are non-blocking even mid-exposure.
2. **Action dispatch** — for any long command, check `commandExecuting`
   first, then `send` (don't `sendEnqueue` unless you understand the
   UDP-buffer caveat at [superunit.m:222](superunit.m#L222)).
3. **Abort path** — always over `abortActivity` / `sendCallback`, never
   `send`.
4. **Recovery** — if a unit's Messenger appears dead but the Responder still
   answers, try `connectResponders`. If the Responder is also dead,
   `terminate` + `spawn`.

## Python controller architecture

The plan is to wrap the existing MATLAB workflow rather than replace it.
Today an operator runs:

```bash
matlab -nodesktop -nosplash
```

```matlab
S = obs.superunit(n)   % n comes from configuration, e.g. '1to10'
```

…and types commands at the prompt. The Python controller does exactly that,
but programmatically and behind a service.

### Bridge: MATLAB Engine for Python

A single Python service starts one MATLAB session at boot and holds the
engine handle for its lifetime:

- `eng = matlab.engine.start_matlab()`
- `eng.eval(f"S = obs.superunit('{n}');", nargout=0)` — `n` is read from
  config (file, env var, or CLI flag) with a sensible default and an
  override path.
- Every command after that is `eng.eval("S.send(...)")`,
  `eng.eval("S.query(...)")`, etc., dispatched through the same handle.

This preserves the existing model: same `superunit` object, same MATLAB
methods, same configuration files. The Python service is just a
well-behaved client at the prompt.

### Versioning

Don't pin a MATLAB version in code. Pin it at **install time** to whatever
MATLAB is on the host:

- Bundled installer: `cd $MATLABROOT/extern/engines/python && python setup.py install`
- Or pip with a matching release: `pip install matlabengine==<version-matching-installed-MATLAB>`

The service code uses the stable Engine API (`start_matlab`, `eval`,
`feval`, futures, stdout capture) that has been steady for years — that's
the "API level" the controller depends on.

### Single-writer enforcement

The MATLAB engine is the only path to the hardware, and there is exactly
**one** of it inside the service. Wrap every dispatch in an `asyncio.Lock`
(or a single-consumer command queue) so concurrent client requests are
serialized. The lock owner is the user/session that currently has control;
others see queue position or a "session in use" response. No distributed
lock needed — the bottleneck is the engine handle itself.

If HA ever becomes a requirement, the lock can be promoted to Redis
(already in use for `FocusData`) without changing the dispatch shape.

### Showing commands to users (transparency)

Centralised dispatch makes this free. Pseudocode shape:

1. Build the MATLAB command string (e.g. `"S.send('Unit.takeExposure([1 2],10,5)', 1)"`).
2. Emit it on a log/event stream (websocket, SSE, file, Redis pub/sub —
   whatever the UI consumes).
3. *Then* call `eng.eval(...)`.
4. Capture MATLAB stdout/stderr by passing `io.StringIO()` buffers to
   `eng.eval(..., stdout=..., stderr=...)` and forward them to the same
   stream.

Clients (CLI, web) subscribe to that stream to display "what's running
now" and to keep an audit trail of every command issued and by whom.

### Client topology

```text
CLI / web UI ──┐
               ├──►  Python service (asyncio + lock + event stream)  ──►  MATLAB Engine  ──►  S = obs.superunit(n)
other client ──┘
```

All clients are thin: they authenticate, request the lock if they want to
issue commands, subscribe to the event stream for visibility. Only the
service touches MATLAB.
