"""Dispatch table for lesson-4 runtime monitoring: which live MAVLink
messages feed which monitorable category, and (separately) which messages
get relayed straight through instead of ever being stored.

drone_backend.py's mavlink_reader() is still the only thing that calls
recv_match() (see its own docstring for why) -- this module stays pure,
same convention as the mavlink_lib.parse_* functions it wraps: message in,
(category, fields) or (topic suffix, fields) out, no side effects, no
state of its own. It owns the one thing that should change when a new
signal is wanted: CATEGORY_HANDLERS. Nothing in drone_backend.py or
VehicleState needs to change to add a category -- see ARCHITECTURE.md's
"The MQTT contract" section.
"""
import json
import logging

import mavlink_lib

log = logging.getLogger("monitor_signals")

# msg_type -> (category name, parser). Every category is latest-value-wins:
# a new message of this type fully replaces the category's last entry in
# VehicleState.monitor, never merged field-by-field -- same semantics as
# every existing telemetry field, just namespaced by category instead of
# being its own VehicleState attribute.
CATEGORY_HANDLERS = {
    "VIBRATION": ("vibration", mavlink_lib.parse_vibration),
    "GPS_RAW_INT": ("gps", mavlink_lib.parse_gps_accuracy),
    "EKF_STATUS_REPORT": ("ekf", mavlink_lib.parse_ekf_status),
    "RAW_IMU": ("compass", mavlink_lib.parse_compass),
    "SYS_STATUS": ("battery", mavlink_lib.parse_battery),
}

# msg_type -> (topic suffix, parser). Relayed the instant they arrive, on
# uav/<id>/<topic suffix>, never stored in VehicleState and never retained.
# Kept in this module for discoverability even though the handling is
# different in kind, not just another category -- STATUSTEXT is an event
# stream, not a value that's meaningfully "current"; see ARCHITECTURE.md.
RELAY_HANDLERS = {
    "STATUSTEXT": ("status_text", mavlink_lib.parse_status_text),
}

KNOWN_CATEGORIES = frozenset(category for category, _ in CATEGORY_HANDLERS.values())


def extract_for_storage(msg):
    """msg -> (category, fields dict), or None if this message type isn't
    one of the stored categories."""
    entry = CATEGORY_HANDLERS.get(msg.get_type())
    if entry is None:
        return None
    category, parser = entry
    return category, parser(msg)


def extract_for_relay(msg):
    """msg -> (topic_suffix, fields dict), or None if this message type
    isn't one of the relay-immediately types."""
    entry = RELAY_HANDLERS.get(msg.get_type())
    if entry is None:
        return None
    topic_suffix, parser = entry
    return topic_suffix, parser(msg)


def parse_requested_categories(payload):
    """A monitor_config MQTT payload (raw JSON string) -> (valid_set,
    unknown_list). Never raises -- a malformed payload or an unknown
    category name gets logged and dropped, not allowed to crash the
    backend's one reader/publish loop. Same "trust but verify" handling
    already applied to uav/<id>/command payloads in drone_backend.py.
    """
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        log.warning("Ignoring malformed monitor_config payload: %r", payload)
        return set(), []

    requested = data.get("categories", [])
    if not isinstance(requested, list):
        log.warning("monitor_config 'categories' must be a list, got: %r", requested)
        return set(), []

    valid = {c for c in requested if c in KNOWN_CATEGORIES}
    unknown = [c for c in requested if c not in KNOWN_CATEGORIES]
    return valid, unknown
