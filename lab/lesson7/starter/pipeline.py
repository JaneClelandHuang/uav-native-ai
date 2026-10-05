"""pipeline.py -- YOUR ClueAnalyzer: runs Stages 2-4 on one Candidate.

The given tools (evaluate.py, detector.py) construct it and call analyze():

    analyzer = ClueAnalyzer(backend, mission, closer_look=fn, on_event=print_fn)
    assessment = analyzer.analyze(candidate)        # -> contract.ClueAssessment

closer_look(candidate) -> Candidate | None gives a zoomed view of the same
object (offline: a higher-resolution render; in flight: None, so the planner
gets an inspect_closer request instead). Take at most ONE closer look per
object, so the pipeline always ends.

on_event(str) narrates pipeline steps in evaluate.py's trace -- call it when
you take a closer look or set a search centre.

A converge_search's search_center is the candidate's position. Your code sets
it, never the model.
"""
import _kit  # noqa: F401
from contract import ClueAssessment, LatLon  # noqa: F401
from stages import assess_relevance, decide_action, describe  # noqa: F401


class ClueAnalyzer:
    def __init__(self, backend, mission, closer_look=None, on_event=None):
        self.backend = backend
        self.mission = mission
        self.closer_look = closer_look
        self.on_event = on_event or (lambda message: None)

    def analyze(self, candidate):
        """Describe -> (closer look?) -> relevance -> decide -> ClueAssessment.
        Store each stage's output with .model_dump() and every StageCall in calls."""
        raise NotImplementedError("TODO: implement ClueAnalyzer.analyze() in pipeline.py")
