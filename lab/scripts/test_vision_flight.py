#!/usr/bin/env python3
"""Scripted vision flight: mimics a route-3-style waypoint/hover/circle
mission (takeoff -> waypoints -> hover -> waypoints -> circle -> waypoints
-> fly home -> land), running YOLO person-detection against the live camera
feed at each hover/circle stop -- the CV counterpart to test_flight.py's
square pattern and test_circle.py's circle/interrupt exercise.

Talks flight control over the same MQTT command/telemetry contract as
test_flight.py/test_circle.py. Vision is a second, independent MQTT feed:
new-gui's `VIDEO_STREAM/+/frame` (see cv/frame-collection.py), decoded and
run through the same yolo26n.pt model as cv/detect-people.py.

Mission-format note: this was adapted from a route-plan JSON built for a
different framework (per-state classes like FlyWaypoints/BriarHover/
CircleTargetPosition, each with their own speed and gimbal-stare args).
drone_backend.py's command contract doesn't have those knobs:
  - "goto" has no speed parameter at all -- default_speed/target_approach_speed
    from the source plan are recorded in comments below but don't do anything
    here. Only "circle" has a speed (see mavlink_lib.circle_point).
  - There's no gimbal/camera-pointing command, so stare_pitch/stare_position
    can't be sent anywhere. Instead, at each hover and during the circle,
    this script pulls whatever frame most recently arrived on VIDEO_STREAM
    and runs person-detection on it -- an actual capability this codebase
    has (cv/yolo26n.pt), standing in for "stare and look".
  - VIDEO_STREAM frames are only published if new-gui's camera simulation is
    running (see ARCHITECTURE.md -- off by default); if none ever arrive,
    detection is skipped rather than failing the flight. ultralytics is also
    optional here for the same reason (cv/requirements.txt, not installed by
    default) -- its absence downgrades detection to a skipped step, not a
    failure.

Requires paho-mqtt (client/requirements.txt) always; ultralytics
(cv/requirements.txt) only if you want detection to actually run.
"""
import base64
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

# new-gui publishes camera frames under the drone's color name (see
# ARCHITECTURE.md's UPDATE_DRONE_COLORS), not VEHICLE_ID, and this script has
# no way to look that mapping up -- so subscribe to every drone's feed the
# same way cv/frame-collection.py does. Fine for the lab's usual one-drone
# setup; set VIDEO_STREAM_NAME to a specific color to filter if more than one
# drone is streaming at once.
VIDEO_STREAM_NAME_FILTER = os.environ.get("VIDEO_STREAM_NAME", "+")
FRAME_TOPIC_FILTER = f"VIDEO_STREAM/{VIDEO_STREAM_NAME_FILTER}/frame"

YOLO_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "cv", "yolo26n.pt"
)
PERSON_CLASS = 0  # COCO class id, same as cv/detect-people.py
DETECT_CONF = 0.25

EARTH_RADIUS_M = 6378137.0
ARRIVAL_TOLERANCE_M = 2.0
RESEND_INTERVAL_S = 8.0

TAKEOFF_ALT_M = 10.0  # route-3's Takeoff.altitude; waypoints below climb to 20m via goto

_latest = {"frame": None}
_yolo_model = None
_yolo_load_attempted = False


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe(HOME_TOPIC)
    client.subscribe(TELEMETRY_TOPIC)
    client.subscribe(FRAME_TOPIC_FILTER)


def on_message(client, userdata, msg):
    if msg.topic == HOME_TOPIC:
        try:
            _latest["home"] = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
    elif msg.topic == TELEMETRY_TOPIC:
        try:
            _latest["telemetry"] = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
    else:
        # VIDEO_STREAM/{name}/frame -- same envelope as cv/frame-collection.py
        try:
            envelope = json.loads(msg.payload)
            image_bytes = base64.b64decode(envelope["image_b64"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return
        _latest["frame"] = image_bytes


def offset_to_lla(origin_lat, origin_lon, east_m, north_m):
    """Small ENU offset -> lat/lon, same throwaway-local-frame idea used by
    test_flight.py/test_circle.py, only needed here for the circle's start
    point (the mission's own waypoints are already absolute lat/lon).
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
    as test_flight.py/test_circle.py's wait_for().
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


def fly_to(client, lat, lon, alt, description):
    wait_for(
        "telemetry",
        lambda t, lat=lat, lon=lon: (
            t.get("lat") is not None
            and horizontal_distance_m(t["lat"], t["lon"], lat, lon) < ARRIVAL_TOLERANCE_M
        ),
        60, f"arrival within {ARRIVAL_TOLERANCE_M}m of {description} ({lat:.6f}, {lon:.6f})",
        command={"type": "goto", "lat": lat, "lon": lon, "alt": alt}, client=client,
    )
    print(f"  reached {description}")


def load_yolo_model():
    """Lazy, best-effort: only imports ultralytics (and loads the model)
    once something is actually available to run it on, and never treats its
    absence as fatal -- see the module docstring's VIDEO_STREAM/ultralytics
    note.
    """
    global _yolo_model, _yolo_load_attempted
    if _yolo_load_attempted:
        return _yolo_model
    _yolo_load_attempted = True
    try:
        from ultralytics import YOLO
    except ImportError:
        print("  (ultralytics not installed -- skipping detection; see cv/requirements.txt)")
        return None
    if not os.path.exists(YOLO_MODEL_PATH):
        print(f"  (model not found at {YOLO_MODEL_PATH} -- skipping detection)")
        return None
    _yolo_model = YOLO(YOLO_MODEL_PATH)
    return _yolo_model


def detect_people(reason):
    """Run person-detection on whatever camera frame most recently arrived,
    standing in for the source mission's gimbal "stare" at each hover/circle
    stop (see module docstring). No-ops quietly if no frame has arrived yet
    or ultralytics isn't available.
    """
    frame_bytes = _latest.get("frame")
    if frame_bytes is None:
        print(f"  [vision] no camera frame received yet ({reason}) -- skipping detection")
        return
    model = load_yolo_model()
    if model is None:
        return

    import io

    from PIL import Image

    image = Image.open(io.BytesIO(frame_bytes))
    result = model(image, classes=[PERSON_CLASS], conf=DETECT_CONF, verbose=False)[0]
    n = len(result.boxes)
    print(f"  [vision] {reason}: {n} person(s) detected")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    home = wait_for("home", lambda h: True, 30, "retained home position")
    home_lat, home_lon = home["lat"], home["lon"]

    print(f"\n=== Takeoff to {TAKEOFF_ALT_M}m ===")
    wait_for(
        "telemetry",
        lambda t: t.get("armed") and (t.get("alt_rel") or 0) > TAKEOFF_ALT_M * 0.9,
        60, f"armed and within 90% of {TAKEOFF_ALT_M}m",
        command={"type": "takeoff", "alt": TAKEOFF_ALT_M}, client=client,
    )
    print("  airborne")

    # route-3-Fly1: default_speed 8.0 (not settable -- see module docstring)
    print("\n=== route-3-Fly1 ===")
    fly_to(client, 41.69843154249188, -86.23673178664703, 20.0, "Fly1 waypoint")

    # route-3-FlyHover2: waypoint leading into the hover below
    print("\n=== route-3-FlyHover2 ===")
    fly_to(client, 41.69626459702116, -86.23658694736022, 20.0, "FlyHover2 waypoint")

    # route-3-Hover2: BriarHover(hover_time=15.0). GUIDED holds position once
    # a goto target is reached (same as the pause between test_flight.py's
    # square legs), so "hover" here is just: stay put and watch the camera
    # feed for hover_time seconds. stare_position (41.696293, -86.235949,
    # 20.0) isn't sent anywhere -- no gimbal command exists -- but is where
    # the source mission wanted the camera pointed, which is what the vision
    # check below approximates.
    print("\n=== route-3-Hover2: hovering 15s, watching for people ===")
    hover_time_s = 15.0
    hover_deadline = time.time() + hover_time_s
    while time.time() < hover_deadline:
        detect_people("hovering")
        time.sleep(3.0)
    print("  hover complete")

    # route-3-Fly3: two waypoints in sequence
    print("\n=== route-3-Fly3 ===")
    fly_to(client, 41.69541542287734, -86.23651720992584, 20.0, "Fly3 waypoint 1")
    fly_to(client, 41.695335311530314, -86.23853959552306, 20.0, "Fly3 waypoint 2")

    # route-3-Circle4: CircleTargetPosition. circle_speed (3.5 m/s) and
    # target_circle_radius/height map onto the backend's circle command
    # directly; target_approach_speed (15.0, speed en route to the circle's
    # start point) has nothing to bind to since goto has no speed knob.
    # Same "fly to bearing-0 start point first" approach as test_circle.py,
    # since drone_backend.py's circle always starts due north of center.
    print("\n=== route-3-Circle4 ===")
    circle_center_lat, circle_center_lon = 41.69692550310074, -86.23864151946563
    circle_radius_m = 25.0
    circle_height_m = 30.0
    circle_speed_mps = 3.5
    sweep_deg = 360.0

    start_lat, start_lon = offset_to_lla(circle_center_lat, circle_center_lon, 0, circle_radius_m)
    fly_to(client, start_lat, start_lon, circle_height_m, "circle start point")

    print(f"  sweeping {sweep_deg:.0f} deg at {circle_speed_mps} m/s, watching for people")
    circle_command = {
        "type": "circle", "lat": circle_center_lat, "lon": circle_center_lon,
        "alt": circle_height_m, "radius": circle_radius_m,
        "degrees": sweep_deg, "speed": circle_speed_mps,
    }
    client.publish(COMMAND_TOPIC, json.dumps(circle_command))
    print(f"  -> sent {circle_command}")

    # No telemetry field marks "degrees swept" (same situation test_circle.py
    # notes) -- the rate is deterministic, so time it rather than poll.
    angular_rate_deg_s = math.degrees(circle_speed_mps / circle_radius_m)
    sweep_duration_s = sweep_deg / angular_rate_deg_s
    sweep_deadline = time.time() + sweep_duration_s
    while time.time() < sweep_deadline:
        detect_people("circling")
        time.sleep(3.0)
    print("  circle complete")

    # route-3-Fly5
    print("\n=== route-3-Fly5 ===")
    fly_to(client, 41.69829135414359, -86.23870052806396, 20.0, "Fly5 waypoint")

    # GoHome: FlyHome(speed=15.0). fly_home has no speed parameter either --
    # it transits at max(current_alt, FLY_HOME_MIN_ALT_M) (see
    # drone_backend.py); land is a deliberately separate follow-up command,
    # same as after any goto.
    print("\n=== GoHome ===")
    wait_for(
        "telemetry",
        lambda t: (
            t.get("lat") is not None
            and horizontal_distance_m(t["lat"], t["lon"], home_lat, home_lon) < ARRIVAL_TOLERANCE_M
        ),
        60, f"arrival within {ARRIVAL_TOLERANCE_M}m of home ({home_lat:.6f}, {home_lon:.6f})",
        command={"type": "fly_home"}, client=client,
    )
    print("  reached home")

    # Land + Disarm: land triggers ArduPilot's own auto-disarm on touchdown,
    # same as test_flight.py/test_circle.py -- no separate disarm command
    # needed to satisfy "not armed".
    print("\n=== Land ===")
    wait_for(
        "telemetry", lambda t: not t.get("armed"),
        60, "landed and disarmed",
        command={"type": "land"}, client=client,
    )
    print("  landed and disarmed")

    print("\nPASS: vision flight completed (takeoff -> waypoints -> hover -> "
          "waypoints -> circle -> waypoints -> fly home -> land).")
    client.loop_stop()


if __name__ == "__main__":
    main()
