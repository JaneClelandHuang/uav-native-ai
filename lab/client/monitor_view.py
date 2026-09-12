"""Minimal MQTT client for lesson-4 runtime monitoring. Same pattern as
matplotlib_view.py -- a pure MQTT client, same env vars, same
connect/on_connect/on_message idiom -- but with no plotting yet: it (1) asks
the backend to include `vibration` on MONITORED_DATA_TOPIC, (2) subscribes
to it, and (3) prints whatever arrives. A real display can replace the
print() later without touching the config/subscribe wiring.
"""
import json
import os

import paho.mqtt.client as mqtt

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

MONITOR_CONFIG_TOPIC = f"uav/{VEHICLE_ID}/monitor_config"
MONITORED_DATA_TOPIC = f"uav/{VEHICLE_ID}/monitored_data"

# Which monitor_signals.py categories this client wants published. See
# lab/backend/monitor_signals.py's CATEGORY_HANDLERS for the full set
# (vibration, gps, ekf, compass, battery) -- add more here to see more.
CATEGORIES = ["vibration"]


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT} ({reason_code})")
    # Retained: this is the current configuration, not a one-off command --
    # the backend (and any other client) picks it up immediately and it
    # stays in effect until something else publishes a new one. See
    # ARCHITECTURE.md's "Runtime monitoring" section.
    client.publish(
        MONITOR_CONFIG_TOPIC, json.dumps({"categories": CATEGORIES}), retain=True
    )
    client.subscribe(MONITORED_DATA_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        return
    print(payload)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_forever()


if __name__ == "__main__":
    main()
