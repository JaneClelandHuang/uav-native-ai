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

The destination message, `SET_POSITION_TARGET_GLOBAL_INT`, has one field for
every possible thing you might want to control. Each field has its own bit
in a single 12-bit number:

```text
bit  0  ->  X / latitude
bit  1  ->  Y / longitude
bit  2  ->  Z / altitude
bit  3  ->  velocity X
bit  4  ->  velocity Y
bit  5  ->  velocity Z
bit  6  ->  acceleration X
bit  7  ->  acceleration Y
bit  8  ->  acceleration Z
bit  9  ->  force (rarely used)
bit 10  ->  yaw
bit 11  ->  yaw rate
```

That 12-bit number is the **type mask**. For every bit:

```text
0  ->  "use the value I put in this field"
1  ->  "ignore this field completely"
```

A bit set to `1` does **not** mean "on" or "enabled." It means the opposite:
"I am not telling you anything about this field -- don't read it." This
trips people up the first time, so it's worth saying twice: `1` = ignore,
`0` = use.

---

# Building `goto()`'s Mask, Bit by Bit

`goto()` only wants to control **position** (latitude, longitude, altitude).
Everything else should be ignored. So bits 0, 1, 2 stay `0`, and every other
bit gets set to `1`:

```text
bit:    11  10   9   8   7   6   5   4   3   2   1   0
field:  yr  yaw  F   az  ay  ax  vz  vy  vx  Z   Y   X
value:   1   1   0   1   1   1   1   1   1   0   0   0
```

Read left to right, that's the binary number `110111111000`, which is
`3576` in decimal (`0xdf8` in hex) -- exactly the value
`mavlink_lib.py`'s `_GOTO_TYPE_MASK` computes.

We never write `3576` directly in the code, because nobody could read it
back and know what it means. Instead we build it out of named constants
with the bitwise OR operator (`|`) -- one constant per bit we want to set to
`1`:

```python
_GOTO_TYPE_MASK = (
    POSITION_TARGET_TYPEMASK_VX_IGNORE           # bit 3
    | POSITION_TARGET_TYPEMASK_VY_IGNORE         # bit 4
    | POSITION_TARGET_TYPEMASK_VZ_IGNORE         # bit 5
    | POSITION_TARGET_TYPEMASK_AX_IGNORE         # bit 6
    | POSITION_TARGET_TYPEMASK_AY_IGNORE         # bit 7
    | POSITION_TARGET_TYPEMASK_AZ_IGNORE         # bit 8
    | POSITION_TARGET_TYPEMASK_YAW_IGNORE        # bit 10
    | POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE   # bit 11
)
```

Notice which three constants are **not** in that list:
`X_IGNORE`, `Y_IGNORE`, `Z_IGNORE` (bits 0, 1, 2). Leaving them out is what
leaves those bits at `0` -- which is exactly what tells ArduPilot "use the
latitude/longitude/altitude I'm sending you."

This is also why the field values themselves matter: a `0` bit means
ArduPilot *will* read that field, so if you ever OR in, say, velocity
control by removing `VX_IGNORE`/`VY_IGNORE`/`VZ_IGNORE` from the mask, you
must also put real numbers in the velocity arguments to
`set_position_target_global_int_send` -- right now those are hardcoded to
`0`, which would suddenly mean "fly at exactly zero velocity" instead of
"I don't care about velocity."

---

# Why Use Bit Masks Instead of, Say, a Dictionary?

Bit masks are how MAVLink -- and most low-level binary protocols -- pack
many independent yes/no flags into the smallest possible number of bytes on
the wire. Twelve `True`/`False` flags fit into a single 16-bit integer on
the wire instead of twelve separate fields.

You'll see this same pattern elsewhere in MAVLink (for example, the
"armed" bit inside a `HEARTBEAT` message's `base_mode` field, which
`mavlink_lib.py`'s `arm()`/`disarm()` set via `MAV_CMD_COMPONENT_ARM_DISARM`
rather than a raw bit -- but something on the ArduPilot side is still just
flipping one bit). It's worth being able to read a mask like this one, even
though `mavlink_lib.py` hides it from you in day-to-day use.

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