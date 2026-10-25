---
title: Team Project
---

# Team Project

> **DRAFT — everything from Project Week 1 (Week 9) to the end of the
> semester is still being finalized.** Dates, deliverables and grading on
> these pages may change before each one is released. Each deliverable's
> page says when it's final.

From Fall Break to finals week, you work in a team to design, build, test
and demonstrate a swarm-based Physical AI system for a disaster-response
problem of your choice. Every project implements an operational
**Perceive → Reason → Act** loop, keeps a person meaningfully in the loop
through a GUI, and is backed by engineering evidence. See the
[Syllabus]({{ '/syllabus.html' | relative_url }}) for how the project is
assessed overall.

**Using AI:** use it however you like. Every deliverable must be vetted by
a human on your team: no AI slop. You are entirely responsible for what you
present, whether AI helped make it or not.

**Every week:** at least 2 small, reviewed, merged PRs per team member, and
no direct commits to `main`.

---

## Deliverables

<div class="table-wrap" markdown="1">

| Deliverable | Points | In class | Due (11:59 PM) |
|---|---:|---|---|
| [D1 — Project Vision](d1.md) | 40 | Vision presentations, Thu. Oct. 29 | Mon. Nov. 2 |
| [D2 — Architecture + Architectural Spike](d2.md) | 60 | Spike gallery, Tue. Nov. 10 | Mon. Nov. 16 |
| [D3 — Working System + Architecture Review](d3.md) | 70 | Live demos, Thu. Nov. 19 | Mon. Nov. 23 |
| [D4 — Testing Agent + Engineering Evidence](d4.md) | 80 | — (fault runs outside class) | Thu. Dec. 3, start of class |
| [D5 — Final System + Live Demo](d5.md) | 150 | Final demos, Tue. Dec. 8 | — |
| [D5 — Final Website](d5.md) | 100 | — | Mon. Dec. 14 |
| [Individual Brief + Oral Defense](defense.md) | 100 | Oral defense, finals week | Brief: Mon. Dec. 14 |

</div>

---

## Week by Week

<div class="table-wrap" markdown="1">

| Project week | Tuesday | Thursday |
|---|---|---|
| **1** (Oct. 27–29) | Planning studio, no AI: vision, use case, wireframes, success criteria. Team repos created. | **D1 vision presentations** |
| **2** (Nov. 3–5) | Guest: Tori Huang-Brauer, *Claude in Software Engineering* | Architecture sketches and architectural spikes; spike questions checked |
| **3** (Nov. 10–12) | **D2 spike gallery**; your slice as GitHub issues | Reading: architecture decision records; AI-assisted code review; studio |
| **4** (Nov. 17–19) | Guest: Jan-Philipp Steghöfer (tentative); intent vs. solution; CI | **D3 live demos**; testing agents |
| **5** (Nov. 24) | **Build and test**, UG Commons | Thanksgiving |
| **6** (Dec. 1–3) | **Build and test**, UG Commons | **Team meetings** with the instructor, UG Commons |
| **7** (Dec. 8) | **D5 final live demonstrations** | — |
| **Finals week** | **Individual oral defenses** | |

</div>

A further guest, Matt Brauer on UAV development, will be scheduled when
confirmed.

---

## Your Project Environment

Each team gets a fresh repo from the team template: the course simulation
environment (`lab/`), the multi-vehicle GUI (`gui/`), a website skeleton
(`docs/`), a PR template and team rules for Claude (`CLAUDE.md`). Your team
chooses how to host the website; its link goes at the top of your README.
Each project week adds one step:

| Project week | Step |
|---|---|
| 1 | Team repo, website, protected `main` |
| 2 | One-command run, `spikes/`, the project section of `CLAUDE.md` |
| 3 | Issues, a project board, your PR-review skill |
| 4 | CI: your unit tests on every PR |
| 5–6 | Your testing agent; demo discipline |

**Resources:** [disaster scenes](disaster-areas.md) ·
[`mischief_d4.py`](tools/mischief_d4.py) (for D4's fault runs)
