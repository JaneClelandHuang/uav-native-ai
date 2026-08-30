# Lesson 2 — Designing an Air Traffic Control System

## Lesson Objectives

By the end of this lesson, you should be able to:

- Analyze an underspecified software problem — the questions it raises, the alternative behaviors, and the tradeoffs between them.
- Make design decisions and explain *why*: what you were trying to achieve and what you gave up.
- Design a solution that integrates with an existing multi-component UAV system, and sketch its architecture.
- Implement your design without bypassing the existing architecture.
- Validate against flight scenarios you did not write, using quantitative evidence for both **correctness** and **performance**.

This week is deliberately different from Lesson 1.

In Lesson 1, the infrastructure and interfaces were largely provided for you. This week, you are given a **problem**:

> **Multiple UAVs need to operate concurrently without violating safe separation.**

There is no single prescribed design. Your job is to analyze the problem, make and justify design decisions, design and implement a solution, and demonstrate that it works.

**Budget about 6 hours.** We start the analysis and design in class. You build the ATC from scratch — but this is a Native AI course, so lean on Claude for the mechanical parts (MQTT wiring, flying a UAV through waypoints, arrival checks) and spend your own time on the design and the coordination logic. If you pass ~8 hours, stop and come to office hours.

---

## Using AI

You are **encouraged to use Claude (Pro) throughout this assignment** — analysis, design, implementation, and testing. This is a Native AI software engineering course; using AI well is part of the work, not a way around it.

You remain fully responsible for understanding, evaluating, and being able to defend everything you submit.

As part of your submission, include a short account (about half a page) in `hw02/AI_USE.md`:

- **Where and how** you used Claude.
- **Where it helped** — concrete examples.
- **Where it didn't** — where it was wrong or misleading, or where you had to override it, and how you noticed.
- **Insights** — anything you learned about using AI as an engineering partner on a problem like this.

Honesty and specificity matter more than length.

---

## The Engineering Process

Work through the problem in this order — don't jump straight to code:

**Analyze → Design → Implement → Validate**

### 1. Analyze

Understand the problem before you solve it. You may build on a design discussed in class or start from one you prefer.

Think through:

- What questions have to be answered before you can design? (Who decides when there's a conflict? Does the system react to conflicts or predict them? When two UAVs are in conflict, which one yields, and why?)
- What are the alternative ways the system could behave?
- What are the important tradeoffs — for example latency, complexity, freedom from deadlock, and how well the design scales as UAVs are added?
- What one or two assumptions are you making that really matter?

There is not a single right answer. Most designs are better on some quality goals and worse on others; your job is to choose deliberately and be able to explain the choice.

### 2. Design

Decide your approach and write it up. This is the main written deliverable — **about one page** — in `hw02/DESIGN.md`:

1. **What you wanted to achieve** and the **tradeoffs** you weighed (this replaces a formal requirements document — explain it in your own words).
2. **Why you chose this design** over the alternatives you considered.
3. **An architecture sketch** — a diagram of the major components and how they communicate. Any tool is fine, including a clear photo of a handwritten diagram.
4. The **responsibility of each component** you add or change, and any new MQTT topics/messages.

Do not assume the simple scripts from Lesson 1 are adequate here — `test_flight.py` flies one predetermined mission. Your ATC introduces concurrency and coordination, so consider how the existing architecture has to evolve.

Your design does **not** need to look like anyone else's. Since we start in class, adopting a similar overall approach to classmates is fine, as long as the rest of the work is your own.

### 3. Implement

Build what you designed.

- Keep UAV commands and telemetry flowing through the Lesson 1 infrastructure — don't bypass it.
- Your code should be recognizable as a realization of your `DESIGN.md`. If implementation forces a real design change, update `DESIGN.md`.
- Don't optimize for the example workload specifically — you'll be graded on scenarios you haven't seen.

You already have everything you need from Lesson 1: the MQTT command and telemetry contract (recapped in `lab/lesson2/README.md`), and `scripts/test_flight.py` as a worked example of driving one UAV over that contract. That script is single-UAV and blocking, so it is a reference, not a design you can reuse directly.

### 4. Validate

An example workload is in `lab/lesson2/`. Run your system against it and record, in a short **Results** section of `DESIGN.md`:

```text
Flights completed:            2 / 2
Minimum required separation:  8.0 m
Minimum observed separation:  13.4 m
Total workload time:          94.2 s
```

Don't just say "it passed." If something behaved unexpectedly, say what happened and what you did about it.

---

## Flight Workloads

Your ATC system is given a JSON file describing flights that must be completed.

```text
UAV 1:  Mission 1A → Mission 1B → Mission 1C
UAV 2:  Mission 2A → Mission 2B
UAV 3:  Mission 3A → Mission 3B → Mission 3C
```

Missions for the **same UAV are sequential** — the next begins as soon as the previous one completes. Different UAVs may have missions active at the same time. The workload says **what** must be accomplished, not how.

### Format

```json
{
  "scenario": "example",
  "description": "...",
  "missions": {
    "1": [
      { "mission_id": "1A",
        "waypoints": [
          { "lat": 41.6983055, "lon": -86.2370550, "alt": 15 }
        ] }
    ],
    "2": [ ... ],
    "3": [ ... ]
  }
}
```

- Keys of `missions` are UAV ids (`"1"`, `"2"`, `"3"`) — the same ids as the Lesson 1 telemetry topics.
- Each mission has a `mission_id` and 1–3 `waypoints`, visited in order.
- `lat` / `lon` are absolute; `alt` is **metres above home** (relative altitude — the value `{"type": "goto", "alt": N}` takes).
- A mission is complete when the UAV comes **within 2 m** (3D) of its final waypoint. This tolerance is fixed — the grading monitor uses it, so a looser one would not help and counts as not meeting the spec.
- All UAVs launch from the standard 3-UAV fleet positions around the home coordinate (see `lab/lesson2/README.md`).

---

## Standard Execution Interface

Every submission must start the same way, so any solution can be run without knowing its internals.

**You write this script:**

```bash
python lab/lesson2/start_tests.py <workload.json> <min-separation-m>
```

It takes the workload and the required minimum separation (metres), starts your ATC, and runs the workload to completion. The standard 3-UAV fleet is already running.

Your `start_tests.py` must:

- Accept the two arguments exactly as shown.
- Start your ATC and anything it needs, with no manual steps.
- Run each UAV's missions in order, beginning the next as soon as the previous completes (2 m).
- Exit once every mission is complete (or after a generous timeout).

`lab/lesson2/` contains **`example_workload.json`** to develop against and a **`README.md`** recapping the MQTT contract and the fleet layout.

### How grading observes your system

The instructor runs a separate **monitor** — you will not see it — that subscribes only to UAV telemetry on the existing infrastructure and measures separation, completion, and timing from telemetry alone.

So your system is graded on **what is observable in the telemetry stream**. Keep commands and telemetry on the Lesson 1 infrastructure — a system that coordinates "off the books" cannot be evaluated. Build your own way to measure separation and completion for your Results section.

Your submitted system is also run against **workloads you have not seen**, which may use different concurrency patterns and a different minimum separation. All submissions run in the same environment so timing is comparable.

---

## What Are We Evaluating?

### Correctness

Does your system do the job?

- Do all required flights complete?
- Is safe separation maintained?
- Does the system keep making progress (no deadlock)?

A system that is fast but unsafe is not a successful solution.

### Performance

Among correct solutions, how well does it use the airspace?

- How long does the whole workload take?
- How much time do UAVs spend unnecessarily waiting?
- How responsive is it when coordination is required?

A solution that flies only one UAV at a time is easy to keep safe but makes poor use of the airspace.

**Safety comes first, but safety alone does not make a good ATC design.**

---

## How This Is Graded

The assignment is graded out of **100 points**. Most components are evaluated with engineering judgment against the criteria below; correctness and performance are measured by the monitor.

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **Design** — `DESIGN.md` | 35 | A clear ~1-page account of what you wanted to achieve, the tradeoffs, and why you chose this design over the alternatives; a readable architecture sketch; component responsibilities and any new topics documented; a design that evolves the existing architecture rather than bypassing it. |
| **Implementation** | 25 | Working, readable code that realizes your design, uses the existing infrastructure, and runs through `start_tests.py` from a clean clone with no manual steps. |
| **Correctness on unseen workloads** | 20 | All flights complete, separation maintained, no deadlock — on scenarios you did not develop against. |
| **Performance on unseen workloads** | 5 | Among correct solutions: workload time, unnecessary waiting, coordination responsiveness. |
| **Validation** — Results in `DESIGN.md` | 5 | Quantitative evidence from your own test run, with brief interpretation and investigation of anything unexpected. |
| **AI Use** — `AI_USE.md` | 5 | Specific reflection on where AI helped, where you challenged or rejected it, how you verified its work, and what you learned. |
| **Individual code understanding** — in class | 5 | See below. |
| **Total** | **100** | |

</div>

### Individual code understanding

Because AI assistance is expected, being able to explain your own work is a skill this course grades directly.

This is the first assignment using this, so it's only **5 points** here — expect it to carry more weight later. In **Thursday's class** you'll get a few questions about the code and design in your repository (for example: why a component holds the state it does, what your system does if a UAV stops responding, how your conflict logic handles a case your validation didn't cover) and answer them **on your own, in class, without AI**.

The goal is to start building the habit of being able to reason about and defend what you submit.

---

## Deliverable

```text
hw02/
├── DESIGN.md        (~1 page: goals + tradeoffs + why this design + architecture sketch + Results)
├── AI_USE.md        (~half a page)
└── <your implementation files>

lab/lesson2/
└── start_tests.py   (you write this)
```

Your solution must run through:

```bash
python lab/lesson2/start_tests.py <workload.json> <min-separation-m>
```

Commit and push:

```bash
git add .
git commit -m "Complete HW02"
git push
```

---

## Before You Submit

Be ready to explain:

- The most important decisions you made, and the tradeoffs behind them.
- How your architecture carries out those decisions.
- What evidence shows your system works.
- The strengths and weaknesses of your design.
- What would happen to it if the number of UAVs grew substantially.

> **Be able to explain why your system is designed the way it is.**
