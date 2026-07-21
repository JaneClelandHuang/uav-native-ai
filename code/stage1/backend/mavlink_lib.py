"""Shared MAVLink command primitives: build-and-send only, no waiting or
polling. drone_backend.py's MQTT command handler and scripts/simple_flight.py's
direct-scripted mission both fire the same arm/takeoff/goto/land vocabulary
at the autopilot -- only the outer wrapper (an MQTT message vs. a scripted
loop with its own resend/poll logic) differs, so that vocabulary lives here
once instead of twice.
"""
import time

from pymavlink import mavutil

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


def goto(conn, lat, lon, alt_m):
    conn.set_mode("GUIDED")
    time.sleep(0.1)
    conn.mav.set_position_target_global_int_send(
        0, conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        _GOTO_TYPE_MASK,
        int(lat * 1e7), int(lon * 1e7), alt_m,
        0, 0, 0, 0, 0, 0, 0, 0,
    )


def land(conn):
    conn.mav.command_long_send(
        conn.target_system, conn.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0, 0, 0, 0, 0, 0, 0, 0,
    )
