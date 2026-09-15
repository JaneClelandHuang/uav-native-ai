# Runtime Monitoring & Fault Injection — A Guide to the New Code

This walks through everything new for Lesson 4: the battery worked
example in `lab/lesson4/battery/`, and the shared infrastructure
underneath it that your own two detectors (GPS + your choice) will use
the exact same way.

Three parts: (1) run the demo yourself, (2) what changed and why, in
plain language, (3) the same thing again with real technical detail.
Part 1 gets you seeing it work; skip straight to Part 3 if you already
know what a category/window/verdict is and just want the code details.

---

## Part 1 — Running the Battery Demo

**1. Bring up the simulated drone.**
```bash
cd lab
docker compose up -d --build
```
Check it came up clean: `docker logs lab-drone_backend_1-1 --tail 10`
should show `Heartbeat received...` and `Connected to MQTT broker...`.

**2. Fly.** Always use `test_monitor_flight.py` to fly — not individual
low-level commands (`arm`/`takeoff`/...) sent by hand. It arms, takes off,
flies a 40m square, returns to the launch point, and lands — all on its
own, in its own terminal:
```bash
python3 scripts/test_monitor_flight.py
```
It prints progress as it goes and takes a couple of minutes end to end.
Leave it running in this terminal; do the rest of the steps below in
*other* terminals while it flies.

**3. Watch the battery, live.** In a second terminal, started as soon as
Step 2's flight begins climbing:
```bash
cd lesson4/battery
pip install -r ../requirements.txt   # first time only
python3 battery_plot.py
```
You'll see three live graphs: voltage, current draw, and remaining
percent. Watch it for 20-30 seconds first — this is what "normal" looks
like, before anything else happens.

**4. Watch the detector, live.** In a third terminal, same folder:
```bash
python3 battery_detector.py
```
It should settle to `no problem` after a few seconds and stay there.

**5. Inject a fault.** In a fourth terminal, any time while Step 2's
flight is still airborne (it holds a steady cruise altitude between
waypoints for most of the route, which is plenty of time):
```bash
python3 ../../scripts/mischief_maker.py POWER-BATTERY 10 60 High
```
It waits for confirmation the vehicle has actually taken off and leveled
out (already true by this point), then injects a randomized-but-High-
severity battery problem at a random moment within 10 seconds. Watch
`battery_detector.py` flip to `problem present`, and the voltage line in
`battery_plot.py` drop.

**6. Let Step 2 finish landing, then clean up.** Ctrl-C
`mischief_maker.py` first (it resets the simulated fault before exiting),
then Ctrl-C `battery_plot.py`/`battery_detector.py`, then:
```bash
cd lab && docker compose down
```

---

## Part 2 — What Changed, in Plain Language

Eight things are new or different. Here's what each one does and why it
exists, no code yet.

**1. `backend/mavlink_lib.py` (modified)** — This file is the translator
that talks to the simulated flight computer. We taught it to understand
two more things the flight computer can say: better GPS quality info,
and compass/magnetometer readings. It doesn't do anything with that
information itself — it just knows how to read it now, for other code to use.

**2. `backend/monitor_signals.py` (new)** — A lookup table: "if this kind
of message shows up, it belongs to this category (like `vibration` or
`battery`), and here's how to read it." This is the one place that
changes if you ever wanted to add a brand-new thing to monitor — nothing
else needs to know.

**3. `backend/drone_backend.py` (modified)** — This is the program that's
always running, sitting between the simulated drone and everything else.
It gained two new abilities: (a) any program can now say "only send me
these specific categories" and it'll start doing exactly that, and (b)
any program can now ask it to simulate a problem (like a weak battery)
happening — that second ability is what `mischief_maker.py` uses.

**4. `client2/monitor_view.py` (new)** — The smallest possible example of
asking for one category and printing what comes back. Not something to
run for your homework — something to *read*, then copy the pattern from.

**5. `scripts/mischief_maker.py` (new)** — The "problem generator." You
tell it a category (or let it pick randomly) and roughly how severe. It
waits until the drone has actually taken off, then at a random moment,
quietly turns on a simulated problem at a random strength within that
severity — so you can't predict exactly when or exactly how bad, the same
way you couldn't predict a real failure.

**6. `scripts/test_monitor_flight.py` (new)** — A scripted flight that
flies a decent-sized square around wherever it took off. It exists purely
to keep the drone in the air long enough for `mischief_maker.py`'s random
timing to actually have room to fire, instead of the flight ending before
anything happens.

**7. `lesson4/battery/battery_plot.py` (new)** — Draws a live, scrolling
graph of battery voltage/current/remaining-charge as the drone flies, so
you can see with your own eyes what normal looks like, and what a problem
looks like when one happens.

**8. `lesson4/battery/battery_detector.py` (new)** — Watches the same
battery data, but instead of drawing a picture, it makes a call: *problem
present*, *no problem*, or *not enough data yet* — and says exactly why,
in a sentence, every time.

**The big picture:** #1-3 are the shared plumbing (you don't touch these
for your own categories, you just use what they provide). #4 is a
template to copy. #5-6 are testing tools. #7-8 are the worked example —
the two things you're actually building yourself, just for GPS and your
choice instead of battery.

---

## Part 3 — How It Actually Works (Technical)

### 1. `backend/mavlink_lib.py`

Two additions, both pure functions (message in, dict out, no side
effects, no state):

- `parse_gps_accuracy()` extended with `hdop_h`/`hdop_v`, computed from
  the `GPS_RAW_INT` message's `eph`/`epv` fields (÷100, per the MAVLink
  spec).
- `parse_compass()` (new): reads `xmag`/`ymag`/`zmag` off `RAW_IMU`, plus
  a derived `field_magnitude = sqrt(x²+y²+z²)` — the orientation-invariant
  total field strength, not just the raw axes.

### 2. `backend/monitor_signals.py`

The dispatch table. Two dicts:

```python
CATEGORY_HANDLERS = {
    "VIBRATION": ("vibration", mavlink_lib.parse_vibration),
    "GPS_RAW_INT": ("gps", mavlink_lib.parse_gps_accuracy),
    "EKF_STATUS_REPORT": ("ekf", mavlink_lib.parse_ekf_status),
    "RAW_IMU": ("compass", mavlink_lib.parse_compass),
    "SYS_STATUS": ("battery", mavlink_lib.parse_battery),
}
RELAY_HANDLERS = {
    "STATUSTEXT": ("status_text", mavlink_lib.parse_status_text),
}
```

`CATEGORY_HANDLERS` entries get **stored** (latest value per category,
always overwritten, never merged). `RELAY_HANDLERS` entries get
**relayed immediately** on their own topic and never stored — `STATUSTEXT`
is an event stream, not a value with a "current" state; storing only the
latest one would silently drop anything that arrived in between.

`KNOWN_CATEGORIES = frozenset(...)` is derived from the table above it —
not a menu you pick from in code, just a whitelist `parse_requested_categories()`
checks incoming requests against, dropping (and logging) anything
unrecognized rather than crashing.

### 3. `backend/drone_backend.py`

- `VehicleState` gained exactly two new attributes: `self.monitor` (a
  dict, one slot per category, filled by `monitor_signals`) and
  `self.monitored_categories` (the currently-requested set). No other
  attribute needed adding, ever, to support a new category — that's the
  point of routing through one dict instead of one field per signal.
- `mavlink_reader()`'s **existing** `if/elif` chain (`HEARTBEAT`,
  `GLOBAL_POSITION_INT`, etc.) is untouched. After it, for **every**
  message (not as another `elif` — `SYS_STATUS` needs to hit both the old
  chain and the new dispatch), it calls
  `monitor_signals.extract_for_storage()`/`extract_for_relay()` and acts
  on whichever one matches.
- Three topics: `uav/<id>/monitor_config` (clients publish, retained —
  "current configuration," not a one-off command), `uav/<id>/
  monitored_data` (backend publishes, filtered to whatever's currently
  requested, every telemetry tick), `uav/<id>/status_text` (backend
  publishes immediately on arrival, never retained).
- `handle_command()` gained one new command type, `inject_fault`: takes a
  `{"params": {...}}` dict of `SIM_*` parameter names/values and calls the
  existing `mavlink_lib.set_param()` for each — the *same* mechanism any
  ArduPilot tuning parameter uses. One guard: any name not starting with
  `SIM_` is logged and dropped, never sent — this command can never touch
  a real tuning parameter.

### 4. `client2/monitor_view.py`

```python
client.publish(MONITOR_CONFIG_TOPIC, json.dumps({"categories": CATEGORIES}), retain=True)
client.subscribe(MONITORED_DATA_TOPIC)
```
That's the entire pattern. `on_message` just prints the payload. Every
detector you build (including `battery_detector.py` below) starts exactly
this way.

### 5. `scripts/mischief_maker.py`

- `FAULT_CATALOG`: per `(type, severity)`, one or more `SIM_*` params and
  a `(low, high)` range — a random value is sampled from that range every
  run, so "High" is a range, not a fixed number.
- **Calibrated against the live system, not guessed** — worth knowing
  since two results are counter-intuitive: `VIBRATION` does **not**
  respond to the obviously-named `SIM_VIB_*` parameters at all (ArduPilot
  computes "vibration" from a loop-*averaged* sample, which washes out
  injected per-sample noise before it's ever measured); real simulated
  wind (`SIM_WIND_SPD`/`SIM_WIND_TURB`) is what actually works, because
  it's a genuine physical disturbance. Similarly, `GPS` only responds to
  `SIM_GPS_NUMSATS` — `SIM_GPS_NOISE` moves nothing ArduPilot reports.
- `wait_for_takeoff()` deliberately does **not** watch `drone_backend.py`'s
  `activity` field — that field only becomes `"flying"` once a
  *subsequent* command is issued after takeoff, never automatically on
  reaching altitude, so a student who just takes off and hovers would
  never trigger it. Instead it watches: armed, climbed past a small
  threshold, then altitude stable (low variance) for a few seconds —
  works regardless of what commands get sent afterward.
- Once triggered: `random.uniform(0, onset_deadline)` second delay, then
  one `inject_fault` command with the sampled params. A `signal` handler
  resets every affected param back to its catalog default on exit
  (Ctrl-C or normal completion) — so a killed run never leaves the
  simulation in a broken state for the next one.

### 6. `scripts/test_monitor_flight.py`

Same helper functions as `test_flight.py` (`offset_to_lla`,
`horizontal_distance_m`, `execute_command`'s resend-until-arrival pattern)
— only the flight plan differs: a 40m-per-side square **centered on the
launch point** (`test_flight.py`'s own square is offset from it), flown
Top-Left → Top-Right → Bottom-Right → Bottom-Left → Top-Left (closing the
loop) → center → land.

### 7. `lesson4/battery/battery_plot.py`

Standard live-plot pattern: a `collections.deque`-based rolling history
(trimmed to the last `HISTORY_S=60` seconds), redrawn on a
`plt.show(block=False)` + `plt.pause(0.2)` loop (not
`matplotlib.animation` — that didn't reliably force a redraw on this
project's WSL2/Tk setup in earlier testing). Three subplots share one
x-axis; `on_message` just appends to a queue the plot loop drains.

### 8. `lesson4/battery/battery_detector.py`

The core is `evaluate()`:
```python
if not_enough_samples_or_time_span:
    return "not enough data yet", ...
avg_voltage = mean(voltages in the last WINDOW_S=5.0 seconds)
if avg_voltage < WARN_VOLTAGE:      # 11.0V
    return "problem present", <evidence with real numbers>
return "no problem", <evidence with real numbers>
```
Two constants worth understanding, not just copying: `WINDOW_S`/
`MIN_SAMPLES` control how much history a verdict is based on (SITL's
battery voltage is rock-steady at rest — confirmed live, noise well under
0.01V — so even a short window separates a real drop from a fluke
reading); `WARN_VOLTAGE=11.0` is set *above* ArduPilot's own real
low-battery failsafe default (`BATT_LOW_VOLT=10.5V`, confirmed from
ArduPilot's own source) on purpose — a runtime monitor's job is to warn
*before* the autopilot's own failsafe has to act, not just re-detect it
after the fact. Both numbers need the same kind of stated reasoning for
whatever you pick for GPS and your second category — "it worked when I
tried it" isn't evidence, a real justification is.
