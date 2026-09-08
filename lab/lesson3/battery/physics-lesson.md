# Voltage & current — the physics behind the battery exercise

Background notes for the FUCHSIA battery-failsafe log. Everything here is keyed to
numbers from that flight: a **12S ~16,000 mAh Li-ion pack**, hovering at about
**26 A**, pack voltage around **44 V**.

---

## 1. The two quantities

**Voltage (V, volts)** is electrical *potential difference* — how hard the
battery pushes charge around the circuit. It's a property *between two points*
(the + and − terminals).

**Current (I, amps)** is the *rate of charge flow* past a point — how much
charge moves per second. 1 amp = 1 coulomb per second.

The water analogy, used carefully:

| electrical | water |
|---|---|
| voltage | pressure difference across a pipe |
| current | flow rate through the pipe |
| resistance | how narrow / restrictive the pipe is |

Pressure (voltage) can exist with nothing flowing. Flow (current) only happens
when something is connected across that pressure and lets charge move. On the
FUCHSIA log, sitting armed on the ground the pack is at 44.5 V but only ~0.5 A
flows — full pressure, almost no flow. In a hover the motors open the "pipe"
and ~26 A flows.

**Ohm's law** ties them together for a resistive path:

```
V = I × R
```

## 2. Power and energy — why a drone cares

**Power (P, watts)** is the rate of energy use:

```
P = V × I
```

Hover on the FUCHSIA flight: `P ≈ 44 V × 26 A ≈ 1,150 W`. That's the electrical
power the six motors are burning to hold the aircraft up.

**Energy (E, watt-hours)** is power accumulated over time: `E = P × t`. A pack's
energy is roughly `capacity × nominal voltage`:

```
16 Ah × ~44 V ≈ 700 Wh   (a full pack)
```

Ideal hover endurance from full would be `700 Wh ÷ 1,150 W ≈ 0.6 h ≈ 37 min`
— before any reserve, and ignoring that efficiency drops as the pack sags. The
FUCHSIA flight started at 23%, so there was only ~2–3 minutes of usable flight in
it before the reserve.

## 3. What "12S" means

A pack is individual **cells** wired together. Li-ion cells:

| state | volts per cell | ×12 (this pack) |
|---|---|---|
| full charge | 4.2 V | 50.4 V |
| nominal ("name plate") | ~3.6–3.7 V | ~43–44 V |
| getting low | 3.5 V | 42 V |
| empty (don't go here) | 3.0 V | 36 V |

**"12S"** = 12 cells in **series** → their voltages add. (Cells in **parallel**,
"P", add capacity instead — a "12S4P" pack is 48 cells, 12 groups of 4.)

Series is why one weak or disconnected cell drags the *whole pack* voltage
down, and why per-cell logs (`BCL` in the CSVs) matter: the pack can read okay
while one cell is collapsing.

On the FUCHSIA flight `BCL` shows all 12 cells within ~20 mV of each other — the
pack is *balanced*, just discharged. No single bad cell.

## 4. Capacity, C-rate, and coulomb counting

**Capacity** is how much charge the pack holds, in amp-hours (Ah) or
milliamp-hours (mAh). `16,000 mAh` = 16 Ah = the pack can (nominally) supply
16 A for 1 hour, or 26 A for `16 ÷ 26 ≈ 0.6 h`.

**C-rate** normalises current to pack size: `1C` = the current that empties the
pack in 1 hour = 16 A here. The 26 A hover is about **1.6C** — modest, well
within what the pack can do.

**Coulomb counting** (a.k.a. "used mAh", the `CurrTot` column) is how the
autopilot tracks charge: it measures current continuously and integrates it
over time.

```
charge used  =  ∫ I dt   ≈   Σ (I × Δt)
```

Every second at 26 A adds `26 A × (1/3600) h ≈ 7.2 mAh` to the running total.
This is a *counter that only goes up* during a flight. It does not know or care
what the voltage is doing. On the FUCHSIA flight it read 12,008 mAh at log start
and 12,502 mAh when the failsafe fired.

`remaining % = 1 − used / capacity` — this is mostly what `RemPct` reports.

## 5. Internal resistance and voltage sag — the key idea

A real battery isn't a perfect voltage source. Model it as an ideal source
`V_oc` (open-circuit voltage, set by chemistry and state of charge) **in series
with a small internal resistance `R_int`**:

```
V_terminal  =  V_oc  −  I × R_int
```

The `I × R_int` term is **voltage sag**: the more current you pull, the more the
*measured* terminal voltage drops below the pack's "true" resting voltage — not
because the pack emptied, but because current is flowing through that internal
resistance.

From the FUCHSIA flight, the pack sits at ~43.7 V under a 26 A hover load
and rests back to ~44.1 V with the motors off — a sag of very roughly

```
ΔV ≈ 0.4 V   →   R_int ≈ ΔV / I ≈ 0.4 / 26 ≈ 0.015 Ω   (order ~10 mΩ)
```

(A clean internal-resistance number needs short before/after-load windows
at the *same* state of charge; fitting voltage against current across a
whole flight is unreliable because the pack is draining the whole time.
The point here is only the order of magnitude.)

That's *small*. A worn-out pack with `R_int` 3–5× higher would sag a full volt
or more under the same load and could trip a **voltage** failsafe while still
having plenty of charge left. This pack does not — its resistance is healthy,
so its low voltage genuinely reflects a low state of charge, not a sick pack.

**This is the crux of Q2 in the diagnosis:** "low voltage under load" has two
possible causes — *empty* (low `V_oc`) or *strained* (high `I × R_int`) — and
you tell them apart by checking how big the sag is relative to the current.

## 6. Why voltage is a poor fuel gauge

Plot a Li-ion cell's resting voltage against how much charge you've taken out
and you get an **S-shaped discharge curve**:

```
V_oc
4.2 |*
    | *
4.0 |  **
    |    ****
3.8 |        *********          <- long flat middle: big charge swing,
    |                 ****         tiny voltage change
3.6 |                     ***
    |                        **
3.4 |                          *
3.2 |                           *   <- steep knee: voltage falls off a cliff
3.0 |                           *
    +---------------------------------
    100%                          0%   state of charge
```

Through the middle 20–80% of the pack, voltage barely moves — a huge range of
"how full is it" maps to a sliver of voltage. Near empty, it drops steeply.

Consequences for reading a log:
- A single voltage number in the flat region tells you almost nothing about
  remaining charge.
- Add load (sag) on top of this and the reading gets *worse*.
- **Coulomb counting** (`used mAh` vs `capacity`) is the reliable gauge for
  most of the flight. Voltage only becomes decisive once you're at the knee.

## 7. Relaxation — why voltage "recovers" after landing

When you cut the load, current → 0, so the `I × R_int` sag term → 0 and
terminal voltage jumps back up toward `V_oc` almost immediately. Over the next
seconds-to-minutes it drifts up a little more as internal chemical gradients
even out ("relaxation").

FUCHSIA flight: 43.6 V under 26 A in the hover → **44.2 V at rest** within a few
seconds of the motors stopping. The pack didn't gain any charge. It's the same
`V_oc − I·R` equation with `I` back to nearly zero.

This is why a **voltage-based failsafe self-clears** on the ground (voltage
rebounds above the threshold) but a **capacity-based failsafe does not** (the
`used mAh` counter doesn't decrease just because the pack is resting). That's
Q3.

## 8. Putting it together with the failsafe parameters

| parameter | what it checks | physics it relies on |
|---|---|---|
| `BATT_LOW_VOLT` / `BATT_CRT_VOLT` | terminal voltage under a sustained threshold for `BATT_LOW_TIMER` s | assumes you're near the knee of the discharge curve; vulnerable to sag on a high-resistance pack; **set to 0 = disabled on this aircraft** |
| `BATT_LOW_MAH` / `BATT_CRT_MAH` | `capacity − used mAh` below a reserve | coulomb counting; independent of load and of voltage; **this is what fired on FUCHSIA**, at `16,000 − 3,500 = 12,500 mAh` used |
| `BATT_ARM_VOLT` | resting terminal voltage at arm time ≥ threshold | a fresh pack sits well above nominal; a depleted one, even rested, doesn't — but this pack rested at 44.2 V, just above the 44.0 V line, so it was *not* the blocker |

The FUCHSIA sequence in one paragraph, physically:

> The pack was flown down to ~23% on a previous sortie. This flight drew a
> steady ~26 A hover current; the coulomb counter integrated that until
> `used mAh` hit the 12,500 mark (3,500 mAh reserve), and the LOW failsafe
> triggered an RTL. Terminal voltage at that moment (43.7 V) was low mostly
> because the pack's `V_oc` was genuinely low — sag only accounts for ~0.3 V of
> it. After landing, with the load removed, voltage relaxed back to 44.2 V, but
> the consumed-mAh counter stayed at ~13,350, so the failsafe condition was
> still true and PreArm refused the next arm. It would clear only on a fresh
> pack (which resets the counter), not by waiting.

---

## Quick reference

```
V = I × R                     Ohm's law (resistive path)
P = V × I                     electrical power  (44 V × 26 A ≈ 1150 W)
E = P × t                     energy            (pack ≈ 16 Ah × 44 V ≈ 700 Wh)
V_terminal = V_oc − I × R_int voltage sag under load
used mAh   = Σ (I × Δt)       coulomb counting  (CurrTot column)
remaining %  ≈ 1 − used / capacity
1C = current that empties the pack in 1 h  (16 A for a 16 Ah pack)
```

Units: 1 A = 1 C/s · 1 W = 1 V·A · 1 Wh = 3600 J · 1 mAh at 44 V ≈ 0.044 Wh

Log columns that matter here: `BAT` (Volt, Curr, CurrTot, RemPct),
`BCL` (per-cell voltages), `ERR` (subsys 6 = battery failsafe),
`MSG` (human-readable failsafe / PreArm text), `MODE` (RTL after the trip).
