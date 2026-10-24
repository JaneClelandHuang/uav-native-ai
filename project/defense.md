# Individual Engineering Brief + Oral Defense

> **DRAFT ONLY — not yet reviewed. Details, dates, and grading below
> are subject to change before this is final.**

## Objectives

Your team built the system together, often in pairs. This part is yours
alone: what you decided, what you understand, and where your judgment
mattered.

Worth **100 points**, separate from the team grade: **20** for the brief
and **80** for the oral defense. Strong team work doesn't substitute for
individual understanding, and a weak team result doesn't cap it.

---

## The Individual Engineering Brief

About **2 pages**, written by you, due **11:59 PM Monday, Dec. 14**, as
`docs/briefs/<your-netid>.md` in your team repo. Write it whenever suits
you during the project; it's easier while things are fresh.

### 1. Contribution map

Your issues, PRs and reviews, grouped by component, with links. For each
group, one line on **what you decided**. Paired work is fine: say so, and
say what you drove ("paired with Sam on the validator; I designed the
timeout").

### 2. Two decisions you'd defend, one you'd reverse

Three engineering decisions you made or shaped. For the two you'd defend:
what you decided, what you weighed, and the evidence that it was right.
For the one you'd reverse: what you'd do now, and what taught you.

### 3. One AI episode

One specific time AI was wrong and you caught it, or a decision you
deliberately kept for yourself. Link the PR or commit. What happened, how
you knew, and what you'd do differently.

### 4. Optional: a Physical AI limitation

If you want to go further: one paper or article on a Physical AI problem
your system has (perception under uncertainty, LLM reasoning in physical
systems, guardrails, human trust, sim-to-real, autonomy and
accountability), with a link, and what it would change in your system.

**Write it yourself.** AI may critique a draft; it doesn't write the
brief. Your defense starts from it.

### How the brief is graded

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **Contribution map** | 6 | Complete, linked, honest about pairing, clear about what you decided. |
| **Decisions** | 8 | Real decisions, real trade-offs, evidence; a reversal you've genuinely learned from. |
| **AI episode** | 6 | Specific, linked, and showing your judgment. |
| **Total** | **20** | The optional section can make up for a weaker section, not exceed 20. |

</div>

---

## The Oral Defense (finals week)

About **15 minutes**, one student at a time, with the instructor. No
slides, no AI, no notes beyond your brief. Your team's repo, website and
running system are available to point at. Sign up for a slot (times to
follow).

It is a **conversation**, built from your brief and your team's system:

1. **Your brief** (about 4 minutes): we start from it. "Walk me through
   the decision you'd reverse."
2. **The system** (about 5 minutes): explain an important part of your
   team's system, including parts you didn't build. Where does this
   message go? Why is this component here?
3. **A scenario** (about 4 minutes): you reason through something that
   goes wrong. "A drone goes silent mid-approval. What does your system
   do, and how would you know?"
4. **AI and judgment** (about 2 minutes): where AI helped, where it
   failed, and what you never let it decide.

### How the defense is graded

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **Your contributions and decisions** | 20 | You explain what you did and why, consistent with your brief and your commits. |
| **System understanding** | 25 | You explain the team's system beyond your own part, accurately. |
| **Reasoning through a scenario** | 20 | You reason from how the system actually works to what it would do, and how you'd find out. |
| **AI and engineering judgment** | 15 | Specific, honest examples of where AI helped, failed, and where you decided. |
| **Total** | **80** | |

</div>

> **Be able to explain why your system works the way it does, and what you
> decided.**
