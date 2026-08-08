#!/usr/bin/env python3
"""Generates docker-compose.override.yml for a fleet of simulated vehicles.

Reads CENTER_LOCATION/CENTER_HEADING/NUM_DRONES/DRONE_SPACING_M from .env
(a nickname into locations.json plus a headcount), computes where each
vehicle starts, and writes one sitl_N/drone_backend_N pair per vehicle into
docker-compose.override.yml -- which `docker compose` auto-merges with
docker-compose.yml, no -f flags needed.

This script only writes that file. It never runs `docker compose` itself --
run `docker compose up -d` / `down` yourself afterward (and again whenever
you re-run this script, e.g. after lowering NUM_DRONES, since Compose won't
know to stop containers for vehicles that disappeared from the file until
you run `docker compose up -d --remove-orphans` or `down` first).

Geometry: NUM_DRONES=1 places that one vehicle exactly at CENTER_LOCATION.
NUM_DRONES>1 arranges all of them evenly spaced on a ring around
CENTER_LOCATION (nothing sits exactly on the center coordinate once there's
more than one) -- the ring radius is solved from DRONE_SPACING_M so that
adjacent vehicles end up that many meters apart, using the regular-polygon
chord length formula: chord = 2 * R * sin(pi / N).

Any of the four settings can also be passed as a flag (--location,
--num-drones, --heading, --spacing) for a one-off run without editing
.env -- a flag wins over a shell env var, which wins over .env, which
wins over the built-in default.
"""
import argparse
import json
import math
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAB_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(LAB_DIR, ".env")
LOCATIONS_PATH = os.path.join(LAB_DIR, "locations.json")
OVERRIDE_PATH = os.path.join(LAB_DIR, "docker-compose.override.yml")

EARTH_RADIUS_M = 6378137.0
MAX_DRONES = 7  # UPDATE_DRONE_COLORS in drone_backend.py has 7 entries


def fail(message, remediation):
    print(f"\nFAIL: {message}")
    print(f"  -> {remediation}")
    sys.exit(1)


def load_dotenv(path):
    """Minimal KEY=VALUE parser -- these scripts don't shell-source .env,
    so this is the only thing that actually reads it (see VEHICLE_ID's
    comment in .env.example: host tools otherwise just see shell env)."""
    values = {}
    if not os.path.exists(path):
        return values
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def get_setting(dotenv, key, default, cli_value=None):
    """Precedence: an explicit CLI flag, then shell environment (e.g.
    `NUM_DRONES=3 python scripts/generate_fleet.py`), then .env, then the
    built-in default -- same precedence python-dotenv uses, with the CLI
    flag added on top as the most explicit override."""
    if cli_value is not None:
        return str(cli_value)
    return os.environ.get(key, dotenv.get(key, default))


def load_locations():
    if not os.path.exists(LOCATIONS_PATH):
        fail(
            f"locations.json not found at {LOCATIONS_PATH}.",
            "This file ships with the repo -- if it's missing, check you're "
            "running from lab/ and haven't deleted it.",
        )
    try:
        with open(LOCATIONS_PATH) as f:
            entries = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"locations.json isn't valid JSON: {e}", "Fix the syntax error and re-run.")

    if not isinstance(entries, list):
        fail("locations.json must be a JSON array of location objects.", "See the seeded entries (ND, CMAC) for the expected shape.")

    by_nickname = {}
    required = ("name", "nickname", "lat", "lon", "alt")
    for i, entry in enumerate(entries):
        missing = [k for k in required if k not in entry]
        if missing:
            fail(
                f"locations.json entry #{i} is missing field(s): {', '.join(missing)}.",
                f"Each entry needs {', '.join(required)}. Offending entry: {entry}",
            )
        nickname = entry["nickname"]
        if nickname in by_nickname:
            fail(
                f"locations.json has two entries with nickname '{nickname}'.",
                "Nicknames must be unique -- rename one of them.",
            )
        by_nickname[nickname] = entry
    return by_nickname


def resolve_center(dotenv, cli_value=None):
    locations = load_locations()
    nickname = get_setting(dotenv, "CENTER_LOCATION", "ND", cli_value)
    if nickname not in locations:
        valid = ", ".join(sorted(locations)) or "(none defined)"
        fail(
            f"CENTER_LOCATION '{nickname}' isn't in locations.json.",
            f"Valid nicknames: {valid}. Add a new entry to locations.json "
            "to save a new favorite, or fix the typo in .env/--location.",
        )
    entry = locations[nickname]
    return entry["lat"], entry["lon"], entry["alt"], entry["name"]


def resolve_num_drones(dotenv, cli_value=None):
    raw = get_setting(dotenv, "NUM_DRONES", "1", cli_value)
    try:
        n = int(raw)
    except ValueError:
        fail(f"NUM_DRONES='{raw}' isn't an integer.", "Set it to a whole number from 1 to 7 in .env or --num-drones.")
    if not (1 <= n <= MAX_DRONES):
        fail(
            f"NUM_DRONES={n} is out of range.",
            f"Must be between 1 and {MAX_DRONES} ({MAX_DRONES} is "
            "UPDATE_DRONE_COLORS' limit in drone_backend.py) -- set it in .env or --num-drones.",
        )
    return n


def resolve_spacing(dotenv, cli_value=None):
    raw = get_setting(dotenv, "DRONE_SPACING_M", "15", cli_value)
    try:
        spacing = float(raw)
    except ValueError:
        fail(f"DRONE_SPACING_M='{raw}' isn't a number.", "Set it to a positive number of meters in .env or --spacing.")
    if spacing <= 0:
        fail(f"DRONE_SPACING_M={spacing} must be positive.", "Set it to a positive number of meters in .env or --spacing.")
    return spacing


def offset_to_lla(origin_lat, origin_lon, east_m, north_m):
    """Small ENU offset -> lat/lon, same throwaway-local-frame approximation
    test_circle.py uses for its own waypoint planning."""
    lat0_rad = math.radians(origin_lat)
    dlat = math.degrees(north_m / EARTH_RADIUS_M)
    dlon = math.degrees(east_m / (EARTH_RADIUS_M * math.cos(lat0_rad)))
    return origin_lat + dlat, origin_lon + dlon


def vehicle_positions(center_lat, center_lon, num_drones, spacing_m):
    if num_drones == 1:
        return [(center_lat, center_lon)]

    # Regular-polygon chord length: chord = 2 * R * sin(pi / N). Solve for R
    # so adjacent vehicles end up spacing_m apart.
    radius_m = spacing_m / (2 * math.sin(math.pi / num_drones))

    positions = []
    for i in range(num_drones):
        bearing_deg = i * (360.0 / num_drones)
        bearing_rad = math.radians(bearing_deg)
        north_m = radius_m * math.cos(bearing_rad)
        east_m = radius_m * math.sin(bearing_rad)
        positions.append(offset_to_lla(center_lat, center_lon, east_m, north_m))
    return positions


SERVICE_TEMPLATE = """\
  sitl_{n}:
    <<: *sitl
    command: >
      ./Tools/autotest/sim_vehicle.py -v ArduCopter --no-rebuild -w
      --custom-location={lat:.7f},{lon:.7f},{alt},{heading}
      --out=udpout:drone_backend_{n}:14550
    depends_on:
      - drone_backend_{n}

  drone_backend_{n}:
    <<: *drone-backend
    environment:
      VEHICLE_ID: "{n}"
      MAVLINK_CONN: udpin:0.0.0.0:14550
      MQTT_HOST: mosquitto
      UPDATE_DRONE: ${{UPDATE_DRONE:-}}
"""

HEADER = """\
# GENERATED by scripts/generate_fleet.py -- do not hand-edit, re-run the
# generator instead (it reads CENTER_LOCATION/NUM_DRONES/etc. from .env).
# Compose auto-merges this with docker-compose.yml.
x-sitl: &sitl
  image: ${SITL_IMAGE:-uav-course-sitl:copter-4.6.3}
  platform: linux/amd64
  tty: true
  stdin_open: true

# MAVLINK_CONN/MQTT_HOST/UPDATE_DRONE are the same for every vehicle -- each
# drone_backend binds udpin:0.0.0.0:14550 inside its own container network
# namespace, so the port is never published to the host and never collides
# across vehicles.
x-drone-backend: &drone-backend
  build:
    context: .
    dockerfile: docker/Dockerfile.backend
  volumes:
    - ./backend/mavlink_lib.py:/app/mavlink_lib.py:ro
    - ./backend/drone_backend.py:/app/drone_backend.py:ro
  depends_on:
    - mosquitto

services:
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Write docker-compose.override.yml for a fleet of simulated vehicles.",
        epilog="Flags override .env for this run only -- .env itself is left untouched. "
               "Example: generate_fleet.py --location CMAC --num-drones 3",
    )
    parser.add_argument("--location", "-l", metavar="NICKNAME", help="locations.json nickname (overrides CENTER_LOCATION)")
    parser.add_argument("--num-drones", "-n", type=int, metavar="N", help="how many vehicles, 1-7 (overrides NUM_DRONES)")
    parser.add_argument("--heading", type=float, metavar="DEG", help="starting heading in degrees (overrides CENTER_HEADING)")
    parser.add_argument("--spacing", type=float, metavar="METERS", help="target spacing between adjacent vehicles (overrides DRONE_SPACING_M)")
    return parser.parse_args()


def main():
    args = parse_args()
    dotenv = load_dotenv(ENV_PATH)
    center_lat, center_lon, center_alt, center_name = resolve_center(dotenv, args.location)
    heading = get_setting(dotenv, "CENTER_HEADING", "0", args.heading)
    num_drones = resolve_num_drones(dotenv, args.num_drones)
    spacing_m = resolve_spacing(dotenv, args.spacing)

    positions = vehicle_positions(center_lat, center_lon, num_drones, spacing_m)

    print(f"Fleet center: {center_name} ({center_lat}, {center_lon}, {center_alt}m AMSL)")
    print(f"Vehicles: {num_drones}" + (f", ~{spacing_m:.0f}m apart on a ring" if num_drones > 1 else " (at center)"))

    blocks = [HEADER]
    for i, (lat, lon) in enumerate(positions, start=1):
        blocks.append(SERVICE_TEMPLATE.format(n=i, lat=lat, lon=lon, alt=center_alt, heading=heading))
        print(f"  vehicle {i}: {lat:.7f}, {lon:.7f}")

    with open(OVERRIDE_PATH, "w") as f:
        f.write("\n".join(blocks))

    print(f"\nWrote {OVERRIDE_PATH}")
    print("Next: `docker compose pull` (first time) then `docker compose up -d`.")
    print("Changed NUM_DRONES down from a previous run? `docker compose up -d --remove-orphans` "
          "(or `docker compose down` first) to drop the vehicles that disappeared.")


if __name__ == "__main__":
    main()
