# Lesson 5 — Testing Your ATC

> **DRAFT ONLY — not yet reviewed. Details, categories, and grading below
> are subject to change before this is final.**

## Lesson Objectives

**GUI programming is deferred to Thursday.** Tuesday we go back to the
multi-UAV ATC you built for HW2, this time through the lens of testing.

By the end of this lesson, you will have:

- Reviewed how to read and draw an architecture diagram with an eye
  toward *where the seams are* — which parts of your system can be
  tested in isolation, and which need a live fleet.
- Learned the difference between **unit** and **integration** tests, and
  where each applies in a system built on SITL + MQTT.
- Built your own **Claude Code Skill** — not one that just runs a fixed
  set of tests, but one whose job is to **generate** a test suite (both
  unit and integration) for a piece of code you hand it.
- Used that skill on your own HW2 ATC to find something real that's
  broken, or to validate something you add — and fixed or built it,
  proven by the tests your own skill generated.

**Native AI focus — building a reusable tool, not a one-off prompt.**
Asking Claude "write me some tests" gets you a different, inconsistent
answer every time depending on how you phrase it and what it happened to
notice. A Skill is Claude given a fixed, repeatable procedure — you are
the one who designs that procedure, and Claude executes it consistently
whenever you invoke it. This week you build the procedure once, then use
it as many times as you want.

**Budget around 6–8 hours**, consistent with every other assignment this
term.

---

## Why this week, why now

Grading HW2 surfaced something worth saying plainly: even strong
submissions tested in a fairly ad-hoc way — a script you ran a few
times, read the output, and moved on. A few concrete things that
happened across the class when the required minimum separation changed
from 30m to 15m (the same kind of change graders make between what you
develop against and what you're actually evaluated on):

- More than one submission's **own safety margin got worse, not
  better**, at the tighter threshold — and nothing caught this
  automatically. It took a human re-running the same three scenarios by
  hand to notice.
- At least one submission's own results output printed a minimum
  separation number **right next to the required number, with no
  pass/fail flag of any kind**, and exited with status 0 regardless.
  Anyone skimming the output — or any automated check keying off exit
  code — would read that as a pass.
- A near-collision (well under half the required separation) showed up
  reliably on the 3-UAV workload but never on the simpler 2-UAV one.
  Nothing in that submission's own testing ever exercised the 3-UAV
  case enough times, with enough variation, to catch it before
  submission.

None of this means the engineering was bad — building a working ATC at
all, under a hard, underspecified problem, in a week, is real work. It
means the *testing* was the part left informal. That's what this lesson
fixes, and you're fixing it on a system you already understand deeply,
not a toy example.

---

## Recap: reading your own architecture for test boundaries

You already wrote an `ARCHITECTURE.md` for your HW4 monitor, and a
`DESIGN.md` architecture sketch for your HW2 ATC. Tuesday, we look at
diagrams like those again, but asking a specific question: **for each
box and arrow, could I test this without a live drone fleet running, or
not?**

The course's own backend gives you a clean example already sitting in
`lab/ARCHITECTURE.md`: `mavlink_lib.py`'s parsing functions are
documented as "pure functions — message in, dict out, no side effects,
no state," and `monitor_signals.py` is "a lookup table." Both can be
tested by calling them directly with fake inputs and checking what comes
back — no SITL, no MQTT broker, no Docker. Anything that touches
`drone_backend.py`'s command handling, or any live MQTT traffic, needs
the real (or realistically faked) system running underneath it.

Your own ATC has the same kind of seam somewhere. Conflict-detection
math, geometry, priority/yield decisions — anything that takes a
position (or two) and returns a decision — is usually pure logic you can
unit-test with made-up coordinates. Anything that has to actually
publish a command and watch telemetry come back needs the fleet up.
Finding that line in your own code is the first real step of this
assignment, before you write anything.

---

## Unit tests vs. integration tests, for this system specifically

**Unit tests** exercise one function or one small piece of logic,
directly, with inputs you make up — no MQTT broker, no SITL, no Docker.
Fast, and precise about what broke when they fail. In your ATC: does
your conflict-detection function correctly flag two hand-constructed
positions as a conflict? Does your priority rule pick the right UAV to
yield, given a fabricated tie? Does your geometry math get the right
answer for a closest-approach distance you can compute by hand?

**Integration tests** exercise the whole pipeline against the real (or
close enough) system — the fleet actually flying, MQTT actually
carrying commands and telemetry, your ATC actually coordinating. Slower,
and when they fail you have to dig to find out *where*, but they catch
what unit tests structurally cannot: does the system actually hold
separation when three real UAVs converge, not just when your function
says two fabricated points are 3 meters apart.

You've already written informal versions of both. Lesson 4's "run the
fault injector three times at the same severity, verify your detector
catches all three" is a repeatability check — close to a regression
test. "Run against a normal flight, verify no false alarm" is a
negative test case. Formalizing habits you already have is most of this
lesson's job.

---

## Building the skill

Full step-by-step walkthrough: **`lab/lesson5/README.md`**. The short
version:

1. Learn the shape of a Claude Code Skill (a `SKILL.md` file: what
   triggers it, what it's told to do, step by step, and what it's
   explicitly told *not* to do).
2. Scaffold one yourself using Claude's own `skill-creator` skill.
3. Design its procedure so that, given a target file or module, it:
   reads the code, decides which parts are unit-testable and which need
   the live fleet, and **writes out real test files for both** — not a
   description of what tests should exist, actual test code.
4. **Prove it on something small and already well understood before
   trusting it on your own ATC** — `lab/scripts/test_flight.py` or
   `lab/lesson4/battery/battery_detector.py` are good targets. If your
   skill can't generate a sensible unit test for a known pure function
   and a sensible integration test for a known live-fleet script, fix
   the skill before pointing it at anything more complex.
5. Point the validated skill at your own `hw02/` ATC. Generate the
   suite. Run it. Read what it tells you.

You are building the skill. It is not something you're handed — the
whole point is that you now own a reusable tool, not a one-time answer.

---

## The assignment: fix it, or extend it — either way, prove it

Once your skill has generated a real test suite against your own ATC,
you'll know things about your own system you may not have known before.
Pick one:

- **Something's broken.** Fix it. Use the regenerated/re-run suite to
  show the fix actually holds, and that you didn't break anything that
  was previously passing.
- **It mostly works.** Extend it — a real feature, a real piece of
  technical debt addressed, not a cosmetic change. Use the suite to show
  the addition didn't regress existing behavior, and add tests (via your
  skill) that cover the new behavior specifically.

Either path needs real evidence: what the tests found, what you changed,
what the tests show afterward.

---

## How This Is Graded

Out of **100 points**.

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **Skill design & quality** | 25 | The skill genuinely *generates* test code (not just descriptions of tests) for both unit and integration cases, correctly separates the two based on your system's real architecture, and is general enough to run again on a different file — not hard-coded to one target. |
| **Validated on the small worked example first** | 10 | You ran your skill against `test_flight.py` or the battery detector *before* your own ATC, and can show the generated tests for that known target actually made sense. |
| **Applied to your own HW2 ATC** | 30 | A real, generated test suite run against your own ATC; a real problem found-and-fixed *or* a real feature added, either way backed by before/after test evidence. |
| **Retrospective** | 15 | Honest account: what the generated tests caught that your original ad-hoc testing didn't, what your skill still can't test, and what you'd do differently starting the skill over. |
| **Individual understanding** — in class | 20 | See below. |
| **Total** | **100** | |

</div>

### Individual understanding

In Thursday's class (before the GUI lecture) you'll answer questions
about your own skill and what it found — for example: why a given piece
of your ATC ended up unit- vs. integration-tested, what your skill would
generate for a function it's never seen before, what a generated test
*wouldn't* catch. On your own, without AI.

---

## Deliverable

```text
hw05/
├── .claude/skills/<your-skill-name>/SKILL.md   the skill itself
├── generated-tests/                             what the skill produced
│   ├── unit/
│   └── integration/
├── WORKED-EXAMPLE.md      the skill validated against test_flight.py or
│                          the battery detector, before you trusted it
│                          on your own code
├── RESULTS.md             what the generated suite found on your own
│                          ATC, what you fixed/added, before-and-after
└── REPORT.md              the retrospective
```

Commit and push:

```bash
git add .
git commit -m "Complete HW05"
git push
```

---

## Before You Submit

Be ready to explain:

- Why each generated test is a unit test or an integration test, in
  terms of your own architecture, not just by category name.
- What your skill's procedure actually is, step by step — not just what
  it produced.
- What broke or improved, with the actual before/after test evidence.
- Something your skill's generated tests would *not* catch, and why.

> **A test suite you generated once and never re-run isn't testing —
> it's a snapshot. The point is that you can run it again.**
