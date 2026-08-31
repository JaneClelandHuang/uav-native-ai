# Lesson 2 — Designing an Air Traffic Control System

## Lesson Objectives

By the end of this lesson, you will have had initial experience in:

- Analyzing an underspecified software problem — the questions it raises, the alternative behaviors, and the tradeoffs between them.
- Making design decisions and explain *why*: what you were trying to achieve and what you gave up.
- Designing a solution that integrates with an existing multi-component UAV system, and sketch its architecture.
- Implementing your design without bypassing the existing architecture.
- Validating against flight scenarios you did not write, using quantitative evidence for both **correctness** and **performance**.

Whereas for the previous 'assignment', the infrastructure and interfaces were largely provided for you. This week, you are given the following **problem** to solve:  **Multiple UAVs need to operate concurrently without violating safe separation.**  However, there is no single prescribed design. Your job is to analyze the problem, make and justify design decisions, design and implement a solution, and demonstrate that it works.

**Budget around 6 hours** of homework time. However, we will start the analysis and design in class, as this is the first design exercise we will conduct inthis course. You will build the ATC from scratch; however, as this is a Native AI course, you can lean on Claude for the mechanical parts (MQTT wiring, flying a UAV through waypoints, arrival checks) and spend your own time on the design and the coordination logic. Importantly, there are many ways to solve this problem, all of which exhibit trade-offs in terms of effectiveness vs runtime processing vs development effort (and expertise). 

---

## Using AI

You are **encouraged to use Claude (Pro) throughout this assignment** — analysis, design, implementation, and testing. This is a Native AI software engineering course; using AI well is part of the work, not a way around it.  However, *you remain fully responsible for understanding, evaluating, and being able to explain and defend everything you submit*.

As part of your submission, include a short account in `hw02/AI_USE.md` explaining:

- **Where and how** you used Claude.
- **Where it helped** — concrete examples.
- **Where it didn't** — where it was wrong or misleading, or where you had to override it, and how you noticed.
- **Insights** — anything you learned about using AI as an engineering partner on a problem like this.

Length is up to you, but anywhere from 1/2 page to 3 pages is OK.  The real purpose for this is for you to think about what you did, what worked, where you felt the need to 'pilot' Claude and/or provide corrective guidance.

---
## The Engineering Problem


When multiple UAVs operate in shared airspace, their individual missions may bring them close enough to threaten safe separation, even though each mission is perfectly reasonable when considered independently. Our existing infrastructure does not prevent two UAVs from being commanded into the same airspace at the same time.  In real-world deployments, mid-air collisions can be both costly and dangerous. Your challenge is to design and implement a **collision-avoidance system** that monitors multiple UAVs and intervenes when necessary to maintain safe separation.

Your solution **must not rely on pre-planning conflict-free routes**. Instead, it must detect and respond to conflicts that arise during flight. At the same time, interventions should disrupt the UAVs' planned missions as little as reasonably possible: after resolving a conflict, UAVs should be able to continue toward their intended destinations whenever it is safe to do so.  You may choose the architecture of your solution—for example, a centralized **Air Traffic Control (ATC)** service, distributed **onboard collision avoidance**, or a hybrid approach.


## The Engineering Process

Work through the problem in this order — don't jump straight to code: **Analyze → Design → Implement → Validate**

## Working with Claude 

At each step of the process, there are various ways in which you can interact with Claude.  Here are a few of the main approaches (especially for the Design and Implementation phases). Notably in all of these cases it helps to start by providing context about the problem and what you seek to achieve. Design a clear prompt explaining this.  Make sure that Claude understands the existing infrastructure first.

- *You know what you want already:* Describe your own design/implementation plan and direct Claude to implement it.
- *You have an idea but want to explore it with Claude:* Suggest a design and ask Claude to critique it. Iterate through the critiques. Ask for explanations where needed.
- *You don't know where to start:* Ask Claude to list key performance tradeoffs associated with the problem. Then ask Claude to propose 2-3 different solutions and to evaluation them against these tradeoffs. Then select one, and ask Claude to generate a design and later to implement it.  Run the tests yourself.  

Use the *tutor me - quiz me* pattern to make sure you thoroughly understand your solution. 

### 1. Analyze

Understand the problem before you solve it. You may build on a design discussed in class or create your own design.  Think through:

- What questions have to be answered before you can design? (Who decides when there's a conflict (e.g., is this a centralized or distributed design)? Does the system react to conflicts or predict them? When two UAVs are in conflict, which one yields, and why?)
- What are the alternative ways the system could behave?
- What are the important tradeoffs — for example latency, complexity, freedom from deadlock, and how well the design scales as UAVs are added?
- What one or two assumptions are you making that really matter?

There is not a single right answer. Most designs are better with respect to some quality goals and worse for others; your job is to consider the design trade-offs, choose deliberately and be able to explain your choice.  In week 3 we will discuss and compare performance across these solutions.

### 2. Design

Decide on your approach and write it up. This is the main written deliverable and should be about 2-3 pages (including sketch) in `hw02/DESIGN.md`. 

1. **What you wanted to achieve** and the **tradeoffs** you weighed (this replaces a formal requirements document — explain it in your own words).
2. **Why you chose this design** over the alternatives you considered.
3. **An architecture sketch** — a diagram of the major components and how they communicate. Any tool is fine, including a clear photo of a handsketched diagram (writing must be legible).
4. A brief description of the **responsibility of each component** you add or change, and any new MQTT topics/messages.

Do not assume the simple scripts from Lesson 1 are adequate here — `test_flight.py` flies one predetermined mission. Your ATC introduces concurrency and coordination, so consider how the existing architecture has to evolve.

Your design does **not** need to look like anyone else's. However, as will will start this work in class, adopting a similar overall approach to classmates is fine, as long as the rest of the work is your own.

### 3. Implement

Build what you designed.  **ALL of your code — including `start_tests.py` — goes in your `hw02/` folder.**

- Leverage the existing infrastructure to startup drones.  Note you'll need to copy over the multi-UAV program infrastructure and rebuild your fleet one time. 
- Your code should be recognizable as a realization of your `DESIGN.md`. If implementation forces a real design change, update `DESIGN.md`.
- Don't optimize for these workloads specifically, your solution will be evaluated against similar, but unseen scenarios. 

You already have everything you need from Lesson 1: the MQTT command and telemetry contract (recapped in `lab/lesson2/README.md`), and `scripts/test_flight.py` as a worked example of driving one UAV over that contract. That script is for a single-UAV, so it is a reference, not a design you can reuse directly. Build a clear mental model of how you want to realize your design before generating code. 

### 4. Validate

Three workloads are in `lab/lesson2/` — `test1.json` (2 UAVs, one conflict), `test2.json` (3 UAVs), and `test3.json` (3 UAVs, longer). Run your system against all three and record, per workload, a short **Results** section in `DESIGN.md`:

```text
test2.json
Flights completed:            6 / 6
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

**You write this script, in `hw02/`:**

```bash
python hw02/start_tests.py <workload.json> <min-separation-m>
```

It takes the workload and the required minimum separation (metres), starts your ATC, and runs the workload to completion. The standard 3-UAV fleet is already running.

Your `start_tests.py` must:

- Accept the two arguments exactly as shown.
- Start your ATC and anything it needs, with no manual steps.
- Run each UAV's missions in order, beginning the next as soon as the previous completes (2 m).
- Exit once every mission is complete (or after a generous timeout).

`lab/lesson2/` contains **`test1.json`–`test3.json`** to develop against and a **`README.md`** recapping the MQTT contract and the fleet layout.

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
├── DESIGN.md         (goals + tradeoffs + why this design + architecture sketch + Results)
├── AI_USE.md         (~half a page)
├── start_tests.py    (you write this — the standard entry point)
└── <your other implementation files>
```

Your solution must run through:

```bash
python hw02/start_tests.py <workload.json> <min-separation-m>
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
