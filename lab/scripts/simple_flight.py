#!/usr/bin/env python3
"""The same mission as test_flight.py -- arm, takeoff, two waypoints, home,
land -- but with **no MQTT**: this script is itself the only pymavlink
speaker, talking straight to the autopilot. Meant to be read/shown before
introducing the MQTT layer, so students see what's actually being commanded
underneath it.

This means it can't run alongside the normal stack -- drone_backend.py is
normally the one thing bound to udpin:0.0.0.0:14550 that SITL's
--out=udpout:drone_backend:14550 connects to (see ARCHITECTURE.md's "one
pymavlink speaker" rationale). Run this in drone_backend's place instead of
adding a second speaker:

    docker compose up -d mosquitto sitl
    docker compose stop drone_backend      # free up the connection
    docker compose run --rm --no-deps --use-aliases \\
      -v "$(pwd)/scripts/simple_flight.py:/app/simple_flight.py" \\
      drone_backend python simple_flight.py

--use-aliases is required -- without it, this one-off container doesn't get
the "drone_backend" network alias SITL's --out is hardcoded to connect to.

Requires pymavlink (already in backend/requirements.txt, which is why this
runs inside the drone_backend image rather than needing its own venv).
"""
import math
import os
import sys
import time

from pymavlink import mavutil

import mavlink_lib

MAVLINK_CONN = os.environ.get("MAVLINK_CONN", "udpin:0.0.0.0:14550")

EARTH_RADIUS_M = 6378137.0

TAKEOFF_ALT_M = 10.0
WAYPOINT_1_OFFSET_M = (0.0, 15.0)   # (east, north) from home
WAYPOINT_2_OFFSET_M = (15.0, 15.0)
ARRIVAL_TOLERANCE_M = 2.0
RESEND_INTERVAL_S = 4.0


def offset_to_lla(origin_lat, origin_lon, east_m, north_m):
    lat0_rad = math.radians(origin_lat)
    dlat = math.degrees(north_m / EARTH_RADIUS_M)
    dlon = math.degrees(east_m / (EARTH_RADIUS_M * math.cos(lat0_rad)))
    return origin_lat + dlat, origin_lon + dlon


def horizontal_distance_m(lat1, lon1, lat2, lon2):
    lat0_rad = math.radians((lat1 + lat2) / 2)
    dx = math.radians(lon2 - lon1) * math.cos(lat0_rad) * EARTH_RADIUS_M
    dy = math.radians(lat2 - lat1) * EARTH_RADIUS_M
    return math.hypot(dx, dy)


def connect():
    print(f"Connecting to {MAVLINK_CONN} ...")
    conn = mavlink_lib.connect(MAVLINK_CONN)
    print(f"  heartbeat from system {conn.target_system} component {conn.target_component}")
    return conn


def current_position(conn, timeout=30):
    msg = conn.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=timeout)
    if msg is None:
        sys.exit("FAIL: no GLOBAL_POSITION_INT received -- is SITL running?")
    return msg.lat / 1e7, msg.lon / 1e7


def wait_until(conn, description, predicate, timeout, on_tick):
    """Drain incoming mavlink messages into `state` until `predicate(state)`
    holds, resending `on_tick`'s command every RESEND_INTERVAL_S so a
    dropped UDP packet or a transient pre-arm rejection doesn't just fail
    the script -- same self-healing idea as test_flight.py's wait_for, just
    reading straight off the connection instead of MQTT telemetry.
    """
    print(f"Waiting up to {timeout:.0f}s: {description}")
    state = {}
    deadline = time.time() + timeout
    next_tick = 0.0
    while time.time() < deadline:
        if time.time() >= next_tick:
            on_tick()
            next_tick = time.time() + RESEND_INTERVAL_S
        msg = conn.recv_match(blocking=True, timeout=0.5)
        if msg is None:
            continue
        msg_type = msg.get_type()
        if msg_type == "GLOBAL_POSITION_INT":
            state["lat"] = msg.lat / 1e7
            state["lon"] = msg.lon / 1e7
            state["alt_rel"] = msg.relative_alt / 1000.0
        elif msg_type == "HEARTBEAT" and msg.get_srcComponent() == mavutil.mavlink.MAV_COMP_ID_AUTOPILOT1:
            state["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        if predicate(state):
            return state
    print(f"FAIL: timed out waiting for: {description}")
    sys.exit(1)


def arm_and_takeoff(conn, alt_m):
    # mavlink_lib.takeoff does the GUIDED/arm/NAV_TAKEOFF sequence as one
    # complete action; resending it every tick makes it restartable instead
    # of a fragile one-shot mode/arm/takeoff dance.
    def send():
        mavlink_lib.takeoff(conn, alt_m)

    wait_until(
        conn, f"armed and within 90% of {alt_m}m",
        predicate=lambda s: s.get("armed") and (s.get("alt_rel") or 0) > alt_m * 0.9,
        timeout=60, on_tick=send,
    )


def goto(conn, lat, lon, alt_m, description):
    def send():
        mavlink_lib.goto(conn, lat, lon, alt_m)

    wait_until(
        conn, description,
        predicate=lambda s: (
            s.get("lat") is not None
            and horizontal_distance_m(s["lat"], s["lon"], lat, lon) < ARRIVAL_TOLERANCE_M
        ),
        timeout=30, on_tick=send,
    )


def land(conn):
    def send():
        mavlink_lib.land(conn)

    wait_until(conn, "landed and disarmed", predicate=lambda s: s.get("armed") is False, timeout=60, on_tick=send)


def main():
    conn = connect()

    origin_lat, origin_lon = current_position(conn)
    print(f"Home: ({origin_lat:.6f}, {origin_lon:.6f})")

    print(f"\n=== Arm + takeoff to {TAKEOFF_ALT_M}m ===")
    arm_and_takeoff(conn, TAKEOFF_ALT_M)
    print("  airborne")

    wp1 = offset_to_lla(origin_lat, origin_lon, *WAYPOINT_1_OFFSET_M)
    wp2 = offset_to_lla(origin_lat, origin_lon, *WAYPOINT_2_OFFSET_M)

    print("\n=== Waypoint 1 ===")
    goto(conn, *wp1, TAKEOFF_ALT_M, f"arrival within {ARRIVAL_TOLERANCE_M}m of waypoint 1 {wp1}")
    print(f"  reached ({wp1[0]:.6f}, {wp1[1]:.6f})")

    print("\n=== Waypoint 2 ===")
    goto(conn, *wp2, TAKEOFF_ALT_M, f"arrival within {ARRIVAL_TOLERANCE_M}m of waypoint 2 {wp2}")
    print(f"  reached ({wp2[0]:.6f}, {wp2[1]:.6f})")

    print("\n=== Return home ===")
    goto(conn, origin_lat, origin_lon, TAKEOFF_ALT_M, "arrival back at home position")
    print("  reached home")

    print("\n=== Land ===")
    land(conn)
    print("  landed and disarmed")

    print("\nPASS: mission complete (arm -> takeoff -> waypoint1 -> waypoint2 -> home -> land).")


if __name__ == "__main__":
    main()
