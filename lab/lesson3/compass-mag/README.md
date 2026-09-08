COMPASS / MAGNETIC INTERFERENCE -- LAB EXAMPLE
=============================================

A compass measures the Earth's magnetic field to work out which way the
aircraft is pointing. If something on the aircraft makes its own
magnetic field -- current through the power wiring, for example -- the
compass reads that instead, and the heading estimate drifts.

This flight has three compasses. One reads cleanly. Another is swamped
by a field that rises and falls with the throttle. Nothing to hand in.


THE FILE
--------

  2024-07-12 11-53-41.bin    LIME

(This is also the worst of the vibration flights -- a single flight can
show more than one problem. Worth keeping in mind for your analysis.)


WHAT TO LOOK AT
--------------

  python ../bin2csv.py "2024-07-12 11-53-41.bin" -t MAG --single
  python ../bin2csv.py "2024-07-12 11-53-41.bin" -t BAT,CTUN

  MAG     one row per compass reading. The I column is the compass
          number (0, 1, 2). MagX/MagY/MagZ are the field components,
          in milligauss (mG).
  BAT     Curr is the battery current draw
  CTUN    ThO is the throttle output, 0.0 to 1.0

For each compass, compute the field magnitude at each moment:

  magnitude = sqrt(MagX^2 + MagY^2 + MagZ^2)

A clean compass sits near a roughly constant value (here ~500 mG, the
local Earth field). A compass whose magnitude swings a lot in flight, or
whose offset is above ~600 mG, is suspect.


WORK THROUGH IT
--------------

- Plot the field magnitude of all three compasses on one chart, over
  the flight. Which one is stable? Which one is not?

- On a second chart, plot the bad compass's magnitude together with
  throttle (CTUN.ThO) or current (BAT.Curr). Do they move together?
  Roughly how strong is the relationship?

- What does that tell you about where that compass is mounted, or what
  is generating the field? Would you trust it for heading?

Things worth noticing, because they matter when you build the detector
(script or prompt):
  - You catch the bad compass by comparing it against the good ones,
    not by looking at it alone. A single-compass reading in isolation
    tells you very little.
  - The giveaway is correlation with throttle or current, not the raw
    value.
