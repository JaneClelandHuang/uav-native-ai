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
- Approximately 5 GB of available disk space

If you don't have administrator rights or virtualization is disabled in your
BIOS, don't spend the class period fighting it -- switch to the cloud
fallback (Codespaces or an equivalent Docker-in-Docker environment) instead.

---

# Step 1 – Install Prerequisites

## Why?

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

## Why?

The course repository contains every lab, example, script, and configuration
file used throughout the semester.

Clone the repository:

```bash
git clone https://github.com/JaneClelandHuang/uav-native-ai.git
cd uav-native-ai/code/stage1
```

All commands in this guide should be executed from the `code/stage1`
directory unless stated otherwise.

---

# Step 3 – Create the Python Environment

## Why?

A Python virtual environment isolates the packages used in this course from
other Python projects installed on your computer.

Copy the environment configuration:

```bash
cp .env.example .env
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

## Why?

Docker starts the software infrastructure required for the course.

This includes:

- MQTT broker (Mosquitto)
- Backend services
- ArduPilot Software-in-the-Loop (SITL)

These components run together as a reproducible development environment,
independent of your operating system. You don't start them by hand -- the
health check script in the next step brings them up for you.

---

# Step 5 – Run the Automated Health Check

## Why?

Professional software projects should verify that their environments are
configured correctly rather than assuming everything is working.

Run:

```bash
client/.venv/bin/python scripts/verify_setup.py
```

The health check verifies that:

| Component | Purpose |
|-----------|---------|
| Docker | Containers start successfully |
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

## Why?

The viewer provides a simple graphical display of the simulated UAV.

Activate the virtual environment:

```bash
source client/.venv/bin/activate
```

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

## Why?

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
> through the MQTT command channel, `docker compose attach sitl` gives you
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

`verify_setup.py` catches this first and tells you to install it.

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

`docker compose up` will fail to pull `eclipse-mosquitto` or the SITL image.
Try a different network, or ask IT to allowlist Docker Hub / GHCR.

---

## Port already in use

Stop any previous containers:

```bash
docker compose down
```

Then rerun the health check.

---

## No admin rights / virtualization disabled in BIOS

This isn't fixable in a class period -- switch to the cloud fallback
(Codespaces or equivalent Docker-in-Docker environment) instead of
continuing to troubleshoot locally.

---

## Health check fails immediately after startup

This is very likely benign, not a real failure: ArduCopter refuses to arm
until its EKF/GPS pre-arm checks pass, which can take 30-60 seconds after
startup.

Wait approximately one minute and rerun:

```bash
python scripts/verify_setup.py
```

If it still fails, `docker compose logs sitl` will show a specific `PreArm`
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
