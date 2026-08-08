#!/usr/bin/env python3
"""Launches flight_vehicle_1.py, _2.py, and _3.py concurrently -- three
different drones flying three different missions (square / circle / fly_home)
at once, over the same MQTT contract test_flight.py/test_circle.py use.

No flags, no config -- run it as-is against a 3-vehicle fleet
(`python scripts/generate_fleet.py --num-drones 3`, then `docker compose up
-d`, before this). It only dispatches the three fixed flight_vehicle_*.py
scripts; it doesn't know how to run a different number of vehicles or
different missions -- see ARCHITECTURE.md for why that's deliberate.

Runs via subprocess (each flight script inherits this process's Python
interpreter and environment -- MQTT_HOST/MQTT_PORT overrides included), not
a shell script, so this behaves identically on WSL2 and macOS without any
OS-specific logic.

Requires paho-mqtt in whichever interpreter `sys.executable` resolves to
(same repo-root .venv every other script here uses).
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FLIGHTS = ["flight_vehicle_1.py", "flight_vehicle_2.py", "flight_vehicle_3.py"]


def main():
    print(f"Launching {len(FLIGHTS)} flights concurrently: {', '.join(FLIGHTS)}\n")

    procs = [
        (name, subprocess.Popen([sys.executable, str(SCRIPT_DIR / name)]))
        for name in FLIGHTS
    ]

    # Output from all three interleaves live in the terminal (each line is
    # already prefixed "[vehicle N]" by the flight scripts themselves, the
    # same way `docker compose up` interleaves multiple services' logs) --
    # deliberately not captured/buffered, so you can watch all three
    # missions progress in real time rather than only seeing results once
    # everything finishes.
    results = [(name, proc.wait()) for name, proc in procs]

    print("\n=== Fleet demo summary ===")
    failures = [name for name, code in results if code != 0]
    for name, code in results:
        print(f"  {'PASS' if code == 0 else 'FAIL'}: {name}")

    if failures:
        print(f"\nFAIL: {len(failures)}/{len(FLIGHTS)} flight(s) failed: {', '.join(failures)}")
        sys.exit(1)

    print(f"\nPASS: all {len(FLIGHTS)} flights completed.")


if __name__ == "__main__":
    main()
