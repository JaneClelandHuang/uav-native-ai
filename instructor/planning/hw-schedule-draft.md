# HW1–HW7 Schedule — Draft

Working draft, not yet final. Grading breakdown is still TBD (see
`syllabus.md`'s placeholder callout). Iterate on this directly.

## Dates

| HW | Assigned | Due | Time |
|---|---|---|---:|
| **HW 1** | Tue Aug 25 | Mon Aug 31 | 6 days |
| **HW 2** | Tue Sep 1 | Mon Sep 7 | 6 days |
| **HW 3** | Tue Sep 8 | Mon Sep 14 | 6 days |
| **HW 4** | Tue Sep 15 | Mon Sep 21 | 6 days |
| **HW 5** | Tue Sep 22 | Mon Sep 28 | 6 days |
| **HW 6** | Tue Sep 29 | Mon Oct 5 | 6 days |
| **HW 7** | Tue Oct 6 | Mon Oct 12 | 6 days |

## Weekly plan

### HW1 — System Architecture

**Learning goal:** Understand the system architecture — MQTT vs. MAVLink,
containers, ports, networking.

**Assignment:** Complete `lab/SETUP.md`, run a scripted flight
(`scripts/test_flight.py` or `scripts/simple_flight.py`), answer in
writing:

- Explain the role of ArduPilot SITL in our architecture.
- Explain the role of `drone_backend.py` and why it exists.
- Explain the role of Mosquitto (MQTT broker).
- Explain why we use MQTT instead of allowing every application to
  communicate directly with the autopilot.
- Identify which components communicate using MQTT and which communicate
  using MAVLink.
- Explain the difference between TCP and UDP, and why each is used in our
  system.
- Know the purpose of port 1883 and port 14550.
- Explain what Docker Compose does when we run `docker compose up`.
- Explain the difference between the Docker private network and the host
  computer.
- Explain the difference between ports that are internal to Docker and
  ports that are published to the host.
- Explain how an application running on the host (e.g., the GUI)
  communicates with the drone.
- Describe the complete communication path when a user clicks Take Off in
  the GUI, including all intermediate components and protocols.
- Explain why we separate the system into multiple Docker containers
  rather than placing everything into one container.
- Explain the concept of loose coupling and how MQTT helps achieve it in
  our architecture.

**Grounded in:** `lab/SETUP.md`, `lab/ARCHITECTURE.md`,
`lab/PYMAVLINK-LIB.md`.

---

### HW2 — Flight Logs + Prompt Engineering

**Learning goal:** Prompt engineering as an empirical discipline, not
guesswork — and, implicitly, the "vibe coding" contrast: a single casual
prompt is itself one point in the comparison, not the default way to work.

**Assignment:** Two real flight logs, finalized and distributed (release,
not committed to git):
https://github.com/nd-native-ai-uav/native-ai-uav-resources/releases/tag/hw02-flight-logs
(grant each student read access via the `fall-2026-students` GitHub team
as they enroll). Full instructor analysis/answer key for both —
**not for student distribution** — in
`instructor/hw02-flight-logs/{fence-breach-fuchsia,failsafe-cascade-lime}.md`.

- **Log A** (`2025-08-24 11-56-32.bin`, FUCHSIA): repeated geofence
  breaches, single clean cause, low complexity. Good first log.
- **Log B** (`2026-03-21 16-46-34.bin`, LIME): radio/GCS comms failsafe
  cascade, text-narrated via plain-English `MSG` entries, moderate
  complexity, different evidence style than Log A (timing/text narrative
  vs. distance-computation detective work) — good contrast pairing.

A third, harder log (stale-home waypoint displacement, near-collision)
was considered and set aside as too advanced for this assignment — real
research incident, being written up separately for a paper.

Students should, per log:

1. Design a fixed set of analytical questions about the flight (both
   answer-key docs above include candidate questions, including a couple
   of deliberate "trap" questions that test whether a prompting strategy
   correctly flags uncertainty rather than overclaiming).
2. Answer those questions using at least two distinct prompting
   strategies against an LLM (e.g. single-shot vs. chain-of-thought,
   or zero-shot vs. few-shot with worked examples).
3. Verify each answer against the actual log data themselves — this is
   the accountability step, not optional.
4. Write up which strategy performed better, on what kinds of questions,
   and why — an empirical quality claim (syllabus objective #5), not "it
   felt more thorough."

**Grounded in:** the two flight logs above, syllabus learning objectives
#1 and #5.

**Open question:** exact question set and rubric depend on the real log's
format/fields once uploaded — revisit after that lands.

---

### HW3 — Unit Testing + a Testing Agent

**Learning goal:** Why untested AI-generated code is risky. Build a
testing agent, not just a test suite.

**Assignment:** Write a pytest suite for testable logic (e.g. the
position-target type-mask bit encoding in `mavlink_lib.py`). Build/prompt
an agent that runs the suite and reports failures in plain English.

**Grounded in:** `lab/backend/mavlink_lib.py`, `lab/PYMAVLINK-LIB.md`.

**Open question:** HW3 needs something stable to test against by week 3.
`instructor/monitor.md` mentions `parse_status_text`/`parse_battery`/etc.
were built into `mavlink_lib.py` but **not yet wired into**
`drone_backend.py`'s reader loop or MQTT publishing. Decide whether that
wiring needs to land (and where) before HW3, or whether HW3 tests only the
already-merged pure `parse_*` functions as-is.

---

### HW4 — Live Telemetry Health and Fault Injection

**Learning goal:** Builds on HW2's log-reading foundation — move from
analyzing a static, already-completed log to interpreting telemetry
*live* and diagnosing problems as they happen: EKF/GPS/vibration health
signals, fault injection.

**Assignment:** `instructor/monitor.md`'s tiered framework, built out as
the assignment:

- **Tier 1:** `STATUSTEXT`, `SYS_STATUS` battery, `HEARTBEAT` mode/armed.
- **Tier 2:** `SYS_STATUS` sensor-health bitmask, `RADIO_STATUS`,
  `NAV_CONTROLLER_OUTPUT`.
- Use `SIM_*` fault-injection parameters (`SIM_GPS_NOISE`,
  `SIM_VIB_FREQ_*`, etc. — see `instructor/monitor.md`'s table) to
  actually break something and detect it, rather than watching idealized
  "healthy" values the whole flight.

**Grounded in:** `instructor/monitor.md` (already has the full technical
research done — message types, gotchas, tiering).

**Open question:** Tier 3 (HAcc/EKF/vibration under fault injection) is
harder and was flagged as needing fault injection as a hard prerequisite
— decide if it's in-scope for HW4 or held back as a stretch/HW7 tie-in.

---

### HW5 — Operator-Facing GUI: Route Planning and Mission Dispatch

**Learning goal:** Build an application supporting safe supervision of
autonomous operations (syllabus objective #4) — and design/integrate a new
interface onto a deliberately minimal starting point, working with Claude
Code as a collaborator rather than just a code generator.

**Assignment:** `matplotlib_view.py` is deliberately stripped down as the
starting point, specifically to leave room for this. Working with Claude
Code, students add:

- **Route planning:** define a multi-waypoint route (click-to-place on the
  plot, or a simple form/file input — student's design choice).
- **Saving:** persist named routes so they can be reloaded later, not
  just used once. `lab/locations.json` (name/nickname/lat/lon/alt) is a
  ready precedent for this exact save/load shape, already in the repo.
- **Dispatch:** a control that runs a saved route as a mission from the
  GUI.

**Real design decision, not a solved problem:** `drone_backend.py`
currently only understands single-waypoint commands (`goto`, `takeoff`,
`land`, `circle`, etc. — see `handle_command`), no native multi-waypoint
"mission" command. The only existing precedent for sequencing multiple
waypoints is *client-side*, in `scripts/test_flight.py`'s `wait_for()`
loop (send one `goto`, poll telemetry until arrival, send the next). HW5
turns that ad hoc script pattern into a proper GUI feature, and forces a
real architectural choice: does mission-sequencing logic live in the GUI
(matches existing precedent, no backend changes) or become a new
server-side `mission` command in `drone_backend.py`/`mavlink_lib.py`
(cleaner separation, more work, reusable by other frontends)? Worth
letting students argue either way, or debate it explicitly.

**Grounded in:** `lab/client/matplotlib_view.py`, `lab/locations.json`,
`lab/backend/drone_backend.py`'s `handle_command`,
`lab/scripts/test_flight.py`, HW4's telemetry work.

**Ties forward:** the GUI-vs-backend sequencing question is a natural
setup for HW7's architectural-critique week — a student's HW5 choice is
fair game for the design-analysis agent exercise later.

---

### HW6 — Computer Vision / Real-World Perception

**Learning goal:** Integrate perception into situational awareness.

**Assignment:** Wire `lab/cv/`'s YOLO person-detection pipeline
(`frame-collection.py`, `detect-people.py`) into the HW5 dashboard.
Report precision/recall on collected frames — an empirical quality claim,
not just "it works" (syllabus objective #5).

**Grounded in:** `lab/cv/`.

---

### HW7 — Architectural Thinking and Analysis Agent

**Learning goal:** Critique architecture, don't just build it.

**Assignment:** Two-agent pattern from
`exemplars/chatgpt-as-a-design-agent/design-analysis-1.md`: one agent
proposes a design/refactor on a real piece of the codebase, a second acts
as an independent critic, student mediates and writes up the analysis.

**Optional stretch:** point the critic agent at a real PR diff via
GitHub's API, comment-only (no write/merge access) — introduces "agent
with real-world side effects" narrowly and safely.

**Grounded in:** `exemplars/chatgpt-as-a-design-agent/design-analysis-1.md`.

**Open question:** the GitHub-agent stretch goal needs a real PR to point
at — either a synthetic one set up ahead of time, or a live PR from a
student's own HW2/HW3 work if timing allows.

---

## Cross-cutting open questions

- Grading breakdown per assignment (syllabus.md still has a placeholder
  callout for this).
- Whether "vibe coding" gets its own explicit discussion/reading before
  HW2, or is introduced entirely through the HW2 assignment itself.
- Late-work policy interaction with the 6-day turnaround — is there any
  slack built in given the density here?
