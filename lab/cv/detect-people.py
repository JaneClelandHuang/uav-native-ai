#!/usr/bin/env python3
"""Very simple YOLO26n person-detector for reviewing frame-collection.py's
output: point it at a folder of frames and it reports which ones contain a
detected person, so you can eyeball whether the stock model catches
new-gui's simulated ("fake") people or whether it needs retraining.

Saves an annotated copy of every image (detection boxes drawn on, if any)
into <folder>/detections/, so you can flip through the results visually
instead of trusting the printed counts alone.

TEMPORARY: also sorts the original (unannotated) frame into <folder>/found/
or <folder>/not-found/ depending on whether a person was detected, for a
quick eyeball pass. Remove the "TEMPORARY" block below once that's no
longer needed.
"""
import argparse
import os
import shutil
import sys

from ultralytics import YOLO

IMAGE_EXTS = (".jpg", ".jpeg", ".png")
PERSON_CLASS = 0  # COCO class id YOLO26n's pretrained weights use for "person"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="folder of frames to scan, e.g. data/Lime-08-10-2026-001")
    parser.add_argument("--model", default="yolo26n.pt", help="model weights (default: yolo26n.pt, auto-downloaded)")
    parser.add_argument("--conf", type=float, default=0.25, help="confidence threshold (default: 0.25)")
    args = parser.parse_args()

    images = sorted(f for f in os.listdir(args.folder) if f.lower().endswith(IMAGE_EXTS))
    if not images:
        sys.exit(f"No images found in {args.folder}")

    out_dir = os.path.join(args.folder, "detections")
    os.makedirs(out_dir, exist_ok=True)

    # TEMPORARY: sort original frames into found/ vs not-found/ for a quick
    # eyeball pass. Delete this block (and the found_dir/not_found_dir
    # lines + the shutil.copy2 call below) when no longer needed.
    found_dir = os.path.join(args.folder, "found")
    not_found_dir = os.path.join(args.folder, "not-found")
    os.makedirs(found_dir, exist_ok=True)
    os.makedirs(not_found_dir, exist_ok=True)

    model = YOLO(args.model)

    hits = 0
    for name in images:
        src_path = os.path.join(args.folder, name)
        result = model(src_path, classes=[PERSON_CLASS], conf=args.conf, verbose=False)[0]
        n = len(result.boxes)
        hits += n > 0
        print(f"{name}: {n} person(s)")
        result.save(filename=os.path.join(out_dir, name))

        # TEMPORARY
        shutil.copy2(src_path, os.path.join(found_dir if n else not_found_dir, name))

    print(f"\n{hits}/{len(images)} frame(s) had at least one person detected.")
    print(f"Annotated frames saved to {out_dir}")


if __name__ == "__main__":
    main()
