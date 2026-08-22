# Instructor Notes

Everything in this `instructor/` directory is deliberately kept **outside**
`lab/` — `lab/` is exactly what gets vendored into student homework repos
(see below), so anything that shouldn't be visible to students (this repo's
lesson planning, GHCR push access, etc.) has to live somewhere else.

## Two-repo course setup

This course runs two repos:

- **`uav-native-ai`** (this repo) — course site + the canonical `lab/`
  infra (ArduPilot SITL, MQTT backend, matplotlib viewer). Used directly
  for team-project work later in the semester.
- **`native-ai-uav-fall-2026`** — the template repo GitHub (or GitHub
  Classroom) stamps out into each student's own private repo for the
  individual `hw01`–`hw06` assignments. It vendors a copy of `lab/` from
  this repo, via `git subtree`, so homeworks get the same SITL/MQTT
  environment without depending on this repo at homework time.

**Initial vendoring** (already done once, re-run only if the template needs
to be rebuilt from scratch): from `uav-native-ai`,
`git subtree split --prefix=lab -b lab-export` produces a branch containing
just `lab/`'s history as if it were a repo root; from
`native-ai-uav-fall-2026`, `git subtree add --prefix=lab <path-or-url-to-
uav-native-ai> lab-export --squash` pulls that in.

**Keeping already-created student repos in sync.** `git subtree pull`
against individual student repos is *not* used for ongoing updates — GitHub
"generate repository from template" commonly gives each student repo a
single fresh commit with none of the template's history behind it, which
breaks subtree pull's usual merge-point tracking. Instead:

```bash
# after committing your fix under lab/ in uav-native-ai:
instructor/scripts/sync-lab-infra.sh <roster-file>
```

`<roster-file>` is a plain text file, one student repo git URL per line —
**never commit this file**, it's private student data (`.gitignore` already
excludes `instructor/roster*`). The script exports the current `lab/` tree,
mirrors it (via `rsync --delete`, so removed files propagate too) into each
student repo's `lab/` directory, and commits + pushes only the repos where
something actually changed. Students just see a new commit land and
`git pull` — no subtree/submodule mechanics on their end.

**Distributing shared, non-per-student material (flight logs, datasets,
etc.).** GitHub Releases do **not** carry over when a repo is generated
from a template — a Release on `native-ai-uav-fall-2026` is only visible
to people with direct access to that repo, not to students who only have
their own individually-generated `native-ai-uav-<netid>` repo. Shared
downloadable material instead goes in a separate repo,
**`nd-native-ai-uav/native-ai-uav-resources`**, with read-only access
granted via the **`fall-2026-students`** GitHub team (`pull` permission
only). Add each student's GitHub username to that team as they enroll;
put shared files as Releases there, e.g.
https://github.com/nd-native-ai-uav/native-ai-uav-resources/releases/tag/hw02-flight-logs.
This repo is separate from the per-student homework repos on purpose —
don't confuse it with the template.

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
