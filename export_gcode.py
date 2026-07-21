"""Export a .tsj job to a .gcode file — no server needed.

For field mode: the controller runs .gcode files from its SD card with
no WiFi link required mid-burn. Export at the design desk, get the file
onto your phone, upload to the card through the board's own web page,
run.

    python export_gcode.py P-2A_face1.tsj
    python export_gcode.py P-2A_face1.tsj -o custom.gcode --power 60

Feed/power/travel default to the values in the .tsj file (the same
defaults the web UI shows); the file burns exactly like a streamed
print would. The web UI's "Export .gcode" button does the same thing
with the job's operator-adjusted settings.
"""

import argparse
import os
import sys

from app import tsj_parser
from hardware.executor import gcode_program


def main():
    ap = argparse.ArgumentParser(
        description="Export a .tsj job to a .gcode file for SD-card runs."
    )
    ap.add_argument("tsj", help="input .tsj file")
    ap.add_argument("-o", "--out", help="output path (default: <stem>.gcode)")
    ap.add_argument("--feed",   type=int, help="burn feed, in/min")
    ap.add_argument("--power",  type=int, help="laser power, percent")
    ap.add_argument("--travel", type=int, help="travel feed, in/min")
    args = ap.parse_args()

    try:
        job = tsj_parser.load(args.tsj)
    except tsj_parser.TsjError as e:
        sys.exit(f"Invalid .tsj: {e}")

    lines = gcode_program(
        job.entities,
        args.feed   or job.feed_in_per_min,
        args.power  or job.laser_power_pct,
        args.travel or job.travel_in_per_min,
        log=lambda m: print(f"  {m}"),
    )

    out = args.out or os.path.splitext(args.tsj)[0] + ".gcode"
    with open(out, "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{out}: {len(lines)} lines, "
          f"{len(job.entities)} entities ({job.timber_id} face "
          f"{job.face.number})")


if __name__ == "__main__":
    main()
