"""
Job store — SQLite-backed queue for TimberScribe print jobs.

Schema:
    jobs
        id          TEXT PRIMARY KEY  (uuid4)
        timber_id   TEXT              (from .tsj timber.id)
        filename    TEXT              (original upload filename)
        tsj_path    TEXT              (absolute path to .tsj file on disk)
        face_count  INTEGER           (number of faces in this timber)
        status      TEXT              (uploaded | selected | queued | printing | done | error)
        selected_face INTEGER         (face number chosen by framer, 1-4)
        feed_in_per_min  INTEGER      (user-set feed rate)
        laser_power_pct  INTEGER      (user-set laser power)
        created_at  TEXT              (ISO timestamp)
        updated_at  TEXT              (ISO timestamp)
        message     TEXT              (last status message or error)
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager

import config


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id               TEXT PRIMARY KEY,
                timber_id        TEXT NOT NULL,
                filename         TEXT NOT NULL,
                tsj_path         TEXT NOT NULL,
                face_count       INTEGER NOT NULL DEFAULT 4,
                status           TEXT NOT NULL DEFAULT 'uploaded',
                selected_face    INTEGER,
                feed_in_per_min  INTEGER NOT NULL DEFAULT 32,
                laser_power_pct  INTEGER NOT NULL DEFAULT 70,
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL,
                message          TEXT
            )
        """)


def create_job(timber_id: str, filename: str, tsj_path: str, face_count: int = 4) -> str:
    """Insert a new job record. Returns the new job id."""
    job_id = str(uuid.uuid4())
    now    = utcnow()
    with _db() as conn:
        conn.execute("""
            INSERT INTO jobs
                (id, timber_id, filename, tsj_path, face_count,
                 status, feed_in_per_min, laser_power_pct,
                 created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            job_id, timber_id, filename, tsj_path, face_count,
            "uploaded",
            config.DEFAULT_FEED_IN_PER_MIN,
            config.DEFAULT_LASER_POWER_PCT,
            now, now
        ))
    return job_id


def get_job(job_id: str) -> sqlite3.Row | None:
    with _db() as conn:
        return conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()


def list_jobs() -> list[sqlite3.Row]:
    """All jobs, newest first."""
    with _db() as conn:
        return conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        ).fetchall()


def update_job(job_id: str, **fields):
    """Update arbitrary fields on a job row."""
    fields["updated_at"] = utcnow()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values     = list(fields.values()) + [job_id]
    with _db() as conn:
        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE id = ?", values
        )


def set_status(job_id: str, status: str, message: str = ""):
    update_job(job_id, status=status, message=message)


def get_active_job() -> sqlite3.Row | None:
    """Return the job currently printing, if any."""
    with _db() as conn:
        return conn.execute(
            "SELECT * FROM jobs WHERE status = 'printing'"
        ).fetchone()


def delete_job(job_id: str):
    with _db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
