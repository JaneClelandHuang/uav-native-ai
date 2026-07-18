#!/usr/bin/env python3
"""One-command health check for the Stage 1 stack.

Run this instead of following a setup guide by hand. It should answer "does
my environment work" with a plain-English PASS or a specific failure plus a
remediation line -- not a stack trace. See SETUP.md's troubleshooting index
for the failure modes this maps to.

Requires paho-mqtt (already needed for client/matplotlib_view.py -- install
client/requirements.txt into your venv before running this).
"""
import json
import os
import shutil
import subprocess
import sys
import time

import paho.mqtt.client as mqtt

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"
COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"

COMPOSE_UP_TIMEOUT = 90
TELEMETRY_TIMEOUT = 60
ARM_ROUNDTRIP_TIMEOUT = 20


def fail(message, remediation):
    print(f"\nFAIL: {message}")
    print(f"  -> {remediation}")
    sys.exit(1)


def check_docker():
    if shutil.which("docker") is None:
        fail(
            "Docker is not installed.",
            "Install Docker Desktop (Mac/Windows) or Docker Engine (Linux), "
            "then re-run this script. See SETUP.md.",
        )
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        fail(
            "Docker is installed but the daemon isn't reachable.",
            "Start Docker Desktop (or `sudo systemctl start docker` on "
            "Linux) and wait for it to say 'running', then re-run this "
            "script. On Windows, make sure WSL2 is enabled -- Docker "
            "Desktop needs it as a backend.",
        )
    print("PASS: Docker is installed and the daemon is running.")


def compose_up():
    print("Starting docker compose (mosquitto + sitl + drone_backend)...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        capture_output=True, text=True, timeout=COMPOSE_UP_TIMEOUT,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "port is already allocated" in stderr or "address already in use" in stderr:
            fail(
                "A port this stack needs (1883) is already in use.",
                "Run `docker compose down` to clear any leftover containers "
                "from a previous run, then re-run this script.",
            )
        if "Cannot connect to the Docker daemon" in stderr:
            fail(
                "Docker daemon isn't reachable.",
                "Start Docker Desktop / the Docker service, then re-run "
                "this script.",
            )
        fail(
            f"`docker compose up` failed: {stderr[:500]}",
            "See the full output above and check SETUP.md's troubleshooting "
            "index -- common causes are a VPN/firewall blocking the image "
            "pull, or no space left on disk.",
        )
    print("PASS: docker compose up succeeded.")


def wait_for_telemetry():
    print(f"Waiting up to {TELEMETRY_TIMEOUT}s for telemetry on {TELEMETRY_TOPIC}...")
    received = {}

    def on_message(client, userdata, msg):
        try:
            received["payload"] = json.loads(msg.payload)
        except json.JSONDecodeError:
            pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    try:
        client.connect(MQTT_HOST, MQTT_PORT)
    except OSError:
        fail(
            f"Couldn't connect to the MQTT broker at {MQTT_HOST}:{MQTT_PORT}.",
            "Check `docker compose ps` -- the mosquitto container should be "
            "'running'. If it's not, run `docker compose logs mosquitto`.",
        )
    client.subscribe(TELEMETRY_TOPIC)
    client.loop_start()

    deadline = time.time() + TELEMETRY_TIMEOUT
    while time.time() < deadline and "payload" not in received:
        time.sleep(0.5)

    if "payload" not in received:
        client.loop_stop()
        fail(
            f"No telemetry arrived on {TELEMETRY_TOPIC} within "
            f"{TELEMETRY_TIMEOUT}s.",
            "Check `docker compose logs sitl` for a MAVProxy heartbeat and "
            "`docker compose logs drone_backend` for a 'Heartbeat received' "
            "line. If sitl is still starting up on first run, give it "
            "another minute and re-run this script.",
        )
    print(f"PASS: telemetry flowing ({received['payload']}).")
    return client


def check_command_roundtrip(client):
    print("Publishing {'type': 'arm'} and watching for armed=true...")
    armed_seen = {"value": False}

    def on_message(client_, userdata, msg):
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        if payload.get("armed"):
            armed_seen["value"] = True

    client.on_message = on_message
    client.publish(COMMAND_TOPIC, json.dumps({"type": "arm"}))

    deadline = time.time() + ARM_ROUNDTRIP_TIMEOUT
    while time.time() < deadline and not armed_seen["value"]:
        time.sleep(0.5)

    client.loop_stop()

    if not armed_seen["value"]:
        fail(
            f"Sent an arm command but never saw armed=true on "
            f"{TELEMETRY_TOPIC} within {ARM_ROUNDTRIP_TIMEOUT}s.",
            "This can be a false failure if SITL just booted -- ArduCopter "
            "refuses to arm until its EKF/GPS pre-arm checks pass, which "
            "can take 30-60s after a cold start. Wait a bit and re-run. If "
            "it persists, check `docker compose logs sitl` for a specific "
            "PreArm message.",
        )
    print("PASS: command round-trip works (arm command was obeyed).")


def main():
    start = time.time()
    check_docker()
    compose_up()
    client = wait_for_telemetry()
    check_command_roundtrip(client)
    print(f"\nPASS: environment is fully working ({time.time() - start:.0f}s).")


if __name__ == "__main__":
    main()
