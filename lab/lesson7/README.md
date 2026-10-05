# lab/lesson7 — HW7 starter kit: the clue-reasoning pipeline

The HW7 spec is on the [Lesson 7 page](../../lessons/lesson7.md#homework). This folder holds
what you're given. Your own code goes in `hw07/clues/`.

```bash
pip install -r lab/lesson7/requirements.txt
cp -r lab/lesson7/starter hw07/clues            # from the repo root: your pipeline starts here
cd hw07/clues && python -m unittest discover tests
```

## Given (don't edit)

| File | What it is |
|---|---|
| `contract.py` | The fixed interface: `Candidate` in, `ClueAssessment` out, `StageSpec` (how you declare a stage), `StageCall`, `ACTIONS`. |
| `llm_tools.py` | `image_block`, `load_api_key`, `PRICES`/`cost_usd`, `LLMError`, **`FakeBackend`** (scripted answers for unit tests), **`TracingBackend`** (prints every call). |
| `evaluate.py` | Runs YOUR pipeline on a scenario's clues without the simulator and scores it against ground truth. Traces every stage call; `--repeat N` measures agreement; reports tokens and cost. |
| `detector.py` | Stage 1 in flight: reads camera frames over MQTT, finds objects (`--oracle`, or YOLOE), geolocates them, runs YOUR pipeline, publishes on `mission/clues`. |
| `inject_clue.py` | Publishes a fake `ClueAssessment` on `mission/clues`, for building your planner hookup (R7) without a working pipeline. |
| `scenario.py`, `imaging.py` | Load a scenario; render each clue the way the drone camera sees it at search altitude, and 6× zoomed. |
| `check_set.py` | Checks a test set: images, transparency, ground truth vs. `clue_sets.csv`. |
| `scenario_to_scene.py` | Places a scenario's clues (and the person) in the GUI's Scene Builder. |
| `icon_kit.py` | Helpers for drawing transparent top-down icons at the people scale. |
| `scenarios/lost-girl-pinafore/` | Lily's set: description, 2 relevant clues, 3 decoys, ground truth. |
| `decoys/` | Shared decoys (man's shoe, doll, soccer ball). |
| `clue_sets.csv` | Which clues belong to which person. |
| `starter/` | The skeleton you copy to `hw07/clues/`. |

## The contract

```python
# your hw07/clues/pipeline.py
class ClueAnalyzer:
    def __init__(self, backend, mission, closer_look=None, on_event=None): ...
    def analyze(self, candidate: Candidate) -> ClueAssessment: ...

# your hw07/clues/stages.py -- each stage declared once
DESCRIBE = StageSpec("describe", Description, effort="low")    # name = prompts/describe.md

# your hw07/clues/llm.py
class ClaudeBackend:
    def __init__(self, model=None, client=None): ...
    def generate(self, spec, system, content) -> (parsed, StageCall): ...   # uses spec.schema, spec.effort
```

`ClueAssessment` holds your stage outputs as dicts, with any fields you design, except:
`relevance["relevance"]` ∈ high / medium / low / none, `decision["action"]` ∈
`ignore` / `log_only` / `inspect_closer` / `converge_search`, and for a converge,
`decision["search_radius_m"]` plus `search_center` (the candidate's position, set by your code).

On MQTT, `mission/clues` carries `ClueAssessment.model_dump_json()` (QoS 1).

## Running

```bash
cd lab/lesson7
python evaluate.py scenarios/lost-girl-pinafore                 # trace every call, then a score table
python evaluate.py scenarios/lost-girl-pinafore --repeat 3 --quiet
python evaluate.py ../../hw07/scenarios/<your-set> --repeat 3
python check_set.py ../../hw07/scenarios/<your-set> --csv ../../hw07/clue_sets.csv

# in the simulator (docker compose up -d in lab/, then the GUI with camera simulation on)
python scenario_to_scene.py scenarios/lost-girl-pinafore          # Scene Builder: toggle the saved scene on
python detector.py scenarios/lost-girl-pinafore --oracle          # drones STREAMING over the clues
mosquitto_sub -t mission/clues
python inject_clue.py 41.698 -86.2382                             # fake converge_search, for R7
```

**About YOLOE.** Without `--oracle`, `detector.py` uses YOLOE (open-vocabulary YOLO) with
generic words (bag, hat, shoe, toy, …). From 25 m the clues are about 20 pixels across, and
in our tests YOLOE found the doll reliably but the teddy and cardigan only at a very low
threshold, and missed the shoe and ball. Use `--oracle` for the homework. Getting YOLOE to
work (lower altitude, zoom, `--conf`) is optional exploration, not required.
