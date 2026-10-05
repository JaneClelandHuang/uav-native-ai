"""Puts the given course code (lab/lesson7: contract.py, llm_tools.py, ...; lab/cv: geolocate.py) on the import path.

Works from hw07/clues/ (where you copied this starter) and from lab/lesson7/starter/.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for candidate in (os.path.join(HERE, "..", "..", "lab", "lesson7"), os.path.join(HERE, "..")):
    if os.path.isfile(os.path.join(candidate, "contract.py")):
        KIT = os.path.normpath(candidate)
        for path in (KIT, os.path.join(os.path.dirname(KIT), "cv")):  # lab/cv: geolocate.distance_m
            if path not in sys.path:
                sys.path.insert(0, path)
        break
else:
    raise ImportError("Can't find lab/lesson7/contract.py. Keep this folder at hw07/clues/ in your repo.")
