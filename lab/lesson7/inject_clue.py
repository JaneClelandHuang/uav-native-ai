#!/usr/bin/env python3
"""inject_clue.py -- publish a fake ClueAssessment on mission/clues.

Develop your planner hookup (R7) without the camera, YOLOE, an API key or a
working pipeline: this sends a message in the same contract detector.py
publishes after your Stages 2-4.

    python inject_clue.py 41.698012 -86.238102                       # relevant -> converge_search
    python inject_clue.py 41.698012 -86.238102 --action log_only --relevance low
    python inject_clue.py 41.698012 -86.238102 --radius 120 --priority medium
"""
import argparse
import os
import sys

import paho.mqtt.client as mqtt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from contract import ACTIONS, ClueAssessment, LatLon, new_id  # noqa: E402

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
CLUES_TOPIC = "mission/clues"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lat", type=float)
    parser.add_argument("lon", type=float)
    parser.add_argument("--action", choices=ACTIONS, default="converge_search")
    parser.add_argument("--relevance", choices=("high", "medium", "low", "none"), default="high")
    parser.add_argument("--object", default="child's red baseball cap")
    parser.add_argument("--radius", type=float, default=80.0, help="converge_search radius, m")
    parser.add_argument("--priority", choices=("high", "medium", "low"), default="high")
    parser.add_argument("--uav", default="1", help="vehicle id that 'found' it")
    parser.add_argument("--mission", default="lost-child-stadium")
    args = parser.parse_args()

    converge = args.action == "converge_search"
    assessment = ClueAssessment(
        mission_id=args.mission,
        candidate={"candidate_id": new_id(), "lat": args.lat, "lon": args.lon, "cv_label": "injected",
                   "cv_confidence": 1.0, "source_uav": args.uav},
        descriptions=[{"object_type": args.object, "description": f"Injected test clue: {args.object}."}],
        relevance={"relevance": args.relevance, "rationale": "Injected."},
        decision={"action": args.action, "search_radius_m": args.radius if converge else None,
                  "priority": args.priority if converge else None, "rationale": "Injected."},
        search_center=LatLon(lat=args.lat, lon=args.lon) if converge else None,
    )
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()
    client.publish(CLUES_TOPIC, assessment.model_dump_json(), qos=1).wait_for_publish()
    client.loop_stop()
    client.disconnect()
    print(f"sent {assessment.assessment_id}: {args.object} at {args.lat:.6f}, {args.lon:.6f} -> {args.action}")


if __name__ == "__main__":
    main()
