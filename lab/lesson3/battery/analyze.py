#!/usr/bin/env python3
"""
analyze.py -- worked Track A example for the battery failsafe log.

Reads the CSVs that bin2csv.py produces, prints a verdict with evidence,
and saves three graphs. This is the *shape* your own two analysis
scripts should have -- read the records, compute the diagnostic signal,
state a verdict you can defend, plot it with the thresholds marked.

    cd lab/lesson3
    python bin2csv.py "battery/2025-07-04 14-41-47.bin" -t BAT,ERR,MSG,EV,MODE
    python battery/analyze.py "battery/2025-07-04 14-41-47"

Requires: pip install -r lab/lesson3/requirements.txt
"""
import csv
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- failsafe / arming config -----------------------------------------------
# From the log's PARM block (bin2csv.py --keep-schema, or a GCS param dump).
# BATT_LOW_VOLT = 0  -> the voltage failsafe is DISABLED on this aircraft.
BATT_CAPACITY = 16000.0        # mAh
BATT_LOW_MAH  = 3500.0         # LOW failsafe reserve -> trips at 12,500 mAh used
BATT_CRT_MAH  = 2000.0         # CRITICAL reserve     -> trips at 14,000 mAh used
BATT_ARM_VOLT = 44.0           # PreArm needs the pack at or above this
LOW_MAH_USED  = BATT_CAPACITY - BATT_LOW_MAH
CRT_MAH_USED  = BATT_CAPACITY - BATT_CRT_MAH

CSV_DIR = sys.argv[1] if len(sys.argv) > 1 else "2025-07-04 14-41-47"
OUT_DIR = os.path.dirname(CSV_DIR) or "."


def load(name):
    """Load <CSV_DIR>/<name>.csv into a dict of numpy columns."""
    with open(f"{CSV_DIR}/{name}.csv") as f:
        rows = list(csv.reader(f))
    hdr, data = rows[0], rows[1:]
    out = {}
    for i, h in enumerate(hdr):
        col = np.array([r[i] for r in data], dtype=object)
        try:
            out[h] = col.astype(float)
        except ValueError:
            out[h] = col
    return out


bat = load("BAT")
err = load("ERR")
msg = load("MSG")

# --- pull the events out of the records ------------------------------------
i0 = bat["Instance"] == 0
t, V, I = bat["t_s"][i0], bat["Volt"][i0], bat["Curr"][i0]
mah, rem = bat["CurrTot"][i0], bat["RemPct"][i0]

# battery failsafe = ERR subsystem 6
fs_err = err["t_s"][err["Subsys"] == 6]
t_fs = float(fs_err.min()) if len(fs_err) else None

# the human-readable lines
fs_msgs = [(ts, m) for ts, m in zip(msg["t_s"], msg["Message"])
           if "Battery Failsafe" in m or "Battery 1 is low" in m
           or "Battery 2 is low" in m]
prearm = [(ts, m) for ts, m in zip(msg["t_s"], msg["Message"])
          if "PreArm" in m and "attery" in m]

kfs = int(np.argmin(np.abs(t - t_fs))) if t_fs else None

# airborne window: current sustained above a hover-ish level
airborne = I > 8
t_land = float(t[airborne].max()) if np.any(airborne) else t.max()

# load sag: voltage under load at the failsafe vs the rested voltage at
# end of log. The pack is *more* depleted by then, so this understates
# the true sag -- it is a lower bound, and it is already small.
v_loaded  = float(V[kfs]) if kfs is not None else float(V[airborne].mean())
v_rested  = float(V[t > t.max() - 5].mean())
sag_lower = v_rested - v_loaded

# --- the verdict ----------------------------------------------------------
print("=" * 68)
print("VERDICT:  battery LOW failsafe (consumed-capacity trip), then the")
print("          next arm was blocked by the latched failsafe.")
print("=" * 68)
print(f"  failsafe fired at t = {t_fs:.1f} s   (ERR subsystem 6)")
for ts, m in fs_msgs:
    print(f"    t={ts:7.1f}  {m}")
print(f"  at that moment: {mah[kfs]:.0f} mAh used  (reserve hit: "
      f"{BATT_CAPACITY - mah[kfs]:.0f} mAh left vs BATT_LOW_MAH {BATT_LOW_MAH:.0f})")
print(f"  pack voltage there: {V[kfs]:.2f} V under {I[kfs]:.0f} A")
print()
print(f"  it was the coulomb counter, not voltage:")
print(f"    - flight STARTED already {rem[0]:.0f}% / {mah[0]:.0f} mAh used "
      f"(this pack's 2nd sortie)")
print(f"    - load sag is small: {v_loaded:.2f} V under load at the trip, "
      f"rests to {v_rested:.2f} V (>= {sag_lower:.2f} V) -> healthy pack, not collapsing")
print(f"    - min voltage all flight: {V.min():.2f} V")
print()
if prearm:
    ts, m = prearm[0]
    print(f"  re-arm blocked at t = {ts:.1f} s:  \"{m}\"")
print(f"    - voltage had recovered to ~{v_rested:.2f} V  "
      f"(>= BATT_ARM_VOLT {BATT_ARM_VOLT:.0f}, so voltage is not the blocker)")
print(f"    - consumed mAh ended at {mah[-1]:.0f} and only ever rises -> "
      f"the failsafe stays latched until a fresh pack")
print("=" * 68)

# --- the graphs ---------------------------------------------------------
plt.rcParams.update({"font.size": 11})
VOLT_C, CURR_C, FS_C = "#1f77b4", "#d1620a", "#c1121f"


def volt_curr(ax, sl=None):
    ax.plot(t, V, color=VOLT_C, lw=2, label="pack voltage")
    ax.set_ylabel("voltage (V)", color=VOLT_C)
    ax.tick_params(axis="y", labelcolor=VOLT_C)
    a2 = ax.twinx()
    a2.plot(t, I, color=CURR_C, lw=1.1, alpha=0.85, label="current")
    a2.set_ylabel("current (A)", color=CURR_C)
    a2.tick_params(axis="y", labelcolor=CURR_C)
    a2.set_ylim(0, I.max() * 1.3)
    if t_fs:
        ax.axvline(t_fs, color=FS_C, ls="--", lw=2)
    if sl:
        ax.set_xlim(*sl)
    return a2


# 1 -- voltage & current, failsafe marked
fig, ax = plt.subplots(figsize=(11, 5))
volt_curr(ax)
ax.set_xlabel("time since boot (s)")
ax.set_title(f"Voltage & current — battery failsafe at t={t_fs:.0f} s")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/fig1_volt_curr.png", dpi=120)

# 2 -- charge state vs the mAh thresholds
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(t, rem, color="#2a9d8f", lw=2.5, label="RemPct (%)")
ax.set_ylabel("remaining (%)", color="#2a9d8f")
ax.set_ylim(0, 30)
ax.tick_params(axis="y", labelcolor="#2a9d8f")
a2 = ax.twinx()
a2.plot(t, mah, color="#6a4c93", lw=2.5, label="consumed (mAh)")
a2.axhline(LOW_MAH_USED, color=FS_C, ls="--", lw=1.6)
a2.set_ylabel("consumed (mAh)", color="#6a4c93")
a2.tick_params(axis="y", labelcolor="#6a4c93")
a2.set_ylim(11500, 14200)
a2.text(t[0] + 2, LOW_MAH_USED + 60,
        f"BATT_LOW_MAH → failsafe at {LOW_MAH_USED:.0f} mAh used", color=FS_C)
if t_fs:
    ax.axvline(t_fs, color=FS_C, ls="--", lw=2)
ax.set_xlabel("time since boot (s)")
ax.set_title("Charge state — started at 23%, coulomb counter trips the failsafe")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/fig2_charge_state.png", dpi=120)

# 3 -- the re-arm block
fig, ax = plt.subplots(figsize=(11, 5))
zoom = t >= (t_fs - 10 if t_fs else t[0])
ax.plot(t[zoom], V[zoom], color=VOLT_C, lw=2, label="pack voltage")
ax.axhline(BATT_ARM_VOLT, color="#2a9d8f", ls="--", lw=1.8,
           label=f"BATT_ARM_VOLT = {BATT_ARM_VOLT:.0f} V")
if prearm:
    ax.axvline(prearm[0][0], color="k", lw=1.5)
    ax.text(prearm[0][0], V[zoom].min(), '  "PreArm: Battery failsafe"', fontsize=10)
ax.set_xlabel("time since boot (s)")
ax.set_ylabel("voltage (V)")
ax.set_title("Re-arm blocked — voltage recovered, but the mAh failsafe stays latched")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/fig3_rearm_blocked.png", dpi=120)

print("\nwrote fig1_volt_curr.png, fig2_charge_state.png, fig3_rearm_blocked.png "
      f"to {OUT_DIR}/")
