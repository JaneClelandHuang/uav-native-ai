---
title: "Lesson 4: Telemetry & command-and-control frontend"
---

<p class="tag">Week 4 · Sep 14 – 18</p>

# Lesson 4: Telemetry &amp; command-and-control frontend

## Topic

`matplotlib_view.py` as a worked example of "just another MQTT client" — and
as the first frontend you'll extend or replace this semester. Walk through
its design choices, since each one is a small lesson on its own:

- Converting LLA to local ENU only for this one plot's own use — never
  published, never shared truth (see Lesson 3).
- A view that's anchored to home and floors at a minimum span, so GPS/EKF
  noise on the ground can't visually masquerade as flight.
- A heading-oriented marker and a short rolling trail, tuned to read as "the
  vehicle right now," not "the whole mission's history."
- Sending commands (`arm`, `takeoff`, `goto`, `land`) over the same MQTT
  contract the backend already exposes — no new plumbing required to close
  the control loop.

## Readings

- [`code/stage1/client/matplotlib_view.py`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/client/matplotlib_view.py) — read in full.
- [`code/stage1/ARCHITECTURE.md`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/ARCHITECTURE.md) — the `matplotlib_view.py` component section.

## Code

- [`code/stage1/client/matplotlib_view.py`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/client/matplotlib_view.py)
- [`code/stage1/scripts/test_flight.py`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/scripts/test_flight.py) — a scripted arm → takeoff → square → land flight, driven entirely over MQTT.

## Assignment

Run the viewer and a scripted flight side by side:

```
source client/.venv/bin/activate
python client/matplotlib_view.py &
python scripts/test_flight.py
```

<div class="callout placeholder">
<p><strong>Submission</strong></p>
<p>[Placeholder — e.g. a small, real extension to <code>matplotlib_view.py</code>
(a battery-level warning color, a second readout, a click-to-goto
prototype) submitted as a diff/PR, plus a short note on what MQTT topic(s)
it used and why no backend changes were needed.]</p>
</div>

---

[← Lesson 3]({{ '/lessons/lesson-03.html' | relative_url }}) · [Lessons index]({{ '/lessons/' | relative_url }}) · [Next: Lesson 5 →]({{ '/lessons/lesson-05.html' | relative_url }})
