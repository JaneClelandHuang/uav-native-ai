# Lesson 3 — Flight-Log Analysis

## Lesson Objectives

By the end of this lesson, you will have had initial experience in:

- Reading an ArduPilot dataflash log and pulling out the records that carry evidence, not the sensor exhaust.
- Recognising two common failure signatures — a GPS/position problem and either excessive vibration or compass/magnetic interference — from what they leave in the data.
- Getting a failure diagnosis out of an AI **two ways**: by having it write you an analysis program you run yourself, and by writing a prompt that returns the answer directly with no code for you to keep.
- Judging, from having done both, **which approach you would reach for** — and being able to say why in terms of effort to verify, robustness, trust, and maintainability.
- Distinguishing a conclusion the data supports from a plausible-sounding one it does not.

**The work is the comparison.** Either approach can get a right answer on a log you have already studied. The engineering question is what each one costs you when the log is new and the stakes are real.

**Budget around 8 hours.** We will work through a failure together in class first.

---

## Readings

Read this before doing the prompt element of the homework.  We will discuss in class on Thursday too.
*Prompt Engineering* by Lee Boenstra (Google), https://share.google/wBICVPdZ6qFvMoZNK 

---

## Using AI

You will use **Claude (Pro)** for this entire assignment — that is the point of it. In one track Claude writes the analysis code; in the other your deliverable *is* a prompt. Either way:

*You remain fully responsible for understanding, evaluating, and being able to explain and defend everything you submit.* In Thursday's class you will answer questions about your work on your own, without AI.

---

## The Two Failures

You will analyse **two** flight-log failures:

- **GPS / position** — required.
- **Vibration** *or* **compass / magnetic interference** — your choice.

`lab/lesson3/` has a labelled example log for each, one folder per problem, plus a **worked example** for a fourth kind of failure — a **battery failsafe** — in `battery/`: a written diagnosis, a short physics primer, and a coded (Track A) solution. Read it first — it is the model for the *depth* your own analysis and write-ups should reach. It does **not** include a prompt; that half is yours to work out. The battery case is **not** one of your two.

Before you write anything, get to know your two failures from the lab folders: extract the records, plot them, and learn each signal — its typical range, its threshold or its tell, and where it gets ambiguous. The folder READMEs say which records to pull. These are not graded; they are how you learn what your analysis has to detect.

---

## Track A — The Coded Solution

For **each** of your two failures, have Claude write you a small Python program that diagnoses that failure from an extracted log.

- Claude writes the code; **you run it locally** and read it. One script per failure — `hw03/<failure>/analyze.py`. It reads the CSV(s) `bin2csv.py` produces and prints a **verdict** (problem present / no problem / not enough data) plus the **evidence** (specific values and timestamps), and saves a **graph** of the diagnostic signal with the relevant thresholds marked.
- Keep it small: one failure, one or two plots, no CLI framework, no GUI. It is a tool you own and can re-run, not a product.
- Iterate against the labelled example log until the verdict and the graph are right, and check the numbers it prints against the raw CSV yourself.

## Track B — The Prompt Solution

For the **same two** failures, write a reusable prompt that gets the diagnosis out of Claude with **no code for you to keep**.

- One prompt per failure — `hw03/<failure>/prompt.md`. Given the extracted data from *any* log, in a **single response** it returns the same three things: verdict, graph, evidence-based explanation. "Reusable" means self-contained — you save it, and it works on the next log without you steering Claude through it.
- The prompt has to tell Claude everything: which CSV(s) and columns it is getting, how to compute the diagnostic signal, what counts as a problem (**and** what "no problem" and "not enough data" look like), what the graph shows, and how to phrase the answer — verdict first, then evidence with specific values, then confidence, then what the data *cannot* establish.
- Any code Claude runs to answer is Claude's, not yours — it is not part of the deliverable and you do not maintain it.

### How a prompt runs

1. Extract the records that failure needs, e.g. `python lab/lesson3/bin2csv.py "<log>.bin" -t VIBE --single`
2. Upload the CSV(s) to Claude.
3. Feed your saved prompt to Claude. **One shot — no follow-up messages.**
4. Claude returns the verdict, the graph, and the explanation.

### Two checks your prompt must pass

- **Reproducibility.** Run the finished prompt on the *same* log at least **three times**. Note anything that changes between runs — the verdict, the numbers, the graph, the confidence. While the exact output won't be exactly the same, the diagnosis should be consistent.
- **No false alarm.** Run it on the `battery/` log. It must not report your failure on a log that does not have it.

---

## The Retrospective

Half a page, in `hw03/REPORT.md`. Having built both solutions for both failures, compare **code vs prompt** across:

- **Effort to verify** — how much work was it to convince yourself each answer was right?
- **Robustness** — which one would you trust more on a log you have never seen, and why?
- **Trust** — where did either approach give you a confident answer that was wrong or unsupported, and how did you catch it?
- **Maintainability** — six months from now, adding a third failure type, which do you extend?
- **Reproducibility** — what did the three same-log prompt runs show?

If both approaches reached the right verdict for both failures, say so. The marks are for the reasoning, not for declaring a winner. Do this section yourself, *without AI*. 

---

## Working with Claude

- **You cannot paste a whole log.** Even after `bin2csv.py`, some records have thousands of rows. In Track A the script does the reducing; in Track B decide what the prompt asks Claude to compute and summarise before it reasons, and give it the columns it needs, not all of them.
- **Make it cite evidence.** Handed a summary, Claude will produce a confident wrong answer if you let it — for the GPS log it reaches for "the EKF drifted," which the data does not support. Require every claim to name a value or a record, and allow "I can't tell from this."
- **Handle "no problem" on purpose.** It is easy to build a detector that always finds something. Test against the healthy vibration flight and the battery log.
- **Iterate against the labelled example.** You know the right answer for the logs in `lab/lesson3/`. Run it, find where it is wrong, fix the code or the prompt, and note what fixed it.

---

## What Goes in `REPORT.md`

Keep it tight — this is *show your work briefly*, not a second assignment.

**Coded solution — one short paragraph per failure** (≈4–6 sentences): which records it reads, what it computes, the verdict it gives on the lab log, and one thing it gets wrong or cannot tell (if you experienced any errors during any stage of your homework). Reference the graph files that you have created for the analysis.

**Prompt solution — one short paragraph per failure** (≈4–6 sentences): the verdict it gives on the lab log; one earlier version of the prompt that failed, the case it failed on, and the change that fixed it; the result of the three same-log runs; and what it said on the `battery/` log.

**Retrospective — half a page** (or the ≤5-minute recording): the code-vs-prompt comparison above.

---

## How Your Work Will Be Tested

The instructor will run **both** your solutions for **both** failures on a few flight logs — some you have seen, some you have not (but with very similar failures), including at least one clean flight and the battery case. For each we check:

- **Right verdict** — including "no problem" when there is none, and not inventing one.
- **Grounded explanation** — does it point at real values in the log, or hand-wave.
- **One shot** (Track B) — the prompt works as saved, with no follow-up.

Your solutions are judged on the unseen logs too, so do not tune them to the examples.

---

## How This Is Graded

Out of **100 points**.

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **`README.txt`** — how to run your code, and your prompt filenames | 5 | Your programs must be self-contained. Put a `README.txt` in your `hw03/` folder with the exact commands to run each `analyze.py` and the names of your prompt files. If I have to install anything, include a `requirements.txt` in `hw03/` and say so. All run instructions go in `README.txt`. |
| **Coded solutions** (both failures) + write-ups | 30 | Two small programs that read the right records, compute the diagnostic signal, reach the right verdict on the example log (including "can't tell" where honest), and produce a clear thresholded graph. Plus the two short paragraphs in `REPORT.md`. |
| **Prompt solutions** (both failures) + write-ups | 30 | Two reusable prompts that specify input, computation, decision rule (including "none" and "can't tell"), graph, and explanation well enough to run one-shot on an unseen log. Plus the two short paragraphs, the three-run reproducibility check, and the battery false-alarm check. |
| **Retrospective** — code vs prompt | 15 | An honest half-page comparing the two approaches across effort to verify, robustness, trust, maintainability, and reproducibility — grounded in what actually happened when you built them. |
| **Individual understanding** — in class | 20 | See below. |
| **Total** | **100** | |

</div>

### Individual understanding

Because AI did part of this work, being able to explain it is graded directly. In **Thursday's class** you will get a few questions — for example: why your GPS analysis looks at `POS` versus `GUIP` rather than the GPS numbers; what your prompt says on a log with two problems at once; when you would reach for the coded solution over the prompt for a brand-new failure type — and answer them **on your own, without AI**.

---

## Deliverable

```text
hw03/
├── gps-position/
│   ├── analyze.py     Track A — the program Claude wrote, that you run
│   ├── <graph>.png    what analyze.py produces
│   └── prompt.md      Track B — your reusable prompt
├── <vibration | compass-mag>/
│   ├── analyze.py
│   ├── <graph>.png
│   └── prompt.md
├── README.txt         how to run each analyze.py + your prompt filenames
├── requirements.txt   only if your code needs anything beyond lab/lesson3's
└── REPORT.md          two coded write-ups + two prompt write-ups + the retrospective
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

- Which records and fields carry the signal for each of your two failures, and what distinguishes the failure from a clean flight.
- What each solution returns on a clean flight and on the battery log.
- Where each solution is unreliable, and the case that would break it.
- For a new failure type: whether you would write a prompt or have Claude code a tool, and why.

> **Be able to explain why a solution reaches the verdict it does — and where it shouldn't be trusted.**
