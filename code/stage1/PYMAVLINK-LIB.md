# Working with MAVLink in Python
## Our Lightweight MAVLink Library

One of the goals of this course is to build intelligent UAV applications—not
to spend every lab wrestling with the details of the MAVLink protocol.

Historically, many Python UAV projects used **DroneKit-Python**, which provided
a high-level object-oriented interface to ArduPilot. Unfortunately,
DroneKit is no longer actively maintained and is not compatible with many
recent versions of ArduPilot.

Instead, this course uses **pymavlink**, the official Python MAVLink library.
However, pymavlink operates at a much lower level than DroneKit. Rather than
providing simple methods such as

```python
vehicle.arm()
vehicle.takeoff(10)
vehicle.goto(...)
```

it requires software to manually construct MAVLink messages.

To make application development simpler, we created our own lightweight
library:

```text
backend/mavlink_lib.py
```

Think of this library as **our replacement for DroneKit**.

Its purpose is to hide the low-level MAVLink protocol and expose a small,
easy-to-understand programming interface for this course.

---

# Software Architecture

Our software stack looks like this:

```text
Your Python Application
        │
        ▼
   mavlink_lib.py
        │
        ▼
     pymavlink
        │
        ▼
 MAVLink Protocol
        │
        ▼
     ArduPilot
```

Your applications should almost never call `pymavlink` directly.

Instead, they call the higher-level functions provided by `mavlink_lib.py`.

---

# Why Create Our Own Library?

Without this library, every application would need to understand the details
of the MAVLink protocol.

For example, both our MQTT backend and our scripted missions need to:

- connect to the vehicle
- arm the vehicle
- take off
- fly to waypoints
- land

Rather than duplicating that code in every application, we implemented these
operations once.

```text
MQTT Backend
       │
       │
Simple Flight Script
       │
       │
Future AI Planner
       │
       ▼
   mavlink_lib.py
```

This gives us several software engineering benefits:

- One implementation of every flight command
- Less duplicated code
- Easier maintenance
- Consistent behavior across every application
- A much simpler API for students

---

# The Public API

The current library provides six high-level operations.

```python
connect(connection_string)

arm(connection)

disarm(connection)

takeoff(connection, altitude)

goto(connection, latitude, longitude, altitude)

land(connection)
```

Notice how these functions describe **what** we want the UAV to do rather than
**how** MAVLink messages are constructed.

---

# Connecting to the Vehicle

```python
conn = connect("udp:127.0.0.1:14550")
```

Internally this creates a MAVLink connection using `pymavlink`.

```python
conn = mavutil.mavlink_connection(conn_str)
```

Immediately afterwards we wait for the vehicle to send a **heartbeat**.

```python
conn.wait_heartbeat()
```

This serves two important purposes.

1. It confirms that ArduPilot is actually running.

2. It discovers the vehicle's

- system ID
- component ID

These identifiers are automatically used when sending future commands.

---

# Arming the Vehicle

To arm the UAV we simply write

```python
arm(conn)
```

Internally this constructs and sends a MAVLink message named

```text
COMMAND_LONG
```

whose command field is

```text
MAV_CMD_COMPONENT_ARM_DISARM
```

The MAVLink message is transmitted to ArduPilot.

ArduPilot then decides whether it is safe to arm.

Notice that **sending a command does not guarantee it will be executed**.
The autopilot may reject it if pre-arm safety checks have not passed.

---

# Taking Off

```python
takeoff(conn, 10)
```

This performs several operations automatically.

1. Switches the vehicle into GUIDED mode.

2. Arms the vehicle.

3. Sends the MAVLink takeoff command.

The caller does not need to remember this sequence.

Instead, taking off becomes a single high-level operation.

---

# Flying to a Position

```python
goto(conn,
     latitude,
     longitude,
     altitude)
```

This sends a MAVLink message named

```text
SET_POSITION_TARGET_GLOBAL_INT
```

Unlike `COMMAND_LONG`, this message contains many possible fields.

For example:

- latitude
- longitude
- altitude
- velocity
- acceleration
- yaw
- yaw rate

Most of these are irrelevant for our course.

We only wish to specify a destination.

---

# Understanding the Type Mask

The destination message contains a **type mask**.

The purpose of the mask is to tell ArduPilot which fields should be ignored.

Imagine a packet containing

```text
Latitude
Longitude
Altitude
Velocity
Acceleration
Yaw
Yaw Rate
```

Our application only wants to control position.

The type mask therefore tells ArduPilot

```text
Ignore velocity.

Ignore acceleration.

Ignore yaw.

Ignore yaw rate.
```

Only

- latitude
- longitude
- altitude

are actually used.

---

# Why Use Bit Masks?

Each "ignore" option is represented by a single binary bit.

For example

```text
Ignore Velocity X
Ignore Velocity Y
Ignore Velocity Z
Ignore Yaw
Ignore Yaw Rate
```

The library combines these bits using the bitwise OR operator.

```python
_GOTO_TYPE_MASK = (
    POSITION_TARGET_TYPEMASK_VX_IGNORE |
    POSITION_TARGET_TYPEMASK_VY_IGNORE |
    POSITION_TARGET_TYPEMASK_VZ_IGNORE |
    ...
)
```

The resulting integer is transmitted inside the MAVLink packet.

ArduPilot examines the bits to determine which fields should be ignored.

Fortunately, application developers rarely need to think about these details—
our library hides them.

---

# Landing

Landing is the simplest command.

```python
land(conn)
```

Internally it sends

```text
COMMAND_LONG

MAV_CMD_NAV_LAND
```

ArduPilot performs the landing.

---

# Why Do We Multiply Latitude by 10⁷?

You may notice

```python
int(latitude * 1e7)
```

inside the library.

MAVLink stores latitude and longitude as **32-bit integers**, not floating-point
numbers.

For example

```text
41.7012345°
```

becomes

```text
417012345
```

This preserves high precision while keeping the protocol efficient and
consistent across different processors.

---

# Why Should Applications Use This Library?

As the semester progresses you will write increasingly sophisticated UAV
applications.

Rather than learning dozens of MAVLink message types, your code can simply
write

```python
takeoff(conn, 20)

goto(conn, lat, lon, 20)

land(conn)
```

This keeps your software focused on **mission logic**, AI, planning, and
decision-making rather than low-level communication details.

Whenever new capabilities are added—for example

- Return to Launch
- Set Airspeed
- Loiter
- Orbit
- Change Heading

they will be implemented once inside `mavlink_lib.py` and immediately become
available to every application in the course.

---

# Summary

Our `mavlink_lib.py` library provides a lightweight, reusable interface for
communicating with ArduPilot.

It replaces the role once served by DroneKit-Python while remaining small,
easy to understand, and compatible with modern versions of ArduPilot.

Most importantly, it allows the rest of the course to focus on **building
intelligent autonomous systems** rather than constructing MAVLink packets.