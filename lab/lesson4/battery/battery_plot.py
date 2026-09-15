#!/usr/bin/env python3
"""Live plot of the `battery` monitored_data category -- voltage, current,
and remaining percent over time. This is the worked example for Lesson 4's
Step 2: subscribe, plot, and watch what "normal" looks like before a fault
is introduced -- for `battery`, not one of your own two graded categories.

Setup: `pip install -r lab/lesson4/requirements.txt`. Start the fleet
(`docker compose up -d` from uav-native-ai/lab), arm and take off a
vehicle, then:

    python battery_plot.py

Stop it with Ctrl-C.
"""
import collections
import json
import os
import time

import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

MONITOR_CONFIG_TOPIC = f"uav/{VEHICLE_ID}/monitor_config"
MONITORED_DATA_TOPIC = f"uav/{VEHICLE_ID}/monitored_data"

HISTORY_S = 60  # how much history the plot keeps on screen at once

_updates = collections.deque()  # (timestamp, battery_dict), written by the MQTT thread


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT} ({reason_code})")
    # Retained -- same pattern client2/monitor_view.py uses: this is the
    # current configuration, not a one-off command.
    client.publish(MONITOR_CONFIG_TOPIC, json.dumps({"categories": ["battery"]}), retain=True)
    client.subscribe(MONITORED_DATA_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        return
    battery = payload.get("battery")
    if battery is not None:
        _updates.append((payload.get("timestamp", time.time()), battery))


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    fig, (ax_volt, ax_curr, ax_pct) = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    ax_volt.set_ylabel("voltage_v")
    ax_curr.set_ylabel("current_a")
    ax_pct.set_ylabel("remaining_pct")
    ax_pct.set_xlabel("time (s, relative)")
    fig.suptitle(f"Vehicle {VEHICLE_ID} -- battery")
    fig.tight_layout()

    line_volt, = ax_volt.plot([], [], color="tab:blue")
    line_curr, = ax_curr.plot([], [], color="tab:orange")
    line_pct, = ax_pct.plot([], [], color="tab:green")

    start_time = None

    def update():
        nonlocal start_time
        while _updates:
            ts, battery = _updates.popleft()
            if start_time is None:
                start_time = ts
            _history["t"].append(ts - start_time)
            _history["volt"].append(battery.get("voltage_v"))
            _history["curr"].append(battery.get("current_a"))
            _history["pct"].append(battery.get("remaining_pct"))

        # Trim to the last HISTORY_S seconds so the plot scrolls forward
        # instead of growing forever.
        while _history["t"] and _history["t"][-1] - _history["t"][0] > HISTORY_S:
            for key in _history:
                _history[key].popleft()

        if not _history["t"]:
            return

        line_volt.set_data(_history["t"], _history["volt"])
        line_curr.set_data(_history["t"], _history["curr"])
        line_pct.set_data(_history["t"], _history["pct"])

        for ax, line in ((ax_volt, line_volt), (ax_curr, line_curr), (ax_pct, line_pct)):
            ax.relim()
            ax.autoscale_view()
        ax_volt.set_xlim(_history["t"][0], _history["t"][0] + HISTORY_S)

    _history = {"t": collections.deque(), "volt": collections.deque(),
                "curr": collections.deque(), "pct": collections.deque()}

    plt.show(block=False)
    try:
        while plt.fignum_exists(fig.number):
            update()
            plt.pause(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()


if __name__ == "__main__":
    main()
