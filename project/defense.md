# Individual Safety Case + Oral Defense

> **DRAFT ONLY — not yet reviewed. Details, dates, and grading below
> are subject to change before this is final.**

## Objectives

Your team built a system that flies. This part is yours alone: where can
it hurt someone or fail its mission, what does your system already do
about it, and what is still technical debt?

Worth **100 points**, separate from the team grade: **30** for your safety
case and **70** for the oral defense. Strong team work doesn't substitute
for individual understanding, and a weak team result doesn't cap it.

---

## The Individual Safety Case

Due **11:59 PM Monday, Dec. 14**, in your team repo under
`docs/safety/<your-netid>/`. Do it **individually**. You may analyze any
part of your team's system, at any level of the stack; teammates may pick
the same part.

### 1. Your own failure modes first

Before you ask AI anything, list the ways you think your system could fail
or cause harm: as many as you can, in a few words each. **Commit that list**
as `my-first-list.md`. It's the baseline for step 4.

### 2. FMECA: ten rows

A spreadsheet (`fmeca.csv` or `.xlsx`) with **10 failure modes**, one per
row:

| Column | What goes in it |
|---|---|
| Item | The function or component |
| Failure mode | How it fails |
| Effect | What happens to the mission, the drones or people |
| Cause | Why it could happen |
| Severity (S) | 1–10 |
| Occurrence (O) | 1–10 |
| Detection (D) | 1–10: how hard it is to notice before harm (10 = undetectable) |
| RPN | S × O × D |
| Mitigation | What your system does about it, and **where in the code** |
| Status | **Handled**, **partly handled**, or **technical debt** |
| Evidence | A test, D4 oracle, fault run, or PR that shows it |
| Source | **Me**, **AI**, or **both** |

At least **2 rows** must involve the **AI component** (a wrong, slow or
missing answer) or the **person on the loop** (a missed alert, a wrong
approval, an operator who isn't there). Check every row against your real
code, including the ones AI suggested.

### 3. One safety assurance case

Pick the most important safety claim for your system, for example *"a
drone is never sent toward a location the validator rejected"* or *"the
operator is never shown a stale drone as live."* Argue it, in a diagram
and about a page of text:

- **Claim:** the top-level safety claim.
- **Argument:** how you'll show it holds (for example, by covering each
  hazard that could break it).
- **Sub-claims:** what must be true for the argument to work.
- **Evidence:** for each sub-claim, the test, oracle, fault run or code
  that supports it.

Any sub-claim **without evidence is marked undeveloped**: that's technical
debt, and saying so honestly is part of the grade.

### 4. What AI suggested, and what you thought

About half a page. Compare your first list with what AI suggested:

- Which of AI's suggestions were good, and which were wrong or generic for
  *your* system?
- What did AI miss that you had thought of?
- What angles did it raise that you hadn't considered?
- What does that tell you about using AI for safety analysis?

### 5. Contribution map

About half a page: your issues, PRs and reviews, grouped by component,
with links, and one line on what you decided in each. Paired work is fine:
say so, and say what you drove.

**Write it yourself.** AI may suggest failure modes and critique a draft;
the analysis, the judgments and the writing are yours. Your defense starts
from it.

### How the safety case is graded

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **FMECA** | 10 | Ten real failure modes, sensible ratings, mitigations located in the code, honest status, evidence linked, at least 2 rows on the AI component or the person on the loop. |
| **Assurance case** | 10 | A clear claim, a sound argument, evidence linked to each sub-claim, and undeveloped sub-claims marked as technical debt. |
| **AI vs. your thinking** | 5 | A first list committed before using AI, and a specific, honest comparison. |
| **Contribution map** | 5 | Complete, linked, honest about pairing, clear about what you decided. |
| **Total** | **30** | |

</div>

---

## The Oral Defense (finals week)

About **15 minutes**, one student at a time, with the instructor. No
slides, no AI, no notes beyond your safety case. Your team's repo, website
and running system are available to point at. Sign up for a slot (times to
follow).

It is a **conversation**, built from your safety case and your team's
system:

1. **Your safety case** (about 4 minutes): "Walk me through your
   highest-RPN row, and show me where it's handled."
2. **The system** (about 4 minutes): explain an important part of your
   team's system, including parts you didn't build.
3. **A scenario** (about 5 minutes): you reason through something that
   goes wrong. "A drone goes silent mid-approval. What does your system
   do, and how would you know?"
4. **AI and judgment** (about 2 minutes): where AI helped, where it
   failed, and what you never let it decide.

### How the defense is graded

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **Your contributions and decisions** | 15 | You explain what you did and why, consistent with your contribution map and your commits. |
| **System understanding** | 20 | You explain the team's system beyond your own part, accurately. |
| **Safety reasoning** | 20 | You reason from how the system actually works to what it would do when something fails, and what your safety case does and doesn't cover. |
| **AI and engineering judgment** | 15 | Specific, honest examples of where AI helped, failed, and where you decided. |
| **Total** | **70** | |

</div>

> **Know how your system can fail, and what stands between that failure and
> harm.**
