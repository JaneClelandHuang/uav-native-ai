LESSON 3 -- FLIGHT-LOG ANALYSIS
==============================

Two things this week.

THE HOMEWORK (HW3) -- on the lesson page, not in this folder
    Write three reusable prompts, one each for vibration, GPS / position,
    and compass / magnetic interference. Given the extracted data from
    any flight log, a prompt returns a verdict, a graph, and an
    evidence-based explanation -- in one shot, run from Claude. The
    graded skill is the prompt engineering. No code to run beyond
    bin2csv.py, no API key.
    Full spec: https://janeclelandhuang.github.io/uav-native-ai/lessons/lesson3.html

THE LAB EXAMPLES (this folder) -- not graded
    Real flight logs, one folder per kind of problem. They are here so
    you can SEE what each problem looks like in the data before you try
    to write a prompt that detects it. Extract the records, plot them,
    get a feel for the signal and for where it gets ambiguous.

Work through the lab examples first. Then write the prompts.


THE LAB EXAMPLE FOLDERS
----------------------

  vibration/       mechanical vibration -- a healthy flight, then a
                   session where it climbs                  (a prompt target)

  gps-position/    a flight told to climb straight up that drifted
                   sideways instead                         (a prompt target)

  compass-mag/     magnetic interference -- one compass reads the motors
                   instead of the Earth                     (a prompt target)

  battery/         a battery that sags under load and trips a failsafe.
                   NOT one of the three you write a prompt for -- it is
                   here as a different kind of problem to compare
                   against, and as a check on whether your prompts
                   false-alarm on something outside their scope.

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

You are encouraged to use Claude to write the plotting code -- then
check what it produced against the raw CSV yourself.
