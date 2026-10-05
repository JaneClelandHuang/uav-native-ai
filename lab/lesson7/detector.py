#!/usr/bin/env python3
"""detector.py -- Stage 1 (detect) in flight, feeding Stages 2-4, publishing Stage 5.

Subscribes to every drone's simulated camera (new-gui's
VIDEO_STREAM/{color}/frame), finds objects that might be clues, geolocates
them (cv/geolocate.py), confirms each over several frames and de-duplicates
it with the same PersonTracker the person detector uses, then hands each new
object to YOUR clue pipeline (hw07/clues: pipeline.ClueAnalyzer) on a worker thread -- the
LLM calls take seconds, frames arrive every 0.3 s. Each result is published as
a ClueAssessment on mission/clues (QoS 1) and logged, with each crop, under
hw07/clues/data/flight/.

Two ways to find objects (Stage 1):

  default   YOLOE open-vocabulary detection, prompted with generic clue words
            (CLUE_CLASSES). A real detector: it misses things and flags junk.
  --oracle  No CV. Uses the scenario's ground truth: whenever a placed clue is
            inside a camera frame, crop it. For testing Stages 2-4 in flight
            when you need to know a miss is the prompts' fault, not YOLOE's.

    python detector.py scenarios/lost-child-stadium
    python detector.py scenarios/lost-child-stadium --oracle
    python detector.py scenarios/lost-child-stadium --no-llm     # Stage 1 only: log candidates

Requires new-gui running with camera simulation on, drones STREAMING, and the
scenario's clues placed in the scene (scenario_to_scene.py).
"""
import argparse
import base64
import io
import json
import logging
import math
import os
import queue
import sys
import threading
import time

import paho.mqtt.client as mqtt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cv"))

from geolocate import EARTH_RADIUS_M, footprint_m, pixel_to_latlon  # noqa: E402
from imaging import crop_b64, to_png_b64  # noqa: E402
from contract import Candidate  # noqa: E402
from person_event_detector import PersonTracker, vehicle_for_color  # noqa: E402
from scenario import load_scenario  # noqa: E402

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
FRAME_TOPIC_FILTER = "VIDEO_STREAM/+/frame"
CLUES_TOPIC = "mission/clues"

# What YOLOE is asked to look for: generic object words, never the specific
# person's items -- Stage 1 shouldn't know who we're searching for.
CLUE_CLASSES = ["backpack", "bag", "hat", "cap", "shoe", "sneaker", "jacket", "shirt", "clothing",
                "teddy bear", "stuffed toy", "doll", "toy", "bicycle", "bottle", "phone", "box",
                "blanket", "chair", "cone"]
DEDUP_RADIUS_M = 5.0

log = logging.getLogger("clue-detector")


def latlon_to_pixel(lat, lon, image_w, image_h, pose):
    """Inverse of geolocate.pixel_to_latlon for a north-up nadir frame."""
    width_m, height_m = footprint_m(pose)
    lat0, lon0 = float(pose["lat"]), float(pose["lon"])
    north_m = math.radians(lat - lat0) * EARTH_RADIUS_M
    east_m = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    return image_w / 2.0 + east_m * image_w / width_m, image_h / 2.0 - north_m * image_h / height_m


class YoloeFinder:
    def __init__(self, weights, conf, classes=CLUE_CLASSES):
        from ultralytics import YOLOE  # heavy import, only when actually used
        self.model = YOLOE(weights)
        self.model.set_classes(classes)
        self.conf = conf

    def find(self, image, pose):
        result = self.model(image, conf=self.conf, verbose=False)[0]
        for box in result.boxes:
            cx, cy, w, h = box.xywh[0].tolist()
            yield cx, cy, max(w, h), result.names[int(box.cls[0])], float(box.conf[0])


class OracleFinder:
    """Fake detector: reports every scenario clue that lies inside the frame.
    Labels are "unknown" -- the oracle knows the clue id, but Stage 2 must not."""

    def __init__(self, scenario):
        self.clues = [(c, scenario.object_width_m(c)) for c in scenario.clues]

    def find(self, image, pose):
        width_m, _ = footprint_m(pose)
        m_per_px = width_m / image.width
        for clue, size_m in self.clues:
            u, v = latlon_to_pixel(clue.lat, clue.lon, image.width, image.height, pose)
            if 0 <= u < image.width and 0 <= v < image.height:
                yield u, v, size_m / m_per_px, "unknown", 1.0  # no hints to the VLM


class ClueDetector:
    def __init__(self, finder, analyzer, save_dir, min_hits=2, scene_scale=1.0):
        self.finder = finder
        self.scene_scale = scene_scale   # sim objects are drawn larger than life; see scenario.py
        self.analyzer = analyzer            # None: --no-llm, just log candidates
        self.save_dir = save_dir
        self.tracker = PersonTracker(radius_m=DEDUP_RADIUS_M, min_hits=min_hits)
        self._latest = {}
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._jobs = queue.Queue()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = lambda c, *a: c.subscribe(FRAME_TOPIC_FILTER)
        self.client.on_message = self._on_message

    def _on_message(self, client, userdata, msg):
        try:
            envelope = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        with self._lock:
            self._latest[envelope.get("drone") or msg.topic.split("/")[1]] = envelope
        self._wake.set()

    def _frame_worker(self):
        while True:
            self._wake.wait()
            self._wake.clear()
            with self._lock:
                batch, self._latest = self._latest, {}
            for color, envelope in batch.items():
                try:
                    self._process(color, envelope)
                except Exception:
                    log.exception("Failed to process frame from %s", color)

    def _process(self, color, envelope):
        pose = envelope.get("pose")
        if pose is None:
            return
        from PIL import Image
        image = Image.open(io.BytesIO(base64.b64decode(envelope["image_b64"]))).convert("RGB")
        frame_id, now = object(), time.time()
        for u, v, size_px, label, conf in self.finder.find(image, pose):
            lat, lon = pixel_to_latlon(u, v, image.width, image.height, pose)
            if self.tracker.observe(lat, lon, conf, now, frame_id) is None:
                continue
            crop, scale = crop_b64(image, u, v, size_px / 2)
            width_m, _ = footprint_m(pose)
            candidate = Candidate(lat=lat, lon=lon, cv_label=label, cv_confidence=conf, crop_png_b64=crop,
                                  context_png_b64=to_png_b64(image),
                                  ground_m_per_px=width_m / image.width / scale / self.scene_scale,
                                  source_uav=vehicle_for_color(color))
            log.info("CANDIDATE %s '%s' (%.2f) at (%.6f, %.6f) from %s",
                     candidate.candidate_id, label, conf, lat, lon, color)
            self._save(candidate)
            if self.analyzer is not None:
                self._jobs.put(candidate)

    def _analysis_worker(self):
        while True:
            candidate = self._jobs.get()
            try:
                assessment = self.analyzer.analyze(candidate)
            except Exception:
                log.exception("Clue analysis failed for %s", candidate.candidate_id)
                continue
            payload = assessment.model_dump_json()
            self.client.publish(CLUES_TOPIC, payload, qos=1)
            with open(os.path.join(self.save_dir, "clues.jsonl"), "a") as f:
                f.write(payload + "\n")
            log.info("ASSESSED %s: %r relevance %s -> %s ($%.4f)", candidate.candidate_id,
                     assessment.object_type, assessment.relevance["relevance"],
                     assessment.decision["action"], assessment.cost_usd)

    def _save(self, candidate):
        os.makedirs(self.save_dir, exist_ok=True)
        with open(os.path.join(self.save_dir, f"{candidate.candidate_id}.png"), "wb") as f:
            f.write(base64.b64decode(candidate.crop_png_b64))
        with open(os.path.join(self.save_dir, "candidates.jsonl"), "a") as f:
            f.write(json.dumps(candidate.without_images()) + "\n")

    def run(self):
        self.client.connect(MQTT_HOST, MQTT_PORT)
        self.client.loop_start()
        threading.Thread(target=self._frame_worker, daemon=True, name="detect").start()
        if self.analyzer is not None:
            threading.Thread(target=self._analysis_worker, daemon=True, name="analyze").start()
        log.info("Watching %s for clues", FRAME_TOPIC_FILTER)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.client.loop_stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario", help="scenario directory (mission context; clue truth for --oracle)")
    parser.add_argument("--oracle", action="store_true", help="find clues from scenario ground truth, not YOLOE")
    parser.add_argument("--weights", default="yoloe-11s-seg.pt", help="YOLOE weights (downloaded on first use)")
    parser.add_argument("--conf", type=float, default=0.15, help="YOLOE confidence threshold")
    parser.add_argument("--min-hits", type=int, default=2, help="frames an object must be seen in before analysis")
    parser.add_argument("--no-llm", action="store_true", help="Stage 1 only: save candidates, skip Stages 2-4")
    parser.add_argument("--pipeline", help="your pipeline directory (default: hw07/clues)")
    parser.add_argument("--save-dir", help="where to log candidates and assessments (default: hw07/clues/data/flight)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s", datefmt="%H:%M:%S")

    scenario = load_scenario(args.scenario)
    finder = OracleFinder(scenario) if args.oracle else YoloeFinder(args.weights, args.conf)
    import student_code
    save_dir = args.save_dir or os.path.join(args.pipeline or student_code.DEFAULT_DIR, "data", "flight")
    analyzer = None
    if not args.no_llm:
        ClueAnalyzer, ClaudeBackend = student_code.load(args.pipeline)
        analyzer = ClueAnalyzer(ClaudeBackend(), scenario.mission)
    ClueDetector(finder, analyzer, save_dir, args.min_hits, scenario.scene_scale).run()


if __name__ == "__main__":
    main()
