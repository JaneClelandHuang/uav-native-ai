BATTERY -- LAB EXAMPLE
=====================

One flight where the battery voltage dropped far enough under load to
trigger an automatic failsafe -- and then blocked the next arm attempt.

This is NOT one of the three problems you write an HW3 prompt for. It
is here as a fourth kind of problem: something to compare the others
against, and a case to check that your prompts do not misreport it as
vibration / GPS / compass. Nothing to hand in.


THE FILE
--------

  2025-07-04 14-41-47.bin    FUCHSIA


WHAT TO LOOK AT
--------------

  python ../bin2csv.py "2025-07-04 14-41-47.bin" -t BAT,ERR,MSG,MODE

  BAT     Volt (pack voltage), Curr (current draw, amps),
          RemPct (estimated charge remaining), Res (internal resistance)
  ERR     subsystem 6 is the battery failsafe
  MSG     text: "Battery Failsafe" fires in flight;
          "PreArm: Battery failsafe" blocks the next arm

This is a 12S pack, so a healthy resting voltage is roughly 44-50 V.


WORK THROUGH IT
--------------

- Plot BAT.Volt and BAT.Curr over the flight. Mark the moment the
  failsafe fired (from ERR or MSG).

- Was the voltage low because the battery was empty, or because it was
  being pulled down under load? Compare RemPct.

- The next flight's arm was blocked. Why would the autopilot still be
  unhappy after the pack had a chance to recover?

Things worth noticing, because they matter when you write the prompt:
  - Unlike vibration or compass interference, this failure has an
    explicit ERR / MSG. When the log tells you plainly, a prompt
    should use that -- it does not have to infer everything.
  - Read voltage under load, not at rest -- a pack can look fine on the
    bench and only sag past the trip point once the motors pull current.
