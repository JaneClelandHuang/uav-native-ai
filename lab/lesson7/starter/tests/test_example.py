"""Example unit tests -- no API key, no simulator. Copy the pattern.

    cd hw07/clues && python -m unittest discover tests

FakeBackend returns scripted answers instead of calling Claude, and records
every request in .requests, so you can test what each stage SENDS and how
your pipeline reacts to each kind of answer -- including failures.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import _kit  # noqa: E402,F401
from contract import ClueAssessment, StageSpec  # noqa: E402
from llm_tools import FakeBackend, LLMError  # noqa: E402
from scenario import load_scenario  # noqa: E402

LILY = os.path.join(_kit.KIT, "scenarios", "lost-girl-pinafore")


class TestContract(unittest.TestCase):
    """These pass now: they test the given contract, not your code."""

    def test_action_must_come_from_the_menu(self):
        with self.assertRaises(ValueError):
            ClueAssessment(mission_id="m", candidate={}, descriptions=[], relevance={"relevance": "high"},
                           decision={"action": "drop_medkit"})

    def test_fake_backend_scripts_answers_and_failures(self):
        from pydantic import BaseModel

        class Verdict(BaseModel):   # a stand-in schema; use your own in your tests
            relevance: str

        verdict = StageSpec("verdict", Verdict, effort="low")
        fake = FakeBackend({verdict: [{"relevance": "low"}, LLMError("declined")]})
        answer, call = fake.generate(verdict, "system", [])
        self.assertEqual(answer.relevance, "low")
        self.assertEqual(call.stage, "verdict")
        with self.assertRaises(LLMError):
            fake.generate(verdict, "system", [])


class TestStages(unittest.TestCase):
    """Passes now, and keeps passing as long as every declared stage has its prompt file."""

    def test_every_stage_has_a_prompt_file(self):
        from stages import STAGES, load_prompt
        for spec in STAGES:
            self.assertTrue(load_prompt(spec), f"prompts/{spec.name}.md is empty")


class TestDescribeExample(unittest.TestCase):
    """An example for YOUR code: fails until describe() is implemented."""

    def test_describe_sends_the_crop_and_never_the_mission(self):
        from stages import DESCRIBE, describe
        scenario = load_scenario(LILY)
        candidate = scenario.candidate(scenario.clues[0])
        fake = FakeBackend({DESCRIBE: [{"object_type": "teddy bear"}]})  # add your Description's other fields
        describe(fake, candidate)
        sent = fake.requests[0]
        self.assertTrue(any(block["type"] == "image" for block in sent["content"]))
        self.assertNotIn(scenario.mission.person.name, str(sent["content"]) + sent["system"])


if __name__ == "__main__":
    unittest.main()
