#!/usr/bin/env bash
set -euo pipefail

# Disarm the vehicle over the same MQTT command channel drone_backend.py
# subscribes to -- useful for leaving the simulator in a safe state after
# manual testing (e.g. verify_setup.py's arm round-trip check).
#
# Requires the mosquitto-clients CLI tools (mosquitto_pub). Override
# MQTT_HOST/MQTT_PORT/VEHICLE_ID as env vars if not using the defaults.

MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
VEHICLE_ID="${VEHICLE_ID:-1}"

mosquitto_pub -h "${MQTT_HOST}" -p "${MQTT_PORT}" \
    -t "uav/${VEHICLE_ID}/command" \
    -m '{"type":"disarm"}'

echo "Sent disarm command to uav/${VEHICLE_ID}/command"
