# Lesson 2 — Designing an Air Traffic Control System

## Lesson Objectives

By the end of this lesson, you should be able to:

- Analyze an underspecified software problem by identifying questions, alternatives, assumptions, and design decisions.
- Translate design decisions into precise, testable requirements using **EARS**.
- Design a software solution that integrates with an existing multi-component UAV system.
- Implement your design without unnecessarily coupling components or bypassing the existing architecture.
- Validate your implementation against externally supplied flight scenarios.
- Use quantitative evidence to evaluate both the **correctness** and **performance** of your solution.

This week is deliberately different from Lesson 1.

In Lesson 1, the infrastructure and interfaces were largely provided for you. This week, you are given a **problem**:

> **Multiple UAVs need to operate concurrently without violating safe separation.**

There is no single prescribed design.

Your job is to analyze the problem, make and justify design decisions, specify what your system must do, design and implement a solution, and demonstrate that it works.

---

## Using AI

You are **encouraged to use Claude (Pro) throughout this assignment** — analysis, requirements, design, implementation, and testing. This is a Native AI software engineering course; using AI well is part of the work, not a way around it.

You remain fully responsible for understanding, evaluating, and being able to defend everything you submit. See [How This Is Graded](#how-this-is-graded) — part of your grade is answering individual questions about *your* code, in class, without AI.

As part of your submission, include a short account (about half a page) in:

`hw02/AI_USE.md`

Cover:

- **Where and how** you used Claude across the process.
- **Where it helped** — concrete examples.
- **Where it didn't** — where it was wrong or misleading, or where you had to override it, and how you noticed.
- **Insights** — anything you learned about using AI as an engineering partner on a problem like this.

Honesty and specificity matter more than length. "I used it for everything and it was great" is not a useful account.

---

## The Engineering Process

For this assignment, use the following process:

**Analyze → Specify → Design → Implement → Validate**

Do not jump directly to implementation.

### 1. Analyze

First, make sure you understand the problem you are solving. You may choose to build upon any design discussed in class, or to start from a new design that you prefer.

Identify:

- Questions that need to be answered as part of the design process.
- Alternative ways the system could behave.
- Assumptions you are making. (Note: There are probably hundreds of assumptions. Document 1 or 2 of the key ones)
- Important tradeoffs.
- Decisions you ultimately make.

There are many reasonable ways to design an Air Traffic Control (ATC) system. Your goal is to make thoughtful decisions and be able to explain them. While some solutions might be better than others, in most cases, they are better with respect to certain quality goals and worse with respect to others. In other words there is not necessarily a right or wrong answer; however, you might want to consider qualities such as latency, complexity, and freedom-from-deadlocks.  

Keep a short record of your analysis in:

`hw02/ANALYSIS.md`

Your analysis should show the **questions and alternatives you considered**, not just the final decisions.

---

### 2. Specify

Once you have made the necessary decisions, specify the behavior of your system.

Write your key behavioral requirements using **EARS (Easy Approach to Requirements Syntax)**.

For example, an EARS requirement might take the general form:

> **When** `<trigger occurs>`, **the system shall** `<required response>`.

or:

> **While** `<state holds>`, **the system shall** `<required behavior>`.

Your functional requirements will define what your system must accomplish without unnecessarily prescribing its internal architecture.

Pay particular attention to requirements involving:

- Safe separation.
- UAV movement and progress.
- Conflict detection and response.
- Completion of assigned flights.
- Starting subsequent flights.
- Failure or exceptional conditions that your design handles.

Put your requirements in:

`hw02/REQUIREMENTS.md`

A good functional requirement is sufficiently precise that you can determine from a test whether it is satisfied.

---

### 3. Design

Now determine how your system will satisfy those requirements.

Think about:

- What components are needed?
- What is each component responsible for?
- Where is state maintained?
- How do components communicate?
- What information does each component need?
- What interfaces or MQTT messages are needed?
- Which existing components need to change?
- Which existing components should remain unchanged?

You are working within an existing system.

Do not assume that the simple scripts from Lesson 1 are adequate for the problem you are now solving. For example, `test_flight.py` was designed to demonstrate a simple predetermined flight. Your ATC system introduces concurrency, coordination, and potentially dynamic decisions.

Your design should therefore consider how the **existing architecture must evolve**.

Create:

`hw02/DESIGN.md`

Include:

1. A short description of your architecture.
2. A diagram showing the major components and communication between them. (Note: you can  use any modeling or sketching tool, and/or a photo of a clearly handwritten model)
3. The responsibility of each new or modified component.
4. Any new interfaces or MQTT topics/messages you introduce.
5. The most important design decisions and why you made them.

Your design does **not** need to look like anyone else's design. As we are starting the exercise in class, it is completely fine if you choose to adopt a similar/same design to others in the class as long as everything else is your own independent work.

---

### 4. Implement

Implement the system you designed.

Use the existing UAV infrastructure rather than bypassing it. UAV commands and telemetry should continue to flow through the infrastructure introduced in Lesson 1.

Your implementation should be understandable as a realization of the architecture described in `DESIGN.md`.

If your implementation forces you to make a significant new design decision, update your design documentation. Design is allowed to evolve as you learn more during implementation.

Do not optimize specifically for the example test scenario. Your system will ultimately be evaluated using additional scenarios that you have not seen.

---

## Flight Workloads

Your ATC system will be given a JSON file describing flights that must be completed.

Conceptually, a workload contains an ordered sequence of missions for each UAV:

```text
Drone 1:  Mission 1A → Mission 1B → Mission 1C
Drone 2:  Mission 2A → Mission 2B
Drone 3:  Mission 3A → Mission 3B → Mission 3C
```

Missions assigned to the **same UAV are sequential**.

As soon as a UAV completes one mission, its next mission is eligible to begin.

Different UAVs may therefore have active missions concurrently.

Your system is responsible for deciding **how these flights can be completed safely**.

The workload describes **what must be accomplished**. It does not prescribe how your ATC system should accomplish it.

### Format

```json
{
  "scenario": "example",
  "description": "...",
  "missions": {
    "1": [
      { "mission_id": "1A",
        "waypoints": [
          { "lat": 41.6983055, "lon": -86.237055, "alt": 15 }
        ] }
    ],
    "2": [ ... ],
    "3": [ ... ]
  }
}
```

- Keys of `missions` are UAV ids (`"1"`, `"2"`, `"3"`) — matching the vehicle ids in the telemetry topics from Lesson 1.
- Each mission has a `mission_id` and 1–3 `waypoints`, visited in order.
- `lat` / `lon` are absolute; `alt` is **metres above home** (relative altitude — the same value `{"type": "goto", "alt": N}` takes).
- A mission is complete when the UAV comes **within 2 m** (3D) of its final waypoint. **Your `start_tests.py` must use this 2 m tolerance** to decide when a mission is done and the next one may begin. The instructor's monitor uses the same 2 m, so a looser tolerance would not help you and counts as not meeting the spec.
- All UAVs launch from the standard 3-UAV fleet positions around the home coordinate.

---

## Standard Execution Interface

Every submission must be startable in exactly the same way, so that any solution can be run and evaluated without knowing anything about its internal design.

**You write this script yourself:**

```bash
python lab/lesson2/start_tests.py <workload.json> <min-separation-m>
```

It takes a flight workload and the required minimum separation (in metres), starts your ATC system, and runs the workload to completion. The standard 3-UAV fleet will already be running.

This is a real constraint of the assignment: although everyone's internal architecture will differ, every solution must expose the **same external boundary** so it can be tested independently. Designing that boundary is part of the exercise.

Your `start_tests.py` must:

- Accept the workload file and minimum separation as arguments, exactly as shown above.
- Start your ATC system, and anything else it needs, with no manual steps.
- Dispatch each UAV's missions in order — a UAV's next mission begins once its previous one completes.
- Exit once every mission is complete (or after a generous timeout).

### How grading observes your system

The instructor runs a separate **monitor** — you will **not** see it — that subscribes only to UAV telemetry on the existing MQTT infrastructure. It measures separation, mission completion, and timing from telemetry alone.

Your system is therefore graded on **what is observable in the telemetry stream**. Your UAV commands and telemetry must keep flowing through the Lesson 1 infrastructure; a system that coordinates UAVs "off the books" cannot be evaluated and will not receive credit for behavior the monitor cannot see. You will need to build your own way to measure separation and completion for `VALIDATION.md`.

Before submitting, confirm that a fresh clone of your repository can be started with the command above — no manual edits, no extra setup scripts.

---

### 5. Validate

An example flight workload is provided in `lab/lesson2/` for you to develop against. The workload format is described in [Flight Workloads](#flight-workloads) above.

Run your system against this workload and collect evidence about its behavior.

At minimum, report:

- Whether **all required flights completed**.
- Whether the required **minimum UAV separation** was maintained.
- The **minimum observed separation** during the test.
- The **total time required to complete the workload**.
- Any other metric that provides useful evidence about the behavior of your design.

Put your results in:

`hw02/VALIDATION.md`

Do not report only that the test "passed."

Provide quantitative evidence.

For example:

```text
Flights completed:          8 / 8
Minimum required separation: 10.0 m
Minimum observed separation:  13.4 m
Total workload time:          94.2 s
```

If your system behaves unexpectedly, investigate the result. Explain what happened and whether you changed your requirements, design, or implementation as a result.

### Instructor Validation

Your submitted system will also be run against **additional flight workloads that you have not seen**.

The same execution mechanism will be used:

```bash
python lab/lesson2/start_tests.py <instructor-workload.json> <min-separation-m>
```

These tests may create different patterns of concurrent UAV activity from the example provided to you, and may use a different minimum separation.

Your implementation will be evaluated on whether it can safely and successfully complete the workload, not whether it reproduces a particular ATC architecture.

All submissions will ultimately be evaluated on the same computing environment so that timing measurements can be meaningfully compared.

---

## What Are We Evaluating?

There are two different questions.

### Correctness

Does your system satisfy its requirements?

In particular:

- Do all required flights complete?
- Is safe separation maintained?
- Does the system continue to make progress?

A system that is fast but unsafe is not a successful solution.

### Performance

Among correct solutions, how effectively does the system allow UAVs to operate?

For example:

- How long does the complete workload take?
- How much time do UAVs spend unnecessarily waiting?
- How responsive is the system when coordination is required?

A solution that permits only one UAV to fly at a time might make maintaining separation easy, but it may make poor use of the available airspace.

**Safety comes first, but safety alone does not necessarily make a good ATC design.**

---

## How This Is Graded

Your grade combines your written engineering work, how your system performs on flight workloads **you have not seen**, and an individual discussion of your code in class.

### Rubric

| Component | Exemplary | Proficient | Developing | Insufficient |
|---|---|---|---|---|
| **Analysis — 13 pts** — `ANALYSIS.md` | **12–13** — Important questions and credible alternatives thoroughly explored; key assumptions explicit; tradeoffs reasoned against quality goals such as latency, complexity, freedom from deadlock, and scalability. | **9–11** — Important questions and alternatives considered; assumptions identified; sound rationale provided for major decisions. | **5–8** — Some alternatives considered, but important questions or assumptions are missing or decisions are weakly justified. | **0–4** — Primarily lists final decisions with little evidence that alternatives, assumptions, or tradeoffs were considered. |
| **Requirements — 7 pts** — `REQUIREMENTS.md` | **7** — Precise, testable EARS requirements with comprehensive coverage, including important boundary/failure cases; requirements clearly reflect analysis decisions. | **5–6** — Correct EARS form; requirements are testable and cover separation, UAV progress, conflict detection/response, mission completion, and subsequent missions. | **3–4** — Some requirements are ambiguous, untestable, incorrectly expressed using EARS, or important behaviors are missing. | **0–2** — Requirements are substantially incomplete, inconsistent, or too vague to test. |
| **Design — 16 pts** — `DESIGN.md` | **15–16** — Coherent architecture with clear responsibilities, state, interfaces, and interactions; decisions strongly justified against requirements and quality goals; thoughtfully evolves the existing architecture. | **11–14** — Clear architecture and diagram; responsibilities and interfaces/MQTT topics documented; appropriately builds on existing infrastructure; major decisions justified. | **6–10** — Basic architecture exists, but responsibilities/interfaces are unclear, important issues remain unresolved, or rationale and connection to requirements are weak. | **0–5** — Architecture is missing/incoherent or substantially bypasses rather than builds on the provided infrastructure. |
| **Implementation — 12 pts** | **11–12** — Robust, clean implementation that clearly realizes the documented architecture and runs through `start_tests.py` without manual intervention. | **8–10** — Runs through the required test mechanism; substantially realizes `DESIGN.md`; correctly uses existing MQTT infrastructure; code is understandable. | **4–7** — Partially works but requires intervention, significantly diverges from the documented design, or contains substantial implementation weaknesses. | **0–3** — Does not reliably run through the required interface or substantially fails to implement the proposed solution. |
| **Correctness on unseen workloads — 14 pts** | **13–14** — Safely completes all workloads, including challenging cases; maintains required separation and progress with no deadlock. | **10–12** — Successfully completes standard unseen workloads while maintaining required separation and making progress. | **5–9** — Generally works but exhibits some safety, completion, coordination, or progress failures. | **0–4** — Significant safety violations, deadlock, incorrect mission execution, or inability to complete substantial portions of the workloads. |
| **Performance on unseen workloads — 8 pts** | **7–8** — Effective concurrency and responsiveness with little unnecessary blocking; strong overall workload completion time while preserving correctness. | **5–6** — Reasonable completion time and concurrency without substantial unnecessary blocking; appropriately responsive when coordination is required. | **3–4** — Generally correct but substantially inefficient, with unnecessary waiting/blocking or poor responsiveness. | **0–2** — Performance substantially prevents useful concurrent operation or causes excessive delays. |
| **Validation — 5 pts** — `VALIDATION.md` | **5** — Strong quantitative evidence; results meaningfully interpreted; unexpected behavior investigated and explained. | **4** — Required quantitative measures reported and used to assess whether requirements are satisfied. | **2–3** — Limited quantitative evidence or results reported with little interpretation. | **0–1** — Little systematic validation or relies primarily on unsupported claims such as "it passed." |
| **AI use reflection — 5 pts** — `AI_USE.md` | **5** — Specific, thoughtful account of where AI helped, where suggestions were challenged/corrected/rejected, how important AI-generated work was verified, and what was learned. | **4** — Clear and specific account of AI use, including how important AI-generated work was evaluated or verified. | **2–3** — Describes AI use but provides limited evidence of critical evaluation, verification, correction, or learning. | **0–1** — Generic/minimal account or little meaningful reflection on AI use. |
| **Individual code understanding (in class) — 20 pts** | **18–20** — Demonstrates deep understanding of own system; can explain architecture and implementation behavior, justify decisions, trace behavior through code, and reason about alternatives and changes. | **14–17** — Accurately explains own architecture, code, interfaces, and important design decisions and can reason about straightforward modifications. | **7–13** — Understands major portions but cannot adequately explain important behavior, decisions, code, or consequences of changes. | **0–6** — Cannot demonstrate sufficient understanding of the submitted solution or significant portions of own code. |

### Individual code understanding — 20%

Because AI assistance is expected, being able to explain your own work is a graded outcome in its own right — a fifth of this assignment.

In class on **Thursday**, you will receive a short set of questions specific to the code and design in your repository — for example, why a particular component holds the state it does, what your system does if a UAV stops responding, or how your conflict logic behaves in a case your validation did not cover. The [Before You Submit](#before-you-submit) questions are a good guide to the kind of thing to be ready for.

You answer these **independently, in class, without AI assistance.** You are graded on how well you can reason about your own system — its design decisions, its behavior, and its limits.

---

## Deliverable

In your repository, create:

```text
hw02/
├── ANALYSIS.md
├── REQUIREMENTS.md
├── DESIGN.md
├── VALIDATION.md
├── AI_USE.md
└── <your implementation files>

lab/lesson2/
└── start_tests.py        (you write this)
```

Your submission should contain:

- **Analysis** — questions, alternatives, assumptions, and decisions.
- **Requirements** — your key behavioral requirements written using EARS.
- **Design** — architecture, responsibilities, interfaces, and rationale.
- **Implementation** — the working ATC system.
- **Validation** — results from running the supplied example workload, including quantitative metrics.
- **AI use reflection** — a short, specific account of how you used Claude.
- **`start_tests.py`** — your entry-point script (see [Standard Execution Interface](#standard-execution-interface)).

Your solution must run through the standard interface:

```bash
python lab/lesson2/start_tests.py <workload.json> <min-separation-m>
```

Commit and push your work:

```bash
git add .
git commit -m "Complete HW02"
git push
```

---

## Before You Submit

Make sure you can answer these questions:

- What were the most important decisions you made during analysis?
- Which of those decisions became requirements?
- How does your architecture realize those requirements?
- What evidence demonstrates that your implementation satisfies them?
- What are the strengths and weaknesses of the design you chose?
- What would happen to your design if the number of UAVs increased substantially?

Most importantly:

> **Be able to explain why your system is designed the way it is.**