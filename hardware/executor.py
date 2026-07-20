"""
Hardware burn loop — GRBL g-code sender.

Translates the .tsj entity list into g-code and streams it to the
sled's GRBL controller (MKS DLC32 V2.2 running FluidNC). The controller
does all motor/laser timing. Transport is config.GRBL_TRANSPORT:

  "wifi"   — raw g-code over TCP (FluidNC's telnet service, port 23).
             The controller hosts its own hotspot; the machine running
             this server joins it. This is the shop configuration —
             nothing rides the sled but the controller.
  "serial" — USB serial to the same board, kept as a bench fallback.

Either way GRBL speaks the same call-response protocol: one line out,
wait for "ok".

Entity → g-code mapping (coordinates pass through 1:1 — machine zero is
homed to the tape-hook / datum-edge corner, exactly where .tsj measures
from; see TSJ_SPEC.md):

  line      travel to start, M4, G1 to end, M5
  polyline  travel to first point, M4, chained G1s (+ close), M5
  circle    center cross (two strokes), then a full G3 — peg bores
  arc       G3 with I/J offsets; .tsj arcs always sweep in the
            increasing-angle direction of P(θ) = C + r·(cosθ, sinθ),
            which IS g-code counter-clockwise

Travel moves are laser-off G1s at the operator's travel feed rather
than G0 rapids — the .tsj travel profile is a contract, and rapids on
this machine run at the (uncalibrated) max_rate. Burns use M4 dynamic
laser power, not M3: call-response streaming starves the planner
between lines, and M4 scales power with true speed and goes dark at
standstill — a pause or a dropped link never parks a firing beam.

hardware_available() probes the configured transport at call time —
nothing is opened or enumerated at import, so joining the hotspot (or
plugging in the USB cable) after the server starts is fine.

burn() is the single public entry point called by app/executor.py.
"""

import math
import socket
import time
from typing import Callable

import config

try:
    import serial                      # pyserial — bench fallback only
    from serial.tools import list_ports
except ImportError:                    # stripped environment — simulate
    serial = None


def hardware_available() -> bool:
    """Cheap probe of the configured transport, called per burn.

    "wifi": try a TCP connect to the controller — fails fast when this
    machine isn't on the sled's hotspot. "serial": enumerate ports
    without opening one. False routes the job to simulation.
    """
    if config.GRBL_TRANSPORT == "wifi":
        try:
            socket.create_connection(
                (config.GRBL_HOST, config.GRBL_TCP_PORT),
                timeout=config.GRBL_CONNECT_TIMEOUT_S,
            ).close()
            return True
        except OSError:
            return False
    if serial is None:
        return False
    return any(p.device == config.SERIAL_PORT for p in list_ports.comports())


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

    ser = _connect(log)
    try:
        # Preamble: inches, absolute coordinates.
        # TODO: confirm units/modes against the FluidNC config.
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


# ── Transport / GRBL plumbing ─────────────────────────────────────────────────
#
# Both links expose the same surface: write(bytes), readline() -> bytes
# (b"" on timeout, pyserial-style), drain() -> bytes (discard + return
# pending input), close().

class _TcpLink:
    """Raw g-code over TCP — FluidNC's telnet service (port 23).

    Connecting does NOT reset the controller (unlike serial DTR), so no
    startup wait is needed. readline() is hand-buffered over recv() to
    keep pyserial's return-empty-on-timeout semantics.
    """

    def __init__(self):
        self._sock = socket.create_connection(
            (config.GRBL_HOST, config.GRBL_TCP_PORT),
            timeout=config.GRBL_CONNECT_TIMEOUT_S,
        )
        self._sock.settimeout(config.GRBL_READ_TIMEOUT_S)
        self._buf = b""

    def write(self, data: bytes):
        self._sock.sendall(data)

    def readline(self) -> bytes:
        while b"\n" not in self._buf:
            try:
                chunk = self._sock.recv(1024)
            except socket.timeout:
                return b""            # timeout — buffer kept for next read
            if not chunk:             # controller closed the connection
                line, self._buf = self._buf, b""
                return line
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line + b"\n"

    def drain(self) -> bytes:
        drained, self._buf = self._buf, b""
        self._sock.settimeout(0.2)
        try:
            while True:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                drained += chunk
        except socket.timeout:
            pass
        finally:
            self._sock.settimeout(config.GRBL_READ_TIMEOUT_S)
        return drained

    def close(self):
        self._sock.close()


class _SerialLink:
    """USB serial bench fallback — the DLC32's CH340 USB-UART.

    Opening the port toggles DTR, which resets GRBL — wait out the
    reset, then wake/flush, before letting the caller send anything.
    """

    def __init__(self):
        self._ser = serial.Serial(
            config.SERIAL_PORT,
            config.SERIAL_BAUD,
            timeout=config.GRBL_READ_TIMEOUT_S,
        )
        time.sleep(config.GRBL_STARTUP_WAIT_S)

    def write(self, data: bytes):
        self._ser.write(data)

    def readline(self) -> bytes:
        return self._ser.readline()

    def drain(self) -> bytes:
        drained = self._ser.read_all()
        self._ser.reset_input_buffer()
        return drained

    def close(self):
        self._ser.close()


def _connect(log: Callable[[str], None]):
    """Open the configured transport and get it quiet and in sync."""
    if config.GRBL_TRANSPORT == "wifi":
        try:
            link = _TcpLink()
        except OSError as e:
            raise RuntimeError(
                f"Can't reach the DLC32 at "
                f"{config.GRBL_HOST}:{config.GRBL_TCP_PORT}. Is the sled "
                f"powered on, and is this machine on its "
                f"'{config.GRBL_AP_SSID}' hotspot? ({e})"
            ) from e
        log(f"Connected to DLC32 at {config.GRBL_HOST}:{config.GRBL_TCP_PORT}")
    else:
        link = _SerialLink()
        link.write(b"\r\n\r\n")   # classic GRBL wake over serial
        time.sleep(0.1)

    banner = link.drain().decode(errors="replace").strip()
    if banner:
        log(f"Controller: {banner.splitlines()[-1]}")
    return link


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
    """Laser on at power_pct (0–100), M4 dynamic power mode.

    M4 (not M3) because the call-response sender starves the planner
    between lines: M4 scales power with actual speed and turns the beam
    off at standstill, so inter-line pauses and dropped links fail dark
    instead of charring a parked spot. Requires the FluidNC spindle to
    be configured as a Laser."""
    s = int(power_pct / 100 * config.GRBL_SPINDLE_MAX_S)
    _send(ser, f"M4 S{s}")


def _laser_off(ser):
    _send(ser, "M5")


# ── Entity g-code emitters ────────────────────────────────────────────────────
#
# Every emitter follows the same bracket: laser-off travel to the mark,
# M4, burn moves at the scribe feed, M5. Coordinates are rounded to
# 0.0001" once and arc I/J offsets are derived from the ROUNDED values,
# so GRBL's start/end-radius consistency check always passes.

def _fmt(v: float) -> str:
    v = round(v, 4) + 0.0     # + 0.0 normalizes -0.0
    return f"{v:.4f}"


def _travel(ser, x: float, y: float, travel: int):
    """Laser-off move at the operator's travel feed (see module docs
    for why this is a G1, not a G0 rapid)."""
    _send(ser, f"G1 X{_fmt(x)} Y{_fmt(y)} F{travel}")


def _stroke(ser, points, feed: int, power: int, travel: int):
    """Travel to points[0], then burn G1s through the rest."""
    _travel(ser, points[0][0], points[0][1], travel)
    _laser_on(ser, power)
    for x, y in points[1:]:
        _send(ser, f"G1 X{_fmt(x)} Y{_fmt(y)} F{feed}")
    _laser_off(ser)


def _burn_line(ser, entity: dict, feed: int, power: int, travel: int):
    start = entity.get("start", [0, 0])
    end   = entity.get("end",   [0, 0])
    _stroke(ser, [start, end], feed, power, travel)


def _burn_polyline(ser, entity: dict, feed: int, power: int, travel: int):
    pts    = entity.get("points", [])
    closed = entity.get("closed", False)
    if len(pts) < 2:
        print("  polyline with <2 points - skipped")
        return
    if closed and pts[-1] != pts[0]:
        pts = pts + [pts[0]]      # spec: closing point is not repeated
    _stroke(ser, pts, feed, power, travel)


def _burn_circle(ser, entity: dict, feed: int, power: int, travel: int):
    """Peg bore: center cross first (the framer drills to it), then the
    outline as a full-circle G3 from the 3 o'clock point."""
    cx, cy = entity.get("center", [0, 0])
    r      = entity.get("radius_in", 0)
    if r <= 0:
        print("  circle with radius <= 0 - skipped")
        return
    if entity.get("scribe_center", True):
        _stroke(ser, [[cx - r, cy], [cx + r, cy]], feed, power, travel)
        _stroke(ser, [[cx, cy - r], [cx, cy + r]], feed, power, travel)
    sx, sy = cx + r, cy
    _travel(ser, sx, sy, travel)
    _laser_on(ser, power)
    _send(ser, f"G3 X{_fmt(sx)} Y{_fmt(sy)} "
               f"I{_fmt(round(cx, 4) - round(sx, 4))} J0.0000 F{feed}")
    _laser_off(ser)


def _burn_arc(ser, entity: dict, feed: int, power: int, travel: int):
    """Arc sweep runs from start_angle to end_angle in the
    increasing-angle direction of P(θ) = C + r·(cosθ, sinθ) — that is
    g-code counter-clockwise, so always G3 (see TSJ_SPEC.md)."""
    cx, cy = entity.get("center", [0, 0])
    r      = entity.get("radius_in", 0)
    sa     = math.radians(entity.get("start_angle_deg", 0))
    ea     = math.radians(entity.get("end_angle_deg",   0))
    if r <= 0:
        print("  arc with radius <= 0 - skipped")
        return
    sx = round(cx + r * math.cos(sa), 4)
    sy = round(cy + r * math.sin(sa), 4)
    ex = round(cx + r * math.cos(ea), 4)
    ey = round(cy + r * math.sin(ea), 4)
    _travel(ser, sx, sy, travel)
    _laser_on(ser, power)
    _send(ser, f"G3 X{_fmt(ex)} Y{_fmt(ey)} "
               f"I{_fmt(round(cx, 4) - sx)} J{_fmt(round(cy, 4) - sy)} "
               f"F{feed}")
    _laser_off(ser)
