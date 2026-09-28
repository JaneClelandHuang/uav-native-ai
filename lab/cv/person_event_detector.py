#!/usr/bin/env python3
"""person_event_detector.py -- live YOLO person detection that raises events.

Subscribes to every drone's simulated camera (new-gui's
VIDEO_STREAM/{color}/frame), runs yolo26n on the newest frame from each
drone, geolocates each detected person (geolocate.py -- trivial for a
north-up nadir camera) and publishes a DetectionEvent on mission/events
(QoS 1) when a person is first confirmed, and again at most every
REANNOUNCE_S while they're still being seen:

    {"event_id": "...", "type": "person", "lat": ..., "lon": ...,
     "confidence": 0.82, "source_uav": "1", "source_drone": "Fuchsia",
     "timestamp": ..., "image_b64": "<annotated JPEG of the detection>"}

Two filters stand between a YOLO box and an event:

  * Confirmation -- a new person needs MIN_HITS detections within
    DEDUP_RADIUS_M of each other inside CONFIRM_WINDOW_S. One-frame false
    positives never become events.
  * De-duplication -- once reported, further detections within
    DEDUP_RADIUS_M of that person are the same person (a drone circling a
    victim sees them in every frame); they don't raise new events, except
    for a re-announcement every REANNOUNCE_S. The planner merges those into
    the person it already knows, and asks about them again only if no
    decision was ever made (timeout, no UAV free) -- and an event lost while
    the planner was down gets another chance.
    Limitation: two real people closer than DEDUP_RADIUS_M merge into one.

Frames arrive every ~0.3 s per streaming drone and CPU inference can be
slower than that, so the MQTT callback only keeps the *latest* frame per
drone and a worker thread processes whatever is newest -- stale frames are
dropped, never queued.

Requirements: cv/requirements.txt (ultralytics, CPU torch, paho-mqtt), and
new-gui running with camera simulation on and the drone's camera set to
STREAMING. Frames without a "pose" (an older new-gui) are skipped.

    python person_event_detector.py [--conf 0.35] [--min-hits 2] [--save-dir data/events]
"""
import argparse
import base64
import io
import json
import logging
import os
import threading
import time
import uuid

import paho.mqtt.client as mqtt

from geolocate import distance_m, pixel_to_latlon

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
FRAME_TOPIC_FILTER = "VIDEO_STREAM/+/frame"
EVENTS_TOPIC = "mission/events"

HERE = os.path.dirname(os.path.abspath(__file__))
PERSON_CLASS = 0  # COCO "person"

DEDUP_RADIUS_M = 10.0
CONFIRM_WINDOW_S = 5.0
REANNOUNCE_S = 30.0

# new-gui names drones by color; VEHICLE_ID n is UPDATE_DRONE_COLORS[n-1]
# (must match backend/drone_backend.py).
UPDATE_DRONE_COLORS = ["Fuchsia", "Navy", "Purple", "Aqua", "Lime", "Orange", "Yellow"]

log = logging.getLogger("detector")


def vehicle_for_color(color):
    try:
        return str(UPDATE_DRONE_COLORS.index(color) + 1)
    except ValueError:
        return None


class PersonTracker:
    """Turns a stream of geolocated detections into one event per person.

    Pure logic (no MQTT, no YOLO) so it can be unit tested. observe()
    returns a dict describing a person to announce (newly confirmed, or
    due for re-announcement), or None.
    """

    def __init__(self, radius_m=DEDUP_RADIUS_M, min_hits=2, window_s=CONFIRM_WINDOW_S,
                 reannounce_s=REANNOUNCE_S):
        self.radius_m = radius_m
        self.min_hits = min_hits
        self.window_s = window_s
        self.reannounce_s = reannounce_s
        self.known = []       # confirmed persons: {"lat", "lon", "confidence", "announced"}
        self.tentative = []   # {"lat", "lon", "hits", "first", "confidence", "frames"}

    def observe(self, lat, lon, confidence, now, frame_id=None):
        """frame_id -- which frame this detection came from. Hits are
        counted per distinct frame, so two boxes in one frame can never
        confirm each other. None means every call is its own frame."""
        for person in self.known:
            if distance_m(person["lat"], person["lon"], lat, lon) <= self.radius_m:
                person["confidence"] = max(person["confidence"], confidence)
                if now - person["announced"] < self.reannounce_s:
                    return None
                person["announced"] = now
                return {k: person[k] for k in ("lat", "lon", "confidence")}
        self.tentative = [c for c in self.tentative if now - c["first"] <= self.window_s]
        for cand in self.tentative:
            if distance_m(cand["lat"], cand["lon"], lat, lon) <= self.radius_m:
                if frame_id is not None and frame_id in cand["frames"]:
                    return None  # another box in a frame already counted
                cand["frames"].add(frame_id)
                cand["hits"] += 1
                # running mean position: repeated sightings refine the estimate
                cand["lat"] += (lat - cand["lat"]) / cand["hits"]
                cand["lon"] += (lon - cand["lon"]) / cand["hits"]
                cand["confidence"] = max(cand["confidence"], confidence)
                break
        else:
            cand = {"lat": lat, "lon": lon, "hits": 1, "first": now, "confidence": confidence,
                    "frames": {frame_id}}
            self.tentative.append(cand)
        if cand["hits"] >= self.min_hits:
            self.tentative.remove(cand)
            person = {"lat": cand["lat"], "lon": cand["lon"], "confidence": cand["confidence"]}
            self.known.append({**person, "announced": now})
            return person
        return None


class Detector:
    def __init__(self, model_path, conf, tracker, save_dir=None):
        from ultralytics import YOLO  # heavy import, only when actually running
        self.model = YOLO(model_path)
        self.conf = conf
        self.tracker = tracker
        self.save_dir = save_dir
        self._latest = {}              # drone color -> envelope (newest only)
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._warned_no_pose = set()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = lambda c, *a: c.subscribe(FRAME_TOPIC_FILTER)
        self.client.on_message = self._on_message

    def _on_message(self, client, userdata, msg):
        try:
            envelope = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        color = envelope.get("drone") or msg.topic.split("/")[1]
        with self._lock:
            self._latest[color] = envelope  # overwrite: stale frames are dropped
        self._wake.set()

    def _worker(self):
        while True:
            self._wake.wait()
            self._wake.clear()
            with self._lock:
                batch, self._latest = self._latest, {}
            for color, envelope in batch.items():
                try:
                    self._process(color, envelope)
                except Exception:  # one bad frame must not kill the detector
                    log.exception("Failed to process frame from %s", color)

    def _process(self, color, envelope):
        pose = envelope.get("pose")
        if pose is None:
            if color not in self._warned_no_pose:
                log.warning("Frames from %s carry no pose -- update new-gui; skipping them", color)
                self._warned_no_pose.add(color)
            return
        from PIL import Image
        image = Image.open(io.BytesIO(base64.b64decode(envelope["image_b64"]))).convert("RGB")
        width, height = image.size
        result = self.model(image, classes=[PERSON_CLASS], conf=self.conf, verbose=False)[0]
        frame_id, now = object(), time.time()  # one identity and time for every box in this frame
        for box in result.boxes:
            u, v = box.xywh[0][:2].tolist()   # bbox centre, pixels
            confidence = float(box.conf[0])
            lat, lon = pixel_to_latlon(u, v, width, height, pose)
            person = self.tracker.observe(lat, lon, confidence, now, frame_id)
            if person is not None:
                self._raise_event(person, color, result)

    def _raise_event(self, person, color, result):
        from PIL import Image
        annotated = Image.fromarray(result.plot()[..., ::-1])  # plot() is BGR
        buf = io.BytesIO()
        annotated.save(buf, format="JPEG", quality=80)
        event = {
            "event_id": uuid.uuid4().hex[:8], "type": "person",
            "lat": person["lat"], "lon": person["lon"], "confidence": person["confidence"],
            "source_uav": vehicle_for_color(color), "source_drone": color,
            "timestamp": time.time(),
            "image_b64": base64.b64encode(buf.getvalue()).decode("ascii"),
        }
        # QoS 1: the broker holds it for the planner's persistent session
        # if the planner is momentarily down.
        self.client.publish(EVENTS_TOPIC, json.dumps(event), qos=1)
        log.info("EVENT person at (%.6f, %.6f) conf %.2f from %s (UAV %s)",
                 person["lat"], person["lon"], person["confidence"], color, event["source_uav"])
        if self.save_dir:
            os.makedirs(self.save_dir, exist_ok=True)
            annotated.save(os.path.join(self.save_dir, f"{event['event_id']}-{color}.jpg"))

    def run(self):
        self.client.connect(MQTT_HOST, MQTT_PORT)
        self.client.loop_start()
        threading.Thread(target=self._worker, daemon=True, name="yolo").start()
        log.info("Watching %s for people (conf >= %.2f)", FRAME_TOPIC_FILTER, self.conf)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.client.loop_stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=os.path.join(HERE, "yolo26n.pt"))
    parser.add_argument("--conf", type=float, default=0.25,
                        help="YOLO confidence threshold (same default as detect-people.py)")
    parser.add_argument("--min-hits", type=int, default=2, help="co-located detections needed to confirm a person")
    parser.add_argument("--save-dir", default=os.path.join(HERE, "data", "events"),
                        help="where to save an annotated image of each event ('' to disable)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    Detector(args.model, args.conf, PersonTracker(min_hits=args.min_hits), args.save_dir or None).run()


if __name__ == "__main__":
    main()
