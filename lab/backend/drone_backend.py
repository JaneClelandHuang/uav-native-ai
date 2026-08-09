"""pymavlink <-> MQTT bridge. The only thing in this stack that speaks
pymavlink directly -- every other component is purely an MQTT client.
"""
import json
import logging
import math
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
FLY_HOME_MIN_ALT_M = 20.0  # fly_home transits at max(current alt_rel, this)

TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"
COMMAND_TOPIC = f"uav/{VEHICLE_ID}/command"
HOME_TOPIC = f"uav/{VEHICLE_ID}/home"

# Optional, off by default: also publish a message in DroneResponse's
# UPDATE_DRONE shape on this topic every tick, alongside the normal
# TELEMETRY_TOPIC publish. Named after the topic/contract itself, not any
# particular consumer -- drone_backend.py doesn't know or care who (if
# anyone) is subscribed; it currently happens to be new-gui.py, but nothing
# here is coupled to that specific program. Unset (the default for
# students) means none of this runs -- not course content, so it doesn't
# touch the default student path at all. See UPDATE_DRONE_ACTIVITY_MAP
# below and ARCHITECTURE.md for what's translated and why.
UPDATE_DRONE = os.environ.get("UPDATE_DRONE")

# VEHICLE_ID ("1", "2", ...) -> uavid, 1-indexed into this list. Confirmed
# against tile_map.py (uav-class-student branch): a live drone's marker
# color is fill_color = QColor(d.name.lower()) -- d.name is uavid -- with
# no fallback to anything meaningful if that string isn't a valid HTML/CSS
# color name (QColor(...).isValid() is False, silently renders flat gray).
# So uavid has to actually be a color name, not Stage 1's own numeric
# VEHICLE_ID -- this list is that mapping, kept out of Stage 1's own
# vehicle_id/telemetry entirely (see update_drone_payload below).
UPDATE_DRONE_COLORS = ["Fuchsia", "Navy", "Purple", "Aqua", "Lime", "Orange", "Yellow"]


def _update_drone_uavid(vehicle_id):
    try:
        index = int(vehicle_id) - 1
    except ValueError:
        return vehicle_id
    if 0 <= index < len(UPDATE_DRONE_COLORS):
        return UPDATE_DRONE_COLORS[index]
    # Falls back to the raw ID rather than crashing/wrapping if Stage 6
    # (multi-vehicle) ever runs more vehicles than this list has colors --
    # renders gray in that case, same as an unmapped ID would have anyway.
    return vehicle_id


# VEHICLE_ID doesn't change after startup, so this is computed once here,
# not recomputed every publish tick in update_drone_payload.
UPDATE_DRONE_UAVID = _update_drone_uavid(VEHICLE_ID)

# activity -> DroneResponse's (status, state_type, onboard_pilot). The
# first two are plain display fields (see drone_panel.py's "Status"/"State
# Type" labels in the new-gui.py client); onboard_pilot is what actually
# drives the flashing drone icon during takeoff/landing -- tile_map.py's
# _is_flashing() checks it case-insensitively for exactly "takeoff" or
# "land", not status/state_type at all. Despite the field's name it's not a
# person -- drone.py's own comment gives "ReceiveMission"/"Takeoff" as
# example values, i.e. the onboard autonomy's current named task, which
# activity already tracks.
UPDATE_DRONE_ACTIVITY_MAP = {
    "idle":       ("OnGround", "Await Mission", ""),
    "taking_off": ("Flying",   "Taking Off",    "Takeoff"),
    "flying":     ("Flying",   "Flying",        ""),
    "circling":   ("Flying",   "Circling",      ""),
    "landing":    ("Flying",   "Landing",       "Land"),
}


def update_drone_payload(snapshot):
    """snapshot (a VehicleState.snapshot() dict) -> DroneResponse's
    UPDATE_DRONE message shape, or None if there's not yet enough to report
    a position (before the first GLOBAL_POSITION_INT arrives, lat/lon/
    alt_amsl are all still None).

    One thing NOT converted here despite first appearances: heading.
    new-gui.py's field is named heading_rad, but every place that actually
    renders it (tile_map.py, drone_panel.py, camera_manager.py) treats the
    incoming value as degrees -- confirmed by reading those call sites, not
    trusting the field name. Converting to radians here was a real bug in
    an earlier version of this (the drone never appeared to face its
    direction of travel) -- passed straight through now.

    altitude uses alt_amsl, not alt_rel: new-gui.py wants AMSL (confirmed
    via tile_map.py's home_altitude(), documented there as "AMSL altitude
    recorded at the drone's most recent arming"). drone_attitude (a
    quaternion) and the DroneResponse-fleet-specific state_info fields this
    doesn't set (air_lease_state, heartbeat_status, ...) are omitted, not
    faked -- checked that map_overlay.py's update_drone_pose() treats a
    missing/empty drone_attitude as falsy and skips it rather than
    crashing, and every state_info field is read with .get(key, default).
    """
    lat, lon, alt_amsl = snapshot.get("lat"), snapshot.get("lon"), snapshot.get("alt_amsl")
    if lat is None or lon is None or alt_amsl is None:
        # update_drone_pose() does float(location.get("latitude", 0.0)) with
        # no None-guard on that particular line -- a location dict with an
        # explicit None value (as opposed to a missing key) would raise in
        # new-gui.py's Qt callback thread. Skip rather than publish a fake
        # (0, 0) or risk that crash.
        return None

    status, state_type, onboard_pilot = UPDATE_DRONE_ACTIVITY_MAP.get(
        snapshot.get("activity"), ("", "", "")
    )
    heading_deg = snapshot.get("heading")
    return {
        "uavid": UPDATE_DRONE_UAVID,
        "status": {
            "location": {"latitude": lat, "longitude": lon, "altitude": alt_amsl},
            "drone_heading": heading_deg if heading_deg is not None else 0.0,
            "mode": snapshot.get("mode") or "",
            "armed": bool(snapshot.get("armed")),
            "speed": snapshot.get("groundspeed"),
            "battery": {
                "voltage": snapshot.get("battery_voltage"),
                "level": snapshot.get("battery_level"),
            },
            "status": status,
            "state_type": state_type,
            "onboard_pilot": onboard_pilot,
        },
    }


class VehicleState:
    def __init__(self):
        self.lock = threading.Lock()
        self.lat = None
        self.lon = None
        self.alt_rel = None
        self.alt_amsl = None
        self.heading = None
        self.groundspeed = None
        self.battery_voltage = None
        self.battery_level = None
        self.armed = False
        self.mode = None
        # Flight-phase, set explicitly by handle_command/maneuver_tick as
        # commands are issued, not inferred from other telemetry fields --
        # takeoff/goto/circle/fly_home all report mode "GUIDED", so mode
        # alone can't distinguish them. armed==False always forces this
        # back to "idle" (see mavlink_reader's HEARTBEAT handling), which
        # self-corrects an optimistic "taking_off" if e.g. an arm attempt
        # is actually rejected by pre-arm checks.
        # One of: idle, taking_off, flying, circling, landing.
        self.activity = "idle"
        # Captured once from HOME_POSITION (see mavlink_reader) -- not part
        # of the telemetry snapshot below (home doesn't change tick to
        # tick, and it's already published separately as retained
        # uav/<id>/home, alt included); kept here so backend-internal
        # commands have somewhere to read it from. home_alt is AMSL, same
        # as HOME_POSITION.altitude/alt_amsl elsewhere -- fly_home doesn't
        # need it (goto() targets relative altitude), but with alt_amsl now
        # part of the telemetry contract, the starting/home elevation is
        # the other AMSL reference point terrain-relative work later in the
        # course will need, so it's captured here now rather than bolted on
        # later.
        self.home_lat = None
        self.home_lon = None
        self.home_alt = None

    def snapshot(self):
        with self.lock:
            return {
                "vehicle_id": VEHICLE_ID,
                "timestamp": time.time(),
                "lat": self.lat,
                "lon": self.lon,
                "alt_rel": self.alt_rel,
                "alt_amsl": self.alt_amsl,
                "heading": self.heading,
                "groundspeed": self.groundspeed,
                "battery_voltage": self.battery_voltage,
                "battery_level": self.battery_level,
                "armed": self.armed,
                "mode": self.mode,
                "activity": self.activity,
            }


class CircleManeuver:
    """One `circle` command's parameters plus its own per-tick advance
    logic. Always starts at bearing 0 (due north of center) -- there's no
    tracking of the vehicle's actual position on the circle at start, so a
    smooth entry means positioning at that point yourself first (see
    scripts/test_circle.py) rather than wherever you happen to be.
    """

    # VehicleState.activity while this maneuver is running -- maneuver_tick
    # uses this to reset activity back to "flying" on completion, but only
    # if nothing else already changed it (see maneuver_tick).
    activity = "circling"

    def __init__(self, center_lat, center_lon, alt_rel_m, radius_m, degrees, speed_mps):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.alt_rel_m = alt_rel_m
        self.radius_m = radius_m
        self.degrees = degrees
        # rad/s = m/s / m; deg/s = degrees(rad/s).
        self.angular_rate_deg_s = math.degrees(speed_mps / radius_m)
        self.start_time = time.time()

    def tick(self, conn):
        """Advance by how much wall-clock time has actually elapsed since
        the maneuver started, not by a fixed per-tick step, so it stays
        correct even if a tick runs late. Returns False once the sweep is
        complete, signaling the caller to drop this maneuver.
        """
        swept_deg = (time.time() - self.start_time) * self.angular_rate_deg_s
        if swept_deg >= self.degrees:
            return False
        mavlink_lib.circle_point(
            conn, self.center_lat, self.center_lon,
            self.alt_rel_m, self.radius_m, swept_deg,
        )
        return True


class ActiveManeuver:
    """Holds at most one ongoing, multi-tick maneuver -- written by the
    MQTT callback thread (start/stop), read once per tick by the main loop
    (maneuver_tick). Protected the same way VehicleState protects
    telemetry: a plain lock around a plain slot, not a thread of its own.
    Starting a new maneuver (or any other command -- see handle_command)
    replaces/clears whatever was active; there's never more than one.

    Not specific to circles or any other maneuver type -- a maneuver object
    just needs a `tick(conn) -> bool` method (return False once it's done)
    and an `activity` attribute (the VehicleState activity name it
    corresponds to). See CircleManeuver.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self._maneuver = None

    def start(self, maneuver):
        with self.lock:
            self._maneuver = maneuver

    def stop(self):
        with self.lock:
            self._maneuver = None

    def current(self):
        with self.lock:
            return self._maneuver


def maneuver_tick(conn, active_maneuver, state):
    """Called once per main-loop iteration, same cadence as telemetry
    publishing. Advances whatever maneuver is currently active, if any.
    """
    maneuver = active_maneuver.current()
    if maneuver is None:
        return
    if maneuver.tick(conn):
        return
    active_maneuver.stop()
    with state.lock:
        # Only if state.activity still matches this maneuver -- a command
        # that arrived since (interrupt/goto/land/...) already stopped it
        # and set its own activity; don't stomp it with a stale value if
        # the maneuver merely finishes sweeping afterward.
        if state.activity == maneuver.activity:
            state.activity = "flying"


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
                if not state.armed:
                    # Always the ground truth, regardless of what the last
                    # command optimistically set activity to -- covers a
                    # completed landing, a bare disarm, and a takeoff/arm
                    # that never actually succeeded (pre-arm check
                    # rejection), all the same way: disarmed means idle.
                    state.activity = "idle"
        elif msg_type == "GLOBAL_POSITION_INT":
            with state.lock:
                state.lat = msg.lat / 1e7
                state.lon = msg.lon / 1e7
                state.alt_rel = msg.relative_alt / 1000.0
                # AMSL, not relative to home -- same message as relative_alt,
                # just a different field. Needed alongside alt_rel (not
                # instead of it) for terrain/elevation work later in the
                # course; alt_rel stays canonical for "did I reach my
                # target altitude" mission logic like test_flight.py's
                # arrival checks.
                state.alt_amsl = msg.alt / 1000.0
                state.heading = msg.hdg / 100.0
        elif msg_type == "VFR_HUD":
            with state.lock:
                state.groundspeed = msg.groundspeed
        elif msg_type == "SYS_STATUS":
            with state.lock:
                state.battery_voltage = msg.voltage_battery / 1000.0
                # 0-100%, or -1 if the autopilot doesn't know yet (e.g. right
                # after boot) -- leave battery_level as None rather than
                # publish a misleading -1 in that case.
                if msg.battery_remaining >= 0:
                    state.battery_level = msg.battery_remaining / 100.0
        elif msg_type == "HOME_POSITION" and not home_captured:
            home = {
                "vehicle_id": VEHICLE_ID,
                "lat": msg.latitude / 1e7,
                "lon": msg.longitude / 1e7,
                "alt": msg.altitude / 1000.0,
            }
            with state.lock:
                state.home_lat = home["lat"]
                state.home_lon = home["lon"]
                state.home_alt = home["alt"]
            mqtt_client.publish(HOME_TOPIC, json.dumps(home), qos=1, retain=True)
            log.info("Published home position (retained): %s", home)
            home_captured = True


def handle_command(conn, payload, active_maneuver, state):
    try:
        cmd = json.loads(payload)
    except json.JSONDecodeError:
        log.warning("Ignoring malformed command payload: %r", payload)
        return

    cmd_type = cmd.get("type")
    try:
        if cmd_type != "circle":
            # Any other command abandons an in-progress maneuver --
            # otherwise maneuver_tick() would keep firing position targets
            # that fight whatever this new command is trying to do.
            active_maneuver.stop()

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
            with state.lock:
                state.activity = "taking_off"
        elif cmd_type == "goto":
            mavlink_lib.goto(conn, float(cmd["lat"]), float(cmd["lon"]), float(cmd["alt"]))
            with state.lock:
                state.activity = "flying"
        elif cmd_type == "circle":
            # circle_point() itself doesn't touch flight mode (see its
            # docstring) since it's called many times a second -- GUIDED
            # only needs setting once, here, before maneuver_tick() starts
            # calling it on the main loop's cadence.
            conn.set_mode("GUIDED")
            active_maneuver.start(CircleManeuver(
                center_lat=float(cmd["lat"]), center_lon=float(cmd["lon"]),
                alt_rel_m=float(cmd["alt"]), radius_m=float(cmd["radius"]),
                degrees=float(cmd["degrees"]), speed_mps=float(cmd["speed"]),
            ))
            with state.lock:
                state.activity = "circling"
        elif cmd_type == "fly_home":
            # Just goto() at the remembered home position -- no new MAVLink
            # primitive needed, the same way circle reused goto()'s
            # underlying send rather than inventing one. Transits at
            # whatever's higher of the current altitude or
            # FLY_HOME_MIN_ALT_M, so a low-altitude command doesn't drag the
            # vehicle home skimming the ground, but a already-high vehicle
            # doesn't needlessly climb first either. land is a deliberately
            # separate follow-up command, same as after a goto.
            with state.lock:
                home_lat, home_lon, current_alt = state.home_lat, state.home_lon, state.alt_rel
            if home_lat is None or home_lon is None:
                log.warning("Ignoring fly_home: home position not yet captured")
            else:
                target_alt = max(current_alt, FLY_HOME_MIN_ALT_M) if current_alt is not None else FLY_HOME_MIN_ALT_M
                mavlink_lib.goto(conn, home_lat, home_lon, target_alt)
                with state.lock:
                    state.activity = "flying"
        elif cmd_type == "interrupt":
            mavlink_lib.interrupt(conn)
            with state.lock:
                # Best fit from the activity vocabulary for "holding
                # position, still airborne" -- there's no distinct
                # "Holding"/"Loiter" state in what new-gui.py's bridge maps
                # to, and this isn't landing or circling anymore.
                state.activity = "flying"
        elif cmd_type == "land":
            mavlink_lib.land(conn)
            with state.lock:
                state.activity = "landing"
        else:
            log.warning("Ignoring unknown command type: %r", cmd_type)
    except (KeyError, ValueError, TypeError) as exc:
        log.warning("Ignoring invalid command %r: %s", cmd, exc)


def on_connect(client, userdata, flags, reason_code, properties):
    log.info("Connected to MQTT broker at %s:%s (%s)", MQTT_HOST, MQTT_PORT, reason_code)
    client.subscribe(COMMAND_TOPIC)


def on_message(client, userdata, msg):
    handle_command(
        userdata["conn"], msg.payload.decode("utf-8", errors="replace"),
        userdata["active_maneuver"], userdata["state"],
    )


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
    active_maneuver = ActiveManeuver()

    mqtt_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata={"conn": conn, "active_maneuver": active_maneuver, "state": state},
    )
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
            maneuver_tick(conn, active_maneuver, state)
            snapshot = state.snapshot()
            mqtt_client.publish(TELEMETRY_TOPIC, json.dumps(snapshot))
            if UPDATE_DRONE:
                payload = update_drone_payload(snapshot)
                if payload is not None:
                    mqtt_client.publish(UPDATE_DRONE, json.dumps(payload))
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        mqtt_client.loop_stop()


if __name__ == "__main__":
    main()
