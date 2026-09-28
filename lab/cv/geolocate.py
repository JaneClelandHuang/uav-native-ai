"""geolocate.py -- pixel in a nadir camera frame -> latitude/longitude.

With a camera pointing straight down (nadir), geolocation is just scaling:
the frame covers a ground rectangle centred under the drone whose size
follows from altitude and field of view,

    footprint_width  = 2 * agl * tan(fov_h / 2) / zoom
    footprint_height = 2 * agl * tan(fov_v / 2) / zoom

so each pixel is footprint/pixels metres wide, and a pixel's offset from the
image centre is a ground offset from the point under the drone. new-gui's
frames are also north-up (image "up" is north, not the drone's heading), so
no rotation is needed: +x is east, +y (down the image) is south.

The pose comes from the frame envelope itself (see new-gui's
camera_frame_publisher.py) -- the exact altitude and zoom the frame was
rendered with -- rather than from telemetry, which would arrive at a
slightly different time and uses a different altitude reference.

A real, tilted camera needs the full projection (camera intrinsics +
attitude + terrain) instead -- that's what "nadir makes it trivial" buys us.
"""
import math

EARTH_RADIUS_M = 6378137.0


def footprint_m(pose):
    """Ground (width, height) in metres covered by a frame with this pose."""
    zoom = max(1.0, float(pose.get("zoom", 1.0)))
    agl = float(pose["agl_m"])
    width = 2.0 * agl * math.tan(math.radians(float(pose["fov_h_deg"]) / 2.0)) / zoom
    height = 2.0 * agl * math.tan(math.radians(float(pose["fov_v_deg"]) / 2.0)) / zoom
    return width, height


def pixel_to_latlon(u, v, image_w, image_h, pose):
    """(u, v) pixel (origin top-left) in a north-up nadir frame -> (lat, lon).

    image_w/image_h must be the actual decoded frame size: new-gui scales the
    footprint into image_px while keeping its aspect ratio, so an 80x60 deg
    camera gives e.g. 320x220 frames, not 320x320.
    """
    if not pose.get("north_up", True):
        raise ValueError("only north-up frames are supported")
    width_m, height_m = footprint_m(pose)
    east_m = (u - image_w / 2.0) * width_m / image_w
    north_m = -(v - image_h / 2.0) * height_m / image_h
    lat0 = float(pose["lat"])
    lat = lat0 + math.degrees(north_m / EARTH_RADIUS_M)
    lon = float(pose["lon"]) + math.degrees(east_m / (EARTH_RADIUS_M * math.cos(math.radians(lat0))))
    return lat, lon


def distance_m(lat1, lon1, lat2, lon2):
    dx = math.radians(lon2 - lon1) * EARTH_RADIUS_M * math.cos(math.radians((lat1 + lat2) / 2))
    dy = math.radians(lat2 - lat1) * EARTH_RADIUS_M
    return math.hypot(dx, dy)
