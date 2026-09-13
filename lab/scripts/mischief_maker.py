#!/usr/bin/env python3
"""mischief-maker.py: lesson-4 randomized fault injection.

Waits for a vehicle to actually complete takeoff, then injects one of four
simulated faults (vibration, GPS, compass/mag, battery) at a randomized
moment and a randomized, severity-appropriate magnitude, via a new
`inject_fault` MQTT command drone_backend.py applies through the existing
generic mavlink_lib.set_param() (see that function's own "SITL fault
injection" notes). Pure MQTT client -- same connect/on_connect/on_message
pattern as client/matplotlib_view.py and client2/monitor_view.py; never
touches pymavlink directly (SITL only serves one direct client -- confirmed
by testing, not assumed, earlier in this tool's design).

Usage:
    python mischief_maker.py TYPE ONSET_DEADLINE [TIME_SPAN] [SEVERITY]

    TYPE            GPS | VIBRATION | MAG-COMPASS | POWER-BATTERY | RANDOM
                    (case-insensitive; RANDOM picks one of the other four)
    ONSET_DEADLINE  fault fires at a random delay within this many seconds
                    *after takeoff completes* (required)
    TIME_SPAN       seconds to wait for takeoff to happen at all before
                    giving up (default: 60)
    SEVERITY        High | Medium | Low (default: random)

Example:
    python mischief_maker.py VIBRATION 30 60 High
    -- injects a High-severity vibration fault at a random point within
       30s of takeoff completing, giving up if takeoff hasn't happened
       within 60s of this script starting.

"Takeoff complete" is detected generically -- armed, climbed past a small
altitude, then leveled off for a few seconds -- not by watching for a
specific command sequence. drone_backend.py's `activity` field only becomes
"flying" once a *subsequent* command (goto/fly_home/...) is issued after
takeoff, not automatically on reaching altitude, so a student who just
takes off and hovers would never trip an activity-based detector.

The fault persists (no auto-heal) until this process exits or is killed --
Ctrl-C (or a normal exit after firing) resets the affected SIM_ params back
to their ArduPilot defaults first, so the next run starts clean.
"""
import argparse
import collections
import json
import os
import random
import signal
import sys
import time

import paho.mqtt.client as mqtt

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"
COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"

# Takeoff-complete heuristic: armed, above LIFTOFF_M, and alt_rel's spread
# over the last STABLE_WINDOW_S seconds is within STABLE_TOLERANCE_M --
# i.e. it climbed and then stopped changing much. Altitude-based rather
# than activity-based on purpose (see module docstring).
LIFTOFF_M = 2.0
STABLE_WINDOW_S = 3.0
STABLE_TOLERANCE_M = 0.75
POLL_INTERVAL_S = 0.5

# Calibrated live against the real fleet (see mischief_maker.py's git log /
# session notes, not guessed from SITL.cpp defaults alone -- several
# plausible-looking params turned out not to work at all, for reasons
# specific to how ArduPilot SITL computes each reported value; see the two
# call-outs below before "fixing" either of these).
FAULT_CATALOG = {
    # VIBRATION does NOT use SIM_VIB_FREQ_*/SIM_VIB_MOT_*/SIM_ACC*_RND --
    # tried all of them, up to extreme values, held for 40+ seconds: zero
    # effect on the reported VIBRATION message. Traced why: ArduPilot's
    # vibration-level calculation (AP_InertialSensor::calc_vibration_and_
    # clipping) is fed the *loop-averaged* accel sample, not the raw
    # per-sample value those params perturb -- injected per-sample noise
    # (and even a coherent injected sine wave) averages toward ~zero before
    # vibration calc ever sees it. What actually works: real physical
    # shaking of the airframe via simulated wind, which the vehicle
    # genuinely fights -- confirmed live, baseline ~0.003 -> 3-8 at the
    # HIGH values below. Side effect worth knowing: real wind also nudges
    # GPS/EKF position variance a little, since the vehicle is physically
    # being pushed off station -- unlike the other three fault types, this
    # one isn't perfectly isolated to just its own category, because it's
    # a real physical disturbance, not injected sensor/measurement noise.
    "VIBRATION": {
        "defaults": {"SIM_WIND_SPD": 0, "SIM_WIND_TURB": 0},
        "severity": {
            "LOW":    {"SIM_WIND_SPD": (2, 5),   "SIM_WIND_TURB": (0.5, 2)},
            "MEDIUM": {"SIM_WIND_SPD": (6, 10),  "SIM_WIND_TURB": (3, 5)},
            "HIGH":   {"SIM_WIND_SPD": (12, 18), "SIM_WIND_TURB": (6, 10)},
        },
    },
    # SIM_GPS_NOISE does NOT move fix_type/h_acc_m/v_acc_m/hdop_h/hdop_v --
    # confirmed live, even at SIM_GPS_NUMSATS=0 fix_type stayed at 6 (RTK-
    # fixed-equivalent). SITL's GPS model is that idealized -- same warning
    # mavlink_lib.parse_gps_accuracy's docstring already gives. Only
    # SIM_GPS_NUMSATS -> satellites_visible is confirmed to move anything
    # this module reports, so that's the only param used here.
    "GPS": {
        "defaults": {"SIM_GPS_NUMSATS": 10},
        "severity": {
            "LOW":    {"SIM_GPS_NUMSATS": (7, 9)},
            "MEDIUM": {"SIM_GPS_NUMSATS": (5, 7)},
            "HIGH":   {"SIM_GPS_NUMSATS": (2, 4)},
        },
    },
    # Confirmed live: SIM_MAG_RND=600 visibly shifted field_magnitude
    # (~526 -> ~452, plus real per-axis movement) within a few seconds.
    "MAG-COMPASS": {
        "defaults": {"SIM_MAG_RND": 0},
        "severity": {
            "LOW":    {"SIM_MAG_RND": (50, 150)},
            "MEDIUM": {"SIM_MAG_RND": (150, 400)},
            "HIGH":   {"SIM_MAG_RND": (400, 800)},
        },
    },
    # Confirmed live: SIM_BATT_VOLTAGE is a direct override of the reported
    # voltage_v -- exact, immediate, no filtering/averaging involved.
    "POWER-BATTERY": {
        "defaults": {"SIM_BATT_VOLTAGE": 12.6},
        "severity": {
            "LOW":    {"SIM_BATT_VOLTAGE": (11.0, 11.8)},
            "MEDIUM": {"SIM_BATT_VOLTAGE": (10.0, 11.0)},
            "HIGH":   {"SIM_BATT_VOLTAGE": (8.5, 10.0)},
        },
    },
}
FAULT_TYPES = list(FAULT_CATALOG)  # excludes RANDOM, resolved separately
SEVERITIES = ["LOW", "MEDIUM", "HIGH"]

# Params whose randomized value should be an int (a satellite count, not a
# continuous quantity) -- everything else is sampled as a float.
INTEGER_PARAMS = {"SIM_GPS_NUMSATS"}

_latest = {}


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe(TELEMETRY_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        return
    if msg.topic == TELEMETRY_TOPIC:
        _latest["telemetry"] = payload


def resolve_type(type_arg):
    type_arg = type_arg.upper()
    if type_arg == "RANDOM":
        return random.choice(FAULT_TYPES)
    if type_arg not in FAULT_CATALOG:
        sys.exit(f"Unknown TYPE {type_arg!r} -- one of {FAULT_TYPES + ['RANDOM']}")
    return type_arg


def resolve_severity(severity_arg):
    if severity_arg is None:
        return random.choice(SEVERITIES)
    severity_arg = severity_arg.upper()
    if severity_arg not in SEVERITIES:
        sys.exit(f"Unknown SEVERITY {severity_arg!r} -- one of {SEVERITIES}")
    return severity_arg


def sample_params(fault_type, severity):
    """(fault_type, severity) -> {param_name: randomized value}. Even a
    fixed severity is a range, not one number -- see FAULT_CATALOG.
    """
    ranges = FAULT_CATALOG[fault_type]["severity"][severity]
    values = {}
    for name, (low, high) in ranges.items():
        value = random.uniform(low, high)
        values[name] = round(value) if name in INTEGER_PARAMS else round(value, 2)
    return values


def wait_for_takeoff(time_span):
    """Blocks until telemetry shows armed + climbed-then-leveled altitude,
    or time_span seconds pass. See LIFTOFF_M/STABLE_WINDOW_S/
    STABLE_TOLERANCE_M and the module docstring for why this is altitude-
    based rather than watching drone_backend.py's `activity` field.
    """
    print(f"Waiting up to {time_span:.0f}s for takeoff to complete...")
    deadline = time.time() + time_span
    recent = collections.deque()  # (timestamp, alt_rel), trimmed to the last STABLE_WINDOW_S
    # Tracked separately from `recent`'s own span: the deque's oldest entry
    # gets trimmed in the same iteration it would otherwise cross
    # STABLE_WINDOW_S, so its span structurally never reaches the full
    # window -- checking "have we been watching long enough" against a
    # plain elapsed-time marker instead of the (permanently short) trimmed
    # deque was the actual bug here, found by watching MISCHIEF_DEBUG=1
    # output live: alt_rel/spread were correct, but the deque's own span
    # topped out just under the window forever.
    window_start = None

    while time.time() < deadline:
        telemetry = _latest.get("telemetry")
        now = time.time()
        if telemetry is not None and telemetry.get("armed"):
            alt_rel = telemetry.get("alt_rel")
            if alt_rel is not None:
                if window_start is None:
                    window_start = now
                recent.append((now, alt_rel))
                while recent and now - recent[0][0] > STABLE_WINDOW_S:
                    recent.popleft()
                spread = max(a for _, a in recent) - min(a for _, a in recent)
                if os.environ.get("MISCHIEF_DEBUG"):
                    print(f"DEBUG alt_rel={alt_rel:.2f} watched={now - window_start:.2f}s spread={spread:.2f}", flush=True)
                if (
                    alt_rel > LIFTOFF_M
                    and now - window_start >= STABLE_WINDOW_S
                    and spread <= STABLE_TOLERANCE_M
                ):
                    return True
        else:
            recent.clear()  # disarmed (or no telemetry yet) resets the window
            window_start = None
        time.sleep(POLL_INTERVAL_S)

    print(f"FAIL: no takeoff completed within {time_span:.0f}s -- no fault fired.")
    return False


def inject(client, params):
    client.publish(COMMAND_TOPIC, json.dumps({"type": "inject_fault", "params": params}))


def main():
    parser = argparse.ArgumentParser(
        description="Inject a randomized simulated fault after the vehicle takes off.",
    )
    parser.add_argument("type", metavar="TYPE",
                         help=f"one of {FAULT_TYPES + ['RANDOM']} (case-insensitive)")
    parser.add_argument("onset_deadline", type=float, metavar="ONSET_DEADLINE",
                         help="fault fires at a random delay within this many seconds after takeoff")
    parser.add_argument("time_span", type=float, nargs="?", default=60.0, metavar="TIME_SPAN",
                         help="seconds to wait for takeoff before giving up (default: 60)")
    parser.add_argument("severity", nargs="?", default=None, metavar="SEVERITY",
                         help=f"one of {SEVERITIES} (default: random)")
    args = parser.parse_args()

    fault_type = resolve_type(args.type)
    severity = resolve_severity(args.severity)
    params = sample_params(fault_type, severity)
    defaults = FAULT_CATALOG[fault_type]["defaults"]

    print(f"mischief-maker: TYPE={fault_type} SEVERITY={severity} PARAMS={params}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    def cleanup(*_args):
        print(f"\nResetting {fault_type} params to defaults: {defaults}")
        inject(client, defaults)
        time.sleep(0.5)  # give the publish a moment to actually go out
        client.loop_stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    if not wait_for_takeoff(args.time_span):
        client.loop_stop()
        sys.exit(1)

    onset_delay = random.uniform(0, args.onset_deadline)
    print(f"Takeoff complete -- firing in {onset_delay:.1f}s (deadline was {args.onset_deadline:.0f}s)")
    time.sleep(onset_delay)

    inject(client, params)
    print(f"FIRED: {fault_type} ({severity}) -- {params}")
    print("Fault persists until this process exits. Ctrl-C to reset and quit.")

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
