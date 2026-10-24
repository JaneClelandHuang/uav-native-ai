#!/usr/bin/env python3
"""mischief_d4.py: D4 fault injection for testing your testing agent.

Run it from your team repo's root while your system and a normal run of your
use case are going. It waits for a drone to take off, then, at a random
moment, injects ONE fault chosen at random -- or nothing at all. It never
touches your code. It prints nothing about what it chose.

    python mischief_d4.py             # arm it; Ctrl-C when your agent is done
    python mischief_d4.py --reveal mischief-receipt-<time>.txt

Each run writes a receipt (mischief-receipt-<time>.txt) recording what was
injected, when, and on which drone. The receipt is encoded so you don't read
it by accident. Honor system: run your agent, commit its report, and only
then run --reveal and record whether your agent got it right.

What can be injected:
  SENSOR     a GPS, vibration, compass or battery fault on one drone
             (the Lesson 4 catalog, via the backend's inject_fault command)
  SILENT     one drone's backend is paused: its telemetry stops
  DETECTION  a person detection far outside any plausible search area
  MALFORMED  a broken message on mission/events, or impossible telemetry
             values published on one drone's telemetry topic
  NONE       nothing at all

Ctrl-C (or --duration running out) undoes the fault: SIM_ params go back to
their defaults and a paused backend is resumed.

Needs: paho-mqtt (already in your lab requirements), and lab/scripts/
mischief_maker.py (in your repo) for the sensor-fault catalog.
"""
import argparse
import base64
import json
import os
import random
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

CATEGORIES = ["SENSOR", "SILENT", "DETECTION", "MALFORMED", "NONE"]
WEIGHTS = [3, 2, 2, 2, 1]          # NONE about one run in ten
LIFTOFF_M = 2.0
AIRBORNE_S = 5.0                   # airborne this long counts as "taken off"

_telemetry = {}                    # vehicle id -> latest telemetry dict


def _on_message(client, userdata, msg):
    try:
        vid = msg.topic.split("/")[1]
        _telemetry[vid] = json.loads(msg.payload)
    except (ValueError, IndexError):
        pass


def _airborne(t):
    return bool(t.get("armed")) and (t.get("alt_rel") or 0) > LIFTOFF_M


def wait_for_takeoff(timeout):
    """Return the ids of drones that have been airborne for AIRBORNE_S, or [] on timeout."""
    since = {}
    deadline = time.time() + timeout
    while time.time() < deadline:
        now = time.time()
        for vid, t in list(_telemetry.items()):
            if _airborne(t):
                since.setdefault(vid, now)
            else:
                since.pop(vid, None)
        ready = [v for v, t0 in since.items() if now - t0 >= AIRBORNE_S]
        if ready:
            return sorted(ready)
        time.sleep(0.5)
    return []


def sensor_catalog(lab_scripts):
    sys.path.insert(0, str(lab_scripts))
    import mischief_maker as mm   # the Lesson 4 catalog, live-calibrated
    return mm


def compose_service(lab_dir, action, service):
    subprocess.run(["docker", "compose", action, service], cwd=lab_dir, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def choose(rng, drones, mm):
    """Pick the fault. Returns a plan dict; nothing is injected yet."""
    # MISCHIEF_D4_FORCE=<CATEGORY> is for instructors testing the tool, not for D4 runs.
    category = os.environ.get("MISCHIEF_D4_FORCE") or rng.choices(CATEGORIES, WEIGHTS)[0]
    vid = rng.choice(drones)
    plan = {"category": category}
    if category == "SENSOR":
        fault = rng.choice(mm.FAULT_TYPES)
        severity = rng.choice(["MEDIUM", "HIGH"])
        plan.update(drone=vid, fault=fault, severity=severity, params=mm.sample_params(fault, severity),
                    defaults=mm.FAULT_CATALOG[fault]["defaults"])
    elif category == "SILENT":
        plan.update(drone=vid, service=f"drone_backend_{vid}")
    elif category == "DETECTION":
        t = _telemetry[vid]
        plan.update(drone=vid, lat=t["lat"] + rng.choice([-1, 1]) * rng.uniform(0.2, 0.4),
                    lon=t["lon"] + rng.choice([-1, 1]) * rng.uniform(0.2, 0.4),
                    confidence=round(rng.uniform(0.85, 0.97), 2))
    elif category == "MALFORMED":
        plan.update(drone=vid, kind=rng.choice(["broken-event", "impossible-telemetry"]))
    return plan


def inject(client, plan, lab_dir):
    c = plan["category"]
    vid = plan.get("drone")
    if c == "SENSOR":
        client.publish(f"uav/{vid}/command", json.dumps({"type": "inject_fault", "params": plan["params"]}))
    elif c == "SILENT":
        compose_service(lab_dir, "pause", plan["service"])
        paused = subprocess.run(["docker", "compose", "ps", "--status", "paused", "--services"], cwd=lab_dir,
                                capture_output=True, text=True).stdout.split()
        if plan["service"] not in paused:      # compose "pauses" a stopped service without complaint
            raise subprocess.CalledProcessError(1, f"docker compose pause {plan['service']} (not running?)")
    elif c == "DETECTION":
        event = {"event_id": uuid.uuid4().hex[:8], "type": "person", "lat": plan["lat"], "lon": plan["lon"],
                 "confidence": plan["confidence"], "source_uav": vid, "source_drone": None,
                 "timestamp": time.time(), "image_b64": None}
        client.publish("mission/events", json.dumps(event), qos=1)
    elif c == "MALFORMED":
        if plan["kind"] == "broken-event":
            client.publish("mission/events", '{"event_id": "x9", "type": "person", "lat": "north", ', qos=1)
        else:
            bad = dict(_telemetry.get(vid, {}))
            bad.update(alt_rel=-35.0, battery=250, groundspeed=180.0)
            client.publish(f"uav/{vid}/telemetry", json.dumps(bad))


def undo(client, plan, lab_dir):
    c = plan["category"]
    if c == "SENSOR":
        client.publish(f"uav/{plan['drone']}/command",
                       json.dumps({"type": "inject_fault", "params": plan["defaults"]}))
    elif c == "SILENT":
        compose_service(lab_dir, "unpause", plan["service"])


def write_receipt(plan, injected_at, started_at):
    record = dict(plan, injected_at=injected_at, started_at=started_at)
    record.pop("defaults", None)
    name = f"mischief-receipt-{time.strftime('%Y%m%d-%H%M%S', time.localtime(started_at))}.txt"
    Path(name).write_text(base64.b64encode(json.dumps(record).encode()).decode() + "\n")
    return name


def reveal(path):
    record = json.loads(base64.b64decode(Path(path).read_text().strip()))
    when = record.get("injected_at")
    print(f"category:  {record['category']}")
    for k in ("drone", "fault", "severity", "params", "service", "lat", "lon", "confidence", "kind", "note"):
        if k in record:
            print(f"{k + ':':<10} {record[k]}")
    if when:
        print(f"injected:  {time.strftime('%H:%M:%S', time.localtime(when))} "
              f"({when - record['started_at']:.0f} s after you started mischief_d4.py)")
    else:
        print("injected:  nothing (NONE, or no takeoff before the timeout)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reveal", metavar="RECEIPT", help="show what a run injected")
    ap.add_argument("--lab", default="lab", help="path to your lab/ folder (default: ./lab)")
    ap.add_argument("--takeoff-timeout", type=float, default=180, help="seconds to wait for a takeoff")
    ap.add_argument("--onset", type=float, nargs=2, default=(20, 90), metavar=("MIN", "MAX"),
                    help="the fault fires this many seconds after takeoff (default: 20 90)")
    ap.add_argument("--duration", type=float, default=300, help="seconds the fault lasts before it is undone")
    args = ap.parse_args()

    if args.reveal:
        reveal(args.reveal)
        return

    lab_dir = Path(args.lab).resolve()
    mm = sensor_catalog(lab_dir / "scripts")
    rng = random.SystemRandom()
    started_at = time.time()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = _on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.subscribe("uav/+/telemetry")
    client.loop_start()

    print("mischief_d4: armed. Start (or keep running) your use case and your agent.")
    print("             Press Ctrl-C when your agent has finished.")

    plan, injected_at = {"category": "NONE"}, None
    state = {"done": False}

    def finish(*_):
        if state["done"]:
            return
        state["done"] = True
        if injected_at:
            undo(client, plan, lab_dir)
        name = write_receipt(plan, injected_at, started_at)
        client.loop_stop()
        client.disconnect()
        print(f"mischief_d4: finished. Receipt: {name}")
        print("             Commit your agent's report first, then run --reveal on the receipt.")
        sys.exit(0)

    signal.signal(signal.SIGINT, finish)
    signal.signal(signal.SIGTERM, finish)

    drones = wait_for_takeoff(args.takeoff_timeout)
    if drones:
        plan = choose(rng, drones, mm)
        if plan["category"] != "NONE":
            time.sleep(rng.uniform(*args.onset))
            try:
                inject(client, plan, lab_dir)
                injected_at = time.time()
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                plan = {"category": "NONE", "note": f"{plan['category']} could not be injected: {exc}"}
    end = time.time() + args.duration
    while time.time() < end:
        time.sleep(0.5)
    finish()


if __name__ == "__main__":
    main()
