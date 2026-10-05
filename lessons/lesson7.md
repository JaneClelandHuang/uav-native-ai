# Lesson 7 — Onboard Intelligence: Perceive → Reason → Act

## Lesson Objectives

Add a lightweight reasoning capability that takes what the UAV perceives,
reasons about it in mission context using AI, and proposes an action —
producing a structured proposed action rather than directly controlling
flight behavior. Deterministic software and safety constraints remain
responsible for whether and how that action executes.

By the end of this lesson, you will have:

- Seen why a detector alone can't search for a person: YOLO can say "teddy
  bear", but not "Lily's teddy bear". Whether a found object matters depends
  on who is missing.
- Built a staged LLM pipeline that describes a found object, judges whether
  it is evidence for *this* missing person, and proposes one action from a
  fixed menu, with every stage's answer constrained by a schema.
- Called the Anthropic API directly: images, system prompts, structured
  output, effort, stop reasons, retries and cost.
- Measured the pipeline against ground truth, on test data you designed,
  and traced a wrong answer back to the stage that caused it.
- Connected it to your HW6 planner, so the AI's proposal goes through the
  same validator as a human's.

**Native AI focus — Engineering an LLM Reasoning Pipeline.** Treat LLM
reasoning as an engineered software capability with explicit inputs,
outputs, stages, and constraints: *LLM reasoning proposes. Deterministic
software constrains. Flight control executes.*

---

## Readings

Optional Reading:

- Cleland-Huang et al., *Cognitive Guardrails for Open-World Decision Making
  in Autonomous Drone Swarms* (arXiv:2505.23576, 2025). Read Sections 1 and 3
  and Table 1 (the clue-reasoning pipeline). Skim Section 4 (the guardrails;
  we come back to them in the project): https://arxiv.org/abs/2505.23576

Some relevant Anthropic documentation:

- Vision (sending images): https://platform.claude.com/docs/en/build-with-claude/vision
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort
- API errors: https://platform.claude.com/docs/en/api/errors
- The Python SDK: https://github.com/anthropics/anthropic-sdk-python

---

## In Class

**Tuesday:** Reading the clues. Why a search needs reasoning about objects no
detector was trained to judge; the CAIRN pipeline; our five stages and the
code behind them; one real API call, line by line; what it costs and how it
fails. Then the first results on Lily's set, including the clue the pipeline
got wrong and how the trace showed why.

**Test Data:** You start your own test set (a missing person, their
clues and decoys) and swap it with a neighbor to look for clues that are too
easy or labels you'd argue about. Then a debugging lab: given a trace with a
wrong final action, find the first stage whose answer was wrong.

---

## Homework

**HW7 — Engineer an LLM Clue-Reasoning Pipeline.** A search drone finds
things before it finds people: a teddy bear, a dropped cardigan, a man's
shoe. You build the pipeline that decides what each one means for *this*
search, prove it works on test data you designed, and wire its proposals
into your HW6 planner.

**HW7 covers two weeks.** It is worth **150 points**, is due **Wednesday,
Oct. 14**, and ends with a **5-minute presentation in class on Thursday,
Oct. 15**. There is no HW8. Budget around **10–13 hours** in total. If you
can't finish, document unfinished work as technical debt in `report.md`.

Pull first (`git pull`) to get `lab/lesson7/` and the updated GUI (clue
icons in the Scene Builder).

---

### Why this week, why now

Last week a human chose the response and your software checked whether it
could happen. This week the proposal comes from a language model. Two things
change.

First, the model's answer is **uncertain evidence**, like a 0.31 YOLO
detection, except it is fluent and confident. The CAIRN paper shows the
same question about the same bike getting opposite answers. So the pipeline
needs structure: stages with explicit inputs and outputs, answers forced into
a schema, and a test set that tells you how often it is right and how often
it agrees with itself.

Second, the model must stay **inside the fence you built last week**. It
proposes one action from a fixed menu. It never writes coordinates. Your
validator decides whether the proposal can happen, exactly as it did for the
operator.

---

### What you're given

Everything is in `lab/lesson7/`; its [README](../lab/lesson7/README.md) lists every file.

| File | What it is |
|---|---|
| `contract.py` | The fixed interface: `Candidate` in, `ClueAssessment` out, the action menu. |
| `starter/` | The skeleton of your pipeline. **Copy it to `hw07/clues/`.** Signatures and docstrings, with `TODO`s. |
| `llm_tools.py` | Image blocks, API key loading, prices, `LLMError`, **`FakeBackend`** for unit tests, **`TracingBackend`**. |
| `evaluate.py` | Runs your pipeline on a scenario's clues without the simulator, renders each clue the way the drone camera sees it, traces every model call, and scores the answers against ground truth. `--repeat N` measures agreement. |
| `detector.py` | Stage 1 in flight. Finds objects in camera frames (`--oracle`: from the scenario's known clue positions), geolocates them, runs your pipeline, publishes on `mission/clues`. |
| `inject_clue.py` | Publishes a fake proposal on `mission/clues`, for building R7 before your pipeline works. |
| `scenarios/lost-girl-pinafore/` | **Lily's set**: her description as last seen, her teddy bear and cardigan, and three decoys. |
| `decoys/`, `icon_kit.py` | Shared decoys, and helpers for drawing your own transparent top-down icons. |
| `check_set.py`, `scenario_to_scene.py` | Check a test set; place it in the GUI's Scene Builder. |

Stage 1 (detecting objects) is given. Your work starts at Stage 2.

```
camera ─► Stage 1: detect (given) ─► Candidate ─► YOUR PIPELINE ──────────────────────► ClueAssessment
                                                  Stage 2 describe  (VLM, no mission)       │ mission/clues
                                                  Stage 3 relevance (vs. the person)        ▼
                                                  Stage 4 decide    (one action)       YOUR HW6 PLANNER
                                                                                       validator ─► flight
```

---

### What you build

#### Requirements

**R1 Three stages, explicit inputs and outputs.** Describe (what is this
object?), Relevance (is it evidence of *this* person?), Decide (one action
from the menu). Each stage is a function in `stages.py` with its own system
prompt in `prompts/` and its own **schema you design** in `messages.py`.
Describe must never see who is missing. You decide what else each stage
sees, and justify it in `design.md`.

**R2 Your Anthropic backend.** Implement `ClaudeBackend.generate()` in
`llm.py`, the only place your code calls the API. It sends the image and
text blocks with the stage's system prompt, uses **structured output** with
your schema, chooses an effort level per stage, checks why the response
stopped before trusting it, retries once on a missing, cut-off, declined or
invalid answer, and otherwise raises `LLMError`. It returns a `StageCall`
with tokens, latency and cost. Tuesday's slides walk through an example
`ClaudeBackend` line by line; recreate it, and make sure you can explain
every line.

**R3 The contract.** `ClueAnalyzer.analyze()` returns a `ClueAssessment`
(`contract.py`) with the action drawn from the fixed menu: `ignore`,
`log_only`, `inspect_closer`, `converge_search`. A converge needs a
`search_radius_m` from the model and a `search_center` from **your code**:
the candidate's position. The model never writes coordinates.

**R4 One closer look.** When Describe can't tell, or Decide picks
`inspect_closer`, take one zoomed look (`closer_look`) and re-run the stages.
At most once per object, so the pipeline always ends. In flight there is no
closer look in your process; an `inspect_closer` proposal goes to the planner.

**R5 Your test set.** Create a new missing person with their own clues:
- a person image from the GUI's `people/` folder, and their description *as
  last seen*, written before you draw the clues;
- **at least 2 relevant clues** (things they carried, wore or dropped) and
  **at least 3 decoys** (the shared ones count; one near miss is encouraged:
  right color, wrong size or kind);
- every clue a top-down PNG with a transparent background at the people
  scale (see `icon_kit.py`, or generate and clean up images);
- `hw07/scenarios/<your-set>/scenario.json` with ground truth (relevant,
  acceptable actions, one-line rationale) and a row in `hw07/clue_sets.csv`.
  `check_set.py` must report OK.

**R6 Evaluation and one traced failure.** Run `evaluate.py --repeat 3` on
Lily's set and on yours. Report relevance accuracy, action accuracy,
agreement across repeats and cost. Then take **one wrong answer** (yours, or
one you provoke), find the **first stage** whose answer was wrong from the
trace, fix it (prompt, schema or what the stage is shown), and show before
and after. Your code will also be run on Lily's set and on classmates' sets.

**R7 Planner hookup.** Your HW6 planner subscribes to `mission/clues` and
turns each proposal into one of its own actions, marked as decided by the
AI. Every proposal goes through **your validator**, and the verdict is
reported on `mission/action_result`, as for the operator:

| Proposal | Becomes |
|---|---|
| `inspect_closer` | `hover_stream` over the clue |
| `converge_search` | `circle_stream` around the search centre, radius clamped by the validator |
| `ignore`, `log_only` | no flight; logged |

Use `inject_clue.py` to develop this before your pipeline works. If your HW6
planner doesn't fly, write a minimal responder with a validator and a
`circle`/`hover` executor instead, and say so in `report.md`.

**R8 Unit tests.** With `FakeBackend`, no API key: what each stage sends
(Describe never contains the person's details), the closer look happening at
most once, the converge centre coming from the candidate, and how the
pipeline handles a failed stage.

#### Out of scope

- Getting YOLOE to detect the clues (use `--oracle`; it's fine to explore).
- More than one UAV converging; abort; restart.
- The CAIRN guardrails beyond your validator (advocates, Bayesian strategy
  updates, human approval rules). They come back in the project.

---

### Calling Claude

You will need a key: `ANTHROPIC_API_KEY` in your environment or in a `.env`
file at the repo root (it is gitignored; **never commit a key**). Your key
has a spending limit. One full evaluation of a 5-clue set costs about
$0.10; with `--repeat 3` about $0.35. Use `claude-haiku-4-5` while you
iterate on code paths and the default model for the numbers you report.

---

### Design first

Before writing code, put in `design.md`:

1. **Each stage's contract**: inputs, what it is deliberately *not* shown,
   your schema with a sentence on each field, and the field order.
2. **One sequence diagram** (Mermaid is fine): candidate → describe → closer
   look → relevance → decide → `mission/clues` → planner → validator →
   flight.
3. **Your decision policy**: which relevance leads to which action, and why
   converge_search should be rare.
4. **Your test set**: who, the description, and why each decoy is there.

Keep it honest as you build. If the code ends up different, update the design
and say what changed and why.

---

### Testing

- **Unit tests** (no API, no simulator): R8, in `hw07/clues/tests/`. Start
  from `starter/tests/test_example.py`.
- **Evaluation** (API, no simulator): R6, with the tables in `report.md`.
- **Integration** (simulator + broker + your planner): two runs are required.
  - `inject_clue.py` sends a `converge_search` → your validator approves →
    the UAV circles the centre → `COMPLETED`.
  - `detector.py --oracle` over **your** set in the GUI → real proposals on
    `mission/clues` → verdicts on `mission/action_result`.

Put the commands, output and what you observed in `report.md`.

---

### Presentation (Thursday, Oct. 15)

**Five minutes**, slides or a live demo:

1. Your integrated system
2. Choose whatever you want to showcase from the work you've done in this half of the semester.
3. Consider recording video snippets instead of running anything live 

Put the slides (or a link) in `hw07/`.

---

### How This Is Graded

Out of **150 points**.

<div class="table-wrap" markdown="1">

| Component | Points | What earns the points |
|---|---:|---|
| **Design** | 20 | `design.md`: stage contracts and schemas, the sequence diagram, a justified decision policy, and code that matches it (or says where and why it doesn't). |
| **Pipeline & LLM calls** | 25 | R1–R4: three working stages, Describe blind to the mission, structured output, a backend that checks stop reasons, retries once and reports cost; the contract met; one closer look at most. |
| **Test set** | 15 | R5: a well-formed set (`check_set.py` OK) with relevant clues and decoys that genuinely test the pipeline. |
| **Evaluation & debugging** | 25 | R6: accuracy, agreement and cost on Lily's set and yours; one failure traced to its first wrong stage and fixed, with before/after. |
| **Planner hookup** | 25 | R7: proposals from `mission/clues` go through your validator, verdicts are reported, `hover`/`circle` fly; both integration runs in `report.md`. |
| **Unit tests** | 10 | R8 with `FakeBackend`. |
| **Presentation** | 15 | Five minutes on Oct. 15 |
| **Reflection** | 15 | `reflection.md`: where the model surprised you, what you would never let it decide, and a "Lessons Learned" section about using Claude to build this. |
| **Total** | **150** | |

</div>

---

### Deliverable

```text
hw07/
├── clues/                 your pipeline (from lab/lesson7/starter): llm.py, messages.py,
│                          stages.py, pipeline.py, prompts/, tests/
├── scenarios/<your-set>/  scenario.json and your clue images
├── clue_sets.csv          your set's row
├── design.md              stage contracts, sequence diagram, decision policy, test set
├── report.md              evaluation tables, the traced failure, integration evidence,
│                          where your planner hookup lives, technical debt
├── reflection.md          text, and/or a recording (include the URL)
└── slides                 your presentation, or a link
```

Your planner hookup (R7) can stay in your `hw06/` planner; say in `report.md`
which files changed.

```bash
git add hw07 hw06
git commit -m "Complete HW07"
git push
```

Check that no API key is in what you commit: `git diff --cached | grep -i sk-ant`
should print nothing.

---

### Before You Submit

Be ready to explain:

- What each stage sees, what it doesn't, and why.
- What happens, line by line, when your `ClaudeBackend` gets a refusal, a
  cut-off answer, or an answer that doesn't fit the schema.
- Where the converge-search centre comes from, and why not from the model.
- Which stage your traced failure started in, and how you could tell.

> **The model proposes *what* a clue means. Your software decides whether
> anything happens because of it.**
