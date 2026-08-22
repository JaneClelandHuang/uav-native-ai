# HW2 Log A: Geofence Breach — FUCHSIA, 2025-08-24

**INSTRUCTOR ONLY — answer key / full analysis. Do not distribute to
students.** Student-facing material should present only the raw log file
and your own crafted questions, not this document.

**File:** `FUCHSIA/2025-08-24 11-56-32.bin` — ArduCopter V4.3.0, HEXA/X,
dual UAVCAN GPS. Duration: ~150s. Size: 16.3MB.

## What happened, in one paragraph

The aircraft climbed to ~18.7m AGL and settled into a position roughly
28.5m from home — essentially right on the geofence boundary (radius
~28.5m in this configuration). Small natural position oscillation around
that boundary caused the fence-breach detector to trip repeatedly: 11
distinct "Fence Breached" events over ~90 seconds, each one clearing again
within a second or two as the small oscillation carried the vehicle back
inside the boundary. Around t=76s an operator (or the autopilot) switched
to POSHOLD, and three more breaches occurred even after that (the vehicle
was still sitting right at the edge). The flight ended with a normal
landing and disarm at t≈150s.

This is a **clean, low-complexity example**: one repeating cause (hovering
at a fixed distance that happens to equal the fence radius), no cascading
failures, no ambiguity about mechanism. Good for a first "read the log,
answer factual questions" exercise.

## Full timeline

All times relative to log start.

| t | Event |
|--:|---|
| 0.00s | Boot: ArduCopter V4.3.0, HEXA/X frame, dual UAVCAN GPS, mode=GUIDED |
| 1.96s | Motors interlock enabled |
| 2.84s | Airborne (`NOT_LANDED`) |
| 5.08–5.09s | EKF3 in-flight yaw alignment complete (all 3 IMUs) + `EKF_YAW_RESET` — routine post-liftoff event, not an anomaly |
| 17.79s | `ERR` NAVIGATION (subsys=22) code=5 begins — repeats every ~0.3s continuously from here through t≈75s (see note below) |
| 21.02s | **1st "Fence Breached"** — `ERR` FAILSAFE_FENCE (subsys=9) code=2 |
| 21.35s | Fence breach clears — `ERR` subsys=9 code=0 |
| 49.28s, 55.60s, 57.26s, 62.25s, 65.58s, 70.23s, 73.22s | Fence breach/clear repeats — each event lasts well under 2s |
| 76.45s | Mode switches to POSHOLD (16) |
| 79.87s, 81.87s, 87.52s | Three more fence breach/clear cycles, *after* the POSHOLD switch |
| 149.05s | `LAND_COMPLETE_MAYBE` |
| 149.85s | `LAND_COMPLETE`, `DISARMED`, motors interlock disabled |

**Distance from home at every breach event: 28.47–28.52m, altitude
18.60–18.67m AGL — remarkably consistent.** This is the strongest single
piece of evidence for what's going on: the vehicle wasn't flying erratic
patterns near the fence, it was essentially parked at one spot that
happens to sit right on the boundary.

## The repeating NAVIGATION (subsys=22) error

`ERR` subsys=22 (NAVIGATION) code=5 fires roughly every 0.3s from t=17.79s
through t≈75s (~190 occurrences) — far more often than the fence-breach
events themselves. I have **not** decoded the exact meaning of NAVIGATION
error code 5 specifically (ArduPilot's error *codes*, unlike subsystems,
are defined per-subsystem in source and I didn't chase this one down) —
flag this as an open item if a student's question requires it. Plausible
reading, not confirmed: a per-cycle navigation-controller complaint tied
to being held at/against the fence boundary, logged far more frequently
than the discrete breach/clear transitions because it's evaluated every
control loop rather than only on state change.

## Good candidate questions for students

- "How far from home was the aircraft when each fence breach occurred?"
  (answer: consistently ~28.5m — same each time, not variable — this is
  the key insight, and it's directly computable from `POS` vs the `ORGN`
  home point)
- "How many total fence-breach events occurred, and how long did each
  last?" (11 events, each clearing within ~0.3-2s)
- "Did switching to POSHOLD at t=76s stop the fence breaches?" (no — 3
  more occurred afterward; good for testing whether a student/LLM
  correctly reads mode-switch timing against event timing rather than
  assuming an intervention immediately fixed things)
- Harder/stretch: "What does the repeating NAVIGATION error suggest about
  how often the fence/nav check runs, versus how often the discrete
  breach event is logged?" (tests distinguishing per-cycle vs. on-change
  logging — legitimately open-ended, we don't have a fully confirmed
  answer either)

## Source/decoding notes

- `ERR.Subsys` decoded against ArduPilot's `LogErrorSubsystem` enum
  ([`AP_Logger.h`](https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Logger/AP_Logger.h)):
  FAILSAFE_FENCE=9, NAVIGATION=22.
  Confirmed by exact co-occurrence with "Fence Breached"/clear `MSG` text.
- Distance-from-home computed via flat-earth ENU conversion from `POS`
  against the `ORGN` (home) record, same method as
  `../../scripts/analyze_gully_incident.py` (not fence-breach-specific,
  but reusable).
