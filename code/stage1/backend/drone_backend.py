"""pymavlink <-> MQTT bridge. The only thing in this stack that speaks
pymavlink directly -- every other component is purely an MQTT client.
"""
import json
import logging
import os
import threading
import time

import paho.mqtt.client as mqtt
from pymavlink import mavutil

import mavlink_lib

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("drone_backend")

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MAVLINK_CONN = os.environ.get("MAVLINK_CONN", "udpin:0.0.0.0:14550")
MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
TELEMETRY_HZ = float(os.environ.get("TELEMETRY_HZ", "4"))

TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"
COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"
HOME_TOPIC = f"uav/{VEHICLE_ID}/home"


class VehicleState:
    def __init__(self):
        self.lock = threading.Lock()
        self.lat = None
        self.lon = None
        self.alt_rel = None
        self.heading = None
        self.groundspeed = None
        self.battery_voltage = None
        self.armed = False
        self.mode = None

    def snapshot(self):
        with self.lock:
            return {
                "vehicle_id": VEHICLE_ID,
                "timestamp": time.time(),
                "lat": self.lat,
                "lon": self.lon,
                "alt_rel": self.alt_rel,
                "heading": self.heading,
                "groundspeed": self.groundspeed,
                "battery_voltage": self.battery_voltage,
                "armed": self.armed,
                "mode": self.mode,
            }


def connect_mavlink():
    log.info("Connecting to MAVLink at %s", MAVLINK_CONN)
    conn = mavlink_lib.connect(MAVLINK_CONN)
    log.info(
        "Heartbeat received from system %s component %s",
        conn.target_system, conn.target_component,
    )
    return conn


def mavlink_reader(conn, state, mqtt_client):
    """Single reader loop for the connection -- HEARTBEAT/position/status
    updates and HOME_POSITION capture all happen here, since pymavlink's
    recv_match isn't safe to call from two threads on the same connection.
    This also means telemetry publishing (driven by `state`, in main())
    never blocks on HOME_POSITION arriving.
    """
    home_captured = False
    last_home_request = 0.0

    def request_home():
        conn.mav.command_long_send(
            conn.target_system, conn.target_component,
            mavutil.mavlink.MAV_CMD_GET_HOME_POSITION,
            0, 0, 0, 0, 0, 0, 0, 0,
        )

    request_home()
    last_home_request = time.time()

    while True:
        if not home_captured and time.time() - last_home_request > 5:
            # Some SITL setups emit HOME_POSITION unprompted, others need an
            # explicit request -- and UDP can drop the first one, so keep
            # re-requesting until it's captured.
            request_home()
            last_home_request = time.time()

        msg = conn.recv_match(blocking=True, timeout=2)
        if msg is None:
            continue
        msg_type = msg.get_type()
        if msg_type == "HEARTBEAT":
            if msg.get_srcComponent() != mavutil.mavlink.MAV_COMP_ID_AUTOPILOT1:
                continue
            with state.lock:
                state.armed = bool(
                    msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                )
                state.mode = mavutil.mode_string_v10(msg)
        elif msg_type == "GLOBAL_POSITION_INT":
            with state.lock:
                state.lat = msg.lat / 1e7
                state.lon = msg.lon / 1e7
                state.alt_rel = msg.relative_alt / 1000.0
                state.heading = msg.hdg / 100.0
        elif msg_type == "VFR_HUD":
            with state.lock:
                state.groundspeed = msg.groundspeed
        elif msg_type == "SYS_STATUS":
            with state.lock:
                state.battery_voltage = msg.voltage_battery / 1000.0
        elif msg_type == "HOME_POSITION" and not home_captured:
            home = {
                "vehicle_id": VEHICLE_ID,
                "lat": msg.latitude / 1e7,
                "lon": msg.longitude / 1e7,
                "alt": msg.altitude / 1000.0,
            }
            mqtt_client.publish(HOME_TOPIC, json.dumps(home), qos=1, retain=True)
            log.info("Published home position (retained): %s", home)
            home_captured = True


def handle_command(conn, payload):
    try:
        cmd = json.loads(payload)
    except json.JSONDecodeError:
        log.warning("Ignoring malformed command payload: %r", payload)
        return

    cmd_type = cmd.get("type")
    try:
        if cmd_type == "arm":
            mavlink_lib.arm(conn)
        elif cmd_type == "disarm":
            mavlink_lib.disarm(conn)
        elif cmd_type == "takeoff":
            # NAV_TAKEOFF is only honored in GUIDED mode and while armed --
            # mavlink_lib.takeoff makes "takeoff" a complete action so a
            # command producer doesn't need its own mode/arm dance first
            # (this is what manually switching to GUIDED in the MAVProxy
            # console was standing in for during testing).
            mavlink_lib.takeoff(conn, float(cmd["alt"]))
        elif cmd_type == "goto":
            mavlink_lib.goto(conn, float(cmd["lat"]), float(cmd["lon"]), float(cmd["alt"]))
        elif cmd_type == "land":
            mavlink_lib.land(conn)
        else:
            log.warning("Ignoring unknown command type: %r", cmd_type)
    except (KeyError, ValueError, TypeError) as exc:
        log.warning("Ignoring invalid command %r: %s", cmd, exc)


def on_connect(client, userdata, flags, reason_code, properties):
    log.info("Connected to MQTT broker at %s:%s (%s)", MQTT_HOST, MQTT_PORT, reason_code)
    client.subscribe(COMMAND_TOPIC)


def on_message(client, userdata, msg):
    handle_command(userdata["conn"], msg.payload.decode("utf-8", errors="replace"))


def connect_mqtt_with_retry(mqtt_client, timeout=30, interval=2):
    """Compose starts mosquitto/sitl/drone_backend together; `depends_on`
    only orders container starts, not readiness, so the first connect can
    hit a transient DNS resolution race. Retry instead of crashing on it.
    """
    deadline = time.time() + timeout
    while True:
        try:
            mqtt_client.connect(MQTT_HOST, MQTT_PORT)
            return
        except OSError as exc:
            if time.time() >= deadline:
                raise
            log.warning("MQTT connect to %s:%s failed (%s), retrying...", MQTT_HOST, MQTT_PORT, exc)
            time.sleep(interval)


def main():
    conn = connect_mavlink()
    state = VehicleState()

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata={"conn": conn})
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    connect_mqtt_with_retry(mqtt_client)
    mqtt_client.loop_start()

    reader_thread = threading.Thread(
        target=mavlink_reader, args=(conn, state, mqtt_client), daemon=True
    )
    reader_thread.start()

    period = 1.0 / TELEMETRY_HZ
    try:
        while True:
            mqtt_client.publish(TELEMETRY_TOPIC, json.dumps(state.snapshot()))
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        mqtt_client.loop_stop()


if __name__ == "__main__":
    main()
