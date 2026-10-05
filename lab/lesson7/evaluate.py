#!/usr/bin/env python3
"""evaluate.py -- run YOUR Stages 2-4 on a scenario's clues, no simulator needed.

Each clue image is rendered the way the drone camera would see it at the
scenario's search altitude (imaging.render_view), sent through the pipeline,
and scored against the clue's ground truth:

  * relevance correct -- relevance high/medium  <=>  truth.relevant
  * action correct    -- decision.action in truth.acceptable_actions

LLM output varies run to run, so --repeat N runs every clue N times and
reports how often the runs agreed with each other, not just with the truth.

    python evaluate.py scenarios/lost-child-stadium
    python evaluate.py scenarios/lost-child-stadium --repeat 3 --clues c01 c04
    python evaluate.py scenarios/lost-child-stadium --model claude-haiku-4-5
    python evaluate.py scenarios/lost-child-stadium --save-crops data/crops
    python evaluate.py scenarios/lost-girl-pinafore --show-prompts     # also print full system prompts
    python evaluate.py scenarios/lost-girl-pinafore --quiet            # summary table only

By default every stage call is traced as it happens: the text and images sent
(images saved under data/trace/<clue>/ so you can open them), the model's
structured answer, tokens and cost, and the pipeline's own steps (closer
looks, the converge-search centre), then the clue's verdict vs ground truth.

Results are appended to hw07/clues/data/eval_runs.jsonl (one ClueAssessment per run).
"""
import argparse
import base64
import collections
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import student_code  # noqa: E402
from contract import RELEVANCE_LEVELS  # noqa: E402,F401
from llm_tools import LLMError, TracingBackend  # noqa: E402
from scenario import load_scenario  # noqa: E402

def judged_relevant(assessment):
    return assessment.relevance["relevance"] in ("high", "medium")


def save_crop(directory, name, b64):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, f"{name}.png"), "wb") as f:
        f.write(base64.b64decode(b64))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--clues", nargs="*", help="only these clue ids")
    parser.add_argument("--model", help="model for every stage (default: your ClaudeBackend's)")
    parser.add_argument("--pipeline", help="your pipeline directory (default: hw07/clues)")
    parser.add_argument("--no-closer-look", action="store_true", help="disable the inspect-closer re-render")
    parser.add_argument("--save-crops", help="directory to write the rendered crops the model sees")
    parser.add_argument("--log", default=os.path.join(student_code.DEFAULT_DIR, "data", "eval_runs.jsonl"))
    parser.add_argument("--quiet", action="store_true", help="no per-stage trace, just results")
    parser.add_argument("--show-prompts", action="store_true", help="print the full system prompt for each call")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    clues = [c for c in scenario.clues if not args.clues or c.id in args.clues]
    missing = [c.id for c in clues if not os.path.exists(scenario.image_path(c))]
    if missing:
        print(f"Skipping clues with no image yet: {', '.join(missing)}")
        clues = [c for c in clues if c.id not in missing]
    if not clues:
        sys.exit("No clues to run.")

    ClueAnalyzer, ClaudeBackend = student_code.load(args.pipeline)
    backend = ClaudeBackend(model=args.model) if args.model else ClaudeBackend()
    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    rows, total_cost = [], 0.0
    started = time.monotonic()
    trace_root = os.path.join(os.path.dirname(args.log), "trace", time.strftime("%Y%m%d-%H%M%S"))
    if not args.quiet:
        m = scenario.mission
        print(f"MISSION {m.mission_id}: looking for {m.person.name} -- {m.person.summary}")
        print(f"  last seen {m.last_seen}; search altitude {scenario.search_agl_m} m")
        print(f"  stage images saved under {trace_root}/")
    for clue in clues:
        on_event = None
        if not args.quiet:
            on_event = lambda msg: print(f"\n  >> {msg}")  # noqa: E731
        analyzer = ClueAnalyzer(backend, scenario.mission, on_event=on_event,
                                closer_look=None if args.no_closer_look else scenario.closer_look_for(clue))
        if args.save_crops:
            save_crop(args.save_crops, clue.id, scenario.candidate(clue).crop_png_b64)
            save_crop(args.save_crops, f"{clue.id}-closer", scenario.candidate(clue, zoom=6.0).crop_png_b64)
        runs = []
        for i in range(args.repeat):
            candidate = scenario.candidate(clue)
            if not args.quiet:
                analyzer.backend = TracingBackend(
                    backend, show_system=args.show_prompts,
                    image_dir=os.path.join(trace_root, clue.id + (f"-run{i + 1}" if args.repeat > 1 else "")))
                print(f"\n{'=' * 100}\nCLUE {clue.id}  run {i + 1}/{args.repeat}   image {os.path.basename(clue.image)}")
                print(f"  STAGE 1 (detect, offline oracle): candidate {candidate.candidate_id} at "
                      f"({candidate.lat:.6f}, {candidate.lon:.6f}), label '{candidate.cv_label}', "
                      f"crop {candidate.ground_m_per_px:.3f} m/px at {scenario.search_agl_m} m")
            try:
                a = analyzer.analyze(candidate)
            except LLMError as exc:
                print(f"  {clue.id} run {i + 1}: FAILED -- {exc}")
                continue
            except NotImplementedError as exc:
                sys.exit(f"\nNot implemented yet: {exc}")
            runs.append(a)
            total_cost += a.cost_usd
            with open(args.log, "a") as f:
                f.write(json.dumps({"scenario": scenario.mission.mission_id, "clue": clue.id,
                                    "truth": clue.truth.model_dump(), **a.model_dump()}) + "\n")
            rel_ok = judged_relevant(a) == clue.truth.relevant
            act_ok = a.decision['action'] in clue.truth.acceptable_actions
            print(f"\n  RESULT {clue.id} run {i + 1}: {a.object_type!r} -> relevance "
                  f"{a.relevance['relevance']}, action {a.decision['action']}  (${a.cost_usd:.4f}, {len(a.calls)} calls)")
            if not args.quiet:
                print(f"  TRUTH: {'RELEVANT' if clue.truth.relevant else 'not relevant'}, acceptable "
                      f"{clue.truth.acceptable_actions} -- {clue.truth.rationale}")
                print(f"  VERDICT: relevance {'OK' if rel_ok else 'WRONG'}, action {'OK' if act_ok else 'WRONG'}")
        rows.append((clue, runs))

    print()
    header = f"{'clue':5} {'truth':6} {'object (last run)':32} {'relevance':18} {'action':28} {'rel ok':7} {'act ok':7}"
    print(header)
    print("-" * len(header))
    rel_ok = act_ok = n = 0
    agree = []
    for clue, runs in rows:
        if not runs:
            continue
        rels = collections.Counter(a.relevance['relevance'] for a in runs)
        acts = collections.Counter(a.decision['action'] for a in runs)
        r_ok = sum(judged_relevant(a) == clue.truth.relevant for a in runs)
        a_ok = sum(a.decision['action'] in clue.truth.acceptable_actions for a in runs)
        rel_ok, act_ok, n = rel_ok + r_ok, act_ok + a_ok, n + len(runs)
        agree.append(acts.most_common(1)[0][1] / len(runs))
        fmt = lambda c: ",".join(f"{k}x{v}" if v > 1 else k for k, v in c.most_common())  # noqa: E731
        print(f"{clue.id:5} {'REL' if clue.truth.relevant else '-':6} {runs[-1].object_type[:31]:32} "
              f"{fmt(rels):18} {fmt(acts):28} {r_ok}/{len(runs):<5} {a_ok}/{len(runs):<5}")
    if n:
        print(f"\nRelevance accuracy {rel_ok}/{n} ({rel_ok / n:.0%}), action accuracy {act_ok}/{n} ({act_ok / n:.0%})")
        if args.repeat > 1:
            print(f"Action agreement across repeats: {sum(agree) / len(agree):.0%} (1.0 = every run chose the same action)")
    print(f"Cost ${total_cost:.3f}, {time.monotonic() - started:.0f} s. Log: {args.log}")


if __name__ == "__main__":
    main()
