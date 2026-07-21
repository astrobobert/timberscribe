"""
TimberScribe Flask routes.

Endpoints:
    GET  /                      Job list + upload form
    POST /upload                Receive .tsj file, validate, store
    GET  /job/<id>              Face selector — 4-face radio dialog
    POST /job/<id>/select       Save selected face + burn settings
    POST /job/<id>/print        Queue selected face for printing
    GET  /job/<id>/delete       Delete job and its .tsj file
    GET  /status                Current print status (JSON, polled by UI)
    POST /settings              Update default burn settings
"""

import os
import uuid
from flask import (
    Blueprint, Response, render_template, request, redirect,
    url_for, flash, jsonify, current_app
)
from werkzeug.utils import secure_filename

import config
from app import job_store, tsj_parser

bp = Blueprint("main", __name__)

ALLOWED_EXT = {".tsj"}


def _allowed(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXT


# ── Job list / upload ─────────────────────────────────────────────────────────

@bp.route("/", methods=["GET"])
def index():
    jobs = job_store.list_jobs()
    return render_template("index.html", jobs=jobs)


@bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("main.index"))

    file = request.files["file"]
    if not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("main.index"))

    if not _allowed(file.filename):
        flash("Only .tsj files are accepted.", "error")
        return redirect(url_for("main.index"))

    # Save to uploads folder with a unique prefix to avoid collisions
    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    tsj_path    = os.path.join(config.UPLOAD_DIR, unique_name)
    file.save(tsj_path)

    # Validate the file
    try:
        job = tsj_parser.load(tsj_path)
    except tsj_parser.TsjError as e:
        os.remove(tsj_path)
        flash(f"Invalid .tsj file: {e}", "error")
        return redirect(url_for("main.index"))

    # Store in database
    job_id = job_store.create_job(
        timber_id  = job.timber_id,
        filename   = safe_name,
        tsj_path   = tsj_path,
        face_count = 4,
    )

    flash(f"Uploaded {safe_name} — select a face to print.", "success")
    return redirect(url_for("main.face_select", job_id=job_id))


# ── Face selector ─────────────────────────────────────────────────────────────

@bp.route("/job/<job_id>", methods=["GET"])
def face_select(job_id: str):
    row = job_store.get_job(job_id)
    if row is None:
        flash("Job not found.", "error")
        return redirect(url_for("main.index"))

    try:
        tsj = tsj_parser.load(row["tsj_path"])
    except tsj_parser.TsjError as e:
        flash(f"Could not read job file: {e}", "error")
        return redirect(url_for("main.index"))

    # Build per-face SVG previews by loading all four face .tsj files
    # for this timber. Face files share the same timber_id prefix.
    faces = _load_face_previews(row, tsj)

    return render_template(
        "face_select.html",
        job      = row,
        tsj      = tsj,
        faces    = faces,
        selected = row["selected_face"] or 1,
    )


@bp.route("/job/<job_id>/select", methods=["POST"])
def select_face(job_id: str):
    """Save selected face number and user burn settings."""
    row = job_store.get_job(job_id)
    if row is None:
        return jsonify({"error": "Job not found"}), 404

    face_num = int(request.form.get("face", 1))
    feed     = _clamp(
        int(request.form.get("feed", config.DEFAULT_FEED_IN_PER_MIN)),
        config.MIN_FEED_IN_PER_MIN,
        config.MAX_FEED_IN_PER_MIN
    )
    power    = _clamp(
        int(request.form.get("power", config.DEFAULT_LASER_POWER_PCT)),
        config.MIN_LASER_POWER_PCT,
        config.MAX_LASER_POWER_PCT
    )

    job_store.update_job(
        job_id,
        selected_face   = face_num,
        feed_in_per_min = feed,
        laser_power_pct = power,
        status          = "selected",
    )
    return redirect(url_for("main.face_select", job_id=job_id))


@bp.route("/job/<job_id>/print", methods=["POST"])
def print_job(job_id: str):
    """Queue the selected face for printing."""
    row = job_store.get_job(job_id)
    if row is None:
        flash("Job not found.", "error")
        return redirect(url_for("main.index"))

    if row["selected_face"] is None:
        flash("Select a face before printing.", "error")
        return redirect(url_for("main.face_select", job_id=job_id))

    # Block if something is already printing
    active = job_store.get_active_job()
    if active and active["id"] != job_id:
        flash(
            f"Print head is busy with job {active['timber_id']}. "
            f"Wait for it to finish.", "error"
        )
        return redirect(url_for("main.face_select", job_id=job_id))

    job_store.set_status(job_id, "queued", "Waiting for print head")

    # Hand off to the hardware executor (runs in a background thread)
    from app.executor import start_print
    start_print(job_id)

    flash("Print job queued — burn starting.", "success")
    return redirect(url_for("main.face_select", job_id=job_id))


@bp.route("/job/<job_id>/gcode")
def download_gcode(job_id: str):
    """Download the job as a .gcode file — for running from the
    controller's SD card (field mode, no server at the timber). Uses
    the job's operator-adjusted feed/power so the file burns exactly
    like a streamed print would."""
    row = job_store.get_job(job_id)
    if row is None:
        flash("Job not found.", "error")
        return redirect(url_for("main.index"))

    try:
        tsj = tsj_parser.load(row["tsj_path"])
    except tsj_parser.TsjError as e:
        flash(f"Could not read job file: {e}", "error")
        return redirect(url_for("main.index"))

    from hardware.executor import gcode_program
    lines = gcode_program(
        tsj.entities,
        row["feed_in_per_min"] or tsj.feed_in_per_min,
        row["laser_power_pct"] or tsj.laser_power_pct,
        tsj.travel_in_per_min,
    )
    stem = os.path.splitext(row["filename"])[0]
    return Response(
        "\n".join(lines) + "\n",
        mimetype="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{stem}.gcode"'
        },
    )


# ── Job management ────────────────────────────────────────────────────────────

@bp.route("/job/<job_id>/delete")
def delete_job(job_id: str):
    row = job_store.get_job(job_id)
    if row:
        try:
            os.remove(row["tsj_path"])
        except FileNotFoundError:
            pass
        job_store.delete_job(job_id)
        flash("Job deleted.", "success")
    return redirect(url_for("main.index"))


# ── Status (polled by UI) ─────────────────────────────────────────────────────

@bp.route("/status")
def status():
    """
    Returns current print status as JSON.
    The face_select page polls this every 2 seconds while printing.
    """
    active = job_store.get_active_job()
    if active:
        return jsonify({
            "printing":   True,
            "job_id":     active["id"],
            "timber_id":  active["timber_id"],
            "face":       active["selected_face"],
            "status":     active["status"],
            "message":    active["message"] or "",
        })

    return jsonify({"printing": False})


@bp.route("/status/<job_id>")
def job_status(job_id: str):
    """Status of a specific job."""
    row = job_store.get_job(job_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "job_id":   row["id"],
        "status":   row["status"],
        "message":  row["message"] or "",
        "face":     row["selected_face"],
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def _load_face_previews(row, tsj: tsj_parser.TsjJob) -> list[dict]:
    """
    Build a list of face dicts for the face_select template.
    Each dict has: number, svg, has_linework, length_in, width_in.

    Looks for all four face .tsj files for this timber in the uploads folder.
    Falls back to the current face's SVG if siblings aren't uploaded yet.
    """
    timber_id = row["timber_id"]
    upload_dir = config.UPLOAD_DIR
    faces = []

    for face_num in range(1, 5):
        # Try to find the matching face file by timber_id + face number
        candidate = _find_face_file(upload_dir, timber_id, face_num)

        if candidate:
            try:
                face_tsj = tsj_parser.load(candidate)
                faces.append({
                    "number":       face_num,
                    "svg":          face_tsj.preview_svg,
                    "has_linework": len(face_tsj.entities) > 0,
                    "length_in":    face_tsj.face.length_in,
                    "width_in":     face_tsj.face.width_in,
                    "job_id":       _find_job_id(candidate),
                })
                continue
            except tsj_parser.TsjError:
                pass

        # Face file not found — show placeholder
        faces.append({
            "number":       face_num,
            "svg":          _placeholder_svg(tsj.face.length_in, tsj.face.width_in),
            "has_linework": False,
            "length_in":    tsj.face.length_in,
            "width_in":     tsj.face.width_in,
            "job_id":       None,
        })

    return faces


def _find_face_file(upload_dir: str, timber_id: str, face_num: int) -> str | None:
    """Find the .tsj file for a specific timber ID and face number."""
    target_suffix = f"_face{face_num}.tsj"
    safe_id = timber_id.replace(" ", "_")

    for fname in os.listdir(upload_dir):
        if fname.endswith(target_suffix) and safe_id in fname:
            return os.path.join(upload_dir, fname)
    return None


def _find_job_id(tsj_path: str) -> str | None:
    """Find the job_id for a given .tsj file path."""
    with job_store._db() as conn:
        row = conn.execute(
            "SELECT id FROM jobs WHERE tsj_path = ?", (tsj_path,)
        ).fetchone()
    return row["id"] if row else None


def _placeholder_svg(length_in: float, width_in: float) -> str:
    return (
        f'<svg viewBox="0 0 {length_in:.3f} {width_in:.3f}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{length_in:.3f}" height="{width_in:.3f}" '
        f'fill="#f8f8f8" stroke="#ddd" stroke-width="0.05"/>'
        f'<text x="{length_in/2:.3f}" y="{width_in/2:.3f}" '
        f'text-anchor="middle" dominant-baseline="middle" '
        f'font-size="0.4" fill="#bbb">not uploaded</text>'
        f'</svg>'
    )
