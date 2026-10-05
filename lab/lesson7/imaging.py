"""imaging.py -- crops for the VLM, and an offline stand-in for the drone camera.

crop_b64(frame, cx, cy, half_px)
    Square crop around (cx, cy), padded to show surroundings, upscaled so a
    20-pixel object isn't a speck. Upscaling adds no detail -- it just stops
    the model from squinting. Used by the live detector and offline runs alike.

render_view(image_path, width_m, agl_m, zoom)
    What new-gui's nadir camera would show of a scene object (width_m is the
    width of the whole PNG, transparent margin included, as in new-gui): the clue at
    the ground resolution for this altitude and zoom (same footprint maths as
    cv/geolocate.footprint_m), composited onto a grass-coloured background.
    Lets run_offline.py test Stages 2-4 at realistic resolution without the sim.
"""
import base64
import io
import math
import random

from PIL import Image

FOV_H_DEG = 80.0     # new-gui camera.config
IMAGE_PX = 320
MIN_CROP_PX = 256


def to_png_b64(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


def ground_m_per_px(agl_m, zoom=1.0, fov_h_deg=FOV_H_DEG, image_px=IMAGE_PX):
    return 2.0 * agl_m * math.tan(math.radians(fov_h_deg / 2.0)) / max(zoom, 1.0) / image_px


def crop_b64(frame, cx, cy, half_px, pad=1.5):
    """Returns (png_b64, scale): scale is output px per frame px, so the
    caller can convert ground_m_per_px for the crop."""
    half = max(8, int(half_px * pad))
    box = (int(cx - half), int(cy - half), int(cx + half), int(cy + half))
    crop = frame.crop(box)  # areas outside the frame come back black
    scale = 1.0
    if crop.width < MIN_CROP_PX:
        scale = MIN_CROP_PX / crop.width
        crop = crop.resize((MIN_CROP_PX, MIN_CROP_PX), Image.BICUBIC)
    return to_png_b64(crop), scale


def visible_bbox(image):
    """Bounding box of the clearly opaque pixels (ignores soft drop shadows)."""
    return image.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox() or (0, 0, *image.size)


def object_width_m(image_path, width_m):
    """Real (placed) width of what's visible, given the image's placed width_m."""
    image = Image.open(image_path).convert("RGBA")
    x0, _, x1, _ = visible_bbox(image)
    return width_m * (x1 - x0) / image.width


def _grass(size, seed):
    rng = random.Random(seed)
    img = Image.new("RGB", size, (86, 112, 62))
    px = img.load()
    for _ in range(size[0] * size[1] // 6):
        x, y = rng.randrange(size[0]), rng.randrange(size[1])
        g = rng.randint(-18, 18)
        px[x, y] = (86 + g, 112 + g, 62 + g // 2)
    return img


def render_view(image_path, width_m, agl_m, zoom=1.0, seed=0):
    """Returns (crop_png_b64, ground_m_per_px_of_crop)."""
    mpp = ground_m_per_px(agl_m, zoom)
    obj = Image.open(image_path).convert("RGBA")
    full_w = obj.width
    obj = obj.crop(visible_bbox(obj))   # width_m is the whole image, as in new-gui
    w_px = max(2, round(width_m * obj.width / full_w / mpp))
    h_px = max(2, round(w_px * obj.height / obj.width))
    obj = obj.resize((w_px, h_px), Image.LANCZOS)
    side = max(w_px, h_px) * 3
    ground = _grass((side, side), seed)
    ground.paste(obj, ((side - w_px) // 2, (side - h_px) // 2), obj)
    b64, scale = crop_b64(ground, side / 2, side / 2, max(w_px, h_px) / 2)
    return b64, mpp / scale
