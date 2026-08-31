# Lesson 2 — ATC assignment support files

Full assignment: [Lesson 2](https://janeclelandhuang.github.io/uav-native-ai/lessons/lesson2.html).

You design and build the ATC from scratch. These files are only the
workload to develop against and a reminder of the interface you already
have from Lesson 1.

## Fleet

Every workload runs on the same fleet — three UAVs on a ring around the
home coordinate. Bring it up from `lab/` first:

```bash
cp .env-copy-multi .env
sed -i 's/^DRONE_SPACING_M=.*/DRONE_SPACING_M=52/' .env      # or edit .env by hand
NUM_DRONES=3 DRONE_SPACING_M=52 CENTER_LOCATION=ND python3 scripts/generate_fleet.py
docker compose up -d --remove-orphans
```

UAV 1 starts ~30 m north of home; UAVs 2 and 3 to the south-east and
south-west; adjacent UAVs are ~52 m apart. Home is
`41.698575, -86.237055` (225 m AMSL). Each UAV also publishes its exact
start point on the retained `uav/<id>/home` topic.

## Files

| File | |
|---|---|
| `test1.json` | 2 UAVs, one crossing conflict. The simplest case — start here. |
| `test2.json` | 3 UAVs, two missions each. All three cross the area at once, then spread out to land. |
| `test3.json` | 3 UAVs, three missions each. The `test2` pattern repeated back to back. |
| `start_tests.py` | **You write this.** `python lab/lesson2/start_tests.py <workload.json> <min-separation-m>` — starts your ATC and runs the given workload to completion. |

Develop against all three. Workload format is in the assignment under
*Flight Workloads*. Your submitted system is also run against **additional
workloads you have not seen**, so don't hard-code to these.

## The interface you already have (Lesson 1)

Everything your ATC needs is already on MQTT (`localhost:1883`). See
`lab/ARCHITECTURE.md` for the full contract.

| Topic | Direction | Payload |
|---|---|---|
| `uav/<id>/telemetry` | UAV → you | `{lat, lon, alt_rel, alt_amsl, heading, groundspeed, battery_*, armed, mode, activity}` at 4 Hz |
| `uav/<id>/home` | UAV → you | retained `{lat, lon, alt}` — the UAV's start point |
| `uav/<id>/command` | you → UAV | one of the commands below |

Commands (publish as JSON to `uav/<id>/command`):

```json
{"type": "arm"}
{"type": "takeoff", "alt": 15}
{"type": "goto", "lat": 41.7, "lon": -86.24, "alt": 15}
{"type": "interrupt"}
{"type": "land"}
```

`goto` / `takeoff` altitude is metres above home. `interrupt` drops the
UAV out of GUIDED into LOITER (holds position). `scripts/test_flight.py`
is a worked example of driving one UAV through one mission over this
contract — a useful reference, but it is single-UAV and blocking, so it
is not a design your ATC can use directly.

The 2 m mission-arrival tolerance is fixed — the grading monitor uses it,
so use the same value.
