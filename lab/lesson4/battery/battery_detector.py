#!/usr/bin/env python3
"""Windowed battery runtime-monitor -- the worked example for Lesson 4's
Step 4: subscribe, maintain a window (not single points), report one of
three verdicts continuously with evidence. Same shape you're asked to
build for your own two categories, just for `battery` instead.

Setup: same as battery_plot.py. Start the fleet, arm and take off, then:

    python battery_detector.py

Try it two ways:
1. Run it against a normal flight -- it should sit at "no problem" the
   whole time.
2. Run mischief_maker.py POWER-BATTERY <onset> <span> <severity> against
   the same vehicle and watch the verdict flip, with evidence.

Threshold note: WARN_VOLTAGE (11.0V) is set a bit above ArduPilot's own
real low-battery failsafe default (BATT_LOW_VOLT = 10.5V, confirmed from
AP_BattMonitor_Params.cpp) -- the whole point of a runtime monitor giving
advance warning is to flag trouble *before* the autopilot's own failsafe
would have to act, not to just re-detect the failsafe after the fact.
"""
import collections
import json
import os
import time

import paho.mqtt.client as mqtt

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

MONITOR_CONFIG_TOPIC = f"uav/{VEHICLE_ID}/monitor_config"
MONITORED_DATA_TOPIC = f"uav/{VEHICLE_ID}/monitored_data"

# The window: how much recent history the verdict is based on, and how
# much of it has to actually be there before we're willing to say
# anything at all. A single low reading could be one noisy sample: SITL's
# battery voltage is otherwise rock-steady in normal flight (confirmed:
# 12.60V +/- noise well under 0.01V), so even a short window is enough to
# separate "one weird sample" from "a real drop."
WINDOW_S = 5.0
MIN_SAMPLES = 5

# Volts. See module docstring for why this sits above ArduPilot's own
# real BATT_LOW_VOLT default (10.5V) rather than matching it.
WARN_VOLTAGE = 11.0

_window = collections.deque()  # (timestamp, battery_dict)
_verdict = None  # last-reported verdict, so we only print on a change


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT} ({reason_code})")
    client.publish(MONITOR_CONFIG_TOPIC, json.dumps({"categories": ["battery"]}), retain=True)
    client.subscribe(MONITORED_DATA_TOPIC)


def on_message(client, userdata, msg):
    global _verdict
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        return
    battery = payload.get("battery")
    if battery is None:
        return

    now = payload.get("timestamp", time.time())
    _window.append((now, battery))
    while _window and now - _window[0][0] > WINDOW_S:
        _window.popleft()

    verdict, evidence = evaluate(now)
    if verdict != _verdict:
        print(f"[{now:.1f}] {verdict} -- {evidence}")
        _verdict = verdict


def evaluate(now):
    """(verdict, evidence string). Same three-verdict vocabulary as
    HW03/Lesson 4: "problem present" / "no problem" / "not enough data
    yet". Windowed, not single-point: every number quoted in the evidence
    comes from the whole window, not just the latest sample.
    """
    if not _window or now - _window[0][0] < WINDOW_S * 0.9 or len(_window) < MIN_SAMPLES:
        return "not enough data yet", f"only {len(_window)} sample(s) in the last {WINDOW_S:.0f}s so far"

    voltages = [b["voltage_v"] for _, b in _window if b.get("voltage_v") is not None]
    if not voltages:
        return "not enough data yet", "no voltage readings in the window"

    avg_voltage = sum(voltages) / len(voltages)
    min_voltage = min(voltages)
    latest = _window[-1][1]

    if avg_voltage < WARN_VOLTAGE:
        return (
            "problem present",
            f"windowed avg voltage {avg_voltage:.2f}V (min {min_voltage:.2f}V) "
            f"< {WARN_VOLTAGE:.1f}V over the last {WINDOW_S:.0f}s -- "
            f"current draw {latest.get('current_a')}A, remaining {latest.get('remaining_pct')}%",
        )

    return (
        "no problem",
        f"windowed avg voltage {avg_voltage:.2f}V (min {min_voltage:.2f}V), "
        f">= {WARN_VOLTAGE:.1f}V threshold",
    )


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_forever()


if __name__ == "__main__":
    main()
