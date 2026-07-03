"""
Executor — bridges the Flask job queue to the hardware burn loop.

Runs the print job in a background daemon thread so Flask stays
responsive during printing. The hardware layer (hardware/executor.py)
does the actual motion and laser control.

The Pi's physical run button is handled here too — it polls for a
queued job and starts it when pressed.
"""

import threading
import traceback

from app import job_store
import config


_lock = threading.Lock()   # only one print at a time


def start_print(job_id: str):
    """
    Called by the Flask route after a job is queued.
    Launches the burn loop in a background thread.
    """
    with _lock:
        active = job_store.get_active_job()
        if active and active["id"] != job_id:
            return  # already printing something else

        job_store.set_status(job_id, "printing", "Starting...")

    t = threading.Thread(target=_run, args=(job_id,), daemon=True)
    t.start()


def _run(job_id: str):
    """Background thread — loads the job and calls the hardware executor."""
    try:
        row = job_store.get_job(job_id)
        if row is None:
            return

        from app.tsj_parser import load as load_tsj
        tsj = load_tsj(row["tsj_path"])

        # Override burn settings with user-adjusted values from the job row
        tsj.feed_in_per_min  = row["feed_in_per_min"]
        tsj.laser_power_pct  = row["laser_power_pct"]

        # Select only the chosen face's entities
        # (all entities in a face .tsj are already for the selected face)
        face_num = row["selected_face"]

        job_store.set_status(
            job_id, "printing",
            f"Burning face {face_num} — {len(tsj.entities)} entities"
        )

        # Hand off to the hardware burn loop
        try:
            from hardware.executor import burn
            burn(
                entities        = tsj.entities,
                feed_in_per_min = tsj.feed_in_per_min,
                laser_power_pct = tsj.laser_power_pct,
                travel_in_per_min = tsj.travel_in_per_min,
                status_cb       = lambda msg: job_store.set_status(
                    job_id, "printing", msg
                ),
            )
        except ImportError:
            # Hardware layer not available (running on dev machine)
            _simulate(job_id, tsj)

        job_store.set_status(job_id, "done", "Complete")

    except Exception as e:
        tb = traceback.format_exc()
        job_store.set_status(job_id, "error", str(e))
        print(f"[executor] ERROR job {job_id}:\n{tb}")


def _simulate(job_id: str, tsj):
    """
    Simulates a burn run on a dev machine without hardware.
    Walks through entities with a short delay per entity.
    """
    import time
    n = len(tsj.entities)
    for i, entity in enumerate(tsj.entities, 1):
        job_store.set_status(
            job_id, "printing",
            f"[sim] Entity {i}/{n} — {entity.get('type', '?')}"
        )
        time.sleep(0.3)
