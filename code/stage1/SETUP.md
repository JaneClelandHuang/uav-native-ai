# Setup

One command, not a guide to follow by hand: once Docker is installed, run
`scripts/verify_setup.py` and follow whatever it tells you. Everything below
exists to support that script and to explain the failures it can report.

## Prerequisites (per OS)

**Linux / WSL2 (Windows):** Install Docker Engine (or Docker Desktop with
the WSL2 backend). On native Windows, do everything from inside a WSL2
terminal, not PowerShell/cmd -- this project is not tested outside WSL2 on
Windows.

**Mac (Intel or Apple Silicon):** Install Docker Desktop.
- **Apple Silicon only:** the SITL image is `linux/amd64` (ArduPilot's own
  dev-toolchain base image doesn't publish an arm64 build). Docker Desktop
  runs it under Rosetta-accelerated emulation rather than raw QEMU, which is
  fast enough for this course, but you must enable it once: **Docker
  Desktop → Settings → General → "Use Rosetta for x86_64/amd64 emulation on
  Apple Silicon."**
- Also bump Docker Desktop's CPU/memory resource limits from the defaults
  (Settings → Resources) -- the out-of-the-box limits are commonly too low
  for SITL.

## Quick start

```
cp .env.example .env
python3 -m venv client/.venv
client/.venv/bin/pip install -r client/requirements.txt
client/.venv/bin/python scripts/verify_setup.py
```

If that prints `PASS`, start the viewer:

```
MQTT_HOST=localhost client/.venv/bin/python client/matplotlib_view.py
```

To manually arm/change mode from the SITL side (rather than through the
MQTT command channel) for testing: `docker compose attach sitl` gives you
MAVProxy's plain command prompt. Detach without stopping the container with
`Ctrl-p Ctrl-q`.

## Troubleshooting index

Keyed to the actual failure, not diagnosed live each time:

- **Docker Desktop not installed** -- `verify_setup.py` catches this first
  and tells you to install it.
- **Docker daemon installed but not running** -- start Docker Desktop (or
  `sudo systemctl start docker` on Linux) and wait for it to report
  "running" before re-running the script.
- **WSL2 not enabled (Windows)** -- Docker Desktop needs it as a backend;
  enable it in Docker Desktop's settings, or `wsl --install` from an admin
  PowerShell if WSL2 itself isn't installed at all.
- **Apple Silicon: Rosetta emulation not enabled** -- see the Mac
  prerequisite above; without it the SITL image either fails to run or runs
  very slowly under plain QEMU emulation.
- **Apple Silicon: Docker resource limits too low** -- raise CPU/memory in
  Docker Desktop's settings.
- **Corporate VPN/firewall blocking image pulls** -- `docker compose up`
  will fail to pull `eclipse-mosquitto` or the SITL image; try a different
  network, or ask IT to allowlist Docker Hub / GHCR.
- **Port already in use** -- usually a leftover container from a previous
  run. `docker compose down`, then re-run `verify_setup.py`.
- **No admin rights / virtualization disabled in BIOS** -- not fixable in a
  class period; use the cloud fallback (Codespaces or equivalent
  Docker-in-Docker environment) instead of continuing to troubleshoot
  locally.
- **`verify_setup.py` fails the arm-command check right after a cold
  start** -- this is very likely benign, not a real failure: ArduCopter
  refuses to arm until its EKF/GPS pre-arm checks pass, which can take
  30-60s after `docker compose up`. Wait a bit and re-run. If it still
  fails, `docker compose logs sitl` will show a specific `PreArm` message.
- **Nothing else works** -- pair with a neighbor whose setup is working
  before escalating; most classroom failures are one of the above.

## Instructor-only: publishing a pinned SITL image

Students should `docker pull`, never build ArduPilot from source in class
(a source build takes 10-20 minutes). To build and publish the pinned image:

```
GHCR_OWNER=your-org ./scripts/build_and_push_sitl.sh Copter-4.6.3
```

Then set `SITL_IMAGE=ghcr.io/your-org/uav-course-sitl:copter-4.6.3` in the
`.env` file you distribute to students. Bumping the ArduPilot version for a
later course run means re-running this script with a new tag and updating
that one `.env` value -- nothing else in the repo needs to change.
