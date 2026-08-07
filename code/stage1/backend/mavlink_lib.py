"""Shared MAVLink command primitives: build-and-send only, no waiting or
polling. drone_backend.py's MQTT command handler and scripts/simple_flight.py's
direct-scripted mission both fire the same arm/takeoff/goto/land vocabulary
at the autopilot -- only the outer wrapper (an MQTT message vs. a scripted
loop with its own resend/poll logic) differs, so that vocabulary lives here
once instead of twice.

Also home to two smaller groups of helpers, both still send/parse-only with
no background threads of their own:

- SITL fault injection (set_param/get_param): SIM_ parameters
  (SIM_GPS_NOISE, SIM_VIB_FREQ_X/Y/Z, SIM_ENGINE_FAIL, ...) are ordinary
  ArduPilot parameters, so the same PARAM_SET/PARAM_REQUEST_READ pair used
  for any tuning parameter also drives simulated failures.
- Telemetry parsing (parse_*): pure functions, message in, dict out. They
  don't call recv_match themselves -- drone_backend.py's mavlink_reader()
  owns the one recv_match loop per connection (see its docstring for why)
  and would call these inline the same way it already builds the
  HOME_POSITION dict by hand.
"""
import os
import time

os.environ.setdefault("MAVLINK20", "1")  # must be set before mavutil is
# imported below -- pymavlink picks the v1 vs v2 dialect module once, at
# import time, based on this env var. Without it, mavutil.mavlink resolves
# to the MAVLink 1 dialect, and MAVLink 2 extension fields like
# GPS_RAW_INT.h_acc/v_acc simply don't exist on the parsed message (not
# None -- an AttributeError), even though ArduPilot SITL sends MAVLink 2 on
# the wire regardless. Confirmed against pymavlink==2.4.41 (the version
# pinned in requirements.txt) in an isolated venv.

import math
from pymavlink import mavutil

EARTH_RADIUS_M = 6378137.0  # equirectangular approx -- same math as
                             # matplotlib_view.py's lla_to_enu (this is its
                             # inverse), fine at the radii this course
                             # circles at (tens of meters), not a geodesic
                             # formula for long distances.

_GOTO_TYPE_MASK = (
    mavutil.mavlink.POSITION_TARGET_TYPEMASK_VX_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_VY_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_VZ_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE
)


def connect(conn_str):
    conn = mavutil.mavlink_connection(conn_str)
    conn.wait_heartbeat()
    return conn


def arm(conn):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1, 0, 0, 0, 0, 0, 0,
    )


def disarm(conn):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 0, 0, 0, 0, 0, 0, 0,
    )


def takeoff(conn, alt_m):
    # NAV_TAKEOFF is only honored in GUIDED mode and while armed -- make this
    # a complete action so callers don't need their own mode/arm dance first.
    conn.set_mode("GUIDED")
    time.sleep(0.1)
    arm(conn)
    time.sleep(0.1)
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0, alt_m,
    )


def _send_position_target(conn, lat, lon, alt_m):
    conn.mav.set_position_target_global_int_send(
        0, conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        _GOTO_TYPE_MASK,
        int(lat * 1e7), int(lon * 1e7), alt_m,
        0, 0, 0, 0, 0, 0, 0, 0,
    )


def goto(conn, lat, lon, alt_m):
    conn.set_mode("GUIDED")
    time.sleep(0.1)
    _send_position_target(conn, lat, lon, alt_m)


def _point_on_circle(center_lat, center_lon, radius_m, bearing_deg):
    theta = math.radians(bearing_deg)
    east_m = radius_m * math.sin(theta)
    north_m = radius_m * math.cos(theta)
    lat0_rad = math.radians(center_lat)
    lat = center_lat + math.degrees(north_m / EARTH_RADIUS_M)
    lon = center_lon + math.degrees(east_m / (EARTH_RADIUS_M * math.cos(lat0_rad)))
    return lat, lon


def circle_point(conn, center_lat, center_lon, alt_rel_m, radius_m, bearing_deg):
    """One point on the circle of `radius_m` around (center_lat, center_lon)
    at compass bearing `bearing_deg` from center (0=North, 90=East,
    clockwise -- same convention as telemetry's `heading` field).

    ArduCopter has no working "circle around this point" command in this
    pinned firmware -- there's no GUIDED circle submode (checked directly
    against the ArduCopter 4.6.3 source: ModeGuided's only submodes are
    TakeOff/WP/Pos/Accel/VelAccel/PosVelAccel/Angle) and MAV_CMD_DO_ORBIT
    isn't in this pymavlink/ArduPilotMega dialect at all. So tracing an arc
    means calling this repeatedly as bearing advances, same as manually
    flying a circle by eye. This function is one point, one send -- the
    caller owns the timing loop; drone_backend.py's circle_tick() is that
    loop for the MQTT path (see ARCHITECTURE.md).

    Unlike goto(), this does NOT set GUIDED mode or sleep before sending --
    a circle calls this many times a second, and repeating goto()'s one-time
    mode-set+settle delay on every tick would eat into the tick budget for
    no reason after the first call. Callers must already be in GUIDED mode.
    """
    lat, lon = _point_on_circle(center_lat, center_lon, radius_m, bearing_deg)
    _send_position_target(conn, lat, lon, alt_rel_m)


def interrupt(conn):
    # GUIDED never queues waypoints -- goto() sends one outstanding position
    # target, and circle_point() calls are just a rapid succession of the
    # same thing, not an AUTO-mode mission. There's no MAVLink "cancel" for
    # any of that, so abandoning it is a mode change: LOITER takes the
    # vehicle out of GUIDED and holds its current position. This alone stops
    # a goto(); stopping a circle also requires the caller to stop calling
    # circle_point() -- see drone_backend.py's ActiveCircle/circle_tick.
    conn.set_mode("LOITER")


def land(conn):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0, 0, 0, 0, 0, 0, 0, 0,
    )


# --- SITL fault injection ---------------------------------------------


def set_param(conn, name, value, param_type=mavutil.mavlink.MAV_PARAM_TYPE_REAL32):
    conn.mav.param_set_send(
        conn.target_system, conn.target_component,
        name.encode("utf-8"), float(value), param_type,
    )


def get_param(conn, name, timeout=2.0):
    """Request one parameter and block for its PARAM_VALUE reply.

    Unlike every other function in this file, this one waits -- the same
    kind of one-shot exception connect()'s wait_heartbeat() already is, not
    a pattern to repeat elsewhere. Don't call this from
    drone_backend.py's mavlink_reader() thread: recv_match isn't safe to
    share across threads on one connection (see that function's docstring),
    and a second reader stealing the PARAM_VALUE reply here would starve
    the main loop of it. Returns None on timeout.
    """
    conn.mav.param_request_read_send(
        conn.target_system, conn.target_component,
        name.encode("utf-8"), -1,
    )
    deadline = time.time() + timeout
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            return None
        msg = conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=remaining)
        if msg is not None and msg.param_id == name:
            return msg.param_value


# --- Telemetry parsing --------------------------------------------------


def _decode_flag_bits(mask, enum_name, strip_prefix):
    """Turns one of pymavlink's bit-per-flag enums (MAV_SYS_STATUS_SENSOR,
    EKF_STATUS_FLAGS, ...) into a name->bool dict for `mask`. Skips the
    dialect's own ENUM_END sentinel -- not a real bit, so not a power of
    two, unlike every actual flag value in these enums.
    """
    decoded = {}
    for bit, entry in mavutil.mavlink.enums[enum_name].items():
        if not isinstance(bit, int) or bit == 0 or (bit & (bit - 1)) != 0:
            continue
        name = entry.name.removeprefix(strip_prefix).lower()
        decoded[name] = bool(mask & bit)
    return decoded


def parse_status_text(msg):
    """From STATUSTEXT. severity is a MAV_SEVERITY value, 0 (EMERGENCY)
    through 7 (DEBUG) -- lower is worse, same ordering as syslog. ArduPilot
    already sends plain-English text for exactly the things a monitor wants
    to surface ("PreArm: ...", "EKF Failsafe", "Low Battery"), so reading
    this is the cheapest way to get meaningful alerts without computing any
    threshold yourself.
    """
    return {"severity": msg.severity, "text": msg.text}


def parse_battery(msg):
    """From SYS_STATUS. current_battery and battery_remaining are -1 when
    the autopilot doesn't know yet (e.g. right after boot) -- reported as
    None rather than a misleading -1 or -0.01, same convention
    drone_backend.py's inline SYS_STATUS handling already uses for
    battery_level.
    """
    return {
        "voltage_v": msg.voltage_battery / 1000.0,
        "current_a": msg.current_battery / 100.0 if msg.current_battery >= 0 else None,
        "remaining_pct": msg.battery_remaining if msg.battery_remaining >= 0 else None,
    }


def parse_sensor_health(msg):
    """From SYS_STATUS's onboard_control_sensors_present/health bitmasks.
    Only sensors marked "present" are reported -- an airframe with no
    rangefinder fitted shouldn't show up as an unhealthy rangefinder.
    """
    present = _decode_flag_bits(
        msg.onboard_control_sensors_present, "MAV_SYS_STATUS_SENSOR", "MAV_SYS_STATUS_"
    )
    health = _decode_flag_bits(
        msg.onboard_control_sensors_health, "MAV_SYS_STATUS_SENSOR", "MAV_SYS_STATUS_"
    )
    return {name: health[name] for name, is_present in present.items() if is_present}


def parse_ekf_status(msg):
    """From EKF_STATUS_REPORT. `flags` says which estimates (attitude,
    velocity, position, ...) the EKF currently trusts; the variance fields
    are the same innovation-based error estimates ArduPilot's own EKF
    failsafe logic watches -- rising variance means the filter is losing
    confidence before a failsafe necessarily trips.
    """
    return {
        "flags": _decode_flag_bits(msg.flags, "EKF_STATUS_FLAGS", "EKF_"),
        "velocity_variance": msg.velocity_variance,
        "pos_horiz_variance": msg.pos_horiz_variance,
        "pos_vert_variance": msg.pos_vert_variance,
        "compass_variance": msg.compass_variance,
    }


def parse_vibration(msg):
    """From VIBRATION. vibration_x/y/z are a clipping-derived vibration
    metric in m/s/s, not raw acceleration; clipping_0/1/2 are cumulative
    clip counts for up to 3 IMUs since boot, so watch them as a rate, not
    just for being nonzero.
    """
    return {
        "vibration_x": msg.vibration_x,
        "vibration_y": msg.vibration_y,
        "vibration_z": msg.vibration_z,
        "clipping": (msg.clipping_0, msg.clipping_1, msg.clipping_2),
    }


def parse_gps_accuracy(msg):
    """From GPS_RAW_INT. h_acc/v_acc are MAVLink 2 extension fields -- see
    the MAVLINK20 note at the top of this file. SITL's default GPS model
    is fairly idealized, so expect these to sit near-constant "good" values
    unless a SIM_GPS_* fault has been injected via set_param().
    """
    return {
        "fix_type": msg.fix_type,
        "satellites_visible": msg.satellites_visible,
        "h_acc_m": msg.h_acc / 1000.0,
        "v_acc_m": msg.v_acc / 1000.0,
    }
