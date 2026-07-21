# UAV Infrastructure — Architecture (Stage 1)

This documents the system **as implemented**, not as originally planned. A few
things changed from the initial sketch in `../drone-infra-spec.md` after
hands-on testing surfaced real problems — those changes and the reasons
behind them are called out explicitly below, since they're as instructive as
the final design itself.

## System diagram

```
ArduPilot SITL (container)
      |  pymavlink over UDP
      |  SITL connects OUT: --out=udpout:drone_backend:14550
      v
drone_backend.py (container)
  binds udpin:0.0.0.0:14550        <- the only pymavlink speaker in the stack
      |
      |  MQTT publish/subscribe (paho-mqtt)
      v
Mosquitto broker (container, port 1883 published to host)
      |
      |  MQTT subscribe (paho-mqtt)
      v
matplotlib_view.py (host process, your own Python venv)
  -- and any other frontend built against the same topics --
```

Everything above the broker runs in Docker, on one Compose network. Only
MQTT (a published TCP port) crosses the host/container boundary — nothing
else needs to.

## Why this shape

**One pymavlink speaker.** `drone_backend.py` is the only thing that talks
pymavlink. Every frontend — `matplotlib_view.py`, `scripts/test_flight.py`,
anything built later — is purely an MQTT client. This means multiple
students/teams can build multiple frontends against one documented contract,
and swapping matplotlib for a real GUI later requires zero backend changes.

**Why `drone_backend.py` is containerized, not host-side.** The original
plan had SITL in Docker but the Python backend running on the host, talking
to SITL over a host↔container UDP link. That link turned out to be a real
risk: MAVProxy's `--out` is a client-mode send (`udpout`), pymavlink's bare
`udp:` prefix has had shifting bind/connect semantics across versions, and
Docker Desktop vs. native Linux/WSL2 disagree about `host.docker.internal`.
Putting `drone_backend.py` in the same Compose network as SITL sidesteps all
of it: `drone_backend` binds `udpin:0.0.0.0:14550` (listens), SITL is
launched with `--out=udpout:drone_backend:14550` (connects out to it by
Compose's built-in service-name DNS), and no port needs to be published for
that link at all. Only MQTT — the well-trodden, unambiguous TCP case — ever
crosses the host boundary.

**LLA canonical, ENU local and throwaway.** See [Coordinate frame
policy](#coordinate-frame-policy) below.

**Docker for infrastructure, not for the code you're editing.** SITL and the
broker are containerized because they're infrastructure nobody needs to
touch, version-pinned so "does this work" reduces to "does Docker run."
`drone_backend.py`'s source is bind-mounted into its container
(`docker compose restart drone_backend` picks up edits — no image rebuild
unless `requirements.txt` changes), and `matplotlib_view.py` runs on the host
entirely. Neither gets a rebuild-and-restart cycle added to routine editing.

## Components

### 1. Mosquitto broker

`eclipse-mosquitto:2`, port `1883` published to the host. Mounts
`docker/mosquitto.conf`:

```
listener 1883
allow_anonymous true
```

Needed explicitly — the image's default config does not enable anonymous
listeners on 2.x, so without this, every connection fails with "not
authorised." Dev-only and insecure by design (no auth, no TLS); fine for
local/course use, not for anything internet-reachable.

### 2. ArduPilot SITL

`docker/Dockerfile.sitl` builds from `ardupilot/ardupilot-dev-base:v0.2.0`
(has the waf/build toolchain already set up for root-context builds — avoids
fighting `install-prereqs-ubuntu.sh`'s non-root assumptions), installs
MAVProxy via pip (the base image has the toolchain but not MAVProxy itself),
then clones ArduPilot pinned to a tag and builds:

```dockerfile
ARG ARDUPILOT_TAG=Copter-4.6.3
RUN git clone --recurse-submodules --shallow-submodules --depth 1 \
        --branch ${ARDUPILOT_TAG} https://github.com/ArduPilot/ardupilot.git . \
    && ./waf configure --board sitl && ./waf copter
```

The compose service runs:

```
./Tools/autotest/sim_vehicle.py -v ArduCopter --no-rebuild -w
  --custom-location=${SITL_LOCATION:--35.363261,149.165230,584,353}
  --out=udpout:drone_backend:14550
```

`--custom-location` (lat,lon,alt,heading) defaults to the Notre Dame area
via `.env`, overriding ArduPilot's own default (CMAC, Canberra). `tty: true`
and `stdin_open: true` are set so `docker compose attach sitl` gives access
to MAVProxy's plain command prompt for manual arm/mode testing — no
`--console`/`--map` GUI, so no X11 forwarding needed. **Detach with
`Ctrl-p Ctrl-q`, never `Ctrl-C`** — since you're attached to the container's
actual foreground process, `Ctrl-C` sends SIGINT straight to MAVProxy/SITL
and kills the simulation.

The image is `linux/amd64` only (`ardupilot-dev-base` has no arm64 build).
On Apple Silicon it runs under Docker Desktop's Rosetta-accelerated
emulation — see `SETUP.md` for the one-time setting.

### 3. `drone_backend.py`

Containerized (`docker/Dockerfile.backend`, thin `python:3.12-slim`, source
bind-mounted so edits apply on `docker compose restart drone_backend`
without a rebuild). Binds `udpin:0.0.0.0:14550` and listens for SITL.

A **single** reader thread (`mavlink_reader`) handles everything read from
the connection: `HEARTBEAT` → armed/mode, `GLOBAL_POSITION_INT` →
lat/lon/alt_rel/heading, `VFR_HUD` → groundspeed, `SYS_STATUS` → battery,
and `HOME_POSITION` capture. This is deliberate, not incidental — an earlier
version used two threads (one blocking on `HOME_POSITION` before starting
telemetry, one reading everything else), both calling `pymavlink`'s
`recv_match` on the same connection. That's a real race (two threads reading
off one socket's parser state) and it also meant telemetry couldn't start
publishing until home capture finished. The fix was folding both into one
loop: `HOME_POSITION` is requested once, re-requested every 5s until
captured (UDP can drop the first request), and telemetry publishing never
waits on it.

Command handling (`handle_command`) is mostly a raw MAVLink passthrough,
with one deliberate exception: **`takeoff` and `goto` both call
`conn.set_mode("GUIDED")` (and `takeoff` also arms) before issuing their
real command.** ArduCopter silently rejects `NAV_TAKEOFF` and
`SET_POSITION_TARGET_GLOBAL_INT` outside GUIDED mode — this was a real bug
found by testing `takeoff` over MQTT and watching it fail, tracing it to a
missing mode switch that had been happening by accident via manual MAVProxy
console use during earlier testing. Fixing it in the backend means the MQTT
command channel is fully self-sufficient — no frontend needs its own
mode-switching logic.

The actual `arm`/`disarm`/`takeoff`/`goto`/`land` MAVLink calls (including
the GUIDED-mode dance above) live in `backend/mavlink_lib.py`, not inline in
`handle_command` — `scripts/simple_flight.py` (a no-MQTT, direct-pymavlink
teaching script; see its own docstring) fires the same command vocabulary,
so the build-and-send logic is shared rather than duplicated. `mavlink_lib.py`
is bind-mounted into the container the same way `drone_backend.py` is.
Only *waiting/polling* for a command's effect stays separate per caller —
`drone_backend.py` has no such concept (it fires commands as MQTT messages
arrive), while `simple_flight.py` has its own local resend/poll loop.

The initial `mqtt_client.connect()` is wrapped in a bounded retry loop
(`connect_mqtt_with_retry`, 30s timeout). Compose's `depends_on` only orders
container *starts*, not readiness, so all three containers starting
simultaneously can hit a transient DNS resolution race on cold start — this
crashed the backend once during testing before the retry loop was added.

Config via environment variables, not hardcoded: `VEHICLE_ID` (default
`"1"`), `MAVLINK_CONN`, `MQTT_HOST`, `MQTT_PORT`, `TELEMETRY_HZ` (default 4).

### 4. `matplotlib_view.py`

Runs on the host, in its own venv (`client/requirements.txt`: `paho-mqtt` +
`matplotlib` — no `pymavlink` needed here at all, since the backend is
containerized). Subscribes to `uav/<id>/home` (retained) and
`uav/<id>/telemetry`.

- **Layout**: two panels side by side — a position plot (East/North) and a
  current-altitude gauge (a thick horizontal line at the current value, not
  a filled bar from ground level).
- **View**: always centered on home `(0,0)`, showing at least ±20m in every
  direction (`MIN_HALF_SPAN_M`), growing only if the vehicle actually flies
  further. Without this floor, `autoscale_view()` fits tightly to whatever
  data is present — including a few centimeters of GPS/EKF noise while
  sitting still, which visually blows up into what looks like a wild flight.
- **Trail**: a short (`TRAIL_LENGTH = 20`, ~5s at 4Hz) rolling window, so it
  reads as a comet-tail trailing the vehicle rather than the whole mission's
  path slowly aging out over a full minute.
- **Marker**: an isosceles triangle (`heading_triangle()`) that rotates to
  match the compass `heading` field — replaced an earlier circle+quiver-arrow
  combination. Colored via a single `DRONE_COLOR` constant, shared with the
  trail and the altitude gauge, so a future second vehicle (Stage 6) reads as
  a distinct color across its whole visual signature, not just its marker.
- **Rendering loop**: a plain `plt.show(block=False)` + `plt.pause(0.2)`
  loop, **not** `matplotlib.animation.FuncAnimation`. `FuncAnimation`'s
  internal timer was found not to reliably force a screen redraw under this
  project's WSLg/Tk test environment — the underlying data was updating
  correctly (confirmed by instrumenting and watching it trace a full flight
  path), the window just never repainted. `plt.pause()` explicitly drives
  the GUI event loop and is the more portable fix across backends and
  remote/virtual displays.

## The MQTT contract

| Topic | Direction | Retained? | Purpose |
|---|---|---|---|
| `uav/<id>/telemetry` | backend → clients | no | Full vehicle state, published at `TELEMETRY_HZ` |
| `uav/<id>/command` | clients → backend | no | Arm/disarm/takeoff/goto/land requests |
| `uav/<id>/home` | backend → clients | **yes** | Shared local-frame origin, published once |

```json
// uav/1/telemetry
{
  "vehicle_id": "1", "timestamp": 1737000000.123,
  "lat": 41.700, "lon": -86.239, "alt_rel": 12.4, "heading": 87.3,
  "groundspeed": 3.2, "battery_voltage": 12.1,
  "armed": true, "mode": "GUIDED"
}
```

```json
// uav/1/command -- one of:
{"type": "arm"}
{"type": "disarm"}
{"type": "takeoff", "alt": 10}
{"type": "goto", "lat": 41.701, "lon": -86.238, "alt": 10}
{"type": "land"}
```

```json
// uav/1/home (retained)
{"vehicle_id": "1", "lat": 41.700, "lon": -86.239, "alt": 225.1}
```

Malformed JSON or unknown command types are logged and ignored — the backend
never crashes on bad input. This is "trust but verify" applied to its own
system boundary, the same principle that applies to AI-generated code.

## Coordinate frame policy

**LLA (lat/lon/alt) is the only frame that ever crosses a system boundary.**
It matches how MAVLink represents position natively and keeps the contract
stable as more clients join.

**Local frames (ENU) are private, per-client, throwaway math.** The
equirectangular conversion in `matplotlib_view.py`'s `lla_to_enu()` exists
only so that one plot can show legible metre-scale movement — raw lat/lon
degrees make normal movement nearly invisible at readable zoom. It is never
published back to MQTT and never treated as shared truth. Two clients
quietly disagreeing about where local `(0,0)` is produces a bug class that's
miserable to debug: correct in one view, subtly wrong in another.

The retained `uav/<id>/home` topic is what prevents that — every local-frame
client converts against the same origin, delivered immediately even to
clients that subscribe late (that's what MQTT's retained-message flag is
for).

## Version pinning

- ArduPilot: `Copter-4.6.3`, built from source, pushed to
  `ghcr.io/janeclelandhuang/uav-course-sitl:copter-4.6.3` (public) so
  students `docker compose pull` instead of a 10-20 minute source build.
- `backend/requirements.txt`: `pymavlink==2.4.41`, `paho-mqtt==2.1.0`.
- `client/requirements.txt`: `paho-mqtt==2.1.0`, `matplotlib==3.9.2`.

Bumping the ArduPilot version for a later course run: re-run
`scripts/build_and_push_sitl.sh <new-tag>` and update `SITL_IMAGE` in
`.env` — nothing else in the repo needs to change.

## Configuration (`.env`)

| Variable | Default | Controls |
|---|---|---|
| `SITL_IMAGE` | `uav-course-sitl:copter-4.6.3` (local build tag) | Which SITL image `docker compose` pulls/runs |
| `VEHICLE_ID` | `1` | MQTT topic prefix (`uav/<id>/...`); Stage 6 bumps this for a second vehicle |
| `SITL_LOCATION` | Notre Dame area | SITL start location: `lat,lon,alt(m),heading(deg)` |

## Scripts

- **`scripts/verify_setup.py`** — one-command health check: Docker
  installed/running, `docker compose up`, telemetry flowing, arm-command
  round-trip. Plain-English PASS or a specific failure + remediation line,
  never a raw stack trace.
- **`scripts/disarm.sh`** — publishes `{"type":"disarm"}`; a documented
  one-liner for leaving the simulator safe after manual testing.
- **`scripts/test_flight.py`** — scripted arm → takeoff → small square →
  land, entirely over the MQTT contract (exactly what a student frontend
  would do). Each command re-publishes every 8s until its telemetry-based
  success condition is met, which makes it self-heal against a dropped UDP
  command or the same cold-start pre-arm-check flakiness `verify_setup.py`
  documents.
- **`scripts/build_and_push_sitl.sh`** — instructor-only: builds the pinned
  SITL image and pushes it to GHCR. Lowercases both the ArduPilot tag *and*
  the GHCR owner name before building — Docker repository paths must be
  lowercase, and GitHub usernames/orgs commonly aren't.

## Known quirks worth knowing

- **`mode` doesn't reset after landing.** ArduCopter leaves `mode: "LAND"`
  reported indefinitely after touchdown+disarm — it only changes on the next
  explicit mode switch. Don't treat `mode == "LAND"` alone as "currently
  landing"; check `armed` too if that distinction matters.
- **Pre-arm checks can reject arm/takeoff for 30-60s after a cold SITL
  boot** (EKF/GPS not settled yet, or "Gyros inconsistent"). Expected, not a
  bug — `verify_setup.py` and `test_flight.py` both handle it via bounded
  retries/resends rather than failing immediately.
- **`DISARM_DELAY`** (~10s) auto-disarms an armed-but-idle vehicle. Relevant
  mainly when testing manually via the MAVProxy console — arm and issue your
  next command in one quick burst, or it disarms out from under you.

## Repo layout

```
uav-course-infra/
  docker-compose.yml
  .env / .env.example
  ARCHITECTURE.md          <- this file
  SETUP.md                 <- per-OS install notes, troubleshooting index
  docker/
    Dockerfile.sitl
    Dockerfile.backend
    mosquitto.conf
  backend/
    drone_backend.py
    requirements.txt
  client/
    matplotlib_view.py
    requirements.txt
  scripts/
    verify_setup.py
    disarm.sh
    test_flight.py
    build_and_push_sitl.sh
```

## Not yet in scope (future stages)

- Stage 2: tile-based map / `new-gui.py`
- Stage 3: click-to-goto
- Stage 4: mission upload / geofence
- Stage 5: log replay
- Stage 6: multi-vehicle — `VEHICLE_ID` and `DRONE_COLOR` are already
  structured with this in mind (per-vehicle topic prefix, per-vehicle color
  scheme), but nothing runs two vehicles concurrently yet.
