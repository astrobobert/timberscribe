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

This module is intentionally minimal now — the entity → g-code motion
mapping (G0/G1/G2/G3 paths per entity type) will be developed here in
the next phase. The transport plumbing (connect, handshake,
call-response send, laser M3/M5) is real.

hardware_available() probes the configured transport at call time —
nothing is opened or enumerated at import, so joining the hotspot (or
plugging in the USB cable) after the server starts is fine.

burn() is the single public entry point called by app/executor.py.
"""

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
    """Laser on at power_pct (0–100). Assumes the FluidNC spindle is
    configured as a Laser (laser mode) so M3 only fires during motion —
    which also means a dropped WiFi link mid-burn goes dark, not hot."""
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
    # ASCII only in console prints — Windows consoles choke on U+2192
    print(f"  LINE ({start[0]:.3f},{start[1]:.3f}) -> "
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
          f"{start:.1f} -> {end:.1f} deg")
