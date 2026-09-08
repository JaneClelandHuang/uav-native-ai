BATTERY -- WORKED EXAMPLE
========================

One flight where the battery tripped an automatic failsafe in the air
and then blocked the next arm attempt.

This is NOT one of the two failures you analyse for HW3. It is here
worked through -- as the model for how deep your own analysis and
write-ups should go, and as a check that your solutions do not misreport
a battery problem as vibration / GPS / compass.

There is a coded solution here but NO prompt. Writing the prompt is your
job on your own two failures -- seeing one done for you would defeat the
point.


WHAT'S IN THIS FOLDER
--------------------

  2025-07-04 14-41-47.bin    the log (FUCHSIA)

  diagnosis.md               the written diagnosis -- verdict, timeline,
                             the three questions answered with evidence
  physics-lesson.md          a short primer on voltage vs current,
                             capacity, internal resistance and sag
  analyze.py                 Track A -- a small program that reads the
                             log and prints the verdict + saves graphs
  *.png                      the graphs analyze.py produces

Read diagnosis.md first, then read analyze.py and see how it gets
there. Your two failures should each end up with a script, a prompt of
your own, and a short paragraph on each in hw03/REPORT.md.


THE QUESTIONS IT ANSWERS
-----------------------

  python ../bin2csv.py "2025-07-04 14-41-47.bin" -t BAT,ERR,MSG,MODE

- Plot BAT.Volt and BAT.Curr over the flight; mark where the failsafe
  fired (from ERR / MSG).
- Was the voltage low because the pack was empty, or because it was
  pulled down under load? Compare RemPct and consumed mAh.
- The next arm was blocked. Why is the autopilot still unhappy after the
  pack has had a chance to recover?

Two things worth carrying into your own analysis:
  - When the log says it plainly (an explicit ERR / MSG), use that --
    don't infer what is already stated.
  - Read voltage under load, not at rest -- a pack can look fine on the
    bench and only sag past the trip point once the motors pull current.
