"""
Hardware burn loop.

Translates .tsj entity list into physical motion and laser commands.
Runs on the Pi with pigpio for hardware-timed GPIO.

This module is intentionally minimal now — the motion and laser
control details (PID loop, tape sensor interrupt, laser PWM) will
be developed here in the next phase.

burn() is the single public entry point called by app/executor.py.
"""

from typing import Callable
import config

try:
    import pigpio
    _PI = pigpio.pi()
    HAS_HARDWARE = _PI.connected
except (ImportError, AttributeError):
    _PI = None
    HAS_HARDWARE = False


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
            "pigpio not connected. Is pigpiod running? "
            "Run: sudo pigpiod"
        )

    try:
        _setup_gpio()
        laser_off()

        n = len(entities)
        log(f"Starting burn — {n} entities, "
            f"{feed_in_per_min} in/min, {laser_power_pct}% power")

        for i, entity in enumerate(entities, 1):
            t = entity.get("type", "")
            log(f"Entity {i}/{n}: {t}")

            if t == "line":
                _burn_line(entity, feed_in_per_min, laser_power_pct,
                           travel_in_per_min)
            elif t == "polyline":
                _burn_polyline(entity, feed_in_per_min, laser_power_pct,
                               travel_in_per_min)
            elif t == "circle":
                _burn_circle(entity, feed_in_per_min, laser_power_pct,
                             travel_in_per_min)
            elif t == "arc":
                _burn_arc(entity, feed_in_per_min, laser_power_pct,
                          travel_in_per_min)
            else:
                log(f"  Unknown entity type '{t}' — skipped")

        log("Burn complete")

    finally:
        laser_off()
        _teardown_gpio()


# ── GPIO setup ────────────────────────────────────────────────────────────────

def _setup_gpio():
    if not _PI:
        return
    _PI.set_mode(config.MOTOR_PWM_PIN,   pigpio.OUTPUT)
    _PI.set_mode(config.MOTOR_DIR_PIN,   pigpio.OUTPUT)
    _PI.set_mode(config.LASER_PWM_PIN,   pigpio.OUTPUT)
    _PI.set_mode(config.TAPE_SENSOR_PIN, pigpio.INPUT)
    _PI.set_pull_up_down(config.TAPE_SENSOR_PIN, pigpio.PUD_UP)
    laser_off()


def _teardown_gpio():
    if not _PI:
        return
    laser_off()
    _PI.set_PWM_dutycycle(config.MOTOR_PWM_PIN, 0)


# ── Laser control ─────────────────────────────────────────────────────────────

def laser_on(power_pct: int):
    """Set laser PWM duty cycle. power_pct is 0–100."""
    if not _PI:
        return
    duty = int(power_pct / 100 * 255)
    _PI.set_PWM_dutycycle(config.LASER_PWM_PIN, duty)


def laser_off():
    if not _PI:
        return
    _PI.set_PWM_dutycycle(config.LASER_PWM_PIN, 0)


# ── Entity burn stubs (to be implemented in next phase) ───────────────────────

def _burn_line(entity: dict, feed: int, power: int, travel: int):
    """
    Travel to line start, laser on, traverse to line end, laser off.
    TODO: implement motion control with tape sensor position feedback.
    """
    start = entity.get("start", [0, 0])
    end   = entity.get("end",   [0, 0])
    print(f"  LINE ({start[0]:.3f},{start[1]:.3f}) → "
          f"({end[0]:.3f},{end[1]:.3f})")


def _burn_polyline(entity: dict, feed: int, power: int, travel: int):
    """Burn each segment of the polyline in sequence."""
    pts    = entity.get("points", [])
    closed = entity.get("closed", False)
    if len(pts) < 2:
        return
    if closed and pts[-1] != pts[0]:
        pts = pts + [pts[0]]
    print(f"  POLYLINE {len(pts)} pts, closed={closed}")


def _burn_circle(entity: dict, feed: int, power: int, travel: int):
    """Burn the centre cross first, then trace the circle outline."""
    c = entity.get("center", [0, 0])
    r = entity.get("radius_in", 0)
    print(f"  CIRCLE centre ({c[0]:.3f},{c[1]:.3f}) r={r:.3f}")


def _burn_arc(entity: dict, feed: int, power: int, travel: int):
    c     = entity.get("center", [0, 0])
    r     = entity.get("radius_in", 0)
    start = entity.get("start_angle_deg", 0)
    end   = entity.get("end_angle_deg",   0)
    print(f"  ARC centre ({c[0]:.3f},{c[1]:.3f}) r={r:.3f} "
          f"{start:.1f}°→{end:.1f}°")
