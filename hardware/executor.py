"""
Hardware burn loop — GRBL g-code sender over USB serial.

Translates the .tsj entity list into g-code and streams it to the
sled's GRBL controller (MKS DLC32 V2.1) over USB serial. The Pi runs
this server; the controller does all motor/laser timing.

This module is intentionally minimal now — the entity → g-code motion
mapping (G0/G1/G2/G3 paths per entity type) will be developed here in
the next phase. The serial plumbing (connect, handshake, call-response
send, laser M3/M5) is real.

HAS_HARDWARE is decided once at import by enumerating serial ports —
the port is never opened at import time. If the controller is plugged
in after the server starts, restart the server.

burn() is the single public entry point called by app/executor.py.
"""

import time
from typing import Callable

import config

try:
    import serial                      # pyserial
    from serial.tools import list_ports
except ImportError:                    # stripped environment — simulate
    serial = None


def _detect_hardware() -> bool:
    """True iff pyserial is importable and config.SERIAL_PORT is an
    enumerated serial device. Cheap check only — never opens the port."""
    if serial is None:
        return False
    return any(p.device == config.SERIAL_PORT for p in list_ports.comports())


HAS_HARDWARE = _detect_hardware()


def burn(
    entities:          list[dict],
    feed_in_per_min:   int,
    laser_power_pct:   int,
    travel_in_per_min: int,
    status_cb:         Callable[[str], None] | None = None,
):
    """
    Execute a list of .tsj entities on the laser print head.

    Parameters
    ----------
    entities          List of entity dicts from the .tsj file (visible only)
    feed_in_per_min   Burn feed rate — inches per minute
    laser_power_pct   Laser power 0–100%
    travel_in_per_min Travel feed rate (laser off) — inches per minute
    status_cb         Optional callback — called with a status string each
                      time a new entity starts burning

    Entity coordinate system
    ------------------------
    X — along timber length, inches from anchor end (tape hook)
    Y — across timber width, inches from datum edge (fixed roller side)
    """

    def log(msg: str):
        if status_cb:
            status_cb(msg)
        print(f"[burn] {msg}")

    if not HAS_HARDWARE:
        raise RuntimeError(
            f"GRBL controller not found on {config.SERIAL_PORT}. "
            "Is the DLC32 plugged in? (Detected at server start — "
            "restart after plugging in.)"
        )

    ser = _connect(log)
    try:
        # Preamble: inches, absolute coordinates.
        # TODO: confirm units/modes against the DLC32's firmware config.
        _send(ser, "G20")
        _send(ser, "G90")
        _laser_off(ser)

        n = len(entities)
        log(f"Starting burn — {n} entities, "
            f"{feed_in_per_min} in/min, {laser_power_pct}% power")

        for i, entity in enumerate(entities, 1):
            t = entity.get("type", "")
            log(f"Entity {i}/{n}: {t}")

            if t == "line":
                _burn_line(ser, entity, feed_in_per_min, laser_power_pct,
                           travel_in_per_min)
            elif t == "polyline":
                _burn_polyline(ser, entity, feed_in_per_min, laser_power_pct,
                               travel_in_per_min)
            elif t == "circle":
                _burn_circle(ser, entity, feed_in_per_min, laser_power_pct,
                             travel_in_per_min)
            elif t == "arc":
                _burn_arc(ser, entity, feed_in_per_min, laser_power_pct,
                          travel_in_per_min)
            else:
                log(f"  Unknown entity type '{t}' — skipped")

        log("Burn complete")

    finally:
        try:
            _laser_off(ser)
        finally:
            ser.close()


# ── Serial / GRBL plumbing ────────────────────────────────────────────────────

def _connect(log: Callable[[str], None]):
    """Open the controller port and wait out the GRBL reset.

    Opening the port toggles DTR, which resets GRBL — so wait for the
    startup banner ("Grbl X.Xx ...") before sending anything.
    """
    ser = serial.Serial(
        config.SERIAL_PORT,
        config.SERIAL_BAUD,
        timeout=config.SERIAL_TIMEOUT_S,
    )
    time.sleep(config.GRBL_STARTUP_WAIT_S)
    banner = ser.read_all().decode(errors="replace").strip()
    if banner:
        log(f"Controller: {banner.splitlines()[-1]}")
    ser.reset_input_buffer()
    ser.write(b"\r\n\r\n")   # wake / flush
    time.sleep(0.1)
    ser.reset_input_buffer()
    return ser


def _send(ser, line: str):
    """Send one g-code line and block until GRBL answers.

    Simple call-response sender — waits for "ok" after every line.
    A character-counting streamer (keeping GRBL's planner buffer full)
    is future work; call-response is plenty for scribing linework.
    """
    ser.write((line + "\n").encode())
    while True:
        resp = ser.readline().decode(errors="replace").strip()
        if resp == "ok":
            return
        if resp.startswith("error:") or resp.startswith("ALARM"):
            raise RuntimeError(f"GRBL rejected '{line}': {resp}")
        if resp == "":
            raise RuntimeError(
                f"GRBL timeout waiting for ok after '{line}'"
            )
        # anything else (status, banner echo) — keep reading


# ── Laser control ─────────────────────────────────────────────────────────────

def _laser_on(ser, power_pct: int):
    """Laser on at power_pct (0–100). Assumes GRBL laser mode ($32=1)
    so M3 only fires during motion."""
    s = int(power_pct / 100 * config.GRBL_SPINDLE_MAX_S)
    _send(ser, f"M3 S{s}")


def _laser_off(ser):
    _send(ser, "M5")


# ── Entity burn stubs (to be implemented in next phase) ───────────────────────

def _burn_line(ser, entity: dict, feed: int, power: int, travel: int):
    """
    Travel to line start, laser on, traverse to line end, laser off.
    TODO: emit G0 travel → M3 → G1 feed → M5 via _send().
    """
    start = entity.get("start", [0, 0])
    end   = entity.get("end",   [0, 0])
    print(f"  LINE ({start[0]:.3f},{start[1]:.3f}) → "
          f"({end[0]:.3f},{end[1]:.3f})")


def _burn_polyline(ser, entity: dict, feed: int, power: int, travel: int):
    """Burn each segment of the polyline in sequence.
    TODO: G0 to first point → M3 → chained G1s → M5 via _send()."""
    pts    = entity.get("points", [])
    closed = entity.get("closed", False)
    if len(pts) < 2:
        return
    if closed and pts[-1] != pts[0]:
        pts = pts + [pts[0]]
    print(f"  POLYLINE {len(pts)} pts, closed={closed}")


def _burn_circle(ser, entity: dict, feed: int, power: int, travel: int):
    """Burn the centre cross first, then trace the circle outline.
    TODO: G0/G1 for the cross, then a full-circle G2 via _send()."""
    c = entity.get("center", [0, 0])
    r = entity.get("radius_in", 0)
    print(f"  CIRCLE centre ({c[0]:.3f},{c[1]:.3f}) r={r:.3f}")


def _burn_arc(ser, entity: dict, feed: int, power: int, travel: int):
    """TODO: G0 to arc start → M3 → G2/G3 (by sweep direction) → M5
    via _send()."""
    c     = entity.get("center", [0, 0])
    r     = entity.get("radius_in", 0)
    start = entity.get("start_angle_deg", 0)
    end   = entity.get("end_angle_deg",   0)
    print(f"  ARC centre ({c[0]:.3f},{c[1]:.3f}) r={r:.3f} "
          f"{start:.1f}°→{end:.1f}°")
