"""Shared MAVLink command primitives: build-and-send only, no waiting or
polling. drone_backend.py's MQTT command handler and scripts/simple_flight.py's
direct-scripted mission both fire the same arm/takeoff/goto/land vocabulary
at the autopilot -- only the outer wrapper (an MQTT message vs. a scripted
loop with its own resend/poll logic) differs, so that vocabulary lives here
once instead of twice.
"""
import math
import time

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
