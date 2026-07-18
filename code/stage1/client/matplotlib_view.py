"""Stage 1 matplotlib client: subscribes to the shared MQTT contract, plots
live position in local ENU, and overlays basic vehicle status. Purely an
MQTT subscriber -- never touches pymavlink or SITL directly, and is meant to
be swappable for new-gui.py later with zero backend changes.
"""
import collections
import json
import math
import os
import queue

import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt
from matplotlib.patches import Polygon

VEHICLE_ID = os.environ.get("VEHICLE_ID", "1")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

HOME_TOPIC = f"uav/{VEHICLE_ID}/home"
TELEMETRY_TOPIC = f"uav/{VEHICLE_ID}/telemetry"

EARTH_RADIUS_M = 6378137.0
TRAIL_LENGTH = 20  # ~5s of history at 4Hz telemetry -- a short comet-tail,
                   # not the whole mission's path
# Floors, not fixed sizes -- both views auto-expand past these once there's
# real movement/altitude, but GPS/EKF noise on the ground shouldn't be able
# to shrink the view enough to make noise look like flight.
MIN_HALF_SPAN_M = 20.0  # position plot always shows at least this far from home
MIN_ALT_CEILING_M = 5.0

# One color per vehicle -- shared by its trail, marker, and altitude
# indicator, so a second drone (Stage 6) reads as a distinct color rather
# than needing a legend.
DRONE_COLOR = "tab:orange"

TRIANGLE_SIZE_FRACTION = 0.048  # 60% of the original 0.08

_updates = queue.Queue()


def lla_to_enu(lat, lon, origin_lat, origin_lon):
    """Local, throwaway conversion for this plot only -- never published
    back to MQTT, never treated as shared truth. LLA stays canonical on the
    wire; this equirectangular approximation is fine at the local scale a
    single plot needs.
    """
    lat0_rad = math.radians(origin_lat)
    x_east = math.radians(lon - origin_lon) * math.cos(lat0_rad) * EARTH_RADIUS_M
    y_north = math.radians(lat - origin_lat) * EARTH_RADIUS_M
    return x_east, y_north


def fmt(value, spec="{:.1f}"):
    return spec.format(value) if value is not None else "n/a"


def heading_triangle(x, y, heading_deg, size):
    """Vertices of an isosceles triangle at (x, y), nose pointing along the
    compass bearing `heading_deg`, sized to `size` (meters, tip to base).
    """
    theta = math.radians(heading_deg)
    sin_t, cos_t = math.sin(theta), math.cos(theta)
    # Local frame: v = forward (nose direction), u = right of forward.
    local_pts = [(0.0, 0.65 * size), (-0.4 * size, -0.35 * size), (0.4 * size, -0.35 * size)]
    verts = []
    for u, v in local_pts:
        east = v * sin_t + u * cos_t
        north = v * cos_t - u * sin_t
        verts.append((x + east, y + north))
    return verts


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT} ({reason_code})")
    client.subscribe(HOME_TOPIC)
    client.subscribe(TELEMETRY_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        return
    if msg.topic == HOME_TOPIC:
        _updates.put(("home", payload))
    elif msg.topic == TELEMETRY_TOPIC:
        _updates.put(("telemetry", payload))


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    fig, (ax, ax_alt) = plt.subplots(
        1, 2, figsize=(9, 6), gridspec_kw={"width_ratios": [3, 1]}
    )
    ax.set_xlabel("East (m)")
    ax.set_ylabel("North (m)")
    ax.set_title(f"Vehicle {VEHICLE_ID} -- local ENU relative to home")
    ax.set_aspect("equal", adjustable="datalim")

    ax_alt.set_title("Altitude")
    ax_alt.set_ylabel("Alt (m)")
    ax_alt.set_xticks([])
    ax_alt.set_xlim(-0.5, 0.5)

    trail_x = collections.deque(maxlen=TRAIL_LENGTH)
    trail_y = collections.deque(maxlen=TRAIL_LENGTH)
    trail_line, = ax.plot([], [], "-", color=DRONE_COLOR, alpha=0.6, linewidth=2)
    drone_marker = Polygon(
        [(0, 0), (0, 0), (0, 0)], closed=True, color=DRONE_COLOR, zorder=5
    )
    ax.add_patch(drone_marker)
    status_text = ax.text(
        0.02, 0.98, "", transform=ax.transAxes, va="top", ha="left",
        family="monospace", fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    alt_line, = ax_alt.plot(
        [-0.3, 0.3], [0, 0], linewidth=10, color=DRONE_COLOR, solid_capstyle="butt"
    )
    ax_alt.set_ylim(-1.0, MIN_ALT_CEILING_M)

    fig.tight_layout()

    # Shared state written by the MQTT thread (via the queue) and read only
    # from the animation callback -- redraws never happen off the MQTT
    # callback thread.
    state = {"origin": None, "latest": None}

    def update():
        while True:
            try:
                kind, payload = _updates.get_nowait()
            except queue.Empty:
                break
            if kind == "home":
                state["origin"] = (payload["lat"], payload["lon"])
                print(f"Home origin set: {state['origin']}")
            elif kind == "telemetry":
                state["latest"] = payload

        artists = (trail_line, drone_marker, alt_line, status_text)

        if state["origin"] is None or state["latest"] is None:
            return artists

        origin_lat, origin_lon = state["origin"]
        t = state["latest"]
        if t.get("lat") is None or t.get("lon") is None:
            return artists

        x, y = lla_to_enu(t["lat"], t["lon"], origin_lat, origin_lon)
        trail_x.append(x)
        trail_y.append(y)

        trail_line.set_data(trail_x, trail_y)

        ax.relim()
        ax.autoscale_view()

        # View is always centered on home (0,0), showing at least
        # +/-MIN_HALF_SPAN_M in every direction -- grows past that only if
        # the vehicle actually flies further out, so GPS/EKF noise on the
        # ground can't shrink the view enough to make noise look like
        # flight.
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        half_span = max(MIN_HALF_SPAN_M, abs(xlim[0]), abs(xlim[1]), abs(ylim[0]), abs(ylim[1]))
        ax.set_xlim(-half_span, half_span)
        ax.set_ylim(-half_span, half_span)

        # Triangle size as a fraction of the current view so it stays a
        # sensible size regardless of zoom level; heading defaults to 0
        # (north) if not yet known rather than skipping the marker.
        heading = t.get("heading") or 0.0
        size = TRIANGLE_SIZE_FRACTION * (2 * half_span)
        drone_marker.set_xy(heading_triangle(x, y, heading, size))

        alt_rel = t.get("alt_rel")
        if alt_rel is not None:
            alt_line.set_ydata([alt_rel, alt_rel])
            ax_alt.set_ylim(-1.0, max(MIN_ALT_CEILING_M, alt_rel + 2.0))

        status_text.set_text(
            f"mode:     {t.get('mode')}\n"
            f"armed:    {t.get('armed')}\n"
            f"alt_rel:  {fmt(t.get('alt_rel'))} m\n"
            f"battery:  {fmt(t.get('battery_voltage'), '{:.2f}')} V"
        )

        return artists

    # A plain plt.pause() loop instead of FuncAnimation -- FuncAnimation's
    # internal timer was not reliably forcing a redraw under this project's
    # WSLg/Tk test environment (data was updating correctly, the window
    # just never repainted). plt.pause() explicitly drives the GUI event
    # loop and flushes each frame, which is the more portable pattern
    # across backends/remote displays.
    plt.show(block=False)
    try:
        while plt.fignum_exists(fig.number):
            update()
            plt.pause(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()


if __name__ == "__main__":
    main()
