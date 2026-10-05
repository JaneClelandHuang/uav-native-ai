#!/usr/bin/env python3
"""check_set.py -- is a test set (scenario + clue_sets.csv row) well formed?

    python check_set.py scenarios/lost-girl-pinafore                       # Lily, against lab/lesson7/clue_sets.csv
    python check_set.py ../../hw07/scenarios/<your-set> --csv ../../hw07/clue_sets.csv

The rule a set encodes: a clue is relevant ONLY for the person whose row in
clue_sets.csv lists it. Every other clue (shared decoys, other people's
clues) is not relevant for that person. Checks:

  * the row exists (its `scenario` column names this scenario's folder)
  * the person image exists in the GUI and is the scenario's target
  * every listed clue is in the scenario, and each clue's truth.relevant
    matches the row; at least 2 relevant clues and 3 decoys
  * every clue image exists, is a PNG with real transparency, and
    converge_search is only acceptable for relevant clues
  * scene_scale is set (sim icons are drawn larger than life)
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image  # noqa: E402

from scenario import load_scenario  # noqa: E402

GUI_SCENE = os.path.normpath(os.path.join(HERE, "..", "..", "gui", "src", "data", "scene"))


def load_rows(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["relevant_clues"] = [c.strip() for c in row["relevant_clues"].split(";") if c.strip()]
    return rows


def check(scenario_dir, csv_path, gui_scene=GUI_SCENE):
    """Returns a list of problems (empty = OK)."""
    problems = []
    scenario = load_scenario(scenario_dir)
    name = os.path.basename(os.path.normpath(scenario_dir))
    rows = [r for r in load_rows(csv_path) if r["scenario"] == name]
    if len(rows) != 1:
        return [f"{csv_path}: expected exactly one row with scenario == {name!r}, found {len(rows)}"]
    row = rows[0]
    if scenario.target is None:
        problems.append("scenario.json has no target (the person)")
    elif scenario.target.image != row["person_image"]:
        problems.append(f"target image {scenario.target.image} != csv person_image {row['person_image']}")
    if os.path.isdir(gui_scene) and not os.path.exists(os.path.join(gui_scene, row["person_image"])):
        problems.append(f"person image {row['person_image']} not found in {gui_scene}")
    if scenario.scene_scale <= 1.0:
        problems.append("scene_scale should be set (about 9 for icons drawn at the people scale)")
    files = {os.path.basename(c.image): c for c in scenario.clues}
    for listed in row["relevant_clues"]:
        if listed not in files:
            problems.append(f"set clue {listed} is not in the scenario")
    for fname, clue in files.items():
        expected = fname in row["relevant_clues"]
        if clue.truth.relevant != expected:
            problems.append(f"{clue.id} ({fname}): truth.relevant should be {expected}")
        if not expected and "converge_search" in clue.truth.acceptable_actions:
            problems.append(f"{clue.id}: converge_search can't be acceptable for a decoy")
        path = scenario.image_path(clue)
        if not os.path.exists(path):
            problems.append(f"{clue.id}: missing image {clue.image}")
            continue
        with Image.open(path) as im:
            if im.format != "PNG" or "A" not in im.getbands() or im.getchannel("A").getextrema()[0] > 0:
                problems.append(f"{clue.id}: {fname} needs a transparent background (PNG with alpha)")
    n_rel = sum(c.truth.relevant for c in scenario.clues)
    if n_rel < 2:
        problems.append(f"only {n_rel} relevant clue(s); need at least 2")
    if len(scenario.clues) - n_rel < 3:
        problems.append(f"only {len(scenario.clues) - n_rel} decoy(s); need at least 3")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario")
    parser.add_argument("--csv", default=os.path.join(HERE, "clue_sets.csv"))
    args = parser.parse_args()
    problems = check(args.scenario, args.csv)
    for p in problems:
        print("PROBLEM:", p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
