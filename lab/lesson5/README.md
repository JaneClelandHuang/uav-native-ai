LESSON 5 -- BUILDING A TEST-GENERATING SKILL
=============================================

The homework (HW5) is on the lesson page, not in this folder:
https://janeclelandhuang.github.io/uav-native-ai/lessons/lesson5.html

This file is the step-by-step "how do I actually build this" guide.
Nothing here is graded on its own -- it's the tutorial, not the spec.

The end state: a Claude Code Skill, living in your own repo at
`.claude/skills/<your-name>/SKILL.md`, that you can invoke against any
Python file or module and it will WRITE OUT real test files -- both unit
tests (no live fleet needed) and integration tests (drives the live
fleet and checks a real outcome). You build this skill once, validate it
on something small, then point it at your own HW2 ATC.


STEP 1 -- WHAT A SKILL ACTUALLY IS
-----------------------------------

A Skill is a single Markdown file, `SKILL.md`, with two parts:

  1. YAML frontmatter -- just `name` and `description`. The
     `description` is not documentation for humans, it's the text
     Claude matches against to decide WHEN to load this skill. Be
     specific: "generates unit and integration tests for a given Python
     file or module" beats "helps with testing."

  2. The body -- plain instructions, written as if briefing a careful
     colleague who's never seen this codebase. Typically:
       - What inputs it expects (a file path? a module? ask if unclear
         rather than guessing)
       - A numbered procedure -- the actual steps Claude follows, in
         order, every time
       - What it explicitly should NOT do (scope matters as much as
         scope)

  A Skill lives at `.claude/skills/<name>/SKILL.md` inside a project.
  Once it's there, Claude Code lists it as available and loads it when
  the task matches the description -- or you invoke it directly by name.


STEP 2 -- SCAFFOLD ONE
------------------------

You don't write a SKILL.md from a blank file. Claude Code ships with its
own skill for building skills. Ask Claude to use it:

  "Use skill-creator to help me build a new skill that generates unit
  and integration tests for a Python file."

It will ask you clarifying questions -- what the skill's name should be,
what it needs as input, what "done" looks like. Answer from what you
already know about YOUR system (see Step 3) rather than answering
generically -- the more specific your answers, the less generic the
resulting skill.


STEP 3 -- DESIGN THE PROCEDURE: CLASSIFY, THEN GENERATE
----------------------------------------------------------

This is the part that makes the skill actually useful instead of
generic. Its procedure needs to do two things, in order, every time it's
invoked on a target file:

  A. CLASSIFY. For each function or class in the target file, decide:
     can this be exercised with made-up inputs and no running system
     (unit-testable), or does it need the live MQTT broker + SITL fleet
     to mean anything (integration-testable)? Tell the skill how to make
     this call for THIS codebase specifically -- e.g.:

       "A function is unit-testable if it takes plain data (positions,
       coordinates, numbers) and returns a decision or a value, with no
       MQTT publish/subscribe calls and no reference to a live
       connection. If it touches `mqtt_io`/`command`/`telemetry`
       directly, or calls something that starts a live run, it needs
       the fleet -- classify it as integration."

  B. GENERATE, don't describe. A skill that outputs "you should test
     that conflict detection returns True for close positions" has not
     done its job. It needs to write an actual test file: for a unit
     test, a small pytest function that calls the real function with
     fabricated coordinates and asserts on the real return value; for
     an integration test, a script that starts (or connects to) the
     live fleet, drives a scenario, and asserts on something observed
     from real telemetry -- the same shape as this course's own
     `scripts/test_flight.py` or your own `start_tests.py`.

  Tell the skill exactly where to write these files (e.g.
  `generated-tests/unit/` and `generated-tests/integration/`) and to
  overwrite safely -- warn before clobbering a file that already has
  content someone might have hand-edited.


STEP 4 -- PROVE IT ON SOMETHING SMALL FIRST
----------------------------------------------

Do not point a freshly-built skill at your own several-hundred-line ATC
and hope. Run it first against something small with well-understood
behavior, so you can tell by inspection whether what it generated is
actually right:

  - `lab/scripts/test_flight.py` -- has a couple of small pure
    functions (`offset_to_lla`, `horizontal_distance_m`) that are
    obvious unit-test candidates, and the whole script is itself a
    working example of an integration-style flight -- good for checking
    whether your skill can generate a sensible integration test that
    actually drives a real flight and checks a real outcome.

  - `lab/lesson4/battery/battery_detector.py` -- a windowed detector
    with a documented threshold; you already know its expected verdict
    on the worked battery log from Lesson 4, so you can check whether a
    generated unit test around its windowing logic makes sense, and
    whether it correctly refuses to be tested as pure logic if it
    actually needs live telemetry to run for real.

  Read what your skill generates for one of these BEFORE trusting it on
  your own code. If the generated unit test doesn't call the real
  function with sensible values, or the generated integration test
  doesn't actually check anything meaningful, fix the skill's procedure
  now -- this is the cheap place to catch that, not after it's produced
  a false sense of coverage on your own ATC.

  Write up what you found in `hw05/WORKED-EXAMPLE.md` -- this is a
  required deliverable, not optional practice.


STEP 5 -- POINT IT AT YOUR OWN HW02 ATC
-------------------------------------------

Once you trust the skill on the small target, run it against your own
`hw02/` code. It should produce a real suite in `generated-tests/unit/`
and `generated-tests/integration/`. Run that suite. Read the output
carefully -- this is where you'll likely learn something about your own
system you didn't already know.

Start `hw05/report.md` with what it found -- this is the evidence your
scope declaration in Step 6 is based on.


STEP 6 -- DECLARE YOUR SCOPE, THEN FIX AND/OR EXTEND -- RE-RUN AS A
REGRESSION CHECK
------------------------------------------------------------------------

Before changing any code, write a specific scope statement at the top of
`hw05/report.md`: what you're fixing (real bugs the suite or your own
review surfaced) and/or extending (a real feature, real technical debt
-- not a cosmetic change). "Clean things up" isn't a scope; name the
actual bug or feature. This is graded on its own, separately from the
work itself.

Then act on it: fix what you scoped, build what you scoped, or both.
Either way, re-run the generated suite afterward and confirm: the thing
you fixed/added now passes, AND nothing that passed before now fails.
That second check -- did I break something that used to work -- is the
entire point of having a suite you can re-run instead of a one-off
script you ran once and threw away. Record the before/after evidence in
`hw05/report.md`.


A NOTE ON WHAT THIS ISN'T
----------------------------

This skill's job is to generate tests, not to fix your code for you, and
not to grade you. If it flags something, that's a finding for you to
investigate and act on -- the same way this course's graders treat their
own tools' findings as evidence to reason about, not automatic verdicts.
