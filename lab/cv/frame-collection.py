#!/usr/bin/env python3
"""Stand-alone sample-frame collector for the CV assignment.

Subscribes to every drone's camera feed (`VIDEO_STREAM/+/frame`, published
by new-gui's CameraFramePublisher -- see camera_frame_publisher.py and
camera_config.py's camera_topic_template in the new-gui repo) and saves each
frame to disk as a JPEG, so students have real sample frames to run YOLO
against before deciding whether the stock model needs retraining on the
simulated ("fake") persons.

Session layout: one folder per drone per run, under data/, named
<drone>-<MM-DD-YYYY>-<seq>, e.g. data/Lime-08-10-2026-001/. A folder is
created lazily the first time a given drone's frame arrives (not one per
program, and not one shared by all drones) -- new-gui may have any number
of drones streaming at once, and giving each its own sequentially-numbered
folder avoids interleaving frames from different drones into one directory
or racing on a shared counter. `seq` is per drone per calendar day: restart
the collector the same day and Lime's frames start a fresh 002 folder next
to 001 rather than overwriting it; a different drone (or the same drone
tomorrow) starts back at 001. Frames within a folder are named
frame_00001.jpg, frame_00002.jpg, ... in arrival order.

Only needs paho-mqtt -- no PyQt5/Pillow -- since image_b64 decodes straight
to on-disk JPEG bytes with no re-encoding.
"""
import base64
import json
import os
import re
from datetime import date

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

FRAME_TOPIC_FILTER = "VIDEO_STREAM/+/frame"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CV_DATA_DIR", os.path.join(SCRIPT_DIR, "data"))

# Drone names are HTML/CSS color words (see UPDATE_DRONE_COLORS in
# ARCHITECTURE.md), but the topic segment is attacker-reachable over MQTT --
# refuse to build a folder name out of anything that isn't safely
# filesystem-friendly rather than trusting it blindly.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

_FORMAT_EXT = {"jpeg": "jpg", "jpg": "jpg", "png": "png"}

# drone name -> {"dir": str, "count": int}
_sessions = {}


def _next_session_dir(name, date_str):
    prefix = f"{name}-{date_str}-"
    seqs = [
        int(d[len(prefix):])
        for d in os.listdir(DATA_DIR)
        if d.startswith(prefix) and d[len(prefix):].isdigit()
    ]
    seq = max(seqs, default=0) + 1
    return os.path.join(DATA_DIR, f"{prefix}{seq:03d}")


def _session_for(name):
    session = _sessions.get(name)
    if session is not None:
        return session
    session_dir = _next_session_dir(name, date.today().strftime("%m-%d-%Y"))
    os.makedirs(session_dir, exist_ok=True)
    print(f"[{name}] new session: {session_dir}")
    session = {"dir": session_dir, "count": 0}
    _sessions[name] = session
    return session


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT} ({reason_code})")
    client.subscribe(FRAME_TOPIC_FILTER)
    print(f"Subscribed to {FRAME_TOPIC_FILTER}")


def on_message(client, userdata, msg):
    # VIDEO_STREAM/{name}/frame -- name is whatever the "+" matched.
    parts = msg.topic.split("/")
    if len(parts) != 3:
        return
    name = parts[1]
    if not _SAFE_NAME.match(name):
        print(f"Ignoring frame from unsafe drone name {name!r}")
        return

    try:
        envelope = json.loads(msg.payload)
        image_bytes = base64.b64decode(envelope["image_b64"])
    except (json.JSONDecodeError, KeyError, ValueError) as ex:
        print(f"[{name}] bad frame payload: {ex}")
        return

    ext = _FORMAT_EXT.get(envelope.get("format", "jpeg"), "jpg")
    session = _session_for(name)
    session["count"] += 1
    frame_path = os.path.join(session["dir"], f"frame_{session['count']:05d}.{ext}")
    with open(frame_path, "wb") as f:
        f.write(image_bytes)
    print(f"[{name}] saved {os.path.basename(frame_path)} ({len(image_bytes)} bytes)")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)

    print("Collecting frames -- Ctrl+C to stop.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        for name, session in _sessions.items():
            print(f"[{name}] {session['count']} frame(s) -> {session['dir']}")


if __name__ == "__main__":
    main()
