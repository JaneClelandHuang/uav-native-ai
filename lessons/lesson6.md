# Lesson 6 — Computer Vision & Perception

## Lesson Objectives

When a UAV's camera finds a person, what happens next? This week connects
the course's computer-vision pipeline (live YOLO person detection on the
simulated camera feed) to a **mission response planner** that decides what
the UAV does about it, with a human operator approving each response.

By the end of this lesson, you will have:

- Designed a human-on-the-loop planner in class with CRC cards, and
  tested that design by role-playing a real scenario through it.
- Seen how a detector turns camera frames into geolocated, confirmed
  person events, and where it goes wrong (weak hits, false positives,
  misses).
- Built your own planner: a world model, a fixed menu of candidate
  responses, a validator every decision passes through, and an executor
  that flies the response and resumes the search route.

**Native AI focus — Engineering an AI Component.** This week shifts from
*using* AI to engineer software to *engineering* software that contains an
AI-enabled component: treating model output as uncertain evidence, not
unquestioned truth. A detection at 0.31 confidence might be a person, or a
shadow. Your planner decides what that uncertainty is allowed to cost.

---

## Readings

Read before Tuesday's class:

- Beck & Cunningham, *A Laboratory for Teaching Object-Oriented Thinking*
  (OOPSLA 1989). The original CRC-card paper. It's short, and it's the
  technique we use in class: http://c2.com/doc/oopsla89/paper.html
- Parasuraman, Sheridan & Wickens, *A Model for Types and Levels of Human
  Interaction with Automation* (IEEE Trans. SMC-A, 2000). Where "human on
  the loop" sits between full manual control and full autonomy:
  https://doi.org/10.1109/3468.844354

Skim before starting the homework:

- Ultralytics YOLO, object detection and prediction settings (especially
  the confidence threshold): https://docs.ultralytics.com/tasks/detect/
  and https://docs.ultralytics.com/modes/predict/

---

## In Class

**Tuesday:** Mission planning. We design the planner together with CRC
cards, then walk a scenario through the design: a person is spotted, the
operator chooses a response, the UAV flies it, and a second detection
arrives mid-response. Then we compare your designs with a reference
architecture.

**Thursday:** Perception. We look at how the live detector works (YOLO,
confirming a person across frames, pixel-to-lat/lon geolocation) and at
real frames from our own simulated flights: a correct hit at 0.26, a false
positive at 0.31, and a person the detector missed.

---

## Homework

**HW6 — Build a Human-on-the-Loop Mission Response Planner.** You build
the planner you designed in class, between the person detector and an
operator popup we provide. The operator chooses *what* should happen. Your
software checks whether it *can*, then makes it happen.

The full specification is in **`lab/lesson6/README.md`** in your homework
repo: requirements, the popup's MQTT contract, how to run everything, the
tests we expect, grading, and the deliverable. Pull first (`git pull`) to
get `lab/lesson6/` and the detector in `lab/cv/`.

**Budget around 6–8 hours**, consistent with every other assignment this
term. Start from your CRC cards, not from a blank prompt. `design.md`
comes before code.

Next week (Lesson 7) an AI decision-maker replaces the human operator. If
your design has a clean seam between "who decides" and "what happens next,"
that will be a small change.
