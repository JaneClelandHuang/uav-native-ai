# Flight Data Monitoring — Working Notes

Context/reference doc for continuing this work in a future session (this
was worked out in conversation, not yet fully implemented). Companion to
`PYMAVLINK-LIB.md` (command side) — this covers the *telemetry* side:
what SITL actually exposes, and what a "monitor flight data" assignment
could ask students to build with it.

---

## What ArduPilot SITL exposes over MAVLink

Grouped by the three things originally asked about, plus what else is in
the same neighborhood.

**GPS / position accuracy** — `GPS_RAW_INT`. `h_acc`/`v_acc` (mm) are the
HAcc/VAcc fields Mission Planner's HUD shows; also `eph`/`epv` (HDOP-style,
older/coarser), `fix_type`, `satellites_visible`. **Caveat:** SITL's
default GPS model is fairly idealized — `h_acc`/`v_acc` sit near-constant
"good" values unless a `SIM_GPS_*` fault is injected (see below).

**EKF health** — `EKF_STATUS_REPORT`. `flags` (bitmask: which estimates —
attitude/velocity/position/etc. — the EKF currently trusts) plus
`velocity_variance`, `pos_horiz_variance`, `pos_vert_variance`,
`compass_variance`, `terrain_alt_variance`. Same innovation-based
variances ArduPilot's own EKF failsafe logic watches. (The richer
`XKF*`/`NKF*` family is dataflash-log-only, not live telemetry.)

**Vibration** — `VIBRATION`. `vibration_x/y/z` (clipping-derived, m/s/s,
not raw accel) plus `clipping_0/1/2` (cumulative clip counts per IMU,
watch as a rate). **Caveat:** same idealized-physics issue as GPS — stays
near zero without `SIM_VIB_FREQ_*` injection.

**Everything else worth knowing about:**
- `STATUSTEXT` — ArduPilot's own plain-English alerts ("Low Battery",
  "PreArm: Compass not calibrated", "EKF Failsafe"). `severity` is
  `MAV_SEVERITY` (0=EMERGENCY..7=DEBUG, lower is worse). Cheapest possible
  signal — no threshold math required, the autopilot already decided it's
  worth telling you.
- `SYS_STATUS` — battery voltage/current/remaining (fields already on the
  message `drone_backend.py` reads, just not fully consumed yet), CPU
  load, and `onboard_control_sensors_present/enabled/health` — three
  bitmasks (which sensors exist / are on / are currently OK).
- `HEARTBEAT` — flight mode + armed state (already consumed).
- `RADIO_STATUS` — rssi/remrssi/noise/txbuf, link quality. Thematically
  relevant to disaster-response BVLOS scenarios but SITL's simulated link
  is normally perfect.
- `NAV_CONTROLLER_OUTPUT` — cross-track error, distance-to-waypoint.
- `BATTERY_STATUS` — more detail than `SYS_STATUS`'s battery fields.

## Two practical gotchas

**Stream rate.** None of the messages above arrive at a useful rate by
default — ArduPilot only streams what's been requested. Need
`MAV_CMD_SET_MESSAGE_INTERVAL` (or the older `REQUEST_DATA_STREAM`) per
message type, or `recv_match` will see them rarely or never.

**MAVLink protocol version (the nonobvious one).** `mavutil.mavlink`
resolves to the **MAVLink 1** dialect module unless `MAVLINK20` is set in
the environment *before* `from pymavlink import mavutil` runs — this is
decided once, at import time. Under v1, `GPS_RAW_INT.h_acc`/`.v_acc` don't
exist as attributes at all (not `None` — `AttributeError`), even though
ArduPilot SITL sends MAVLink 2 on the wire regardless. Confirmed against
`pymavlink==2.4.41` (the version pinned in `backend/requirements.txt`) in
an isolated venv. Fix: `os.environ.setdefault("MAVLINK20", "1")` before
the `mavutil` import.

## SITL fault injection

The simulated failures that make the accuracy/EKF/vibration values above
actually move are ordinary ArduPilot parameters, prefixed `SIM_`, set the
same way as any tuning parameter (`PARAM_SET` / `PARAM_REQUEST_READ` —
no separate "inject a fault" message type exists). Useful ones:

| Parameter | Effect |
|---|---|
| `SIM_GPS_NOISE` / `SIM_GPS_GLITCH` | Degrades/glitches simulated GPS — moves `h_acc`/`v_acc` |
| `SIM_VIB_FREQ_X/Y/Z`, `SIM_VIB_MOT_MAX` | Injects vibration — moves `VIBRATION` fields |
| `SIM_ENGINE_FAIL` | Kills a motor (multicopter) |
| `SIM_RC_FAIL` | Simulates RC signal loss |
| `SIM_BARO_DRIFT` / `SIM_BARO_GLITCH` | Degrades simulated barometer |
| `SIM_MAG_FAIL` | Flips the compass bit in `SYS_STATUS` sensor health |

Set live during a session (`PARAM_SET`) or via a params file loaded at
SITL startup.

## Tiered framework for assignment design

Worked out by difficulty, since Tier 3 has a hidden prerequisite (fault
injection) that Tier 1 doesn't:

- **Tier 1 (easy win):** `STATUSTEXT`, `SYS_STATUS` battery, `HEARTBEAT`
  mode/armed. No bitmask decoding, no fault injection needed to see
  something meaningful — ArduPilot already did the interpretation.
- **Tier 2 (moderate):** `SYS_STATUS` sensor-health bitmask (reuses the
  bit-flag pattern already taught for the `SET_POSITION_TARGET_GLOBAL_INT`
  type mask in `PYMAVLINK-LIB.md`), `RADIO_STATUS`, `NAV_CONTROLLER_OUTPUT`.
- **Tier 3 (the original HAcc/EKF/vibration ask):** needs SITL fault
  injection as a prerequisite skill, or the values just sit flat and
  "healthy" the whole flight.

## Current implementation state

`backend/mavlink_lib.py` today only has command primitives (`connect`,
`arm`, `disarm`, `takeoff`, `goto`, `circle_point`, `interrupt`, `land`) —
build-and-send only, no telemetry reading at all. `drone_backend.py`'s
`mavlink_reader()` (its single `recv_match` loop — see that function's
docstring for why it's not shared across threads) currently only handles
`HEARTBEAT`, `GLOBAL_POSITION_INT`, `VFR_HUD`, `SYS_STATUS` (voltage/
remaining only), and `HOME_POSITION`.

**Merged into `backend/mavlink_lib.py`.** Built and unit-tested first in an
isolated scratchpad copy (a second Claude session was concurrently active
in this repo), then copied in once `git diff` confirmed the base file
hadn't moved underneath it — no conflicts. What landed:

- `os.environ.setdefault("MAVLINK20", "1")` fix, top of file.
- `set_param(conn, name, value, param_type=...)` / `get_param(conn, name,
  timeout=2.0)` — generic `PARAM_SET`/`PARAM_REQUEST_READ` wrappers for
  fault injection. `get_param` blocks (documented as a deliberate,
  one-shot exception to the file's send-only contract, same class as
  `connect()`'s `wait_heartbeat()` — not to be called from
  `mavlink_reader()`'s thread).
- `_decode_flag_bits(mask, enum_name, strip_prefix)` — private helper,
  turns any of pymavlink's bit-per-flag enums into a `name -> bool` dict.
- `parse_status_text`, `parse_battery`, `parse_sensor_health`,
  `parse_ekf_status`, `parse_vibration`, `parse_gps_accuracy` — pure
  `msg -> dict` functions (no `recv_match` calls of their own), meant to
  be called inline from `mavlink_reader()`'s existing `elif msg_type ==
  ...` chain the same way it already hand-builds the `HOME_POSITION` dict.

**Not done:** wiring any of the `parse_*` functions into
`drone_backend.py`'s reader loop or MQTT publishing, requesting the
relevant message intervals via `MAV_CMD_SET_MESSAGE_INTERVAL`, and
anything student-facing (assignment text, starter code).
