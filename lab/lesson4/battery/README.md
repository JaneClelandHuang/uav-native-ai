BATTERY -- WORKED EXAMPLE
========================

A live runtime monitor for one signal: `battery` (voltage, current,
remaining percent), built the same way you're asked to build your own
two categories in Step 2 and Step 4.

This is NOT one of the two categories you build a detector for. Your two
are GPS plus a choice of vibration or compass. Battery is here worked
through -- as the model for how deep your own plot and detector should
go, and as a check that your own solutions do not misreport a battery
problem as GPS / vibration / compass.

There are two scripts here, matching the two things you build for each
of your own categories, but NO combined version that shows the verdict
directly on the plot. Building that yourself, if you want it, is a real
extension beyond what's graded -- seeing it done for you here would
defeat the point of Step 4 asking you to design that connection yourself.


WHAT'S IN THIS FOLDER
----------------------

  battery_plot.py       Step 2's worked example -- subscribes to the
                         `battery` category, plots voltage/current/
                         remaining_pct live, no verdict of any kind.

  battery_detector.py   Step 4's worked example -- windowed heuristic
                         detector, same three-verdict vocabulary as
                         HW03 ("problem present" / "no problem" / "not
                         enough data yet"), each verdict printed with
                         quoted evidence from the window, not a bare
                         claim.

Read `battery_detector.py`'s module docstring first -- it explains why
its voltage threshold (11.0V) is set where it is, grounded in ArduPilot's
own real low-battery failsafe default (10.5V), not picked arbitrarily.
The same kind of grounding -- a real, stated reason for wherever your own
threshold ends up -- is what your write-up needs for GPS and your second
category.


HOW TO RUN IT
-------------

    pip install -r ../requirements.txt

Bring up the fleet, arm and take off a vehicle, then in separate
terminals:

    python battery_plot.py
    python battery_detector.py

Then inject a fault and watch both react:

    python ../../scripts/mischief_maker.py POWER-BATTERY 10 60 High

Two things worth carrying into your own two categories:
  - The verdict doesn't flip the instant the fault fires -- it flips once
    the *windowed average* crosses the threshold. That lag is the
    tradeoff a window buys you: it can't be fooled by one noisy sample,
    but it also can't react instantly. Both of your own detectors will
    have this same tradeoff; know what your own window size is buying and
    costing you.
  - Run `mischief_maker.py` more than once at the same severity before
    you trust a detector -- the magnitude is randomized even within one
    severity level, so one run against a fixed value tells you less than
    it feels like it does.
