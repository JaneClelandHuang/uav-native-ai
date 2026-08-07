#!/usr/bin/env python3
"""Vehicle 2's flight: takeoff, circle, interrupt partway through, land.

Fixed to VEHICLE_ID "2" -- this is the flight for drone 2, not a generic
tool (compare scripts/test_circle.py, which this is adapted from and which
stays configurable via the VEHICLE_ID env var). Run via
scripts/fleet_demo/run_fleet_demo.py alongside flight_vehicle_1.py/_3.py,
or standalone the same way you'd run test_circle.py.

Talks only over the MQTT command/telemetry contract -- same as
test_circle.py, not scripts/simple_flight.py's direct-pymavlink path.

Requires paho-mqtt (already needed for client/matplotlib_view.py -- install
client/requirements.txt into your venv before running this).
"""
import json
import math
import os
import sys
import time

import paho.mqtt.client as mqtt

VEHICLE_ID = "2"
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

HOME_TOPIC = f"uav/{VEHICLE_ID}/home"
TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"
COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"

EARTH_RADIUS_M = 6378137.0

TAKEOFF_ALT_M = 10.0
RADIUS_M = 30.0  # 2x test_circle.py's 15m
CIRCLE_DEGREES = 720.0  # two full sweeps
INTERRUPT_AT_DEGREES = 500.0  # partway through the second sweep
SPEED_MPS = 3.0
ARRIVAL_TOLERANCE_M = 2.0
RESEND_INTERVAL_S = 8.0

_latest = {}


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe(HOME_TOPIC)
    client.subscribe(TELEMETRY_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        return
    if msg.topic == HOME_TOPIC:
        _latest["home"] = payload
    elif msg.topic == TELEMETRY_TOPIC:
        _latest["telemetry"] = payload


def offset_to_lla(origin_lat, origin_lon, east_m, north_m):
    """Small ENU offset -> lat/lon, purely to plan this script's own
    waypoints -- same throwaway-local-frame idea as matplotlib_view.py's
    ENU conversion, never published anywhere.
    """
    lat0_rad = math.radians(origin_lat)
    dlat = math.degrees(north_m / EARTH_RADIUS_M)
    dlon = math.degrees(east_m / (EARTH_RADIUS_M * math.cos(lat0_rad)))
    return origin_lat + dlat, origin_lon + dlon


def horizontal_distance_m(lat1, lon1, lat2, lon2):
    lat0_rad = math.radians((lat1 + lat2) / 2)
    dx = math.radians(lon2 - lon1) * math.cos(lat0_rad) * EARTH_RADIUS_M
    dy = math.radians(lat2 - lat1) * EARTH_RADIUS_M
    return math.hypot(dx, dy)


def wait_for(key, predicate, timeout, description, command=None, client=None):
    """Poll telemetry/home for `predicate`, optionally re-publishing
    `command` every RESEND_INTERVAL_S -- same resend-until-satisfied pattern
    as test_circle.py's wait_for(), so this self-heals against a dropped UDP
    command the same way.
    """
    print(f"[vehicle {VEHICLE_ID}] Waiting up to {timeout:.0f}s: {description}")
    deadline = time.time() + timeout
    next_send = 0.0
    while time.time() < deadline:
        if command is not None and time.time() >= next_send:
            client.publish(COMMAND_TOPIC, json.dumps(command))
            print(f"[vehicle {VEHICLE_ID}]   -> sent {command}")
            next_send = time.time() + RESEND_INTERVAL_S
        value = _latest.get(key)
        if value is not None and predicate(value):
            return value
        time.sleep(0.5)
    print(f"[vehicle {VEHICLE_ID}] FAIL: timed out waiting for: {description}")
    print(f"[vehicle {VEHICLE_ID}]   Check `docker compose logs sitl_{VEHICLE_ID}` "
          f"and `docker compose logs drone_backend_{VEHICLE_ID}`.")
    sys.exit(1)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    home = wait_for("home", lambda h: True, 30, "retained home position")
    center_lat, center_lon = home["lat"], home["lon"]

    print(f"[vehicle {VEHICLE_ID}]\n=== Takeoff to {TAKEOFF_ALT_M}m ===")
    wait_for(
        "telemetry",
        lambda t: t.get("armed") and (t.get("alt_rel") or 0) > TAKEOFF_ALT_M * 0.9,
        60, f"armed and within 90% of {TAKEOFF_ALT_M}m",
        command={"type": "takeoff", "alt": TAKEOFF_ALT_M}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   airborne")

    # drone_backend.py's circle always starts the sweep at bearing 0 (due
    # north of center) -- see ARCHITECTURE.md. Flying here first, rather
    # than to the center itself, means the circle command doesn't open with
    # a sudden lurch from the center out to the radius.
    start_lat, start_lon = offset_to_lla(center_lat, center_lon, 0, RADIUS_M)
    print(f"[vehicle {VEHICLE_ID}]\n=== Flying to circle start point ({RADIUS_M:.0f}m north of center) ===")
    wait_for(
        "telemetry",
        lambda t: (
            t.get("lat") is not None
            and horizontal_distance_m(t["lat"], t["lon"], start_lat, start_lon) < ARRIVAL_TOLERANCE_M
        ),
        30, f"arrival within {ARRIVAL_TOLERANCE_M}m of circle start ({start_lat:.6f}, {start_lon:.6f})",
        command={"type": "goto", "lat": start_lat, "lon": start_lon, "alt": TAKEOFF_ALT_M}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   at circle start point")

    print(f"[vehicle {VEHICLE_ID}]\n=== Circling: {CIRCLE_DEGREES:.0f} deg requested, "
          f"interrupting at {INTERRUPT_AT_DEGREES:.0f} deg ===")
    circle_command = {
        "type": "circle", "lat": center_lat, "lon": center_lon,
        "alt": TAKEOFF_ALT_M, "radius": RADIUS_M,
        "degrees": CIRCLE_DEGREES, "speed": SPEED_MPS,
    }
    client.publish(COMMAND_TOPIC, json.dumps(circle_command))
    print(f"[vehicle {VEHICLE_ID}]   -> sent {circle_command}")

    # No telemetry field marks "degrees swept" -- the rate is deterministic
    # (angular_rate = speed / radius), so we can just compute how long
    # INTERRUPT_AT_DEGREES takes and sleep, the same way you'd time a
    # physical maneuver rather than poll for it.
    angular_rate_deg_s = math.degrees(SPEED_MPS / RADIUS_M)
    interrupt_after_s = INTERRUPT_AT_DEGREES / angular_rate_deg_s
    print(f"[vehicle {VEHICLE_ID}]   waiting {interrupt_after_s:.1f}s "
          f"(~{INTERRUPT_AT_DEGREES:.0f} deg at {angular_rate_deg_s:.1f} deg/s)...")
    time.sleep(interrupt_after_s)

    client.publish(COMMAND_TOPIC, json.dumps({"type": "interrupt"}))
    print(f"[vehicle {VEHICLE_ID}]   -> sent interrupt")
    wait_for(
        "telemetry", lambda t: t.get("mode") == "LOITER",
        15, "mode switched to LOITER after interrupt",
    )
    print(f"[vehicle {VEHICLE_ID}]   circle interrupted, holding in LOITER")

    print(f"[vehicle {VEHICLE_ID}]\n=== Flying to a new point ===")
    new_lat, new_lon = offset_to_lla(center_lat, center_lon, RADIUS_M * 2, 0)
    wait_for(
        "telemetry",
        lambda t: (
            t.get("lat") is not None
            and horizontal_distance_m(t["lat"], t["lon"], new_lat, new_lon) < ARRIVAL_TOLERANCE_M
        ),
        30, f"arrival within {ARRIVAL_TOLERANCE_M}m of ({new_lat:.6f}, {new_lon:.6f})",
        command={"type": "goto", "lat": new_lat, "lon": new_lon, "alt": TAKEOFF_ALT_M}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   reached new point")

    print(f"[vehicle {VEHICLE_ID}]\n=== Landing ===")
    wait_for(
        "telemetry", lambda t: not t.get("armed"),
        60, "landed and disarmed",
        command={"type": "land"}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   landed and disarmed")

    print(f"[vehicle {VEHICLE_ID}]\nPASS: circle test completed (takeoff -> circle -> interrupt -> goto -> land).")
    client.loop_stop()


if __name__ == "__main__":
    main()
