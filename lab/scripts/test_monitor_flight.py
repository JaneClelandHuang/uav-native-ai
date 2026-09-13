#!/usr/bin/env python3
"""Scripted test flight for Lesson 4: arm+takeoff, fly a square centered on
the launch point, then return to center and land.

Same shape as test_flight.py (talks only over the MQTT command/telemetry
contract, exactly what a student-built frontend does, just scripted), but
bigger and centered differently: test_flight.py's square is offset from
home; this one treats home itself as the square's *center*, with each side
40m long -- long enough to give mischief_maker.py's onset window real
flight time to fire and be observed, rather than being over before a fault
even has a chance to trigger.

Route: Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left -> Top-Left
(closing the loop), then back to center, then land. Uses relative altitude
throughout (alt_rel), same as test_flight.py.

Requires paho-mqtt (already needed for client/matplotlib_view.py -- install
client/requirements.txt into your venv before running this).
"""
import json
import math
import os
import sys
import time

import paho.mqtt.client as mqtt

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

HOME_TOPIC = f"uav/{VEHICLE_ID}/home"
TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"
COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"

EARTH_RADIUS_M = 6378137.0

TAKEOFF_ALT_M = 20.0
SIDE_M = 40.0  # length of each side of the square, per corner-to-corner leg
HALF_SIDE_M = SIDE_M / 2.0  # each corner's offset from center, on each axis
ARRIVAL_TOLERANCE_M = 2.0
RESEND_INTERVAL_S = 8.0
# 40m legs take noticeably longer to fly than test_flight.py's 15m ones --
# scaled up from its 30s accordingly, not just copied.
LEG_TIMEOUT_S = 60

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


def wait_for(key, predicate, timeout, description):
    print(f"Waiting up to {timeout:.0f}s: {description}")
    deadline = time.time() + timeout

    while time.time() < deadline:
        value = _latest.get(key)

        if value is not None and predicate(value):
            return value

        time.sleep(0.5)

    print(f"FAIL: timed out waiting for: {description}")
    print("  Check `docker compose logs sitl` and `docker compose logs drone_backend`.")
    sys.exit(1)


def execute_command(key, predicate, timeout, description, command, client):
    print(f"Waiting up to {timeout:.0f}s: {description}")

    deadline = time.time() + timeout
    next_send = 0.0

    while time.time() < deadline:
        if time.time() >= next_send:
            client.publish(COMMAND_TOPIC, json.dumps(command))
            print(f"  -> sent {command}")
            next_send = time.time() + RESEND_INTERVAL_S

        value = _latest.get(key)

        if value is not None and predicate(value):
            return value

        time.sleep(0.5)

    print(f"FAIL: timed out waiting for: {description}")
    print("  Check `docker compose logs sitl` and `docker compose logs drone_backend`.")
    sys.exit(1)


def fly_to(name, lat, lon, client):
    execute_command(
        "telemetry",
        lambda t, lat=lat, lon=lon: (
            t.get("lat") is not None
            and horizontal_distance_m(t["lat"], t["lon"], lat, lon) < ARRIVAL_TOLERANCE_M
        ),
        LEG_TIMEOUT_S, f"arrival at {name} ({lat:.6f}, {lon:.6f})",
        command={"type": "goto", "lat": lat, "lon": lon, "alt": TAKEOFF_ALT_M}, client=client,
    )
    print(f"  reached {name}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    home = wait_for("home", lambda h: True, 30, "retained home position")
    origin_lat, origin_lon = home["lat"], home["lon"]

    print(f"\n=== Takeoff to {TAKEOFF_ALT_M}m ===")
    execute_command(
        "telemetry",
        lambda t: t.get("armed") and (t.get("alt_rel") or 0) > TAKEOFF_ALT_M * 0.9,
        60, f"armed and within 90% of {TAKEOFF_ALT_M}m",
        command={"type": "takeoff", "alt": TAKEOFF_ALT_M}, client=client,
    )
    print("  airborne")

    print(f"\n=== Flying a {SIDE_M:.0f}m square centered on launch ===")
    # Compass/local-ENU convention: north = "top", east = "right" -- same
    # as everywhere else in this codebase (matplotlib_view.py's plot,
    # circle_point()'s bearing). Launch/home is the square's center, so
    # each corner is +/-HALF_SIDE_M on both axes, not offset from it the
    # way test_flight.py's square is.
    top_left = offset_to_lla(origin_lat, origin_lon, -HALF_SIDE_M, HALF_SIDE_M)
    top_right = offset_to_lla(origin_lat, origin_lon, HALF_SIDE_M, HALF_SIDE_M)
    bottom_right = offset_to_lla(origin_lat, origin_lon, HALF_SIDE_M, -HALF_SIDE_M)
    bottom_left = offset_to_lla(origin_lat, origin_lon, -HALF_SIDE_M, -HALF_SIDE_M)

    route = [
        ("Top-Left", top_left),
        ("Top-Right", top_right),
        ("Bottom-Right", bottom_right),
        ("Bottom-Left", bottom_left),
        ("Top-Left (closing the loop)", top_left),
    ]
    for name, (lat, lon) in route:
        fly_to(name, lat, lon, client)

    print("\n=== Returning to center ===")
    fly_to("Center (launch point)", origin_lat, origin_lon, client)

    print("\n=== Landing ===")
    execute_command(
        "telemetry", lambda t: not t.get("armed"),
        60, "landed and disarmed",
        command={"type": "land"}, client=client,
    )
    print("  landed and disarmed")

    print("\nPASS: full flight completed (takeoff -> square around launch -> center -> land).")
    client.loop_stop()


if __name__ == "__main__":
    main()
