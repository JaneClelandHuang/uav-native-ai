---
title: "Lesson 3: MQTT architecture & interface design"
---

<p class="tag">Week 3 · Sep 7 – 11</p>

# Lesson 3: MQTT architecture &amp; interface design

## Topic

- **The rule:** `drone_backend.py` is the only thing in the whole stack
  that speaks pymavlink. Every frontend is purely an MQTT
  subscriber/publisher. This is deliberate, and it's the main thing this
  lesson is about — not the plumbing itself, but *why* this shape.
- **The topic schema is the contract.** `uav/<id>/telemetry`,
  `uav/<id>/command`, `uav/<id>/home` — three topics, real JSON, documented
  once, and every frontend (yours, a classmate's, the eventual real GUI)
  builds against the same thing without touching the backend.
- **A subtlety worth sitting with: coordinate frames.** LLA (lat/lon/alt) is
  the only frame that ever crosses the wire. Local frames (ENU) are private,
  per-client, throwaway math — never published, never shared truth. Two
  clients quietly disagreeing about where local `(0,0)` is produces a bug
  class that's miserable to debug: correct in one view, subtly wrong in
  another. The retained `home` topic is what prevents that.

## Readings

- [`code/stage1/ARCHITECTURE.md`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/ARCHITECTURE.md) — sections "The MQTT contract" and "Coordinate frame policy."
- [`code/stage1/backend/drone_backend.py`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/backend/drone_backend.py) — read `mavlink_reader()` and `handle_command()` end to end.

## Code

- [`code/stage1/backend/drone_backend.py`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/backend/drone_backend.py)
- [`code/stage1/docker/mosquitto.conf`](https://github.com/JaneClelandHuang/uav-native-ai/blob/main/code/stage1/docker/mosquitto.conf)

## Assignment

With the stack running (`docker compose up -d`), subscribe to everything and
watch the contract in action:

```
mosquitto_sub -h localhost -p 1883 -t 'uav/#' -v
```

<div class="callout placeholder">
<p><strong>Submission</strong></p>
<p>[Placeholder — e.g. a short write-up: what fields appear in
<code>telemetry</code>, why <code>home</code> only appears once yet a
client subscribing a minute later still receives it immediately, and what
would break if a second client computed its own local origin instead of
using the retained <code>home</code> topic.]</p>
</div>

---

[← Lesson 2]({{ '/lessons/lesson-02.html' | relative_url }}) · [Lessons index]({{ '/lessons/' | relative_url }}) · [Next: Lesson 4 →]({{ '/lessons/lesson-04.html' | relative_url }})
