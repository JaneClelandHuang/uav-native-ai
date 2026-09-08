GPS / POSITION -- LAB EXAMPLE
============================

The aircraft was commanded to climb straight up above its launch point,
then a bit higher to clear some trees. Instead, after reaching about
7 m it flew roughly 15 m sideways -- toward the trees -- while still
being told to go up. The pilot took manual control and landed it.

This one is harder than the others, and part of what you learn from it
is what the log CANNOT tell you. Nothing to hand in.


THE FILE
--------

  2025-09-04 10-23-55.bin    FUCHSIA


WHAT TO LOOK AT
--------------

  python ../bin2csv.py "2025-09-04 10-23-55.bin" -t GPS,POS,GUIP,ORGN,MODE,MSG,ERR

  GPS     HDop (lower is better; under ~1.5 is good), NSats, Status
  POS     Lat, Lng, RelHomeAlt -- where the aircraft actually was
  GUIP    the position the autopilot was TOLD to fly to (guided-mode
          target). pX and pY are latitude/longitude x 1e7; pZ is target
          altitude in cm.
  ORGN    two reference points. Type 0 = ekf_origin (where the position
          filter started). Type 1 = ahrs_home (the takeoff point / where
          RTL returns to).
  MODE    flight mode over time
  MSG/ERR anything the autopilot logged


WORK THROUGH IT
--------------

- Plot the horizontal track (POS.Lat/Lng, converted to metres from the
  launch point) with the commanded target (GUIP) on the same axes. Plot
  altitude vs time too.

- Did the aircraft lose track of where it was (its own position
  estimate went wrong), or did it fly accurately to a target that was
  itself in the wrong place? What in the data tells you which?

- Look at the two ORGN records. How far apart are they?

- Check GPS.HDop and ERR. Did the autopilot think anything was wrong
  during this flight?

- What can this log NOT tell you about the root cause? Where would that
  information have to come from instead?

Things worth noticing, because they matter when you build the detector
(script or prompt):
  - A "GPS / position problem" does not always show up as a bad GPS
    number. Here HDop is fine and there are zero errors.
  - The log records what the aircraft did, precisely. It does not always
    record why.
  - State each finding as something the data supports, something it
    hints at, or something outside what the log can show.
