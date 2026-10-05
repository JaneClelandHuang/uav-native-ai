"""scenario.py -- load a test scenario (a missing person plus placed clues).

A scenario directory holds scenario.json and an images/ folder:

    {
      "mission": { ...MissionContext... },
      "search_agl_m": 25,                     # altitude the search flies at
      "target": {"image": "people/girl-pinafores.png",   # optional: the person,
                 "lat": ..., "lon": ..., "width_m": 8},   # a new-gui scene image
      "clues": [
        {"id": "c01", "image": "images/red-cap.png", "lat": ..., "lon": ...,
         "width_m": 8.0,                       # width of the whole PNG as placed in new-gui
         "image_prompt": "...",                # how the image was / should be generated
         "truth": {"relevant": true,
                   "acceptable_actions": ["converge_search"],
                   "rationale": "..."}}
      ]
    }

"scene_scale" says how many times life size the objects are drawn (new-gui
icons at the people scale, placed at 8 m: ~9). The ground scale the VLM is
told is divided by it, so sizes it estimates are life-size. Positions and
distances are real and are not scaled. Real flight: 1.

"width_m" follows new-gui: it is the width of the whole image, transparent
margin included, and is deliberately larger than life -- see README: at
search altitude a real-size cap would be ~2 pixels. Icons drawn at the same
scale as new-gui's people icons are placed at the person's width_m.
"""
import json
import os
import zlib

from typing import Optional

from pydantic import BaseModel, Field

from imaging import object_width_m, render_view
from contract import Candidate, MissionContext

INSPECT_ZOOM = 6.0   # new-gui camera max_zoom


class Truth(BaseModel):
    relevant: bool
    acceptable_actions: list
    rationale: str = ""


class ClueSpec(BaseModel):
    id: str
    image: str
    lat: float
    lon: float
    width_m: float
    image_prompt: str = ""
    truth: Truth


class Target(BaseModel):
    image: str               # relative to new-gui's src/data/scene/
    lat: float
    lon: float
    width_m: float
    note: str = ""


class Scenario(BaseModel):
    mission: MissionContext
    search_agl_m: float = 25.0
    scene_scale: float = 1.0  # how many times life size the scene's objects are drawn (new-gui icons: ~9)
    target: Optional[Target] = None
    clues: list[ClueSpec] = Field(default_factory=list)
    directory: str = ""

    def image_path(self, clue):
        return os.path.join(self.directory, clue.image)

    def object_width_m(self, clue):
        """Placed width of the visible object (not the whole PNG); width_m if no image yet."""
        path = self.image_path(clue)
        return object_width_m(path, clue.width_m) if os.path.exists(path) else clue.width_m

    def candidate(self, clue, zoom=1.0):
        """The Stage-1 output an ideal detector would produce for this clue."""
        crop, mpp = render_view(self.image_path(clue), clue.width_m, self.search_agl_m, zoom,
                                seed=zlib.crc32(clue.id.encode()))
        return Candidate(lat=clue.lat, lon=clue.lon, cv_label="unknown", cv_confidence=1.0,
                         crop_png_b64=crop, ground_m_per_px=mpp / self.scene_scale, zoomed=zoom > 1.0,
                         candidate_id=clue.id)

    def closer_look_for(self, clue):
        return lambda _candidate: self.candidate(clue, zoom=INSPECT_ZOOM)


def load_scenario(path):
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    with open(os.path.join(directory, "scenario.json")) as f:
        data = json.load(f)
    return Scenario(**data, directory=os.path.abspath(directory))
