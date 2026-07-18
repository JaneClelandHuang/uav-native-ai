---
title: "Lesson 2: Environment setup — ArduPilot, SITL, Docker"
---

<p class="tag">Week 2 · Aug 31 – Sep 4</p>

# Lesson 2: Environment setup — ArduPilot, SITL, Docker

## Topic

- **What is ArduPilot?** Open-source autopilot firmware — the real
  flight-control loop (attitude, navigation, failsafes), not a toy. It's
  what the physical drones you'll fly later in the course run.
- **Why ArduPilot, not PX4?** Not a technical-superiority claim — your real
  hardware runs ArduPilot, so code built against SITL this semester
  transfers directly to it later.
- **What is SITL?** Software-In-The-Loop: the actual ArduPilot firmware,
  running against a simulated physics model instead of real motors/sensors.
  Safe to crash, no hardware required.
- **Why not Gazebo?** Our SITL uses ArduPilot's own lightweight built-in
  physics model. Gazebo needs real GPU-accelerated OpenGL, which fails
  unpredictably across a room of student laptops (VMs, integrated graphics,
  locked-down images) — exactly the kind of opaque failure that derails a
  live class session.
- **Why Docker, and why only for some of it.** SITL and the MQTT broker are
  containerized (version-pinned, reproducible). The Python code you'll
  edit constantly stays on your host — no rebuild-and-restart cycle for
  routine changes.

## Readings

- [`code/stage1/ARCHITECTURE.md`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/ARCHITECTURE.md) — read in full; this is the reference for the whole semester's infrastructure.
- [`code/stage1/SETUP.md`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/SETUP.md) — per-OS install notes and the troubleshooting index.

## Code

- [`code/stage1/`](https://github.com/JaneClelandHuang/uav-native-ai/tree/main/code/stage1) — clone the repo, `cd code/stage1`.
- [`code/stage1/docker-compose.yml`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/docker-compose.yml)
- [`code/stage1/scripts/verify_setup.py`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/scripts/verify_setup.py)

## Assignment

Run the one-command health check and confirm your environment actually
works, end to end:

```
cp .env.example .env
python3 -m venv client/.venv
source client/.venv/bin/activate
pip install -r client/requirements.txt
python scripts/verify_setup.py
```

<div class="callout placeholder">
<p><strong>Submission</strong></p>
<p>[Placeholder — e.g. submit a screenshot/paste of the final <code>PASS</code>
output, or a short note on what failed and how you resolved it if you hit one
of the documented failure modes.]</p>
</div>

---

[← Lesson 1]({{ '/lessons/lesson-01.html' | relative_url }}) · [Lessons index]({{ '/lessons/' | relative_url }}) · [Next: Lesson 3 →]({{ '/lessons/lesson-03.html' | relative_url }})
