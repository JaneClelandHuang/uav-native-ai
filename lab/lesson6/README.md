# HW6 — Build a Human-on-the-Loop Mission Response Planner

**DRAFT. Not yet released.**

When a UAV's camera finds a person, the operator shouldn't have to fly the
UAV to them. Instead, the system offers a short **menu of responses**
("hover and stream", "circle and stream", "deliver the medical kit"). The
operator picks one, and software checks it and carries it out. The operator
stays *on* the loop, deciding what happens, not *in* it, flying the aircraft.

In class you designed this planner with CRC cards. This week you build
**your** design.

**Budget around 6–8 hours**, consistent with every other assignment this
term. If you can't finish in that time, document unfinished work as
technical debt in `report.md`.

---

## Why this week, why now

This week is about treating an AI component's output as **uncertain
evidence**. A YOLO detection at 0.31 confidence might be a person, or it
might be a shadow. The planner is where that uncertainty turns into
consequences: flying a UAV away from its search route, or dropping the only
medical kit you have.

Next week (Lesson 7), the human decision-maker is replaced by an AI one. The
rule then is *the LLM proposes, deterministic software constrains, flight
control executes*. This week you build the structure that rule depends on:
a fixed menu of responses, a validator that every decision passes through
no matter who made it, and an executor that owns the flying. If your design
has a clean seam between "who decides" and "what happens next", swapping in
an AI next week is a small change. If it doesn't, you'll find out.

---

## What you're given

| File | What it is |
|---|---|
| `lab/cv/person_event_detector.py` | Live YOLO person detection on the simulated camera feed. Geolocates each person and publishes an event on `mission/events`. Confirms a person from 2 frames before reporting, and re-announces them every 30 s while still in view. |
| `lab/cv/geolocate.py` | Pixel → lat/lon for the nadir, north-up simulated camera. |
| `lab/lesson6/hotl_popup.py` | The operator popup (PyQt5), **finished and unwired**. No planner is behind it. Your planner must speak its MQTT contract (below). |
| `lab/lesson6/inject_event.py` | Publishes a fake person event. Use it to develop and test without the camera pipeline. |
| `lab/lesson6/mission_config.json` | Starter config: the UAV you own, its payload, battery costs, default parameters, and a search route. Input, not a spec. Change it as you like. |
| `lab/ARCHITECTURE.md` | The flight primitives on `uav/<id>/command` (`takeoff`, `goto`, `circle`, `interrupt`, `land`, …) and telemetry on `uav/<id>/telemetry`. Your planner flies the UAV only through these. |

The live detector needs camera frames that carry a `pose` (the drone's
position, altitude and zoom when the frame was taken). If yours don't, or
you just want repeatable tests, use `inject_event.py`. Either way, your
planner sees the same message.

---

## What you build

A planner process that sits between the detector and the popup:

```
mission/events ──► YOUR PLANNER ──► mission/decision_request ──► popup
                   (world model,    ◄── mission/decision ◄───── (operator)
                    candidates,     ──► mission/action_result ─►
                    validator,      ──► mission/behavior_status ►
                    executor)       ◄── mission/cancel, mission/abort
                        │  ▲
          uav/1/command ▼  │ uav/1/telemetry
                      ArduPilot SITL
```

How you divide that into classes and modules is **your design**. The
requirements say what it must do, not how to structure it.

### Requirements

**R1 World model.** Track what the planner currently believes:
- UAV state: position, battery, payload on board, what it's doing now, and
  its progress along its search route.
- **Found persons only.** Location, confidence, who saw them, when, and a
  decision status. You don't need to model where people *might* be, or
  which areas have been searched.

**R2 Detections are uncertain evidence.** Your planner needs an explicit
policy for low-confidence detections. For example, below some threshold
the menu offers only responses that *verify* (hover or circle and stream),
not one that spends the medical kit. You choose the policy and the
threshold, and you justify both in `design.md`.

**R3 One decision per person.** The detector re-announces people it keeps
seeing, and a circling UAV sees the same person over and over. A person the
operator has already decided about (responded to, or chose "No action" for)
**must not** raise another popup. Treat events within ~10 m of a known
person as that person. A person nobody decided about (the request timed out)
may be asked about again when next seen.

**R4 Candidate responses.** For each person, build the menu: at least
`hover_stream`, `circle_stream` and `deliver`. Each candidate gets its
eligible UAVs, a default UAV and default parameters (from the config).

**R5 Decision loop through the popup.** Send a `decision_request`, then
handle what comes back: an action, a dismiss ("No action"), or nothing.
Enforce the `timeout_s` you advertised. Keep the decision-maker behind an
interface, so that next week an AI one can replace the human one without
touching the rest.

**R6 Validator, as its own stage.** Every action passes through it before
anything flies, whoever chose it. At minimum:
- `deliver` needs the chosen item on board.
- Battery must cover the reserve plus the response's cost (from the config).

Report every verdict on `mission/action_result`. On a rejection, ask again
with the reasons in `previous_rejection`, so the operator sees why.
Keep the checks simple; the point is that the stage exists.

**R7 Execution, then resume.** The UAV flies its search route. When an
action is approved, it leaves the route, performs the response, and
reports progress on `mission/behavior_status` (`PENDING`, `RUNNING`,
`COMPLETED`, `FAILED`, `CANCELLED`). When the response finishes, it
**resumes the route at the waypoint it was heading to**. **Cancel** from
the popup stops the response and resumes the route too.

What each response means in flight:

| Response | Behavior |
|---|---|
| `hover_stream` | Fly to the target (or `standoff_m` from it) and hold for `duration_s`. |
| `circle_stream` | Orbit the target at `radius_m` for `duration_s`. `circle` always starts due north of the center; see `lab/scripts/test_circle.py`. |
| `deliver` | Fly to the target, descend to `delivery_alt_m`, dwell, release (simulated: remove the item from the payload), climb back out. |

### Out of scope

Leave these out. You're not graded on them:
- Multiple UAVs responding at once.
- Abort / return-to-launch, critical-battery overrides, and noticing that
  someone else took control of the UAV. (The popup has an **Abort** button;
  it's fine if your planner ignores it.)
- Surviving a planner restart.
- Geofences, altitude limits and other parameter range checks.
- Area search and follow-a-road responses.

Stretch goals, if you have time: Abort → return to launch; a second UAV
(so the operator chooses *which* UAV responds); crash-and-resume.

---

## The popup contract

All topics are JSON over MQTT on `localhost:1883`.

| Topic | Direction | Payload |
|---|---|---|
| `mission/events` | detector → planner | `{event_id, type, lat, lon, confidence, source_uav, source_drone, timestamp, image_b64}` |
| `mission/decision_request` | planner → popup | `{request_id, event, world_state, candidates, previous_rejection, timeout_s}` |
| `mission/decision` | popup → planner | `{request_id, action: {type, uav, target: {lat, lon}, parameters}}` or `{request_id, dismiss: true}` |
| `mission/action_result` | planner → popup | `{request_id, action_id, uav, type, approved, reasons}` |
| `mission/behavior_status` | planner → popup | `{uav, behavior, state, detail, action_id, stream_required}` |
| `mission/cancel` | popup → planner | `{uav, action_id}`: stop that response if it's still running |
| `mission/abort` | popup → planner | `{uav}` (out of scope) |

The pieces the popup reads:

- **`event`**: the event as received (`image_b64` may be `null`).
- **`world_state`**: `{"uavs": [{uav, color, battery_level, payloads, current_behavior}, ...]}`.
  `battery_level` is 0–1. `current_behavior` is `null` when idle.
- **`candidates`**: a list of
  `{type, label, description, eligible_uavs, default_uav, parameters, options}`.
  `parameters` is a dict of name → default value. Numbers get a spin box,
  anything else a text field. `options` (optional) maps a parameter name
  to a list of choices, which get a drop-down (e.g. `{"item": ["medical_kit"]}`).
- **`previous_rejection`**: `null`, or a list of reason strings.
- **`request_id`**: yours to generate. A re-ask after a rejection uses a
  **new** `request_id` with the same `event`, and the popup reuses the
  same window.
- **`stream_required`**: `true` for the streaming responses. The popup
  reminds the operator to turn on streaming for that drone in the GUI.

Read `hotl_popup.py` if anything here is unclear. It is the ground truth.

---

## Running it

1. `docker compose up -d` in `lab/`.
2. `python lab/lesson6/hotl_popup.py`
3. Your planner.
4. Either `python lab/lesson6/inject_event.py <lat> <lon>` with a location
   near the route, or the GUI with camera simulation on, a person placed
   under the route in the Scene Builder, streaming on for the drone, and
   `python lab/cv/person_event_detector.py` (needs `lab/cv/requirements.txt`).

---

## Design first

Start from your CRC cards from class, not from a blank prompt to Claude.
Before writing code, put in `design.md`:

1. **Your CRC cards**, cleaned up: each class, its responsibilities, its
   collaborators.
2. **One sequence diagram** (Mermaid is fine) for: event arrives → operator
   approves `hover_stream` → UAV flies it → UAV resumes its route.
3. **The seam for next week**: which class or interface an AI
   decision-maker would replace, and what it would be handed.
4. **Your low-confidence policy** (R2), with the threshold and why. The
   detection frames from class (a hit at 0.26, a false positive at 0.31)
   are fair evidence to cite.

As you build, keep `design.md` honest. If the code ends up different from
the cards, update the design and add a line saying what changed and why.
That's normal. Code that quietly diverges from its design isn't.

---

## Testing

- **Unit tests** (no SITL, no MQTT): person merging and status (R3), your
  confidence policy (R2), the candidate menu (R4), and the validator (R6).
  These are pure logic. Your HW5 test skill should handle them.
- **Integration tests** (SITL + broker + your planner), with
  `inject_event.py` standing in for the popup's input where it helps:
  - event → approve `hover_stream` → `COMPLETED` → route resumes at the
    right waypoint
  - `deliver` approved, then a second `deliver` for someone else rejected,
    because the kit is gone
  - the same person re-announced after a decision → no second popup
  - Cancel mid-response → route resumes

Put the evidence in `report.md`: commands, output, and what you observed.

---

## How This Is Graded

Out of **100 points**.

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **Design** | 20 | `design.md`: CRC cards, sequence diagram, the named seam for an AI decision-maker, and code that matches the design, or says where and why it doesn't. |
| **World model & uncertain evidence** | 15 | R1–R3: persons tracked with a real decision status; no repeat popups for decided persons; a low-confidence policy that's explicit, implemented and justified. |
| **Candidates & decision loop** | 15 | R4–R5: the popup works against your planner, including dismiss, timeout, and re-ask after a rejection. The decision-maker is behind an interface. |
| **Validator** | 10 | R6: a separate stage every action passes through, with verdicts reported and rejections re-asked. |
| **Execution & resume** | 15 | R7: all three responses fly correctly, status is reported throughout, and the UAV resumes its route after completion and after Cancel. |
| **Testing evidence** | 10 | Unit tests for the pure logic plus the integration scenarios, with real output in `report.md`. |
| **Reflection** | 10 | `reflection.md`: where your design helped or got in the way, what surprised you when it flew, what you'd change before an AI starts making the decisions, and a "Lessons Learned" section about using Claude. |
| **Individual understanding** — in class | 5 | Questions pushed to your folder, as in HW5. |
| **Total** | **100** | |

</div>

---

## Deliverable

```text
hw06/
├── planner/            your planner (any structure you like)
├── tests/              unit and integration tests
├── design.md           CRC cards, sequence diagram, AI seam, confidence policy
├── report.md           what works, what doesn't (technical debt), test evidence
└── reflection.md       text, and/or a recording (include the URL)
```

```bash
git add hw06
git commit -m "Complete HW06"
git push
```

---

## Before You Submit

Be ready to explain:

- Where a decision goes, step by step, from the event arriving to the UAV
  moving, in terms of your own classes.
- What stops a 0.31-confidence detection from using up the medical kit.
- Exactly what you would change to let an AI make the decision instead of
  the operator, and what you would *not* have to change.
- How your UAV knows which waypoint to go back to.

> **The operator chooses *what* should happen. Your software decides
> whether it *can*, and then makes it happen.**
