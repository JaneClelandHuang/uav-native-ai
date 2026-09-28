#!/usr/bin/env python3
"""inject_event.py -- publish a fake person detection on mission/events.

Develop and test your planner without the camera pipeline: this sends the
same message cv/person_event_detector.py sends when YOLO confirms a person,
minus the image.

    python inject_event.py 41.6992 -86.2370                  # person at lat, lon
    python inject_event.py 41.6992 -86.2370 --conf 0.31      # a weak detection
    python inject_event.py 41.6992 -86.2370 --repeat 3       # same person, seen 3 times

--repeat re-sends the same location with a new event_id each time, the way
the detector re-announces a person it keeps seeing. Your planner should not
ask the operator about them again once a decision has been made.
"""
import argparse
import json
import os
import time
import uuid

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lat", type=float)
    parser.add_argument("lon", type=float)
    parser.add_argument("--conf", type=float, default=0.82, help="detection confidence, 0-1")
    parser.add_argument("--uav", default="1", help="vehicle id of the UAV that 'saw' the person")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between repeats")
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()
    for i in range(args.repeat):
        if i:
            time.sleep(args.interval)
        event = {"event_id": uuid.uuid4().hex[:8], "type": "person", "lat": args.lat, "lon": args.lon,
                 "confidence": args.conf, "source_uav": args.uav, "source_drone": None,
                 "timestamp": time.time(), "image_b64": None}
        client.publish("mission/events", json.dumps(event), qos=1).wait_for_publish()
        print(f"sent {event['event_id']}: person at {args.lat:.6f}, {args.lon:.6f} conf {args.conf:.2f}")
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
