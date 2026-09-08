# Lesson 3 — Flight-Log Analysis

## Lesson Objectives

By the end of this lesson, you will have had initial experience in:

- Reading an ArduPilot dataflash log and pulling out the records that carry evidence, not the sensor exhaust.
- Recognising three common failure signatures — excessive vibration, GPS/position problems, and compass/magnetic interference — from what they leave in the data.
- Writing **reusable prompts** that diagnose a failure from a flight log in one shot: a verdict, a graph, and an evidence-based explanation, with no follow-up steering.
- Validating a prompt against logs it has not seen, and being honest about where it is uncertain or wrong.
- Distinguishing a conclusion the data supports from a plausible-sounding one it does not.

There is almost no code to write this week. You will run a small helper to turn a log into CSV, and everything else happens in Claude. **The work is the prompting** — can you observe a failure, understand it, and specify it precisely enough that a prompt diagnoses it reliably on *any* log, not just the one you tested?

**Budget around 6 hours.** We will start by working through the lab examples together in class.

---

## Readings

Prompt Engineering by Lee Boenstra (Google), https://share.google/wBICVPdZ6qFvMoZNK

---

## Using AI

You will use **Claude (Pro)** for this entire assignment — that is the point of it. Your deliverable *is* a set of prompts.

*You remain fully responsible for understanding, evaluating, and being able to explain and defend everything you submit.* In Thursday's class you will answer questions about your prompts on your own, without AI.

Include a short `hw03/AI_USE.md` (half a page to three pages):

- **Where and how** you used Claude beyond the prompts themselves — understanding the signatures, drafting, debugging your prompts.
- **Where it helped**, with concrete examples.
- **Where it didn't** — where it gave you a confident wrong answer, and how you noticed.
- **Insights** — what you learned about getting reliable behaviour out of a prompt.

---

## The Lab Examples

Before you write anything, get to know the three failures. `lab/lesson3/` has real flight logs, one folder per kind of problem, each with a README explaining which records to pull and what to look at:

```text
lab/lesson3/
├── vibration/       a healthy flight, then a session where vibration climbs
├── gps-position/    a flight told to climb that drifted sideways instead
├── compass-mag/     one compass reading the motors instead of the Earth
├── battery/         a battery failsafe — NOT one of your three, a compare-against case
├── bin2csv.py       dumps a .bin to CSV, one file per record type
└── requirements.txt
```

Install the helper's dependencies once:

```bash
pip install -r lab/lesson3/requirements.txt
```

Work through the examples: extract the records with `bin2csv.py`, plot them, and get a feel for each signal — its typical range, its threshold, and where it gets ambiguous. Use Claude to write the plotting code, then check it against the raw CSV. `battery/` is not one of your three — it is there to make sure your prompts do not false-alarm on a problem outside their scope.

These are not graded. They are how you learn what your prompts have to detect.

---

## The Assignment

Write **three reusable prompts**, one for each failure type:

1. **Vibration**
2. **GPS / position**
3. **Compass / magnetic interference**

Each prompt takes the extracted data from *any* flight log and, in a single response, produces:

- a **verdict** — problem present, no problem, or not enough data to tell;
- a **graph** of the diagnostic signal, with the relevant thresholds marked;
- an **explanation** — what was found, in which records, with specific values, and how confident it is.

"Reusable" means self-contained: you save the prompt, and it works on the next log without you steering Claude through it.

---

## How a Prompt Runs

The workflow your prompt is written for:

1. Extract the records that problem needs:

   ```bash
   python lab/lesson3/bin2csv.py "<some-log>.bin" -t VIBE --single
   ```

2. Upload the resulting CSV(s) to Claude.
3. Paste your saved prompt. **One shot — no follow-up messages.**
4. Claude returns the verdict, the graph, and the explanation.

Your prompt has to tell Claude everything it needs: which files it is getting, how to compute the diagnostic signal from them, what counts as a problem, what the graph should show, and how to phrase the answer.

---

## What Each Prompt Must Specify

- **Input contract** — which CSV(s) and columns it expects, named exactly.
- **Computation** — how to derive the diagnostic signal (for example: the largest of `VibeX/VibeY/VibeZ` at each moment; field magnitude `sqrt(MagX² + MagY² + MagZ²)` for each compass; distance from home from `POS` against `ORGN`).
- **Decision rule** — the threshold, the correlation strength, or the comparison that separates "problem" from "fine" — **and** what "no problem" and "not enough data" look like, explicitly.
- **Graph** — what to plot, threshold lines, what to annotate.
- **Explanation** — verdict first, then the evidence (specific numbers and timestamps), then confidence, then what the data *cannot* establish.
- **Robustness** — it must not invent a problem on a log that does not have this one, and it must stay in its lane when a *different* problem is present.

---

## The Three Prompts

| Prompt | Records it works from | What makes it hard |
|---|---|---|
| **Vibration** | `VIBE` | Threshold logic, but "healthy" is not zero, and ArduPilot's own vibration failsafe never fires in these logs — the prompt cannot wait for an error. It must not flag the clean flight. |
| **Compass / magnetic** | `MAG`, `CTUN`, `BAT` | The diagnosis is relational: compute the field magnitude for all three compasses, compare them, and correlate the bad one with throttle or current. There is no single number to threshold. |
| **GPS / position** | `POS`, `GUIP`, `ORGN`, `GPS`, `ERR` | The signature is *not* a bad GPS number — HDOP can look fine and there can be zero errors. It needs `POS` vs `GUIP` and the two `ORGN` records, and the honest verdict includes "the log cannot establish the root cause." |

Start with vibration. GPS/position is the one that will fight you.

---

## Working with Claude

- **You cannot paste a whole log.** Even after `bin2csv.py`, some records have thousands of rows. Decide what your prompt asks Claude to compute and summarise before it reasons — and give it the columns it actually needs, not all of them.
- **Ask for the answer in a fixed shape.** Verdict, then evidence, then confidence, then limits. A reader — and a grader — should be able to skim it the same way every time.
- **Make it cite evidence.** A prompt handed a summary will produce a confident wrong answer if you let it (for the GPS log it will reach for "the EKF drifted," which the data does not support). Require every claim to name a value or a record, and allow "I can't tell from this."
- **Handle "no problem" on purpose.** It is easy to write a prompt that always finds something. Test each prompt on the healthy vibration flight and on the battery log.
- **Iterate against the labelled examples.** You know the right answer for every log in `lab/lesson3/`. Run your prompt, find where it is wrong, and fix the prompt — or fix what you feed it — and record which change fixed it.

---

## The Engineering Process

Work through it in this order: **Analyse → Draft → Test & Iterate → Validate → Reflect**

### 1. Analyse

From the lab examples, work out for each failure: which records and fields carry the signal, what distinguishes it (a threshold, a trend, a correlation, a gap between commanded and actual), and what a clean flight and a *different* failure look like.

### 2. Draft

Write a first version of each prompt against the spec above. Save each one as a file — this is your submission.

### 3. Test & Iterate

Run each prompt in Claude against its example log(s). Where it is wrong — wrong threshold, misread column, hallucinated finding, wrong graph, over- or under-diagnosis — change the prompt and run it again. Then run it on the *healthy* vibration flight and on a log for a *different* problem, and make sure it does not misfire. Keep the versions that failed and note what fixed each.

### 4. Validate

Build a table in `hw03/VALIDATION.md`: each prompt against every log in `lab/lesson3/` (including `battery/` and the healthy flight) and against the holdout log the instructor provides. For each: what the prompt returned, the right answer, whether it matched, and — for the misses — what you think went wrong. Include the graphs Claude generated.

### 5. Reflect

Submit `hw03/REFLECTION.md` (about a page) **or** a recording of at most 5 minutes (link or file in that file). Cover: prompts you tried that did not work, how you told a prompt problem apart from a data problem, what you changed, and where your prompts still fall short. Do this yourself, without AI.

---

## How Your Prompts Will Be Tested

The instructor will run your three prompts on a set of flight logs — some you have worked with, some you have not, including at least one clean flight and the battery case. For each we check:

- **Did it reach the right verdict** — including "no problem" when there is none, and not inventing one.
- **Is the explanation grounded** — does it point at real values in the log, or is it hand-waving.
- **Is it one shot** — the prompt has to work as saved, with no follow-up.

Your prompts are judged on the unseen logs as well as the examples, so do not tune them to the four you have.

---

## How This Is Graded

The assignment is graded out of **100 points**.

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **The three prompts** | 40 | Prompts that specify their input, computation, decision rule (including "none" and "can't tell"), graph, and explanation clearly enough to run reliably on an unseen log. |
| **Development & iteration** — `PROMPTS.md` | 15 | For each prompt: the final version, an earlier version that failed with the case it failed on and the fix, and why it is structured the way it is. |
| **Validation** — `VALIDATION.md` | 20 | The full test matrix against every lab log plus the holdout, the generated graphs, and honest analysis of the misses. |
| **Robustness on the holdout** | 10 | Correct verdicts on logs you did not develop against — no false positives, handles "none". |
| **AI Use** — `AI_USE.md` | 5 | Specific reflection on where AI helped, where you challenged or rejected it, and how you verified its work. |
| **Individual understanding** — in class | 10 | See below. |
| **Total** | **100** | |

</div>

### Individual understanding

Because the AI's output is part of what you submit, being able to explain your own prompts is graded directly. In **Thursday's class** you will get a few questions — for example: why your vibration prompt asks for the summary it does, what your GPS prompt says on a log with two problems at once, how you know a given verdict is not the model bluffing — and answer them **on your own, without AI**.

---

## Deliverable

```text
hw03/
├── prompts/
│   ├── vibration.md
│   ├── gps-position.md
│   └── compass-mag.md
├── PROMPTS.md        (final + one failed earlier version each + the fix + rationale)
├── VALIDATION.md     (the test matrix + the generated graphs + analysis of the misses)
├── REFLECTION.md     (the discussion, or a link/file for a ≤5-min recording)
└── AI_USE.md
```

Commit and push:

```bash
git add .
git commit -m "Complete HW03"
git push
```

---

## Before You Submit

Be ready to explain:

- Why each prompt asks Claude for the computation and the summary it does.
- What each prompt returns on a clean flight, and on the battery log.
- Where each prompt is unreliable, and the case that would break it.
- What you would change to add a fourth failure type.

> **Be able to explain why a prompt reaches the verdict it does — and where it shouldn't be trusted.**
