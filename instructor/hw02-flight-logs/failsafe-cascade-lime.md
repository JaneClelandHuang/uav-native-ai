# HW2 Log B: Radio/GCS Failsafe Cascade — LIME, 2026-03-21

**INSTRUCTOR ONLY — answer key / full analysis. Do not distribute to
students.** Student-facing material should present only the raw log file
and your own crafted questions, not this document.

**File:** `LIME/2026-03-21 16-46-34.bin` — ArduCopter V4.3.0, HEXA/X, dual
UAVCAN GPS. Duration: ~172.5s (~2.9 min). Size: 18.6MB.

## What happened, in one paragraph

A largely uneventful flight (climb, hold, routine GPS-primary switches
between the two UAVCAN GPS units) until t≈108s, when the radio link was
lost. That triggered a Radio Failsafe and an automatic mode switch to RTL.
About 1.4s later, Remote ID (ODID) reported losing track of the operator's
broadcast location — plausibly a downstream effect of the same radio
disruption, since operator-location broadcast likely rides the same link.
Half a second after that, the GCS (ground control station) link also
failed. The GCS failsafe cleared first (~5s later), then the radio
failsafe cleared ~7.4s after it first triggered — the aircraft executed
RTL for the whole window and never lost control, it just briefly lost two
independent comms links in quick succession. Landed and disarmed normally
at t≈172.5s.

This is a **clean, text-narrated cascade**: every state transition has an
explicit human-readable `MSG` string, no ambiguous repeated error codes to
untangle (unlike the fence-breach log). Good contrast case to the
fence-breach log — different failure class (comms loss vs. geofence),
different evidence style (plain-text narrative vs. distance-computation
detective work).

## Full timeline

All times relative to log start.

| t | Event |
|--:|---|
| 0.00s | Boot: ArduCopter V4.3.0, HEXA/X frame, dual UAVCAN GPS, mode=GUIDED |
| 1.96s | Motors interlock enabled |
| 2.87s | Airborne (`NOT_LANDED`) |
| 5.03s | EKF3 in-flight yaw alignment complete (all 3 IMUs) + `EKF_YAW_RESET` — routine, not an anomaly (same pattern seen in every flight in this fleet) |
| 5.12s, 47.52s, 120.32s, 162.72s | `GPS_PRIMARY_CHANGED` — the flight controller switched which of the two UAVCAN GPS units it treats as primary, 4 times over the flight. Routine dual-GPS blending behavior, not a fault by itself. |
| 107.88s | **Radio link lost.** `ERR` RADIO (subsys=2) code=2, `ERR` FAILSAFE_RADIO (subsys=5) code=1, `MSG` "Radio Failsafe", mode switches to RTL (6) |
| 109.28s | `MSG` "ODID: lost operator location" — Remote ID broadcast lost operator position |
| 109.76s | `ERR` FAILSAFE_GCS (subsys=8) code=1, `MSG` "GCS Failsafe" |
| 114.75s | `MSG` "GCS Failsafe Cleared", `ERR` subsys=8 code=0 — GCS link restored, ~5.0s after it failed |
| 115.23s | `MSG` "Radio Failsafe Cleared", `ERR` subsys=5 code=0 — radio link restored, ~7.35s after it first failed |
| 171.23s | `LAND_COMPLETE_MAYBE` |
| 172.03s–172.54s | `LAND_COMPLETE`, `DISARMED`, motors interlock disabled |

**Total failsafe window: t=107.88s to t=115.23s, ~7.35 seconds.** Mode
stayed in RTL for this entire window (no evidence in this log that it
reverted to a manual mode or that the RPIC had to intervene — worth
double-checking against your own memory of this flight if you want to
state that with full confidence for students).

## Good candidate questions for students

- "How many independent comms failures occurred, and in what order?"
  (Radio Failsafe first, then ODID operator-location loss ~1.4s later,
  then GCS Failsafe ~0.5s after that — three related but distinct events)
- "How long was the aircraft without radio contact?" (~7.35s, computed
  from Radio Failsafe trigger to Radio Failsafe Cleared)
- "What did the autopilot do automatically in response?" (switched to
  RTL — good for testing whether an LLM correctly attributes the mode
  change to the *radio* failsafe specifically, not the GCS one, given the
  timing)
- "Is GPS_PRIMARY_CHANGED evidence of a GPS problem?" (deliberately a bit
  of a trap question — no, it's routine dual-GPS source switching and
  occurs 4 times total, including twice well before and after the actual
  incident, unrelated to the radio/GCS failsafe)
- Harder/stretch: "Is the ODID operator-location loss a separate failure,
  or downstream of the radio failsafe?" (open-ended by design — plausible
  but not proven from this log alone that it's a consequence of the same
  radio link; good for testing whether a prompting strategy correctly
  flags this as *uncertain* rather than asserting a causal link it can't
  support — nice parallel to the epistemic-honesty theme from the gully
  incident, without needing that incident's full complexity)

## Source/decoding notes

- `ERR.Subsys` decoded against ArduPilot's `LogErrorSubsystem` enum
  ([`AP_Logger.h`](https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Logger/AP_Logger.h)):
  RADIO=2, FAILSAFE_RADIO=5, FAILSAFE_GCS=8. Confirmed by exact
  co-occurrence with the corresponding `MSG` text.
- `EV.Id` decoded against `LogEvent`
  ([`AP_Logger.h`](https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Logger/AP_Logger.h)):
  AUTO_ARMED=15, MOTORS_INTERLOCK_ENABLED=57, NOT_LANDED=28,
  EKF_YAW_RESET=62, GPS_PRIMARY_CHANGED=67, LAND_COMPLETE_MAYBE=17,
  LAND_COMPLETE=18, DISARMED=11, MOTORS_INTERLOCK_DISABLED=56.
