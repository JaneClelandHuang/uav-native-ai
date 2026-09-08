LESSON 3 -- FLIGHT-LOG ANALYSIS
==============================

Two things this week.

THE HOMEWORK (HW3) -- on the lesson page, not in this folder
    Analyse TWO flight-log failures -- GPS / position (required) plus
    vibration OR compass / magnetic interference -- each one TWO ways:

      A. have Claude write you a small Python program you run yourself
      B. write a reusable prompt that returns the diagnosis with no
         code for you to keep

    Then a half-page retrospective: code vs prompt -- effort to verify,
    robustness, trust, maintainability, reproducibility. The graded
    skill is the comparison.
    Full spec: https://janeclelandhuang.github.io/uav-native-ai/lessons/lesson3.html

THE LAB EXAMPLES (this folder) -- not graded
    Real flight logs, one folder per kind of problem. They are here so
    you can SEE what each problem looks like in the data before you try
    to detect it. Extract the records, plot them, get a feel for the
    signal and for where it gets ambiguous.

    battery/ has a WORKED example -- a written diagnosis, a short physics
    primer, and a coded (Track A) solution. Read it first; it is the
    model for how deep your own analysis should go. It does NOT include a
    prompt -- that half is yours. It is NOT one of the failures you
    analyse.

Work through your two lab folders first. Then build the solutions.


THE LAB EXAMPLE FOLDERS
----------------------

  gps-position/    a flight told to climb straight up that drifted
                   sideways instead                         (required)

  vibration/       mechanical vibration -- a healthy flight, then a
                   session where it climbs                  (pick this OR compass-mag)

  compass-mag/     magnetic interference -- one compass reads the motors
                   instead of the Earth                     (pick this OR vibration)

  battery/         a battery failsafe -- a WORKED example: a written
                   diagnosis, a short physics primer, and a coded
                   (Track A) solution with its graphs. No prompt -- that
                   half is yours. Your model for how deep to go, and a
                   check on whether your solutions false-alarm on a
                   problem outside their scope. NOT one of your two.

Open the README in each folder for the file list, which records to
pull, and what to look at.

  prompt-activity/   a separate one-shot prompting exercise -- has its
                     own README.


READING A .bin
-------------

A .bin is a binary log of ~60 different record types. Use bin2csv.py to
export the ones you care about:

  cd lab/lesson3
  python bin2csv.py "vibration/2026-02-26 14-27-34.bin" -t VIBE --single

That writes  vibration/2026-02-26 14-27-34_VIBE.csv  -- one row per VIBE
record, with a t_s column (seconds since the log started).

  -t NAME1,NAME2    only export those record types (recommended)
  --single          write one flat .csv instead of a folder of them

With no -t it exports everything, which is a lot (the IMU record alone
is hundreds of thousands of rows).

Install what you need first:

  pip install -r lab/lesson3/requirements.txt

In Track A, Claude writes the analysis code -- you run it and check what
it produced against the raw CSV yourself. In Track B, the prompt does
the work in Claude and there is no code for you to keep.
