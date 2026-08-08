# Native AI + UAV Systems
# Lab 1 – Setting Up Your Development Environment

Welcome to the first lab for **Native AI + UAV Systems**.

In this lab you will install and configure the software environment used
throughout the course. By the end of the lab you will have a complete UAV
simulation environment running on your laptop, capable of executing
autonomous flights and publishing live telemetry.

This is primarily a **one-time setup**. Once your environment is working,
future labs will focus on building intelligent UAV applications rather than
configuring software.

---

# Learning Objectives

By the end of this lab you will be able to:

- Install the course software.
- Run a complete UAV simulation environment.
- Verify that all software components are communicating correctly.
- Dispatch your first autonomous flight.
- Observe live telemetry from the simulated UAV.

---

# What You Are Building

Rather than installing a collection of unrelated programs, you are assembling
a complete software ecosystem for UAV development.

```
GitHub Repository
        ↓
Python Environment
        ↓
Backend Services (Docker)
        ↓
ArduPilot SITL
        ↓
Your UAV Applications
```

At the end of this lab you will have a simulated drone that can receive
commands, publish telemetry, and execute autonomous missions.

---

# Before You Begin

Estimated time: **20–30 minutes**

You will need:

- A reliable Internet connection
- Administrator privileges on your computer
- Hardware virtualization (Intel VT-x / AMD-V) enabled in your BIOS/UEFI --
  on by default on most machines, but see the Troubleshooting section below
  if Docker complains about it
- Approximately 5 GB of available disk space

---

# Step 1 – Install Prerequisites

Before running the course software, install the tools required to build and
run the development environment.

### Required Software

- Git
- Python 3.12 or later (check with `python3 --version`)
- Docker

### Platform-specific notes

- **Linux / WSL2 (Windows):** Install Docker Engine (or Docker Desktop with
  the WSL2 backend). If you're on Windows, do everything from inside a
  **WSL2 terminal** -- PowerShell and Command Prompt are not supported for
  this course. If WSL2 itself isn't installed, run `wsl --install` from an
  admin PowerShell first.
- **Mac (Intel or Apple Silicon):** Install Docker Desktop.
  - **Apple Silicon only:** the SITL image is `linux/amd64` (ArduPilot's own
    dev-toolchain base image doesn't publish an arm64 build). Docker Desktop
    runs it under Rosetta-accelerated emulation, which is fast enough for
    this course, but you must enable it once: **Docker Desktop → Settings →
    General → "Use Rosetta for x86_64/amd64 emulation on Apple Silicon."**
    Also raise Docker Desktop's CPU/memory limits from the defaults
    (Settings → Resources) -- the out-of-the-box limits are commonly too low
    for SITL.

---

# Step 2 – Download the Course Repository

The course repository will contain every lab, example, script, and configuration
file used throughout the semester.  These will be updated each week prior to use.

Clone the repository:

```bash
git clone https://github.com/JaneClelandHuang/uav-native-ai.git
cd uav-native-ai/code/stage1
```

All commands in this guide should be executed from the `code/stage1`
directory unless stated otherwise.

---

# Step 3 – Create the Python Environment

A Python virtual environment isolates the packages used in this course from
other Python projects installed on your computer.

Copy the environment configuration. `.env` itself is gitignored -- it's your
local config, kept out of git so your edits never conflict with the weekly
repo updates -- so it isn't something the clone can hand you directly.
Instead, two ready-to-use starting points are tracked in the repo, each
meant to be copied as-is:

- `.env-copy` -- single drone (`NUM_DRONES=1`), matching every command in
  this lab. Use this one now.
- `.env-copy-multi` -- three drones (`NUM_DRONES=3`), matching
  `scripts/fleet_demo/run_fleet_demo.py`. Come back to this later, once
  you're past this lab and want a multi-vehicle fleet, by copying it over
  `.env` the same way.

Both include `UPDATE_DRONE`, required for the `new-gui` viewer. `.env.example`
is a third, separate file -- an annotated reference for hand-building your
own `.env` from scratch -- not something to copy directly.

```bash
cp .env-copy .env
```

Create the virtual environment:

```bash
python3 -m venv client/.venv
```

Install the required Python packages:

```bash
client/.venv/bin/pip install -r client/requirements.txt
```

---

# Step 4 – Start the Development Environment

Docker starts the software infrastructure required for the course.

This includes:

- MQTT broker (Mosquitto)
- Backend services
- ArduPilot Software-in-the-Loop (SITL)

These components run together as a reproducible development environment,
independent of your operating system.

First, generate your fleet configuration. `docker-compose.yml` doesn't fix
how many vehicles run or where they start -- that's computed by a script
from settings in `.env`:

```bash
python3 scripts/generate_fleet.py
```

The defaults (`CENTER_LOCATION=ND`, `NUM_DRONES=1`) start a single vehicle
at Notre Dame, matching every command in the rest of this lab. To fly
somewhere else or with more vehicles, edit `.env`: `CENTER_LOCATION` picks
a saved spot from `locations.json` by nickname (add your own entries there
-- each needs `name`, `nickname`, `lat`, `lon`, `alt`), and `NUM_DRONES`
(1-7) scatters that many vehicles around it. Re-run this script any time
you change either value -- it only rewrites `docker-compose.override.yml`,
it does not itself start or stop anything.

For a one-off run without editing `.env`, pass flags instead:
`python3 scripts/generate_fleet.py --location CMAC --num-drones 3`
(`--help` lists all of them). Flags only affect that run -- `.env` is left
untouched either way.

Then pull the images:

```bash
docker compose pull
```

> **This step can take several minutes the first time.** The SITL image is
> ~3.7 GB, so on a normal connection expect this to take a few minutes --
> possibly longer on a slow or restricted network. This is a one-time cost:
> once the image is pulled it's cached, and every future `docker compose`
> command reuses it. Let it run to completion rather than assuming it has
> hung.

Then build and start the containers:

```bash
docker compose up -d
```

The first run also builds the backend image, which takes another moment.
Confirm the services from `generate_fleet.py`'s output are up:

```bash
docker compose ps
```

With the default `NUM_DRONES=1` you should see three containers:
`mosquitto`, `sitl_1`, and `drone_backend_1`. If you raised `NUM_DRONES`,
you'll see a `sitl_N`/`drone_backend_N` pair for each additional vehicle.
This lab only ever exercises vehicle 1 (`VEHICLE_ID=1` in `.env`) --
additional vehicles are there for multi-vehicle frontends (e.g. `new-gui`)
to connect to; `matplotlib_view.py` itself only ever shows one vehicle at a
time.

---

# Step 5 – Run the Automated Health Check

Professional software projects should verify that their environments are
configured correctly rather than assuming everything is working. This
script also runs `docker compose up -d` itself (harmless to repeat -- the
containers from Step 4 are already up, so it's a no-op there), then waits
for telemetry and does an arm round-trip.

Step 4 stays a separate step on purpose: on a first run, pulling/building
the ~3.7GB SITL image can take long enough that running it inside this
script's bounded timeouts caused false failures. Doing it as its own step
first gives you visibility into that pull/build progress instead of it
looking like a hang.

Activate the virtual environment:

```bash
source client/.venv/bin/activate
```

Run:

```bash
python scripts/verify_setup.py
```

The health check verifies that:

| Component | Purpose |
|-----------|---------|
| Docker | Containers start successfully |
| Fleet config | `docker-compose.override.yml` exists (from Step 4's `generate_fleet.py`) |
| MQTT Broker | Message broker is reachable |
| Backend | Backend service is running |
| ArduPilot SITL | Simulator is operational |
| Telemetry | Vehicle state is being published |
| Commands | MQTT commands reach the simulator |

A successful installation ends with:

```text
PASS: Environment is fully working.
```

If a problem is detected, the script explains what failed and how to fix it.

---

# Step 6 – Launch the Viewer

The viewer provides a simple graphical display of the simulated UAV.

The virtual environment should still be active from Step 5. If you opened a
new terminal, activate it again first: `source client/.venv/bin/activate`.

Launch the viewer:

```bash
python client/matplotlib_view.py
```

You should see:

- Vehicle position
- Heading
- Altitude

Initially the vehicle will remain stationary because no commands have yet
been sent.

---

# Step 7 – Fly Your First Mission

The final step confirms that the entire software stack is working correctly.

Open a **second terminal** and run:

```bash
cd uav-native-ai/code/stage1

source client/.venv/bin/activate

python scripts/test_flight.py
```

The mission automatically:

1. Arms the vehicle
2. Takes off
3. Flies a small square
4. Lands

Watch the viewer window as telemetry updates in real time.

> **Optional:** to manually arm or change mode from the SITL side instead of
> through the MQTT command channel, `docker compose attach sitl_1` gives you
> MAVProxy's plain command prompt. Detach without stopping the container
> with `Ctrl-p Ctrl-q` -- **not** `Ctrl-C`, which kills the simulation.

---

# Step 8 – Shut Down the Environment

When you are finished:

```bash
docker compose down
```

This stops all Docker containers while preserving your configuration for
future labs.

---

# Troubleshooting

## Docker Desktop not installed

`docker compose pull` in Step 4 will fail with a "command not found" style
error. `verify_setup.py` also checks for this and tells you to install it.

---

## Docker daemon not running

Start Docker Desktop or run:

```bash
sudo systemctl start docker
```

Wait until Docker reports that it is running before continuing.

---

## Windows

Run the course entirely from a **WSL2 terminal**.

PowerShell and Command Prompt are not supported for this course.

---

## Apple Silicon

Enable Rosetta emulation in Docker Desktop and increase Docker's CPU and
memory allocation if SITL performs poorly.

---

## Corporate VPN / firewall blocking image pulls

`docker compose pull` will fail (or hang) trying to reach `eclipse-mosquitto`
or the SITL image on GHCR. Try a different network, or ask IT to allowlist
Docker Hub / GHCR.

---

## Port already in use

Stop any previous containers:

```bash
docker compose down
```

Then re-run `docker compose up -d` (Step 4) and the health check.

---

## Virtualization disabled in BIOS

Docker Desktop (or `docker info` on Linux/WSL2) will report this explicitly
-- on Windows it usually shows up as a WSL2 install failure or a "Hardware
assisted virtualization and data execution protection must be enabled"
message. It's almost always just off by default rather than actually
unavailable:

1. Reboot and enter BIOS/UEFI setup (commonly `F2`, `F10`, `Del`, or `Esc`
   at boot -- check your manufacturer if none of those work).
2. Find the virtualization setting -- named **Intel VT-x**, **AMD-V**,
   **SVM Mode**, or generically **Virtualization Technology**, usually under
   a CPU or Advanced/Security menu.
3. Enable it, save, and exit (often `F10`).
4. On Windows, also make sure the WSL2 and Virtual Machine Platform features
   are turned on: `wsl --install` from an admin PowerShell (see Step 1)
   enables both.

---

## Health check fails immediately after startup

This is very likely benign, not a real failure: ArduCopter refuses to arm
until its EKF/GPS pre-arm checks pass, which can take 30-60 seconds after
startup.

Wait approximately one minute and rerun:

```bash
python scripts/verify_setup.py
```

If it still fails, `docker compose logs sitl_1` will show a specific `PreArm`
message.

---

## Still having problems?

Before asking for instructor assistance:

1. Read the error message carefully.
2. Review this troubleshooting guide.
3. Compare your setup with a nearby classmate.
4. Ask a teaching assistant or instructor if the problem persists.

---

# Congratulations!

You now have a fully functioning UAV development environment.

From this point onward, the focus of the course shifts from configuring
software to engineering intelligent autonomous UAV applications.
