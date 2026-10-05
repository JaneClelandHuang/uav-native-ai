"""Tests for the given HW7 tools (not your pipeline).  cd lab/lesson7 && python -m unittest discover tests"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(os.path.dirname(KIT), "cv"))

from PIL import Image  # noqa: E402

import check_set  # noqa: E402
from contract import ClueAssessment  # noqa: E402
from detector import OracleFinder, latlon_to_pixel  # noqa: E402
from geolocate import pixel_to_latlon  # noqa: E402
from imaging import ground_m_per_px  # noqa: E402
from scenario import load_scenario  # noqa: E402

LILY = os.path.join(KIT, "scenarios", "lost-girl-pinafore")


class TestKit(unittest.TestCase):
    def test_lily_set_is_well_formed(self):
        self.assertEqual(check_set.check(LILY, os.path.join(KIT, "clue_sets.csv")), [])

    def test_candidate_scale_is_life_size(self):
        s = load_scenario(LILY)
        c = s.candidate(s.clues[0])
        self.assertLess(c.ground_m_per_px, ground_m_per_px(25) / 5)

    def test_oracle_finds_clue_under_the_drone_and_hides_its_id(self):
        s = load_scenario(LILY)
        clue = s.clues[0]
        pose = {"lat": clue.lat, "lon": clue.lon, "agl_m": 25.0, "fov_h_deg": 80.0, "fov_v_deg": 60.0,
                "zoom": 1.0, "north_up": True}
        found = list(OracleFinder(s).find(Image.new("RGB", (320, 240)), pose))
        self.assertTrue(found and all(f[3] == "unknown" for f in found))

    def test_latlon_to_pixel_inverts_geolocate(self):
        pose = {"lat": 41.698, "lon": -86.238, "agl_m": 25.0, "fov_h_deg": 80.0, "fov_v_deg": 60.0,
                "zoom": 1.0, "north_up": True}
        lat, lon = pixel_to_latlon(250, 40, 320, 240, pose)
        u, v = latlon_to_pixel(lat, lon, 320, 240, pose)
        self.assertAlmostEqual(u, 250, places=3)
        self.assertAlmostEqual(v, 40, places=3)

    def test_contract_requires_centre_and_radius_for_converge(self):
        with self.assertRaises(ValueError):
            ClueAssessment(mission_id="m", candidate={}, descriptions=[], relevance={"relevance": "high"},
                           decision={"action": "converge_search", "search_radius_m": 80})


if __name__ == "__main__":
    unittest.main()
