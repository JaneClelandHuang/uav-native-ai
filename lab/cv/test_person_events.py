"""Tests for nadir geolocation and person confirmation/de-duplication.

    cd lab/cv && python -m unittest test_person_events
"""
import math
import unittest

from geolocate import distance_m, footprint_m, pixel_to_latlon
from person_event_detector import PersonTracker, vehicle_for_color

POSE = {"lat": 41.698575, "lon": -86.237055, "agl_m": 20.0,
        "fov_h_deg": 80.0, "fov_v_deg": 60.0, "zoom": 1.0, "north_up": True}
W, H = 320, 220


class TestGeolocate(unittest.TestCase):
    def test_centre_is_under_drone(self):
        lat, lon = pixel_to_latlon(W / 2, H / 2, W, H, POSE)
        self.assertAlmostEqual(lat, POSE["lat"], places=9)
        self.assertAlmostEqual(lon, POSE["lon"], places=9)

    def test_footprint(self):
        width, height = footprint_m(POSE)
        self.assertAlmostEqual(width, 2 * 20 * math.tan(math.radians(40)), places=6)
        self.assertAlmostEqual(height, 2 * 20 * math.tan(math.radians(30)), places=6)
        self.assertAlmostEqual(width / height, W / H, delta=0.01)  # matches new-gui's frame aspect

    def test_edges_are_half_footprint_away(self):
        width, height = footprint_m(POSE)
        lat, lon = pixel_to_latlon(W, H / 2, W, H, POSE)          # right edge -> east
        self.assertAlmostEqual(distance_m(POSE["lat"], POSE["lon"], lat, lon), width / 2, delta=0.01)
        self.assertGreater(lon, POSE["lon"])
        lat, lon = pixel_to_latlon(W / 2, 0, W, H, POSE)          # top edge -> north
        self.assertAlmostEqual(distance_m(POSE["lat"], POSE["lon"], lat, lon), height / 2, delta=0.01)
        self.assertGreater(lat, POSE["lat"])

    def test_zoom_narrows_footprint(self):
        zoomed = dict(POSE, zoom=2.0)
        lat1, lon1 = pixel_to_latlon(W, H / 2, W, H, POSE)
        lat2, lon2 = pixel_to_latlon(W, H / 2, W, H, zoomed)
        d1 = distance_m(POSE["lat"], POSE["lon"], lat1, lon1)
        d2 = distance_m(POSE["lat"], POSE["lon"], lat2, lon2)
        self.assertAlmostEqual(d2, d1 / 2, delta=0.01)


class TestPersonTracker(unittest.TestCase):
    def test_single_hit_is_not_an_event(self):
        tracker = PersonTracker(min_hits=2)
        self.assertIsNone(tracker.observe(41.0, -86.0, 0.9, now=0.0))

    def test_confirm_then_dedup(self):
        tracker = PersonTracker(min_hits=2)
        tracker.observe(41.0, -86.0, 0.6, now=0.0)
        event = tracker.observe(41.00001, -86.0, 0.8, now=0.3)   # ~1 m away
        self.assertIsNotNone(event)
        self.assertAlmostEqual(event["confidence"], 0.8)
        for i in range(20):  # circling: seen again and again
            self.assertIsNone(tracker.observe(41.00002, -86.00001, 0.7, now=1.0 + i))

    def test_known_person_reannounced_after_interval(self):
        tracker = PersonTracker(min_hits=1, reannounce_s=30.0)
        self.assertIsNotNone(tracker.observe(41.0, -86.0, 0.6, now=0.0))
        self.assertIsNone(tracker.observe(41.0, -86.0, 0.6, now=29.0))
        again = tracker.observe(41.0, -86.0, 0.6, now=31.0)
        self.assertEqual(set(again), {"lat", "lon", "confidence"})
        self.assertIsNone(tracker.observe(41.0, -86.0, 0.6, now=32.0))  # interval restarts

    def test_two_boxes_in_one_frame_do_not_confirm(self):
        tracker = PersonTracker(min_hits=2)
        frame = object()
        self.assertIsNone(tracker.observe(41.0, -86.0, 0.9, now=0.0, frame_id=frame))
        self.assertIsNone(tracker.observe(41.00005, -86.0, 0.9, now=0.0, frame_id=frame))  # ~5 m
        self.assertIsNotNone(tracker.observe(41.0, -86.0, 0.9, now=0.3, frame_id=object()))

    def test_hits_must_be_colocated(self):
        tracker = PersonTracker(min_hits=2)
        tracker.observe(41.0, -86.0, 0.9, now=0.0)
        self.assertIsNone(tracker.observe(41.001, -86.0, 0.9, now=0.3))  # ~110 m away

    def test_hits_must_be_recent(self):
        tracker = PersonTracker(min_hits=2, window_s=5.0)
        tracker.observe(41.0, -86.0, 0.9, now=0.0)
        self.assertIsNone(tracker.observe(41.0, -86.0, 0.9, now=10.0))

    def test_two_people(self):
        tracker = PersonTracker(min_hits=1)
        self.assertIsNotNone(tracker.observe(41.0, -86.0, 0.9, now=0.0))
        self.assertIsNotNone(tracker.observe(41.0005, -86.0, 0.9, now=0.1))  # ~55 m away

    def test_color_to_vehicle(self):
        self.assertEqual(vehicle_for_color("Fuchsia"), "1")
        self.assertIsNone(vehicle_for_color("Chartreuse"))


if __name__ == "__main__":
    unittest.main()
