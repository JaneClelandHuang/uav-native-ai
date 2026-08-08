#!/usr/bin/env python3
"""Vehicle 3's flight: takeoff, fly out to a point, fly_home, land.

Fixed to VEHICLE_ID "3" -- this is the flight for drone 3, not a generic
tool. Exercises `fly_home`, the one command neither test_flight.py's
square (goto/land) nor test_circle.py's circle (circle/interrupt) exercises
-- between all three flight_vehicle_*.py scripts, goto/circle/fly_home all
get demonstrated somewhere. Run via
scripts/fleet_demo/run_fleet_demo.py alongside flight_vehicle_1.py/_2.py.

Talks only over the MQTT command/telemetry contract -- same as
test_flight.py/test_circle.py, not scripts/simple_flight.py's
direct-pymavlink path.

Requires paho-mqtt (already needed for client/matplotlib_view.py -- install
client/requirements.txt into your venv before running this).
"""
import json
import math
import os
import sys
import time

import paho.mqtt.client as mqtt

VEHICLE_ID = "3"
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

HOME_TOPIC = f"uav/{VEHICLE_ID}/home"
TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"
COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"

EARTH_RADIUS_M = 6378137.0

TAKEOFF_ALT_M = 10.0
OUT_M = 30.0  # distance flown out from home before flying back -- matches
              # the 2x-15m scale flight_vehicle_1.py/_2.py use
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
    as test_flight.py's wait_for(), so this self-heals against a dropped UDP
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
    home_lat, home_lon = home["lat"], home["lon"]

    print(f"[vehicle {VEHICLE_ID}]\n=== Takeoff to {TAKEOFF_ALT_M}m ===")
    wait_for(
        "telemetry",
        lambda t: t.get("armed") and (t.get("alt_rel") or 0) > TAKEOFF_ALT_M * 0.9,
        60, f"armed and within 90% of {TAKEOFF_ALT_M}m",
        command={"type": "takeoff", "alt": TAKEOFF_ALT_M}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   airborne")

    out_lat, out_lon = offset_to_lla(home_lat, home_lon, OUT_M, 0)
    print(f"[vehicle {VEHICLE_ID}]\n=== Flying {OUT_M:.0f}m out from home ===")
    wait_for(
        "telemetry",
        lambda t: (
            t.get("lat") is not None
            and horizontal_distance_m(t["lat"], t["lon"], out_lat, out_lon) < ARRIVAL_TOLERANCE_M
        ),
        30, f"arrival within {ARRIVAL_TOLERANCE_M}m of ({out_lat:.6f}, {out_lon:.6f})",
        command={"type": "goto", "lat": out_lat, "lon": out_lon, "alt": TAKEOFF_ALT_M}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   reached ({out_lat:.6f}, {out_lon:.6f})")

    # fly_home takes no params -- drone_backend.py replays the lat/lon it
    # captured from HOME_POSITION at boot, so the wait_for predicate below
    # checks arrival against home_lat/home_lon directly rather than
    # something echoed back in the command.
    print(f"[vehicle {VEHICLE_ID}]\n=== Flying home ===")
    wait_for(
        "telemetry",
        lambda t: (
            t.get("lat") is not None
            and horizontal_distance_m(t["lat"], t["lon"], home_lat, home_lon) < ARRIVAL_TOLERANCE_M
        ),
        30, f"arrival within {ARRIVAL_TOLERANCE_M}m of home ({home_lat:.6f}, {home_lon:.6f})",
        command={"type": "fly_home"}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   back home")

    print(f"[vehicle {VEHICLE_ID}]\n=== Landing ===")
    wait_for(
        "telemetry", lambda t: not t.get("armed"),
        60, "landed and disarmed",
        command={"type": "land"}, client=client,
    )
    print(f"[vehicle {VEHICLE_ID}]   landed and disarmed")

    print(f"[vehicle {VEHICLE_ID}]\nPASS: flight completed (takeoff -> out -> fly_home -> land).")
    client.loop_stop()


if __name__ == "__main__":
    main()
