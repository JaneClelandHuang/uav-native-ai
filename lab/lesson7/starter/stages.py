"""stages.py -- YOUR Stages 2-4: each declared once, then one function each.

A StageSpec (contract.py) is the single place a stage is defined: its name
(which is also its prompt file, prompts/<name>.md), the schema its answer
must fit, and how hard the model thinks (effort). Everything else -- your
backend, the tracer, FakeBackend in your tests -- reads the spec, so nothing
else has to know or spell a stage's name.

Each function builds the request for its stage from typed inputs and calls

    backend.generate(SPEC, load_prompt(SPEC), content) -> (result, StageCall)

What goes into each request -- which images, which facts -- is a design
decision you justify in design.md. Describe must never see who is missing.
"""
import os

import _kit  # noqa: F401
from contract import StageSpec
from llm_tools import image_block  # noqa: F401
from messages import ClueDecision, Description, Relevance

# TODO: choose each stage's effort ("low", "medium", "high", ...) and justify it in design.md.
DESCRIBE = StageSpec("describe", Description, effort="medium")
RELEVANCE = StageSpec("relevance", Relevance, effort="medium")
DECIDE = StageSpec("decide", ClueDecision, effort="medium")
STAGES = (DESCRIBE, RELEVANCE, DECIDE)

PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def load_prompt(spec):
    with open(os.path.join(PROMPT_DIR, f"{spec.name}.md")) as f:
        return f.read()


def describe(backend, candidate):
    """Stage 2: what is this object? Sees only the pixels (crop, maybe the full
    frame) and their scale, never the mission."""
    raise NotImplementedError("TODO: implement describe() in stages.py")


def assess_relevance(backend, mission, candidate, description):
    """Stage 3: is this object evidence of THIS missing person?"""
    raise NotImplementedError("TODO: implement assess_relevance() in stages.py")


def decide_action(backend, mission, candidate, description, relevance, already_inspected):
    """Stage 4: one action from the fixed menu (contract.ACTIONS).
    already_inspected: a closer look has been taken; don't offer inspect_closer again."""
    raise NotImplementedError("TODO: implement decide_action() in stages.py")
