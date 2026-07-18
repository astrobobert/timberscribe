"""Bench tool — push config.yaml to the DLC32 over USB.

The controller's FluidNC configuration lives in the sibling
``config.yaml`` (source of truth, version-controlled). After editing
it, run this with the board on USB to upload it and restart:

    pip install pyserial xmodem        # once
    python upload_config.py            # default port COM4
    python upload_config.py --port COM7

Nothing else may hold the port open (close the FluidNC web-installer
tab / any serial monitor first). The script sends the file via XModem
($Xmodem/Receive), restarts the board ($Bye), and prints the boot log
— read it: config errors show up there as [MSG:ERR:...] lines, and a
healthy boot ends with the machine name, "AP started", and "Telnet
started on port 23".
"""

import argparse
import os
import sys
import time

import serial
from xmodem import XMODEM


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default="COM4", help="serial port (default COM4)")
    ap.add_argument(
        "--file",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "config.yaml"),
        help="config file to upload (default: sibling config.yaml)",
    )
    args = ap.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=2)
    time.sleep(0.3)
    ser.reset_input_buffer()

    def cmd(line, wait=1.0):
        ser.write((line + "\n").encode())
        time.sleep(wait)
        out = ser.read_all().decode(errors="replace")
        print(f">>> {line}\n{out}")
        return out

    # Hand the board the file over XModem-CRC.
    ser.write(b"$Xmodem/Receive=config.yaml\n")
    deadline = time.time() + 10
    while time.time() < deadline:
        b = ser.read(1)
        if b == b"C":          # receiver's CRC poll — ready for data
            break
        if b:
            sys.stdout.write(b.decode(errors="replace"))
    else:
        sys.exit("Board never started XModem — is this a FluidNC board?")

    def getc(size, timeout=1):
        return ser.read(size) or None

    def putc(data, timeout=1):
        return ser.write(data)

    with open(args.file, "rb") as f:
        if not XMODEM(getc, putc).send(f, retry=8):
            sys.exit("XModem transfer failed")
    time.sleep(1.0)
    print(ser.read_all().decode(errors="replace"))
    cmd("$LocalFS/List")

    print("=== restarting — boot log follows ===")
    ser.write(b"$Bye\n")
    time.sleep(6.0)
    print(ser.read_all().decode(errors="replace"))
    cmd("$I", wait=1.5)
    ser.close()


if __name__ == "__main__":
    main()
