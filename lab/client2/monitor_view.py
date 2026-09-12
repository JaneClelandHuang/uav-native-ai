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

# Other topics this client doesn't touch but could -- uncomment and
# client.subscribe() any of these in on_connect() below if you want them
# too. See ARCHITECTURE.md's "The MQTT contract" for the full picture.
# TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"    # core flight state, always on, no config needed
# HOME_TOPIC = f"uav/{VEHICLE_ID}/home"               # retained, published once at boot
# STATUS_TEXT_TOPIC = f"uav/{VEHICLE_ID}/status_text" # ArduPilot's own PreArm/failsafe messages,
#                                                      # relayed the instant they arrive, not retained
# COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"         # clients -> backend only; a monitor wouldn't
#                                                      # subscribe to this, just listed for completeness

# Which monitor_signals.py categories this client wants published.
# Uncomment any of the below (or add several at once) to see more -- this
# is the full set CATEGORY_HANDLERS knows about as of lesson 4; add a new
# category there first if you need one that isn't listed here.
CATEGORIES = [
    "vibration",  # VIBRATION: vibration_x/y/z, clipping (3 cumulative counts)
    # "gps",      # GPS_RAW_INT: fix_type, satellites_visible, h_acc_m/v_acc_m, hdop_h/hdop_v
    # "ekf",      # EKF_STATUS_REPORT: flags, velocity/pos_horiz/pos_vert/compass variance
    # "compass",  # RAW_IMU: mag_x/y/z, derived field_magnitude
    # "battery",  # SYS_STATUS: voltage_v, current_a, remaining_pct
]


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
