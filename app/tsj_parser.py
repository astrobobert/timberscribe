"""
.tsj file parser and validator.

Reads a TimberScribe Job file, validates required fields, and
extracts the data the Flask routes need — timber ID, face metadata,
entity list, and the embedded SVG preview.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any


class TsjError(ValueError):
    """Raised when a .tsj file fails validation."""
    pass


@dataclass
class FaceInfo:
    number:    int
    length_in: float
    width_in:  float


@dataclass
class TsjJob:
    """Parsed and validated contents of a .tsj file."""
    tsj_version:    str
    timber_id:      str
    description:    str
    length_in:      float
    width_in:       float
    face:           FaceInfo
    feed_in_per_min:  int
    laser_power_pct:  int
    travel_in_per_min: int
    entities:       list[dict[str, Any]]
    preview_svg:    str
    raw:            dict[str, Any]   # full parsed JSON for reference


def load(path: str) -> TsjJob:
    """
    Parse and validate a .tsj file.
    Raises TsjError on any validation failure.
    Returns a TsjJob on success.
    """
    if not os.path.isfile(path):
        raise TsjError(f"File not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise TsjError(f"Invalid JSON: {e}")

    # ── Required top-level fields ─────────────────────────────────────────
    version = data.get("tsj_version", "")
    if not version.startswith("2."):
        raise TsjError(
            f"Unsupported .tsj version '{version}'. Expected 2.x"
        )

    # ── Timber section ────────────────────────────────────────────────────
    timber = data.get("timber")
    if not timber:
        raise TsjError("Missing 'timber' section")

    timber_id = timber.get("id", "").strip()
    if not timber_id:
        raise TsjError("timber.id is empty")

    length_in = _pos_float(timber, "length_in", "timber")
    width_in  = _pos_float(timber, "width_in",  "timber")

    # ── Face section ──────────────────────────────────────────────────────
    face_data = data.get("face")
    if not face_data:
        raise TsjError("Missing 'face' section")

    face_number = face_data.get("number")
    if face_number not in (1, 2, 3, 4):
        raise TsjError(f"face.number must be 1–4, got {face_number!r}")

    face = FaceInfo(
        number    = face_number,
        length_in = _pos_float(face_data, "length_in", "face"),
        width_in  = _pos_float(face_data, "width_in",  "face"),
    )

    # ── Settings section ──────────────────────────────────────────────────
    settings = data.get("settings", {})
    scribe   = settings.get("scribe", {})
    travel   = settings.get("travel", {})

    feed        = int(scribe.get("feed_in_per_min",  32))
    power       = int(scribe.get("laser_power_pct",  70))
    travel_feed = int(travel.get("feed_in_per_min",  118))

    # ── Entities ──────────────────────────────────────────────────────────
    entities = data.get("entities", [])
    if not isinstance(entities, list):
        raise TsjError("'entities' must be a list")

    for i, e in enumerate(entities):
        if "type" not in e:
            raise TsjError(f"Entity {i} missing 'type' field")

    # ── Validate all coordinates are within face bounds ───────────────────
    _validate_entity_bounds(entities, face, path)

    # ── Preview SVG ───────────────────────────────────────────────────────
    preview_svg = data.get("preview_svg", "")
    if not preview_svg:
        # Generate a minimal placeholder if absent
        preview_svg = (
            f'<svg viewBox="0 0 {face.length_in:.3f} {face.width_in:.3f}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{face.length_in:.3f}" height="{face.width_in:.3f}" '
            f'fill="white" stroke="#ccc" stroke-width="0.05"/>'
            f'<text x="{face.length_in/2:.3f}" y="{face.width_in/2:.3f}" '
            f'text-anchor="middle" font-size="0.5" fill="#aaa">No preview</text>'
            f'</svg>'
        )

    return TsjJob(
        tsj_version       = version,
        timber_id         = timber_id,
        description       = timber.get("description", ""),
        length_in         = length_in,
        width_in          = width_in,
        face              = face,
        feed_in_per_min   = feed,
        laser_power_pct   = power,
        travel_in_per_min = travel_feed,
        entities          = entities,
        preview_svg       = preview_svg,
        raw               = data,
    )


def _pos_float(obj: dict, key: str, section: str) -> float:
    val = obj.get(key)
    if val is None:
        raise TsjError(f"{section}.{key} is missing")
    try:
        f = float(val)
    except (TypeError, ValueError):
        raise TsjError(f"{section}.{key} must be a number, got {val!r}")
    if f <= 0:
        raise TsjError(f"{section}.{key} must be positive, got {f}")
    return f


def _validate_entity_bounds(
    entities: list, face: FaceInfo, path: str
) -> None:
    """
    Warn (don't fail) if any entity coordinate is outside the face bounds.
    Out-of-bounds coordinates usually mean a projection error in AutoCAD.
    """
    L, W = face.length_in, face.width_in
    tol  = 0.5  # inches tolerance for floating point rounding

    def check(x: float, y: float, idx: int, entity_type: str):
        if x < -tol or x > L + tol or y < -tol or y > W + tol:
            # Log warning but don't raise — let the Pi UI show it
            print(
                f"[tsj_parser] WARNING: entity {idx} ({entity_type}) "
                f"coordinate ({x:.3f}, {y:.3f}) outside face bounds "
                f"({L:.3f} × {W:.3f}) in {os.path.basename(path)}"
            )

    for i, e in enumerate(entities):
        t = e.get("type", "")
        if t == "line":
            s, end = e.get("start", [0, 0]), e.get("end", [0, 0])
            check(s[0], s[1], i, t)
            check(end[0], end[1], i, t)
        elif t == "polyline":
            for pt in e.get("points", []):
                check(pt[0], pt[1], i, t)
        elif t in ("circle", "arc"):
            c = e.get("center", [0, 0])
            check(c[0], c[1], i, t)
