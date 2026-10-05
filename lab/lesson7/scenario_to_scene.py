#!/usr/bin/env python3
"""scenario_to_scene.py -- place a scenario's clues in new-gui.

Writes a new-gui saved scene (src/data/scene/saved/<name>.json) with every
clue (and the missing person, if the scenario has a "target") at its lat/lon
and width_m, and copies the clue images into new-gui's
scene palette (src/data/scene/clues/). Then in new-gui: Scene Builder ->
toggle the saved scene on.

    python scenario_to_scene.py scenarios/lost-girl-pinafore            # into this repo's gui/
    python scenario_to_scene.py ../../hw07/scenarios/<your-set>         # your own set
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from scenario import load_scenario  # noqa: E402

DECOY_DIR = os.path.join(HERE, "decoys")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario")
    parser.add_argument("--new-gui", default=os.path.normpath(os.path.join(HERE, "..", "..", "gui")),
                        help="the GUI checkout (default: this repo's gui/)")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    scene_dir = os.path.join(args.new_gui, "src", "data", "scene")
    if not os.path.isdir(scene_dir):
        sys.exit(f"Not a new-gui checkout: {scene_dir} not found")
    clue_dir = os.path.join(scene_dir, "clues")
    os.makedirs(clue_dir, exist_ok=True)

    objects, skipped = [], []
    for z, clue in enumerate(scenario.clues):
        src = scenario.image_path(clue)
        if not os.path.exists(src):
            skipped.append(clue.id)
            continue
        # shared decoys (lab/clues/decoys/) go to new-gui's clues/decoys/, scenario icons to clues/
        sub = "clues/decoys" if os.path.dirname(os.path.abspath(src)) == DECOY_DIR else "clues"
        os.makedirs(os.path.join(scene_dir, sub), exist_ok=True)
        shutil.copy2(src, os.path.join(scene_dir, sub, os.path.basename(src)))
        objects.append({"image": f"{sub}/{os.path.basename(src)}", "lat": clue.lat, "lon": clue.lon,
                        "width_m": clue.width_m, "z_order": z})

    if scenario.target is not None:   # the person: an image already in new-gui's palette
        t = scenario.target
        if not os.path.exists(os.path.join(scene_dir, t.image)):
            print(f"Warning: target image {t.image} not found in {scene_dir}")
        objects.append({"image": t.image, "lat": t.lat, "lon": t.lon, "width_m": t.width_m,
                        "z_order": len(objects)})

    name = scenario.mission.mission_id
    os.makedirs(os.path.join(scene_dir, "saved"), exist_ok=True)
    out = os.path.join(scene_dir, "saved", f"{name}.json")
    with open(out, "w") as f:
        json.dump({"name": name, "objects": objects}, f, indent=2)
    print(f"Wrote {out} with {len(objects)} objects; clue images in {clue_dir}")
    if skipped:
        print(f"Skipped (no image yet): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
