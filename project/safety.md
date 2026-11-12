# Safety Analysis — FMECA + Safety Cases

## Objectives

A team safety analysis of your system: how it can fail or cause harm, what
stands between each failure and its effect, and which safety claims are
supported by evidence rather than assumed.

This is an **intermediate deliverable**. You started it in class on
Thursday, Nov. 12; finish it alongside your project work.

By the deadline, your team will have:

- A **Failure Modes, Effects and Criticality Analysis (FMECA)** of your
  system: ten failure modes, each rated for severity, occurrence and
  detection difficulty, with its mitigation traced to the code.
- **Three safety assurance cases** in Goal Structuring Notation (GSN),
  each arguing one safety claim down to evidence, with gaps marked as
  undeveloped.

Worth **40 points**, a team grade. Due **11:59 PM Monday, Nov. 23**.

---

## What to Submit

In your team repo, under `docs/safety/`:

| File | What it is |
|---|---|
| `fmeca.csv` (or `.xlsx`) | Your FMECA, ten rows |
| `safety-case-1.png`, `-2`, `-3` (or `.pdf`) | Three GSN diagrams |
| `safety-cases.md` | A short paragraph per safety case: the claim, why you chose it, and what is still undeveloped |

### The FMECA

One failure mode per row:

| Column | What goes in it |
|---|---|
| Item | The function or component |
| Failure mode | How it fails |
| Effect | What happens to the mission, the drones or people |
| Cause | Why it could happen |
| Severity (S) | 1–10 |
| Occurrence (O) | 1–10 |
| Detection difficulty (D) | 1–10: how hard it is to notice before harm (10 = undetectable) |
| RPN | S × O × D |
| Mitigation | What your system does about it, and **where in the code** |
| Status | **Handled**, **partly handled**, or **technical debt** |
| Evidence | A test, oracle, fault run or PR that shows it, if any |
| Source | **Us**, **AI**, or **both** |

At least **2 rows** must involve the **AI component** (a wrong, late or
missing answer) or the **person on the loop** (a missed alert, a wrong
approval, an operator who isn't there). Rate the system as it is built
now: a planned mitigation doesn't lower the ratings yet.

### The safety cases

Three safety claims, each threatened by rows of your FMECA. A natural split
is one per team member. For each, a GSN diagram with:

- a **goal**: the top-level safety claim;
- a **strategy**: how you break it down;
- **sub-goals**: what must hold for the claim to hold;
- **solutions**: the evidence for each sub-goal;
- **context** and **assumptions** where the claim depends on them.

Any sub-goal **without evidence is marked undeveloped** (a hollow diamond
in GSN). That's technical debt, and saying so is expected.

The UTM air-leasing example from class shows the level of detail we're
looking for.

---

## Using AI

Use AI to suggest failure modes and to critique your drafts, **after**
your team has written its own list. Check every AI-suggested row against
your real code, and record it in the Source column.

---

## How It's Graded

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **FMECA** | 16 | Ten real failure modes for your system, sensible ratings, mitigations located in the code, honest status, at least 2 rows on the AI component or the person on the loop. |
| **Safety cases** | 24 | 8 each: a clear claim linked to your FMECA, a sound strategy, evidence linked to each sub-goal, and undeveloped goals marked. |
| **Total** | **40** | |

</div>

> **Keep building.** Next week is an intensive project sprint. FMECA rows
> with a high detection difficulty make good D4 oracles.
