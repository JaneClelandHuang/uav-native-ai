# Lesson 1 — UAV Infrastructure

## Lesson Objectives

By the end of this lesson, you should be able to:

- Install and run the ArduPilot SITL + MQTT environment locally
- Fly the simulated Copter manually (arm, take off, move, land) and watch
  it happen — both via the MAVProxy console directly, and via the
  scripted `test_flight.py`
- Explain, at a high level, how the pieces talk to each other: SITL →
  `drone_backend.py` → MQTT broker → your viewer

This is infrastructure-and-orientation week. You're not writing flight
code yet — Assignment 1 is where you start building against this
environment. Right now the goal is: get it running, poke at it, and
understand the shape of the system well enough that the architecture
isn't a black box next lecture.

## Readings

Prioritized — if you only have time for the first two, do those.

1. **[SITL Simulator (Software in the Loop) — ArduPilot Dev Docs](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html)**
   What SITL actually is: a build of the real autopilot code using an
   ordinary C++ compiler, so it runs natively on your machine with no
   hardware. This is the concept the whole environment is built on.

2. **[Copter SITL/MAVProxy Tutorial — ArduPilot Dev Docs](https://ardupilot.org/dev/docs/copter-sitl-mavproxy-tutorial.html)**
   Hands-on, not just reading — walks through arming and taking off in
   GUIDED mode via the MAVProxy console. This is the same console you
   get through `docker compose attach sitl`. Do this once by hand before
   Assignment 1; it'll make the backend's code make a lot more sense.

3. **[MAVLink Basics — ArduPilot Dev Docs](https://ardupilot.org/dev/docs/mavlink-basics.html)**
   The messaging protocol underneath everything. One line worth reading
   twice: MAVLink messages aren't guaranteed to be delivered, so a
   ground station or companion computer has to check vehicle state
   rather than assume a command landed. That's exactly why parts of this
   course's backend retry things.

4. **[Copter Flight Modes — ArduPilot Docs](https://ardupilot.org/copter/docs/flight-modes.html)**
   Skim for GUIDED mode specifically. You'll see it referenced directly
   in the MQTT command contract.

5. *(Optional, quick background)* **[ArduPilot — Wikipedia](https://en.wikipedia.org/wiki/ArduPilot)**
   Five-minute orientation: what ArduPilot is, its history, how widely
   it's used.

6. *(Optional, deeper dive)* **[MAVLink Developer Guide](https://mavlink.io/en/)**
   The full, vehicle-agnostic protocol documentation, if #3 leaves you
   wanting more detail.

## Getting Started

Follow **`GETTING_STARTED.md`** in this repo for the full step-by-step
install (Docker setup, Apple Silicon note, cloning, environment
variables, and `verify_setup.py`). Come to Lecture 2 with
`verify_setup.py` passing.

## Homework

**1. Know the architecture — pop quiz Thursday.**
Self-graded, does not count toward your grade — this is a checkpoint for
*you*, not for us. Make sure you can explain, without looking anything
up: what SITL is, why `drone_backend.py` is the only thing that speaks
pymavlink, why MQTT sits between the backend and any frontend, and what
the retained `home` topic is for.

**2. Fly something over MQTT.**
Using `test_flight.py` as a reference for the pattern (arm → command →
watch telemetry for the outcome → next command), write your own short
script that flies a route more interesting than a straight line. Pick
**one**:

- A **zig-zag** — a sequence of `goto` waypoints alternating left/right
  as the vehicle moves generally forward.
- The zig-zag above, but **change altitude partway through** — issue a
  `goto` with a different `alt` mid-route, not just at takeoff.
- A **shape** traced entirely by `goto` waypoints — triangle, star,
  your initials, whatever. (A circle works too — approximate it with
  enough short waypoint segments.)
- **Land somewhere other than home** — fly out to a point, then land
  there directly, instead of returning first. Notice what does and
  doesn't reset when you do this.
- A **there-and-back** flight — fly out along any path, then explicitly
  `goto` back to the coordinates from the retained `home` topic before
  landing, rather than eyeballing a return path.

Whichever you pick, keep it simple: this is meant to be doable entirely
with the `arm` / `takeoff` / `goto` / `land` commands you already have,
no new backend features required. Watch it happen in `matplotlib_view.py`
while it runs.