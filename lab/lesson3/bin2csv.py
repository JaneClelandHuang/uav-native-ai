#!/usr/bin/env python3
"""
bin2csv.py -- dump an ArduPilot dataflash (.bin) log to CSV.

A .bin holds ~60 different message types, each with its own columns, so the
natural output is one CSV per message type.

    python bin2csv.py flight.bin                 -> flight/  (MODE.csv, GPS.csv, ...)
    python bin2csv.py flight.bin -o out_dir      -> out_dir/
    python bin2csv.py flight.bin -t POS,GPS,ERR  -> only those types
    python bin2csv.py flight.bin -t POS --single -> one file: flight_POS.csv

Every row gets an extra `t_s` column: seconds since boot (TimeUS / 1e6),
handy for plotting.

Requires: pip install pymavlink
"""
import argparse
import csv
import pathlib
import sys

from pymavlink import mavutil

SKIP = {"FMT", "FMTU", "UNIT", "MULT", "PARM"}  # schema / param dumps, not flight data


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bin", help="path to the .bin log")
    ap.add_argument("-o", "--out", help="output directory (default: <bin name>/)")
    ap.add_argument("-t", "--types", help="comma-separated message types to keep "
                    "(default: all, e.g. POS,GPS,ERR,MODE,MSG)")
    ap.add_argument("--single", action="store_true",
                    help="write one flat file <bin>_<TYPE>.csv instead of a folder "
                         "(use with a single -t type)")
    ap.add_argument("--keep-schema", action="store_true",
                    help="also dump FMT/PARM/etc. (skipped by default)")
    args = ap.parse_args()

    src = pathlib.Path(args.bin)
    if not src.exists():
        sys.exit(f"no such file: {src}")

    wanted = {s.strip() for s in args.types.split(",")} if args.types else None
    skip = set() if args.keep_schema else SKIP

    log = mavutil.mavlink_connection(str(src), dialect="ardupilotmega")

    writers, files, count = {}, {}, {}
    outdir = None
    if not args.single:
        outdir = pathlib.Path(args.out) if args.out else src.with_suffix("")
        outdir.mkdir(parents=True, exist_ok=True)

    while True:
        msg = log.recv_match(blocking=False)
        if msg is None:
            break
        mtype = msg.get_type()
        if mtype == "BAD_DATA" or mtype in skip:
            continue
        if wanted and mtype not in wanted:
            continue

        row = msg.to_dict()
        row.pop("mavpackettype", None)
        if "TimeUS" in row:
            row["t_s"] = round(row["TimeUS"] / 1e6, 3)

        w = writers.get(mtype)
        if w is None:
            if args.single:
                path = src.with_name(f"{src.stem}_{mtype}.csv")
            else:
                path = outdir / f"{mtype}.csv"
            f = open(path, "w", newline="")
            files[mtype] = f
            w = csv.DictWriter(f, fieldnames=list(row.keys()),
                               extrasaction="ignore", restval="")
            w.writeheader()
            writers[mtype] = w
            count[mtype] = 0
        w.writerow(row)
        count[mtype] += 1

    for f in files.values():
        f.close()

    if not count:
        sys.exit("no matching records found")
    where = "" if args.single else f" in {outdir}/"
    for mtype in sorted(count):
        print(f"  {mtype:8} {count[mtype]:>9,} rows")
    print(f"{len(count)} file(s){where}")


if __name__ == "__main__":
    main()
