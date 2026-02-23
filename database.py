"""
database.py - SQLite-backed parking log with CSV export support.

Schema:
    parking_log (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number  TEXT NOT NULL,
        entry_time    TEXT NOT NULL,       -- ISO-8601 UTC
        exit_time     TEXT,               -- NULL while vehicle is inside
        duration_sec  INTEGER             -- populated on exit
    )
"""

import sqlite3
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("parking.db")


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS parking_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number  TEXT    NOT NULL,
                entry_time    TEXT    NOT NULL,
                exit_time     TEXT,
                duration_sec  INTEGER
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_plate
            ON parking_log (plate_number)
        """)
    logger.info(f"Database ready at {DB_PATH}")


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def vehicle_inside(plate: str) -> bool:
    """Return True if there is an open entry (no exit_time) for this plate."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM parking_log WHERE plate_number = ? AND exit_time IS NULL",
            (plate,)
        ).fetchone()
    return row is not None


def mark_entry(plate: str) -> None:
    """
    Log a new entry for the given plate.
    If the vehicle is already inside (no exit recorded), logs a warning and skips.
    """
    if vehicle_inside(plate):
        logger.warning(f"ENTRY skipped — {plate} already has an open entry record")
        return

    now = _now_iso()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO parking_log (plate_number, entry_time) VALUES (?, ?)",
            (plate, now)
        )
    logger.info(f"ENTRY logged → {plate} at {now}")


def mark_exit(plate: str) -> None:
    """
    Update the most recent open entry for this plate with the current exit time.
    Computes duration in seconds.
    """
    with _connect() as conn:
        row = conn.execute(
            """SELECT id, entry_time FROM parking_log
               WHERE plate_number = ? AND exit_time IS NULL
               ORDER BY id DESC LIMIT 1""",
            (plate,)
        ).fetchone()

        if row is None:
            logger.warning(f"EXIT skipped — no open entry found for {plate}")
            return

        now = _now_iso()
        entry_dt = datetime.fromisoformat(row["entry_time"])
        exit_dt  = datetime.fromisoformat(now)
        duration = int((exit_dt - entry_dt).total_seconds())

        conn.execute(
            "UPDATE parking_log SET exit_time = ?, duration_sec = ? WHERE id = ?",
            (now, duration, row["id"])
        )
    logger.info(f"EXIT logged  → {plate} | duration {duration // 60}m {duration % 60}s")


def get_active_vehicles() -> list[dict]:
    """Return all vehicles currently inside (no exit recorded)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT plate_number, entry_time FROM parking_log WHERE exit_time IS NULL ORDER BY entry_time"
        ).fetchall()
    return [dict(r) for r in rows]


def export_csv(output_path: str = "parking_log.csv") -> None:
    """Export full parking_log table to a CSV file."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT plate_number, entry_time, exit_time, duration_sec FROM parking_log ORDER BY id"
        ).fetchall()

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["plate_number", "entry_time", "exit_time", "duration_sec"])
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
    logger.info(f"Exported {len(rows)} records to {output_path}")


# ─────────────────────────────────────────────
# Init on import
# ─────────────────────────────────────────────
init_db()
