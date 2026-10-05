"""messages.py -- YOUR stage schemas.

Each stage's answer is a pydantic model you pass to the API as the output
schema (structured output), so the model's reply either validates or is
rejected. Designing these is part of the homework: what does each stage need
to say, in what order, for the next stage (and for you, debugging) to use it?

Field order matters: the model writes fields in schema order.

Two fields are fixed by the contract (contract.py), because the given tools
and your planner read them. Keep them; add whatever else you need.
"""
from typing import Literal, Optional

from pydantic import BaseModel

import _kit  # noqa: F401  (puts lab/lesson7 on the path)
from contract import ACTIONS, Candidate, ClueAssessment, LatLon, MissionContext, StageCall  # noqa: F401

RelevanceLevel = Literal["high", "medium", "low", "none"]
ActionType = Literal["ignore", "log_only", "inspect_closer", "converge_search"]
assert set(ActionType.__args__) == set(ACTIONS)


class Description(BaseModel):
    """Stage 2 output: what the object looks like. Entirely your design."""
    object_type: str            # evaluate.py prints this if present
    # TODO: add fields


class Relevance(BaseModel):
    """Stage 3 output: is this evidence of THIS missing person?"""
    # TODO: add fields (think about what should come before the verdict)
    relevance: RelevanceLevel   # required by the contract


class ClueDecision(BaseModel):
    """Stage 4 output: one action from the fixed menu."""
    # TODO: add fields
    action: ActionType                       # required by the contract
    search_radius_m: Optional[float] = None  # required by the contract when action == "converge_search"
