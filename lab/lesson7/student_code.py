"""student_code.py -- find and import YOUR pipeline for the given tools.

evaluate.py and detector.py run your code from hw07/clues/ (copied from
lab/lesson7/starter/). They need exactly two things from it:

    pipeline.ClueAnalyzer(backend, mission, closer_look=None, on_event=None)
        .analyze(candidate) -> contract.ClueAssessment
    llm.ClaudeBackend(model=None)        a backend with .generate(stage, system, content, schema)

Use --pipeline DIR on either tool to point somewhere else.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "hw07", "clues"))


def load(directory=None):
    """Returns (ClueAnalyzer, ClaudeBackend) from your pipeline directory."""
    directory = os.path.abspath(directory or DEFAULT_DIR)
    if not os.path.isfile(os.path.join(directory, "pipeline.py")):
        sys.exit(f"No pipeline.py in {directory}.\n"
                 f"Start one with:  cp -r lab/lesson7/starter hw07/clues   (from the repo root)")
    sys.path.insert(0, directory)
    pipeline = importlib.import_module("pipeline")
    llm = importlib.import_module("llm")
    return pipeline.ClueAnalyzer, llm.ClaudeBackend
