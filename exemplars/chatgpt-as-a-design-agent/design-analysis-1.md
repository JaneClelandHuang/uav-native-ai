# Design Analysis in Practice: From Code Smell to Better Abstraction

## Purpose

This example illustrates a design-analysis activity that should happen
*while code is being developed*, not only after implementation is
complete.

The workflow uses two AI agents in different roles as well as involving the developer

-   **Claude Code** works directly with the codebase and
    proposes/implements changes.
-   **ChatGPT** acts as an **independent design reviewer**, questioning
    abstractions, evaluating alternatives, and critiquing proposed
    refactorings.

The important activity is not simply asking an AI to "fix the code." It
is using independent reasoning to identify a design concern, articulate
why it matters, propose an alternative, and then critically evaluate the
implementation agent's proposed solution.

------------------------------------------------------------------------

## 1. Identifying the Design Smell

### Developer:
Why is `circle` required in every `handle_command`?  That seems clumsy, because most commands don't have anything to do with the circle? Here is the code:

```python
def handle_command(conn, payload, circle, state):
    try:
        cmd = json.loads(payload)
    except json.JSONDecodeError:
        log.warning("Ignoring malformed command payload: %r", payload)
        return

    cmd_type = cmd.get("type")
    try:
        if cmd_type != "circle":
            # Any other command abandons an in-progress circle -- otherwise
            # circle_tick() would keep firing position targets that fight
            # whatever this new command is trying to do.
            circle.stop()

        if cmd_type == "arm":
            mavlink_lib.arm(conn)
        elif cmd_type == "disarm":
            mavlink_lib.disarm(conn)
        elif cmd_type == "takeoff":
            # NAV_TAKEOFF is only honored in GUIDED mode and while armed --
            # mavlink_lib.takeoff makes "takeoff" a complete action so a
            # command producer doesn't need its own mode/arm dance first
            # (this is what manually switching to GUIDED in the MAVProxy
            # console was standing in for during testing).
            mavlink_lib.takeoff(conn, float(cmd["alt"]))
            with state.lock:
                state.activity = "taking_off"
        elif cmd_type == "goto":
            mavlink_lib.goto(conn, float(cmd["lat"]), float(cmd["lon"]), float(cmd["alt"]))
            with state.lock:
                state.activity = "flying"
        elif cmd_type == "circle":
            # circle_point() itself doesn't touch flight mode (see its
            # docstring) since it's called many times a second -- GUIDED
            # only needs setting once, here, before circle_tick() starts
            # calling it on the main loop's cadence.
            conn.set_mode("GUIDED")
            circle.start(
                center_lat=float(cmd["lat"]), center_lon=float(cmd["lon"]),
                alt_rel_m=float(cmd["alt"]), radius_m=float(cmd["radius"]),
                degrees=float(cmd["degrees"]), speed_mps=float(cmd["speed"]),
            )
            with state.lock:
                state.activity = "circling"
        elif cmd_type == "fly_home":
            # Just goto() at the remembered home position -- no new MAVLink
            # primitive needed, the same way circle reused goto()'s
            # underlying send rather than inventing one. Transits at
            # whatever's higher of the current altitude or
            # FLY_HOME_MIN_ALT_M, so a low-altitude command doesn't drag the
            # vehicle home skimming the ground, but a already-high vehicle
            # doesn't needlessly climb first either. land is a deliberately
            # separate follow-up command, same as after a goto.
            with state.lock:
                home_lat, home_lon, current_alt = state.home_lat, state.home_lon, state.alt_rel
            if home_lat is None or home_lon is None:
                log.warning("Ignoring fly_home: home position not yet captured")
            else:
                target_alt = max(current_alt, FLY_HOME_MIN_ALT_M) if current_alt is not None else FLY_HOME_MIN_ALT_M
                mavlink_lib.goto(conn, home_lat, home_lon, target_alt)
                with state.lock:
                    state.activity = "flying"
        elif cmd_type == "interrupt":
            mavlink_lib.interrupt(conn)
            with state.lock:
                # Best fit from the activity vocabulary for "holding
                # position, still airborne" -- there's no distinct
                # "Holding"/"Loiter" state in what new-gui.py's bridge maps
                # to, and this isn't landing or circling anymore.
                state.activity = "flying"
        elif cmd_type == "land":
            mavlink_lib.land(conn)
            with state.lock:
                state.activity = "landing"
        else:
            log.warning("Ignoring unknown command type: %r", cmd_type)
    except (KeyError, ValueError, TypeError) as exc:
        log.warning("Ignoring invalid command %r: %s", cmd, exc)
```

```python
def on_message(client, userdata, msg):
    handle_command(
        userdata["conn"], msg.payload.decode("utf-8", errors="replace"),
        userdata["circle"], userdata["state"],
    )
```

### ChatGPT
Notice that `on_message()` passes `userdata["circle"]` into the generic `handle_command()` path for **every** incoming command, regardless of whether the command itself is a circle command.


The relevant code in `drone_backend.py` was:

``` python
def handle_command(conn, payload, circle, state):
    ...
```

Every MQTT command was dispatched through this function, including
commands such as:

``` json
{"type": "land"}
```

Yet `circle` was an `ActiveCircle` object associated with one particular
kind of persistent maneuver.

The code used it in two important ways:

``` python
if cmd_type != "circle":
    circle.stop()
```

and:

``` python
elif cmd_type == "circle":
    ...
    circle.start(...)
```

------------------------------------------------------------------------

## 2. Independent Design Critique

### ChatGPT

Yes. **It is clumsy**, and the reason is quite specific.

`circle` is an `ActiveCircle` object representing the state of a
currently executing **circle command**. It is created once in `main()`:

``` python
state = VehicleState()
circle = ActiveCircle()
```

and both are placed into Paho's `userdata`. Every MQTT command therefore
eventually arrives at:

``` python
def handle_command(conn, payload, circle, state):
```

even when the command has nothing inherently to do with circling.

There are two reasons the current implementation needs the object:

1.  A `"circle"` command starts an ongoing circle maneuver.
2.  Every command other than `"circle"` cancels an existing circle so
    that `circle_tick()` does not continue generating position targets
    that conflict with the new command.

The **behavior makes sense**. The concern is the **abstraction**.

Conceptually, the parameters are:

``` text
conn      -> connection to the vehicle
payload   -> new command
state     -> state of the vehicle
circle    -> state of ONE PARTICULAR kind of command
```

The final parameter is different from the others. `handle_command()` is
a generic dispatcher, but it explicitly depends on state belonging to
one specific command type.

That creates an extensibility problem. If the system later adds
persistent behaviors such as:

``` text
survey
orbit
follow
search_pattern
return_home_sequence
```

we do not want the signature to evolve into:

``` python
handle_command(
    conn,
    payload,
    circle,
    survey,
    follow,
    search_pattern,
    state
)
```

The deeper abstraction appears to be something closer to an **active
command**, **active maneuver**, or **ongoing behavior**.

Most commands are effectively one-shot operations:

``` text
takeoff  -> send MAVLink command
goto     -> send MAVLink command
land     -> send MAVLink command
```

But `circle` is different:

``` text
circle -> START ongoing maneuver
             |
             v
         circle_tick()
             |
             v
         circle_tick()
             |
             v
         circle_tick()
```

When another command arrives:

``` text
new command
    |
    v
cancel active maneuver
    |
    v
execute new command
```

So `circle` happens to be the **first command that requires persistent
execution state**. The generic command-dispatch architecture should not
expose that particular implementation detail.

A possible refactoring would therefore replace `ActiveCircle` in the
generic infrastructure with something like:

``` python
ActiveManeuver
```

or:

``` python
ActiveCommand
```

The key design goal is not merely renaming the object. The goal is to
ensure that adding another persistent maneuver does **not** require
threading another maneuver-specific parameter through `main()`, MQTT
`userdata`, `on_message()`, and `handle_command()`.

------------------------------------------------------------------------

## 3. Turning the Critique into a Request for the Coding Agent

### Developer

> Can you please write this complaint in a way I can hand over to Claude
> Code?

### ChatGPT

A useful request to the coding agent should describe the **design
problem and constraints** without over-prescribing the solution:

> Please review the design around `ActiveCircle` and `handle_command()`
> in `drone_backend.py`.
>
> I am concerned that the current abstraction is too specific and will
> not scale well.
>
> Currently we have:
>
> ``` python
> def handle_command(conn, payload, circle, state):
> ```
>
> where `circle` is an `ActiveCircle` instance. `handle_command()` needs
> this object for two reasons:
>
> 1.  A `"circle"` command starts an ongoing circle maneuver.
> 2.  Every non-circle command calls `circle.stop()` so that
>     `circle_tick()` does not continue generating MAVLink position
>     targets that conflict with the new command.
>
> The behavior itself makes sense. My concern is the **design**.
>
> `handle_command()` is a generic command dispatcher, but one of its
> parameters represents state associated with one particular command
> type. As we add other persistent behaviors---e.g., survey, search
> pattern, follow, orbit, etc.---I do not want the signature to evolve
> into something like:
>
> ``` python
> handle_command(conn, payload, circle, survey, search_pattern, follow, state)
> ```
>
> Please refactor this so that the generic command-handling
> infrastructure does not depend explicitly on `ActiveCircle`.
>
> I think the underlying abstraction is closer to an **active command /
> active maneuver / ongoing behavior**: most commands such as `takeoff`,
> `goto`, and `land` result in a MAVLink command being issued, while
> `circle` is currently special because it establishes persistent state
> that must be advanced on subsequent main-loop ticks and cancelled when
> another command supersedes it.
>
> Please:
>
> -   Examine the existing code and choose an appropriate general
>     abstraction for this ongoing behavior.
> -   Refactor `ActiveCircle`, `handle_command()`, and `circle_tick()`
>     accordingly.
> -   Preserve the existing circle behavior and thread-safety.
> -   Preserve the rule that issuing another flight command cancels an
>     active circle before the new command takes effect.
> -   Keep the implementation simple enough for students to understand;
>     avoid introducing an elaborate command-pattern/framework just to
>     solve this.
> -   Design it so that adding another persistent maneuver later would
>     not require adding another maneuver-specific parameter to
>     `handle_command()`.
>
> Before making the change, briefly explain the design you propose and
> why it is cleaner than passing `ActiveCircle` directly through the
> generic command-dispatch path.

A deliberate feature of this request is that it does **not** tell the
coding agent exactly which classes to create. The agent is asked to
solve the architectural problem, making its design proposal something
that can then be independently evaluated.

------------------------------------------------------------------------

## 4. Claude Code Proposes a Design

### Claude Code

Claude first checked whether the relevant names were coupled elsewhere
in the repository and then proposed the following design before changing
the code.

#### `CircleManeuver`

A plain class holding the circle parameters currently stored as a raw
dictionary in `ActiveCircle.params`, plus:

``` python
tick(conn) -> bool
```

The body of the existing `circle_tick()` would move into this class so
that the logic for progressing a circle belongs to the maneuver itself
rather than to the generic dispatcher/main loop.

It would also carry:

``` python
activity = "circling"
```

which would support resetting `state.activity` to `"flying"` when the
maneuver completes, while preserving the existing check that prevents a
completed old maneuver from overwriting state established by a newer
command.

#### `ActiveManeuver`

Rename/generalize `ActiveCircle` into a lock-protected single-slot
container that can hold **any maneuver object** satisfying the small
`tick(conn)` / `activity` contract.

Instead of storing circle-specific parameters:

``` python
active_maneuver.start(maneuver)
```

would accept an already-created maneuver object.

`stop()` and access to the current maneuver would remain generic.

#### `handle_command()`

The signature becomes:

``` python
handle_command(conn, payload, active_maneuver, state)
```

The generic dispatcher would no longer receive an `ActiveCircle`.

For a persistent command such as `"circle"`, the appropriate branch
would construct a `CircleManeuver` and place it into the active maneuver
slot.

For commands that supersede a persistent maneuver, the dispatcher would
stop the current active maneuver.

#### `maneuver_tick()`

The circle-specific:

``` python
circle_tick(...)
```

would become something like:

``` python
maneuver_tick(conn, active_maneuver, state)
```

The main loop would no longer know anything specifically about circles.
It would simply:

1.  retrieve the current maneuver;
2.  invoke its `tick()` operation;
3.  determine whether it has finished;
4.  clear the active maneuver and update activity state appropriately.

#### Design rationale from Claude

Adding a future `SurveyManeuver`, for example, would require a new
dispatch branch that constructs the maneuver:

``` python
active_maneuver.start(SurveyManeuver(...))
```

but would **not** require a new `survey` parameter to be threaded
through `main()`, MQTT `userdata`, `on_message()`, and
`handle_command()`.

Claude also deliberately proposed **duck typing rather than an abstract
base class or a full Command Pattern**, because the contract is very
small and the code is intended to remain understandable to students.

------------------------------------------------------------------------

## 5. Independent Review of Claude's Proposal

### Developer

> I think this proposed design is better. What do you think?

### ChatGPT

Yes. This is substantially better than merely renaming `ActiveCircle` to
`ActiveCommand`.

The strongest part is that the proposal discovers **two separate
abstractions**:

``` text
ActiveManeuver
    What persistent maneuver, if any, is currently active?

CircleManeuver
    How does this particular maneuver progress over time?
```

Previously those concerns were tangled together.

`handle_command()` can now remain a dispatcher:

``` python
handle_command(conn, payload, active_maneuver, state)
```

It still reasonably knows that a `"circle"` command requires
construction of a `CircleManeuver`, because recognizing command types is
its job. But the **generic infrastructure and function signature no
longer depend on circle-specific state**.

The proposed generic `maneuver_tick()` is also an architectural
improvement. The main loop can become conceptually:

``` python
maneuver_tick(conn, active_maneuver, state)
publish_telemetry(...)
```

instead of the main loop knowing that there is a special concept called
a circle.

This significantly reduces coupling.

### Two points to challenge

The proposal is good, but an independent reviewer should still question
details rather than simply approve it.

#### 1. Where does cancellation policy actually live?

Claude stated that:

> The "one persistent behavior at a time, cancelled by any other
> command" rule lives once, in `ActiveManeuver`.

That is not quite accurate if `handle_command()` still contains logic
equivalent to:

``` python
if cmd_type != "circle":
    active_maneuver.stop()
```

In that case:

-   **slot management** lives in `ActiveManeuver`;
-   the **policy deciding which commands supersede an active maneuver**
    still lives in the dispatcher.

That may actually be the correct design. The important point is to
recognize the distinction.

It may matter later because a future command might *not* need to cancel
the currently active maneuver.

#### 2. Make the Boolean `tick()` contract obvious

Claude proposed:

``` python
tick(conn) -> bool
```

with `False` meaning the maneuver is complete.

That works, but a bare Boolean can make control flow difficult to read.

For example, either of these conventions might be clearer:

``` python
finished = maneuver.tick(conn)
```

where `True` explicitly means finished, or:

``` python
still_active = maneuver.tick(conn)
```

where `True` explicitly means continue.

The contract should make the semantics immediately apparent.

### Overall assessment

The design reaches a good balance:

-   it removes the accidental circle-specific dependency;
-   it supports future persistent maneuvers;
-   it moves circle behavior into the object responsible for circles;
-   it keeps the main loop generic;
-   it avoids introducing a large framework;
-   it uses a small, understandable duck-typed contract rather than an
    unnecessary hierarchy.

The important architectural improvement is:

> **Remove the accidental circle-specific architecture without turning a
> small backend into a framework.**

------------------------------------------------------------------------


## 6. The Implemented Fix

The refactoring was then applied to the command path.

The generic dispatcher no longer receives an `ActiveCircle`. Instead, it receives a generic `active_maneuver` object:

```python
def handle_command(conn, payload, active_maneuver, state):
    try:
        cmd = json.loads(payload)
    except json.JSONDecodeError:
        log.warning("Ignoring malformed command payload: %r", payload)
        return

    cmd_type = cmd.get("type")
    try:
        if cmd_type != "circle":
            # Any other command abandons an in-progress maneuver --
            # otherwise maneuver_tick() would keep firing position targets
            # that fight whatever this new command is trying to do.
            active_maneuver.stop()

        if cmd_type == "arm":
            mavlink_lib.arm(conn)
        elif cmd_type == "disarm":
            mavlink_lib.disarm(conn)
        elif cmd_type == "takeoff":
            # NAV_TAKEOFF is only honored in GUIDED mode and while armed --
            # mavlink_lib.takeoff makes "takeoff" a complete action so a
            # command producer doesn't need its own mode/arm dance first
            # (this is what manually switching to GUIDED in the MAVProxy
            # console was standing in for during testing).
            mavlink_lib.takeoff(conn, float(cmd["alt"]))
            with state.lock:
                state.activity = "taking_off"
        elif cmd_type == "goto":
            mavlink_lib.goto(
                conn,
                float(cmd["lat"]),
                float(cmd["lon"]),
                float(cmd["alt"]),
            )
            with state.lock:
                state.activity = "flying"
        elif cmd_type == "circle":
            # circle_point() itself doesn't touch flight mode (see its
            # docstring) since it's called many times a second -- GUIDED
            # only needs setting once, here, before maneuver_tick() starts
            # calling it on the main loop's cadence.
            conn.set_mode("GUIDED")
            active_maneuver.start(
                CircleManeuver(
                    center_lat=float(cmd["lat"]),
                    center_lon=float(cmd["lon"]),
                    alt_rel_m=float(cmd["alt"]),
                    radius_m=float(cmd["radius"]),
                    degrees=float(cmd["degrees"]),
                    speed_mps=float(cmd["speed"]),
                )
            )
            with state.lock:
                state.activity = "circling"
        elif cmd_type == "fly_home":
            # Just goto() at the remembered home position -- no new MAVLink
            # primitive needed, the same way circle reused goto()'s
            # underlying send rather than inventing one. Transits at
            # whatever's higher of the current altitude or
            # FLY_HOME_MIN_ALT_M, so a low-altitude command doesn't drag the
            # vehicle home skimming the ground, but a already-high vehicle
            # doesn't needlessly climb first either. land is a deliberately
            # separate follow-up command, same as after a goto.
            with state.lock:
                home_lat, home_lon, current_alt = (
                    state.home_lat,
                    state.home_lon,
                    state.alt_rel,
                )
            if home_lat is None or home_lon is None:
                log.warning("Ignoring fly_home: home position not yet captured")
            else:
                target_alt = (
                    max(current_alt, FLY_HOME_MIN_ALT_M)
                    if current_alt is not None
                    else FLY_HOME_MIN_ALT_M
                )
                mavlink_lib.goto(conn, home_lat, home_lon, target_alt)
                with state.lock:
                    state.activity = "flying"
        elif cmd_type == "interrupt":
            mavlink_lib.interrupt(conn)
            with state.lock:
                # Best fit from the activity vocabulary for "holding
                # position, still airborne" -- there's no distinct
                # "Holding"/"Loiter" state in what new-gui.py's bridge maps
                # to, and this isn't landing or circling anymore.
                state.activity = "flying"
        elif cmd_type == "land":
            mavlink_lib.land(conn)
            with state.lock:
                state.activity = "landing"
        else:
            log.warning("Ignoring unknown command type: %r", cmd_type)
    except (KeyError, ValueError, TypeError) as exc:
        log.warning("Ignoring invalid command %r: %s", cmd, exc)
```

The MQTT callback is also now generic:

```python
def on_connect(client, userdata, flags, reason_code, properties):
    log.info(
        "Connected to MQTT broker at %s:%s (%s)",
        MQTT_HOST,
        MQTT_PORT,
        reason_code,
    )
    client.subscribe(COMMAND_TOPIC)


def on_message(client, userdata, msg):
    handle_command(
        userdata["conn"],
        msg.payload.decode("utf-8", errors="replace"),
        userdata["active_maneuver"],
        userdata["state"],
    )
```

The important change is visible directly in the signatures and data flow:

```text
Before:
    handle_command(conn, payload, circle, state)
    userdata["circle"]

After:
    handle_command(conn, payload, active_maneuver, state)
    userdata["active_maneuver"]
```

The dispatcher still knows that a `"circle"` command creates a `CircleManeuver`, because recognizing and dispatching command types is its responsibility:

```python
active_maneuver.start(CircleManeuver(...))
```

But the surrounding infrastructure is no longer coupled to circle-specific state.

This is the architectural improvement we were looking for. A future persistent maneuver can be introduced by creating another maneuver implementation and starting it through the same `active_maneuver` slot, rather than adding another maneuver-specific parameter throughout the backend.

One subtle point from the earlier review still remains: the **policy** that a non-circle command cancels the current maneuver still lives in `handle_command()`:

```python
if cmd_type != "circle":
    active_maneuver.stop()
```

That is reasonable for the current system. It also leaves a useful future design question: if some later command should coexist with an active maneuver rather than supersede it, this policy may need to become more explicit.


# What Students Should Learn from This Example

The important lesson is **not** that `ActiveManeuver` is the one correct
answer.

The important lesson is the *design reasoning process*.

A productive AI-assisted software engineering workflow can look like
this:

1.  **Notice something awkward in the code.**\
    Why does a generic command dispatcher require a `circle` parameter?

2.  **Ask why it exists before changing it.**\
    The parameter is not arbitrary: persistent circle commands must be
    cancelled when superseded.

3.  **Separate required behavior from accidental design.**\
    Cancelling an ongoing maneuver is required behavior. Making generic
    infrastructure explicitly depend on `ActiveCircle` is not.

4.  **Look for the abstraction hiding behind the special case.**\
    Circle is not fundamentally special because it is circular. It is
    special because it is currently the first **persistent maneuver**.

5.  **Give the implementation agent the problem and constraints---not
    the answer.**\
    Ask it to propose a design before editing code.

6.  **Use an independent agent to critique the proposal.**\
    Do not assume that a plausible AI-generated refactoring is a good
    design.

7.  **Challenge details even when the overall design is good.**\
    Where does policy belong? Is the interface understandable? Is the
    abstraction too general or too specific?

8.  **Prefer the smallest abstraction that solves the foreseeable design
    problem.**\
    `ActiveManeuver` + a small maneuver contract may be enough. A full
    Command Pattern, registry, class hierarchy, or framework may be
    unnecessary.

------------------------------------------------------------------------

## The Broader Native-AI Software Engineering Principle

AI coding agents are very good at **producing working code**.

That does not remove the need for software engineering judgment.

A strong workflow is therefore not:

``` text
Requirement
    |
    v
Coding Agent
    |
    v
Code
```

Instead:

``` text
Requirement
    |
    v
Coding Agent <------> Developer
    |                    |
    |               questions design
    v                    |
Proposed Design          |
    |                    |
    +----> Independent Review Agent
                  |
                  v
          critique / alternatives
                  |
                  v
          Developer judgment
                  |
                  v
            implementation
```

The developer remains responsible for asking:

-   Is this the right abstraction?
-   What assumption has the implementation made?
-   Will this design survive the next feature?
-   Has the agent generalized too little?
-   Has it generalized too much?
-   Is the proposed solution understandable and maintainable?
-   What tradeoff is being made?

**Using AI well does not mean accepting generated code faster. It means
creating a tighter and more deliberate design--critique--revision
loop.**
