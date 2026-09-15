# Lesson 4 — Runtime Monitoring & Fault Injection

## Lesson Objectives

This week moves from retrospective flight-log analysis to recognizing
degraded or unsafe behavior while a UAV is actually operating: telemetry
health, runtime evidence, and fault detection using signals like
`STATUSTEXT`, battery and sensor-health status, and mode/armed state.

**Native AI focus — AI-Assisted Diagnosis.** Use AI to help interpret
telemetry and formulate hypotheses while explicitly distinguishing
observation from inference, and evidence from explanation — not treating
an AI-generated diagnosis as ground truth.

**Budget around 8 hours.** We will build a battery-failsafe detector
together in class first — the same role the battery worked example played
in Lesson 3, a model for the depth your own work should reach, not one of
your two graded categories.

---

## Readings

Read ArduPilot's own arming-check and failsafe documentation before
Thursday's class — the same categories your detector will watch (GPS,
vibration, compass, battery) are exactly the ones ArduPilot's own onboard
safety logic already watches, and it's worth seeing how a real autopilot
draws the line between "problem" and "no problem" before you draw your own.

- Arming checks: https://ardupilot.org/copter/docs/prearm_safety_check.html
- Failsafe actions (start with Battery Failsafe, then browse GPS/EKF): https://ardupilot.org/copter/docs/failsafe-battery.html

We will discuss in class on Thursday too.

---

## Using AI

Same principle as HW03: you remain fully responsible for understanding,
evaluating, and being able to explain and defend everything you submit.
This assignment is one coded artifact, not a code-vs-prompt comparison —
use Claude throughout to help design your subscriber/plotter, reason about
what you're seeing in a plot, and write your detector. The retrospective
and architecture sketch below must be your own thinking, done without AI,
the same way HW03's retrospective was.

---

## What You're Building

A **runtime monitor** — a program that watches a running vehicle's live
telemetry and reports, continuously, whether it's seeing a problem. That's
the real shift from HW03: there, the whole flight was already in front of
you before you started. Here, you don't know when — or whether — a fault
will occur, and your monitor has to make that call as data arrives, using
only what it's seen so far.

The infrastructure is already built for you:

- `lab/backend/monitor_signals.py` extracts five categories (`vibration`,
  `gps`, `ekf`, `compass`, `battery`) from live MAVLink traffic and
  publishes whichever ones you ask for on `uav/<id>/monitored_data`, at the
  normal telemetry rate.
- `uav/<id>/monitor_config` (retained) is how you ask — publish
  `{"categories": [...]}` and the backend starts including exactly those
  categories, nothing else, until you ask for something different.
- `lab/client2/monitor_view.py` does exactly that for `vibration` and
  prints what arrives — it is **not** a detector, just Step 1 already done
  once for you to read. Copy what you need into your own `lab/client/` (or
  a new file there); `client2/` is instructor-synced infrastructure, not
  somewhere your own edits belong.
- `lab/scripts/mischief_maker.py` injects one of four faults — `GPS`,
  `VIBRATION`, `MAG-COMPASS`, `POWER-BATTERY` — at a randomized moment
  after a real takeoff, at a randomized magnitude within whichever severity
  you ask for (or a random severity, if you don't ask). See its own
  docstring for full usage and examples.

---

## Your Two Categories

- **GPS** — required.
- **VIBRATION** or **MAG-COMPASS** — your choice.

`POWER-BATTERY` is not one of your two. `lab/lesson4/battery/` has a
worked example for it — a plotter and a detector, built the same way
you're building your own two. Read it first, the same way `lesson3/
battery/` was the model for HW03: it's there to show the depth your own
work should reach, and to give you something to check your own solutions
against (they should never misreport a battery problem as GPS/vibration/
compass). It does **not** include a combined plot+detector — building
that connection yourself, for your own categories, is Step 4's job, not
something to copy.

**[`lab/lesson4/BATTERY-MONITOR-GUIDE.md`](../lab/lesson4/BATTERY-MONITOR-GUIDE.md)**
walks through every new file behind this lesson — how to run the battery
demo yourself, a plain-language pass on what each program does and why,
then the real technical detail underneath that. Read the plain-language
pass first regardless of how comfortable you already are with the code —
it's the fastest way to see how the pieces fit together before diving into
any one of them.

---

## Step 1 — Subscribe

Get your own client publishing a `monitor_config` for GPS plus your chosen
second category, and subscribing to `monitored_data`. Confirm you're
actually receiving real values — print them, the way `monitor_view.py`
does — before building anything on top. Not graded on its own, but
everything after it depends on it working.

## Step 2 — Plot a Normal Flight

Build your own matplotlib plotter — start from `monitor_view.py`'s
subscribe/config pattern, but plot instead of printing. Take off, fly
normally (no fault), and watch both your categories' values for the whole
flight. Get a feel for:

- What "normal" actually looks like — not a single number, a *range*, and
  how much it moves on its own.
- How fast it updates, and how noisy one reading is versus a few seconds
  of them.

Not graded directly, but the observations here are the evidence Step 4's
thresholds need to be defensible, and `REPORT.md` asks you to reference
what you saw.

## Step 3 — Observe a Fault

With your plotter still running, start `mischief_maker.py` for one of your
categories and watch what happens: how fast the signal moves once the
fault fires, how far it moves from what you saw in Step 2, and whether
your *other* subscribed category changes too. Do this for both categories,
more than once each — `mischief_maker.py` picks a genuinely different
value every run, even at the same severity, so one run tells you less than
you'd think.

## Step 4 — Build the Detector

For each of your two categories, build a program that:

- Subscribes the way Step 1 does.
- Maintains a **window** of recent values, not just the latest one — a
  single reading can't tell a real fault from one noisy sample, and Step
  2's own observations should tell you roughly how much normal wobble your
  window needs to tolerate.
- Reports one of three verdicts, continuously, as data arrives: **problem
  present**, **no problem**, or **not enough data yet** (same vocabulary as
  HW03) — with evidence: which values, over what window, crossed what
  threshold.

**Two checks your detector must pass, for each category:**

- **No false alarm.** Run it against a normal flight (Step 2's scenario or
  a fresh one) for the whole flight. It must never report a problem.
- **Consistency across randomized magnitude.** Run `mischief_maker.py` at
  the same severity at least three times. Your detector doesn't need to
  report the exact same numbers each time — `mischief_maker.py` doesn't
  inject the exact same numbers either — but it needs to catch all three.

---

## Sketch Your Architecture

Before or alongside building Step 4, sketch — a diagram, or a
clearly-organized written description, whichever you communicate better
with — how your monitor is actually put together: where the window lives,
who owns clearing or updating it, what happens the moment a fault resolves
(does your verdict change back?), and how a third category would slot into
what you've built. This goes in `ARCHITECTURE.md` in your `hw04/` folder —
a few paragraphs and/or a diagram, not an essay.

---

## What Goes in `REPORT.md`

- **Baseline observations** (one short paragraph per category): what
  "normal" looked like in Step 2 — typical value, how much it moved on its
  own, anything surprising.
- **Detector write-up** (one short paragraph per category): your window
  size and why, the verdict on a normal flight and on an injected fault,
  and one case where you had to adjust your threshold after seeing it fail.
- **Retrospective** (half a page, done yourself, without AI): now that
  you've built this against a live system instead of a static log, what's
  actually different about detecting a fault as it happens versus finding
  one in a log you already have? Where did HW03's habits (evidence over
  assertion, "I can't tell from this") carry over directly, and where did
  they need to change?

---

## How This Is Graded

Out of 100 points.

| Component | Points | What earns the points |
|---|---:|---|
| `README.txt` — how to run everything | 5 | Exact commands for your plotter and both detectors. If anything needs installing beyond `lab/client2/requirements.txt`, say so and include a `requirements.txt`. |
| Baseline + fault observation | 15 | Evidence (plots or plot descriptions) from Steps 2-3 for both categories, referenced in `REPORT.md`. |
| GPS detector | 20 | Windowed, correct verdict on normal and faulted flight, passes both checks, evidence-based. |
| Your second detector | 20 | Same standard as GPS. |
| Architecture sketch | 10 | Clear enough that someone else could extend it to a third category without guessing at your design. |
| Retrospective | 10 | Honest, specific comparison to HW03's static-log experience — not a restatement of the lesson objectives. |
| Individual understanding — in class | 20 | See below. |

### Individual Understanding

Same reasoning as HW03: AI helped build this, so being able to explain it
is graded directly. In Thursday's class, be ready to answer questions
like: why your window is the size it is; what your detector reports if
two of your categories go wrong at once; what you'd change if
`mischief_maker.py`'s severity levels were reversed without telling you;
and why a runtime monitor has to make calls a retrospective log analysis
never has to — on your own, without AI.

---

## Deliverable

```text
hw04/
├── plotting/
│   └── monitor_plot.py        Step 2's plotter (and Step 1's subscriber, or a shared module)
├── gps/
│   └── detector.py            Step 4's GPS detector
├── <vibration | compass-mag>/
│   └── detector.py            Step 4's second detector
├── README.txt
├── requirements.txt            only if you need anything beyond lab/client2's
├── ARCHITECTURE.md             your architecture sketch
└── REPORT.md                   baseline + detector write-ups + retrospective
```

Commit and push:

    git add .
    git commit -m "Complete HW04"
    git push

---

## Before You Submit

Be ready to explain:

- What "normal" looks like for each of your two categories, and how you
  decided your thresholds from that.
- Why a single data point isn't enough, in your own words, with a
  concrete example from what you saw in Step 3.
- What your detector does the moment a fault resolves.
- For a category you didn't build (one of the other two, or the battery
  case from class): what you'd change about your approach, and why.

> **Be able to explain why your detector reaches the verdict it does — and
> where it shouldn't be trusted.**
