#!/usr/bin/env python3
"""Scripted test flight: arm+takeoff, fly a small square, then land.

Talks only over the MQTT command/telemetry contract -- this is exactly what
a student-built frontend does, just scripted instead of driven from a GUI.
Uses relative altitude throughout (alt_rel); mission/geofence work with
absolute altitude is Stage 4, not this.

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

TAKEOFF_ALT_M = 10.0
LEG_M = 15.0  # side length of the flight square
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
    `command` every RESEND_INTERVAL_S. That resend makes this self-heal
    against a dropped UDP command or a transient pre-arm-check rejection
    right after a cold start -- the same class of flakiness verify_setup.py
    documents, rather than a one-shot send that just fails.
    """
    print(f"Waiting up to {timeout:.0f}s: {description}")
    deadline = time.time() + timeout
    next_send = 0.0
    while time.time() < deadline:
        if command is not None and time.time() >= next_send:
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


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    home = wait_for("home", lambda h: True, 30, "retained home position")
    origin_lat, origin_lon = home["lat"], home["lon"]

    print(f"\n=== Takeoff to {TAKEOFF_ALT_M}m ===")
    wait_for(
        "telemetry",
        lambda t: t.get("armed") and (t.get("alt_rel") or 0) > TAKEOFF_ALT_M * 0.9,
        60, f"armed and within 90% of {TAKEOFF_ALT_M}m",
        command={"type": "takeoff", "alt": TAKEOFF_ALT_M}, client=client,
    )
    print("  airborne")

    print("\n=== Flying a small square ===")
    waypoints = [
        offset_to_lla(origin_lat, origin_lon, 0, LEG_M),
        offset_to_lla(origin_lat, origin_lon, LEG_M, LEG_M),
        offset_to_lla(origin_lat, origin_lon, LEG_M, 0),
        (origin_lat, origin_lon),
    ]
    for lat, lon in waypoints:
        wait_for(
            "telemetry",
            lambda t, lat=lat, lon=lon: (
                t.get("lat") is not None
                and horizontal_distance_m(t["lat"], t["lon"], lat, lon) < ARRIVAL_TOLERANCE_M
            ),
            30, f"arrival within {ARRIVAL_TOLERANCE_M}m of ({lat:.6f}, {lon:.6f})",
            command={"type": "goto", "lat": lat, "lon": lon, "alt": TAKEOFF_ALT_M}, client=client,
        )
        print(f"  reached ({lat:.6f}, {lon:.6f})")

    print("\n=== Landing ===")
    wait_for(
        "telemetry", lambda t: not t.get("armed"),
        60, "landed and disarmed",
        command={"type": "land"}, client=client,
    )
    print("  landed and disarmed")

    print("\nPASS: full flight completed (takeoff -> square pattern -> land).")
    client.loop_stop()


if __name__ == "__main__":
    main()
