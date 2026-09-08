VIBRATION -- LAB EXAMPLE
=======================

Four real flights of the LIME hexacopter. The first is a healthy flight
-- your reference for what "normal" looks like. The other three are one
flying session, about 15 minutes apart, and the vibration climbs across
them.

These are here so you can get to know the signal before you write a prompt
to detect it. Nothing to hand in.


THE FILES
---------

  2025-04-24 17-13-12.bin    ~1 min    a clean flight -- your baseline
  2026-02-26 14-12-41.bin    ~6 min  \
  2026-02-26 14-21-44.bin    ~5 min   > one session, ~15 min apart each
  2026-02-26 14-27-34.bin    ~8 min  /

The last flight ends in an automatic RTL. That RTL is a planned mission
step, not a vibration failsafe -- ArduPilot's vibration failsafe never
fired in any of these logs, even on the worst one.


WHAT TO LOOK AT
--------------

The record is called VIBE. Export it:

  python ../bin2csv.py "2026-02-26 14-27-34.bin" -t VIBE --single

Columns:
  t_s                  seconds since the log started
  VibeX, VibeY, VibeZ  vibration on each axis, in m/s^2
  Clip                 running count of accelerometer clipping events
                       (should stay at 0)

ArduPilot's rule of thumb for the VibeX/Y/Z values:
  under 30    normal, fine
  30 to 60    elevated -- investigate
  over 60     likely to degrade position/altitude control


WORK THROUGH IT
--------------

- Plot the healthy flight first, so you know the shape of a normal
  trace -- the typical level and the worst spike.

- Plot the three session flights. How does the vibration change from
  the first to the last? Put numbers on it.

- For each flight, where would you land: healthy, elevated, or unsafe?
  What in the data puts it there?

- On the worst flight, check whether anything else moves with the
  vibration -- try BAT.Curr (battery current) and the ATT record
  (DesRoll vs Roll, DesPitch vs Pitch).

Things worth noticing, because they matter when you write the prompt:
  - High vibration is evidence, not a diagnosis. It tells you the
    measurements are noisy, not what caused it (a chipped prop, a loose
    mount, a resonance).
  - The autopilot's own vibration failsafe never fired here. A detector
    can't just wait for ArduPilot to raise the alarm.
  - "Healthy" is not zero -- even the clean flight has real vibration.
    You need a threshold, and you have to defend where you put it.
