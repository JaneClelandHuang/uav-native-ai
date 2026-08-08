# UAV Infrastructure — Architecture (Stage 1)

This documents the system **as implemented**, not as originally planned. A few
things changed from the initial sketch in `../drone-infra-spec.md` after
hands-on testing surfaced real problems — those changes and the reasons
behind them are called out explicitly below, since they're as instructive as
the final design itself.

## System diagram

```
ArduPilot SITL x N (containers: sitl_1 .. sitl_N, N = NUM_DRONES)
      |  pymavlink over UDP, one pair per vehicle
      |  each SITL connects OUT: --out=udpout:drone_backend_N:14550
      v
drone_backend.py x N (containers: drone_backend_1 .. _N, VEHICLE_ID 1..N)
  each binds its own udpin:0.0.0.0:14550   <- own container network
  namespace per pair, so the port never collides across vehicles
      |
      |  MQTT publish/subscribe (paho-mqtt), topics prefixed uav/<id>/...
      v
Mosquitto broker (container, port 1883 published to host)
      |
      |  MQTT subscribe (paho-mqtt)
      v
matplotlib_view.py (host process, your own Python venv)
  -- shows one vehicle (VEHICLE_ID) at a time; new-gui is the multi-vehicle
  frontend, subscribing across all N --
```

Everything above the broker runs in Docker, on one Compose network. Only
MQTT (a published TCP port) crosses the host/container boundary — nothing
else needs to. Each `sitl_N`/`drone_backend_N` pair is fully independent:
no shared state or synchronization between vehicles, just N copies of the
same one-pymavlink-speaker pattern below.

**N is not fixed in `docker-compose.yml`.** That file only defines
`mosquitto` — `scripts/generate_fleet.py` writes the `sitl_N`/
`drone_backend_N` pairs into `docker-compose.override.yml` (gitignored,
regenerated on demand), which Compose auto-merges. See "Fleet generation"
below.

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
(`docker compose restart drone_backend_1` picks up edits — no image rebuild
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

Each `sitl_N` service runs the same command, parameterized per vehicle
(shown here for vehicle 1 at a single-vehicle `NUM_DRONES=1`; see "Fleet
generation" below for how `_2..N` and their `--custom-location`s are
derived):

```
./Tools/autotest/sim_vehicle.py -v ArduCopter --no-rebuild -w
  --custom-location=41.6985750,-86.2370550,225,0
  --out=udpout:drone_backend_1:14550
```

`--custom-location` (lat,lon,alt,heading) is computed by
`scripts/generate_fleet.py`, overriding ArduPilot's own default (CMAC,
Canberra). `tty: true` and `stdin_open: true` are set so `docker compose
attach sitl_1` gives access to MAVProxy's plain command prompt for manual
arm/mode testing — no
`--console`/`--map` GUI, so no X11 forwarding needed. **Detach with
`Ctrl-p Ctrl-q`, never `Ctrl-C`** — since you're attached to the container's
actual foreground process, `Ctrl-C` sends SIGINT straight to MAVProxy/SITL
and kills the simulation.

The image is `linux/amd64` only (`ardupilot-dev-base` has no arm64 build).
On Apple Silicon it runs under Docker Desktop's Rosetta-accelerated
emulation — see `SETUP.md` for the one-time setting.

### 3. `drone_backend.py`

Containerized (`docker/Dockerfile.backend`, thin `python:3.12-slim`, source
bind-mounted so edits apply on `docker compose restart drone_backend_1`
without a rebuild). Binds `udpin:0.0.0.0:14550` and listens for SITL.

A **single** reader thread (`mavlink_reader`) handles everything read from
the connection: `HEARTBEAT` → armed/mode, `GLOBAL_POSITION_INT` →
lat/lon/alt_rel/alt_amsl/heading, `VFR_HUD` → groundspeed, `SYS_STATUS` →
battery_voltage/battery_level, and `HOME_POSITION` capture. This is
deliberate, not incidental — an earlier
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

**`circle` has no ArduCopter command to hook into, so it's built from the
same primitive as `goto`.** There's no working "circle around this point"
command in this pinned firmware: ArduCopter's GUIDED mode has no circle
submode (checked directly against the `Copter-4.6.3` source — `ModeGuided`'s
only submodes are `TakeOff`/`WP`/`Pos`/`Accel`/`VelAccel`/`PosVelAccel`/
`Angle`), and `MAV_CMD_DO_ORBIT`, the more commonly documented "orbit a
point" command, isn't even present in this pinned `pymavlink==2.4.41`/
ArduPilotMega dialect. (An earlier version of this used the ArduPilot-custom
`MAV_CMD_SET_GUIDED_SUBMODE_CIRCLE` message, which *is* in the dialect but
turned out not to be handled by this firmware version either — confirmed
against source before it shipped, not assumed, but worth remembering that
"the message exists in the dialect" and "the firmware acts on it" are
different claims.)

So `circle` is built the way you'd fly one by hand: `mavlink_lib.circle_point()`
computes one lat/lon on the circle at a given compass bearing from the
center and sends it as one `SET_POSITION_TARGET_GLOBAL_INT` — the same
message `goto` sends, just recomputed as bearing advances. One call traces
one point; tracing an arc means calling it repeatedly over time.

**That timing loop lives in `drone_backend.py`, not as a new thread, but
folded into the loop `main()` already runs.** `main()`'s existing loop ticks
once per `TELEMETRY_HZ` period to publish telemetry; `circle_tick()` runs
once per that same tick, ahead of the publish. If a circle is active (an
`ActiveCircle` instance — a lock-protected dict, the same shape
`VehicleState` already uses for telemetry, not a new synchronization idiom),
it computes how many degrees have been swept from elapsed wall-clock time
(`angular_rate_deg_s = degrees(speed_mps / radius_m)`, not a fixed per-tick
step, so a late tick doesn't throw off the total), sends the next
`circle_point()`, and auto-clears itself once the requested `degrees` is
reached. A dedicated thread per active circle was the first design
considered and rejected: every vehicle already runs a reader thread plus
paho's own network thread, and a third thread type — with its own
start/cancel/join lifecycle — was judged not worth the added concurrency
surface when the existing telemetry loop already ticks at a usable rate.

**`interrupt` cancels an outstanding `goto` or `circle`.** Neither uses
ArduCopter's built-in AUTO/mission-waypoint system — both stay in GUIDED
mode, so there's no queued waypoint or mission state to clear, and no
MAVLink "cancel" message for either. For `goto`, `interrupt` alone is
enough: switching to `LOITER` takes the vehicle out of GUIDED and holds its
position. For `circle`, `interrupt` additionally has to stop `circle_tick()`
from continuing to fire new `circle_point()` calls, or they'd fight the mode
switch — so `handle_command` clears the active circle (`circle.stop()`) for
*any* incoming command that isn't itself a new `circle`, not just
`interrupt`. That also means a `goto`/`takeoff`/`land` sent mid-circle
implicitly cancels it, which is deliberate: leaving a stale circle running
underneath a new command would be a confusing bug, not a feature.

**`circle` always starts at bearing 0 (due north of center).** There's no
tracking of where the vehicle actually is relative to the center when the
command arrives, so starting anywhere else means a sudden jump onto the
circle rather than a smooth entry. `scripts/test_circle.py` handles this by
flying to the bearing-0 point itself before sending `circle`, rather than to
the center.

**`fly_home` is `goto()` against a remembered position, not a new MAVLink
primitive.** `mavlink_reader`'s `HOME_POSITION` handler already captures
lat/lon (and now `alt`, AMSL) once per boot for the retained `uav/<id>/home`
topic; `fly_home` just also stashes that lat/lon on `VehicleState`
(`home_lat`/`home_lon` — not part of the telemetry snapshot, home doesn't
change tick to tick) so `handle_command` has something to read. It transits
at `max(current alt_rel, FLY_HOME_MIN_ALT_M)` — high enough not to drag the
vehicle home skimming the ground if it was flying low, but not forcing an
unnecessary climb if it was already higher. Same as any other `goto`, this
stays in GUIDED and doesn't land on its own — `land` is a deliberate,
separate follow-up command, same pattern as after any other `goto`. If
`home_lat`/`home_lon` haven't been captured yet, the command is logged and
ignored rather than flying toward `(0, 0)`.

The actual `arm`/`disarm`/`takeoff`/`goto`/`circle_point`/`interrupt`/`land`
MAVLink calls (including the GUIDED-mode dance above) live in
`backend/mavlink_lib.py`, not inline in `handle_command` — `scripts/simple_flight.py` (a no-MQTT, direct-pymavlink
teaching script; see its own docstring) fires the same one-shot command
vocabulary (`circle`'s timing loop is MQTT-path-only, not part of
`simple_flight.py`), so the build-and-send logic is shared rather than
duplicated. `mavlink_lib.py` is bind-mounted into the container the same way
`drone_backend.py` is. Beyond `circle_tick()`, waiting/polling for a
command's effect stays separate per caller — `drone_backend.py` otherwise
fires commands as MQTT messages arrive, while `simple_flight.py` has its own
local resend/poll loop.

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
- **View**: a fixed ±50m window (`VIEW_HALF_SPAN_M`) that starts centered on
  home `(0,0)` and slides — independently on each of N/S/E/W — only when the
  vehicle would otherwise leave it, stopping just enough to put the vehicle
  back at the edge rather than snapping to center. This replaced an earlier
  design that grew the window to fit the data (via `relim`/`autoscale_view`)
  while always staying centered on home: flying far in one direction forced
  the *whole* window to expand symmetrically around `(0,0)`, wasting most of
  the view on empty space behind the vehicle, and a raw `autoscale_view()`
  with no floor at all fits tightly enough to make a few centimeters of
  GPS/EKF noise while sitting still look like a wild flight. The window
  never shrinks or grows now — just pans — so neither problem applies; it
  also doesn't drift back toward home on its own once it's slid away.
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
| `uav/<id>/command` | clients → backend | no | Arm/disarm/takeoff/goto/circle/fly_home/interrupt/land requests |
| `uav/<id>/home` | backend → clients | **yes** | Shared local-frame origin, published once |

```json
// uav/1/telemetry
{
  "vehicle_id": "1", "timestamp": 1737000000.123,
  "lat": 41.700, "lon": -86.239,
  "alt_rel": 12.4, "alt_amsl": 237.5, "heading": 87.3,
  "groundspeed": 3.2, "battery_voltage": 12.1, "battery_level": 0.83,
  "armed": true, "mode": "GUIDED", "activity": "flying"
}
```

`activity` is one of `idle` / `taking_off` / `flying` / `circling` /
`landing` — the vehicle's current flight phase, set explicitly by
`handle_command` (and `circle_tick` when a circle finishes sweeping on its
own) as each command is issued, not inferred from other telemetry fields.
That's a deliberate choice, not the simpler option: `mode` alone can't
distinguish these, since `takeoff`/`goto`/`circle`/`fly_home` all report
`mode: "GUIDED"` — a consumer trying to infer "is this circling or just
flying straight" from telemetry alone would need fragile heuristics
(heading-rate, climb-rate) with real false-positive/negative cases, when
`drone_backend.py` already knows exactly which command it just executed.
`armed == False` always forces `activity` back to `idle` regardless of
what was last commanded (in `mavlink_reader`'s `HEARTBEAT` handling) — this
is a deliberate safety net, not redundant with the per-command sets above:
it self-corrects an optimistic `taking_off` if an arm attempt is actually
rejected by pre-arm checks, and is what marks a completed landing as
`idle` once the vehicle actually disarms, without `land`'s handler needing
to know when touchdown happens.

`alt_rel` (relative to home) and `alt_amsl` (above mean sea level) are both
published, from the same `GLOBAL_POSITION_INT` message's `relative_alt` and
`alt` fields respectively — not a second MAVLink request. `alt_rel` stays
canonical for "did I reach my target altitude" mission logic (what
`test_flight.py`/`test_circle.py`'s arrival checks use); `alt_amsl` is there
for terrain/elevation work, where relative-to-launch-point is the wrong
frame — a launch point on a hillside vs. a valley gives the same `alt_rel`
for very different real elevations. `heading` deliberately stays in
degrees, not radians: it matches `GLOBAL_POSITION_INT.hdg`'s native MAVLink
representation (no conversion at the source), and every other bearing
convention already in this codebase (`circle`'s compass bearing, the
matplotlib heading-triangle marker) is degrees too. A consumer that
specifically needs radians (e.g. for quaternion/rotation composition, not
just display) should convert at its own boundary, not push the conversion
back into the canonical telemetry.

`battery_level` (0.0-1.0) comes from `SYS_STATUS.battery_remaining`
(0-100%, or -1 if the autopilot doesn't know yet, e.g. right after boot) —
again the same message already read for `battery_voltage`, not a new
request. Published as `null` (`None`) while unknown rather than a
misleading `-1` or `0`.

```json
// uav/1/command -- one of:
{"type": "arm"}
{"type": "disarm"}
{"type": "takeoff", "alt": 10}
{"type": "goto", "lat": 41.701, "lon": -86.238, "alt": 10}
{"type": "circle", "lat": 41.701, "lon": -86.238, "alt": 10, "radius": 15, "degrees": 720, "speed": 3}
{"type": "fly_home"}
{"type": "interrupt"}
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

## Fleet generation

`docker-compose.yml` deliberately doesn't know how many vehicles exist —
Compose's YAML has no loops or arithmetic, so it can't turn a single
`NUM_DRONES` integer into N service blocks by itself. `scripts/
generate_fleet.py` does that work once, on the host, before you ever run
`docker compose`:

1. Reads `CENTER_LOCATION`, `CENTER_HEADING`, `NUM_DRONES`, and
   `DRONE_SPACING_M` from `.env`. Unlike Compose (which loads `.env`
   automatically for its own `${VAR}` substitution), this and every other
   host-side script has no automatic `.env` loading — `load_dotenv()` in
   this script is a small hand-rolled `KEY=VALUE` parser for that reason,
   not a stand-in for a shell `source .env`. Each of the four also has a
   matching CLI flag (`--location`, `--num-drones`, `--heading`,
   `--spacing`) for a one-off run without touching `.env` — precedence is
   flag > shell env var > `.env` > built-in default, e.g.
   `generate_fleet.py --location CMAC --num-drones 3` leaves `.env` alone.
2. Looks up `CENTER_LOCATION` (a nickname, e.g. `ND`) in `locations.json`
   for its lat/lon/alt. There's deliberately no raw-lat/lon fallback in
   `.env` — every flight center has to be a saved favorite, so there's one
   place (`locations.json`) that defines what a location *is*, not two.
3. Computes where each vehicle starts. `NUM_DRONES=1` places that one
   vehicle exactly at the looked-up center — this is what every earlier
   lab already assumed, so it stays a strict special case, not "a ring of
   one." `NUM_DRONES>1` arranges all N vehicles evenly spaced on a ring
   around the center instead (nothing sits exactly on the typed coordinate
   once there's more than one vehicle), with the ring radius solved from
   `DRONE_SPACING_M` via the regular-polygon chord formula
   (`chord = 2 * R * sin(pi / N)`) so adjacent vehicles end up that many
   meters apart regardless of N.
4. Writes `docker-compose.override.yml` — one `sitl_N`/`drone_backend_N`
   pair per vehicle, `VEHICLE_ID` 1..N, each with its own computed
   `--custom-location`. Compose auto-merges a file by that exact name
   sitting next to `docker-compose.yml`, so nothing downstream needs a
   `-f` flag to pick it up.

This script only writes that file — it never calls `docker compose`
itself. Bringing the fleet up/down (and back up again after re-running the
generator) is a separate, explicit step; see `SETUP.md`. One consequence
worth knowing: if you lower `NUM_DRONES` and regenerate, Compose won't
know to stop the containers for vehicles that disappeared from the file
until you say so explicitly — `docker compose up -d --remove-orphans`, or
`docker compose down` first.

`locations.json` is git-tracked and seeded with a couple of entries (`ND`,
`CMAC` — ArduPilot's own upstream default, kept as a reference point far
from campus). It's not secret or machine-specific like `.env`, so add your
own favorites to it directly; each entry needs `name`, `nickname`, `lat`,
`lon`, and `alt` (AMSL, matching the `alt_amsl` telemetry field, not
`alt_rel`). Nicknames must be unique — the generator fails immediately, before writing anything, if they collide or a required field is missing.

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
| `VEHICLE_ID` | `1` | Which vehicle single-vehicle host tools (`matplotlib_view.py`, `test_flight.py`, `test_circle.py`, `disarm.sh`, `verify_setup.py`) point at — does not affect which vehicles `docker compose` starts, see below |
| `CENTER_LOCATION` | `ND` | Nickname of a `locations.json` entry — read by `scripts/generate_fleet.py`, not by `docker compose` directly |
| `CENTER_HEADING` | `0` | Starting heading (deg) for every vehicle, also read by `generate_fleet.py` |
| `NUM_DRONES` | `1` | How many vehicles `generate_fleet.py` writes into `docker-compose.override.yml`, 1-7 |
| `DRONE_SPACING_M` | `15` | Target distance (m) between adjacent vehicles on the ring, only used when `NUM_DRONES>1` |

## Scripts

- **`scripts/generate_fleet.py`** — writes `docker-compose.override.yml`
  from `CENTER_LOCATION`/`CENTER_HEADING`/`NUM_DRONES`/`DRONE_SPACING_M` in
  `.env` plus `locations.json`. See "Fleet generation" above. Run this
  before `docker compose pull`/`up` (or after changing any of those `.env`
  values) — it never runs `docker compose` itself.
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
  docker-compose.override.yml  <- generated by generate_fleet.py, gitignored
  .env / .env.example
  locations.json            <- saved flight-center favorites (name/nickname/lat/lon/alt)
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
    generate_fleet.py
    verify_setup.py
    disarm.sh
    test_flight.py
    test_circle.py
    build_and_push_sitl.sh
```

## DroneResponse `UPDATE_DRONE` integration

Required for the `new-gui` viewer, off by default for the plain Stage 1 path
(`matplotlib_view.py`/`test_flight.py`/`test_circle.py` don't need it).
`.env-copy` (the working config students copy to `.env` -- see SETUP.md
Step 3) sets it already; `.env.example` intentionally leaves it out since
that file is a from-scratch reference, not a copy-and-go config. Set
`UPDATE_DRONE` to the topic name to also publish a translated message on
every tick, alongside the normal `TELEMETRY_TOPIC` publish —
`drone_backend.py`'s `update_drone_payload()`. Left unset, none of this
runs. Named after the DroneResponse message contract/topic itself
(lowercase `update_drone` is the actual topic string — must match exactly
what the consuming GUI subscribes to, MQTT topics are case-sensitive), not
after any particular consumer program — `drone_backend.py` doesn't know or
care who's subscribed. The current known consumer is `new-gui.py`, which is
what the specifics below are checked against, but nothing here is coupled
to that program specifically.

This used to be a separate bridge process (a standalone script in the
`new-gui` repo translating `uav/1/telemetry` into `update_drone`) but folding
it into `drone_backend.py` directly means one fewer process to run — the
`uav/<id>/telemetry` contract itself is completely unchanged either way, so
`matplotlib_view.py`/`test_flight.py`/`test_circle.py` don't know or care
whether this is enabled.

Things worth knowing if this needs touching again:
- `new-gui.py`'s field is named `heading_rad`, but every place that actually
  renders it (`tile_map.py`, `drone_panel.py`, `camera_manager.py`) treats
  the value as **degrees** — confirmed by reading those call sites, not the
  field name. Converting Stage 1's degrees to radians here was a real bug
  in an earlier version: the drone never visibly faced its direction of
  travel.
- The flashing drone icon during takeoff/landing isn't driven by
  `status`/`state_type` — it's `onboard_pilot`, checked case-insensitively
  in `tile_map.py`'s `_is_flashing()` for exactly `"takeoff"` or `"land"`.
  Despite the name, it's not a person — `drone.py`'s own comment gives
  `"ReceiveMission"`/`"Takeoff"` as example values, i.e. the onboard
  autonomy's current named task, which Stage 1's `activity` already tracks
  and `UPDATE_DRONE_ACTIVITY_MAP` maps onto directly.
- `uavid` has to be an HTML/CSS color name, not Stage 1's own numeric
  `VEHICLE_ID` — confirmed via `tile_map.py`: a live drone's marker color is
  `fill_color = QColor(d.name.lower())` (`d.name` is `uavid`) with no
  meaningful fallback if that string isn't a valid color name (`QColor(...)
  .isValid()` is `False`, silently renders flat gray). `UPDATE_DRONE_COLORS`
  (`Fuchsia`, `Navy`, `Purple`, `Aqua`, `Lime`, `Orange`, `Yellow`) maps
  `VEHICLE_ID` to a color 1-indexed into that list; `VEHICLE_ID="1"` sends
  `uavid: "Fuchsia"`. Stage 1's own `vehicle_id` field (in
  `uav/<id>/telemetry`) and MQTT topic names (`uav/1/...`) are untouched —
  this mapping exists only inside `update_drone_payload`. Running more
  vehicles than the list has colors (Stage 6, multi-vehicle) falls back to
  the raw numeric ID rather than crashing, which renders gray the same way
  an unmapped ID always would have.

## Not yet in scope (future stages)

- Stage 2: tile-based map / `new-gui.py` is now infrastructure, not future
  scope — it's the multi-vehicle viewer in the separate `new-gui` repo, and
  needs `UPDATE_DRONE` set (see above) to receive telemetry from this repo.
- Stage 3: click-to-goto
- Stage 4: mission upload / geofence
- Stage 5: log replay
- Stage 6: multi-vehicle is now infrastructure, not future scope —
  `scripts/generate_fleet.py` + `docker compose up` starts 1-7 independent
  `sitl_N`/`drone_backend_N` pairs (`VEHICLE_ID` 1..N, each with its own
  MQTT topic prefix, scattered around a `locations.json` favorite, and,
  when `UPDATE_DRONE` is set, its own `DRONE_COLOR`). `matplotlib_view.py`
  deliberately stays single-vehicle (`VEHICLE_ID` picks which one it shows)
  since multi-vehicle *display* is `new-gui`'s job, not this stage's.
