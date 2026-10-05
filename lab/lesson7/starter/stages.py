"""stages.py -- YOUR Stages 2-4, one function each.

Each builds the request for its stage from typed inputs, loads its system
prompt from prompts/<stage>.md, and calls backend.generate(). What goes into
each request -- which images, which facts -- is a design decision you justify
in design.md. Describe must never see who is missing.

Each returns (result, StageCall).
"""
import os

import _kit  # noqa: F401
from llm_tools import image_block  # noqa: F401
from messages import ClueDecision, Description, Relevance  # noqa: F401

PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def load_prompt(stage):
    with open(os.path.join(PROMPT_DIR, f"{stage}.md")) as f:
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
