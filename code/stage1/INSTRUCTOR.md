# Instructor Notes

## Publishing a pinned SITL image

Students should `docker pull`, never build ArduPilot from source in class
(a source build takes 10-20 minutes). To build and publish the pinned image:

```bash
GHCR_OWNER=your-org ./scripts/build_and_push_sitl.sh Copter-4.6.3
```

Then set `SITL_IMAGE=ghcr.io/your-org/uav-course-sitl:copter-4.6.3` in the
`.env` file you distribute to students. Bumping the ArduPilot version for a
later course run means re-running this script with a new tag and updating
that one `.env` value -- nothing else in the repo needs to change.

## Next lesson: pymavlink deep dive (slides TODO)

Students already flew a mission with `scripts/test_flight.py` (MQTT). The
prior course offering used DroneKit, which hid the MAVLink mechanics
entirely; this course uses raw pymavlink instead, so the plan is to walk
students through what's happening underneath `test_flight.py` *before*
layering MQTT on top of it.

**What's already built** (commits `31a83cc`, `63ae855`):

- `scripts/simple_flight.py` -- the identical mission (arm, takeoff,
  waypoint 1, waypoint 2, home, land) but with **no MQTT**: talks pymavlink
  straight to SITL. Meant to be shown/read line by line first.
- `backend/mavlink_lib.py` -- shared `connect`/`arm`/`disarm`/`takeoff`/
  `goto`/`land` primitives, used by both `drone_backend.py` (MQTT path) and
  `simple_flight.py` (direct path). This is "our own DroneKit."
- `PYMAVLINK-LIB.md` -- full write-up, including a concrete bit-by-bit
  walkthrough of the `SET_POSITION_TARGET_GLOBAL_INT` type mask (`0` = use
  this field, `1` = ignore it; worked example: `goto()`'s mask = binary
  `110111111000` = `3576` = `0xdf8`).
- `ARCHITECTURE.md` -- updated to point at `mavlink_lib.py` as where the
  MAVLink command logic now lives.

**Planned lesson flow** (agreed in conversation, not yet turned into
slides):

1. Walk through `simple_flight.py` step by step -- no MQTT, direct
   pymavlink, arm/takeoff/goto/land.
2. Let students feel the repetition/pain: the GUIDED-mode dance before
   arm/takeoff/goto, the arm bitmask, the position-target type mask. This
   *is* the motivation for wanting a library -- don't skip past it.
3. Reveal (or live-build) `mavlink_lib.py` as the extraction. `git show
   31a83cc` is a ready-made before/after diff if you'd rather project it
   than retype it live.
4. `PYMAVLINK-LIB.md`'s "Building `goto()`'s Mask, Bit by Bit" section is
   written to lift almost directly into a slide (bit table + worked
   binary/decimal/hex example).
5. Forward-pointer only, **not** to build now: `goto()` is a one-shot,
   non-interruptible send. A later need for smooth/interruptible
   trajectories (Ruckig-based) will need a different, *streaming* setpoint
   pattern (position+velocity+accel sent continuously, not a single
   target) -- likely a new module built on top of `mavlink_lib.py`, not a
   change to `goto()` itself. Worth a mention/teaser, not a build item, for
   this lesson.
