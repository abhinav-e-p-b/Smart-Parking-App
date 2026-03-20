"""
db/supabase_client.py — Supabase interface for the parking ANPR system.

All database operations go through this module.

Tables expected in your Supabase project:
  registered_users   — users registered on your website (read-only from here)
  parking_sessions   — live entry/exit log written by ANPR
  parking_slots      — physical slot inventory (capacity tracking)

Run  python db/supabase_client.py --setup  once to create the ANPR tables.
"""

import os
import argparse
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Connection — reads from environment or .env file
# ---------------------------------------------------------------------------

def _get_client() -> Client:
    url  = os.environ.get("SUPABASE_URL")
    key  = os.environ.get("SUPABASE_KEY")    # use service-role key for writes
    if not url or not key:
        raise RuntimeError(
            "Set SUPABASE_URL and SUPABASE_KEY environment variables.\n"
            "  Windows : set SUPABASE_URL=https://xxx.supabase.co\n"
            "  Linux   : export SUPABASE_URL=https://xxx.supabase.co"
        )
    return create_client(url, key)


# Module-level singleton (lazy init)
_client: Optional[Client] = None

def get_db() -> Client:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


# ---------------------------------------------------------------------------
# Schema bootstrap — run once
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Parking sessions table
CREATE TABLE IF NOT EXISTS parking_sessions (
    id              BIGSERIAL PRIMARY KEY,
    plate           TEXT NOT NULL,
    camera_entry    TEXT NOT NULL,
    camera_exit     TEXT,
    entry_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exit_time       TIMESTAMPTZ,
    duration_mins   INTEGER,
    status          TEXT NOT NULL DEFAULT 'inside',   -- 'inside' | 'exited'
    is_registered   BOOLEAN DEFAULT FALSE,
    user_id         UUID,                              -- FK to registered_users if matched
    entry_image_url TEXT,
    exit_image_url  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast plate lookups
CREATE INDEX IF NOT EXISTS idx_sessions_plate  ON parking_sessions(plate);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON parking_sessions(status);

-- Parking slots capacity table
CREATE TABLE IF NOT EXISTS parking_slots (
    id          SERIAL PRIMARY KEY,
    zone        TEXT NOT NULL DEFAULT 'A',
    total       INTEGER NOT NULL DEFAULT 100,
    occupied    INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Insert a default zone if none exists
INSERT INTO parking_slots (zone, total, occupied)
VALUES ('A', 100, 0)
ON CONFLICT DO NOTHING;
"""


def setup_schema():
    """Print the SQL to run in Supabase SQL editor."""
    print("Run the following SQL in your Supabase project → SQL Editor:\n")
    print(SCHEMA_SQL)
    print("\nAlso make sure your 'registered_users' table has at least:")
    print("  id (uuid), plate_number (text), name (text), email (text)")


# ---------------------------------------------------------------------------
# registered_users — lookup (read-only)
# ---------------------------------------------------------------------------

def lookup_registered_user(plate: str) -> Optional[dict]:
    """
    Check if a plate is registered on your website.
    Returns user dict or None.

    Expects your website's registered_users table to have a
    'plate_number' column (exact uppercase match).
    """
    db = get_db()
    result = (
        db.table("registered_users")
        .select("id, name, email, plate_number, vehicle_type")
        .eq("plate_number", plate.upper())
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


# ---------------------------------------------------------------------------
# parking_sessions — write operations
# ---------------------------------------------------------------------------

def record_entry(
    plate: str,
    camera_id: str,
    image_url: str = None,
) -> dict:
    """
    Log a vehicle entry. Returns the created session record.
    Skips duplicate if the same plate is already 'inside'.
    """
    db = get_db()

    # Guard: don't create duplicate active session for same plate
    existing = (
        db.table("parking_sessions")
        .select("id, plate, entry_time")
        .eq("plate", plate.upper())
        .eq("status", "inside")
        .limit(1)
        .execute()
    )
    if existing.data:
        print(f"  [DB] Plate {plate} already has an active session — skipping entry.")
        return existing.data[0]

    user = lookup_registered_user(plate)

    session = {
        "plate":          plate.upper(),
        "camera_entry":   camera_id,
        "entry_time":     datetime.now(timezone.utc).isoformat(),
        "status":         "inside",
        "is_registered":  user is not None,
        "user_id":        user["id"] if user else None,
        "entry_image_url": image_url,
    }

    result = db.table("parking_sessions").insert(session).execute()
    _increment_occupied(1)
    created = result.data[0] if result.data else session
    print(f"  [DB] ENTRY recorded: {plate}  registered={user is not None}")
    return created


def record_exit(
    plate: str,
    camera_id: str,
    image_url: str = None,
) -> Optional[dict]:
    """
    Mark an existing 'inside' session as exited.
    Returns updated session or None if no active session found.
    """
    db = get_db()

    # Find the latest active session for this plate
    result = (
        db.table("parking_sessions")
        .select("id, entry_time")
        .eq("plate", plate.upper())
        .eq("status", "inside")
        .order("entry_time", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        print(f"  [DB] EXIT: no active session found for plate {plate}")
        return None

    session_id  = result.data[0]["id"]
    entry_time  = datetime.fromisoformat(result.data[0]["entry_time"].replace("Z", "+00:00"))
    exit_time   = datetime.now(timezone.utc)
    duration    = int((exit_time - entry_time).total_seconds() / 60)

    update = {
        "camera_exit":    camera_id,
        "exit_time":      exit_time.isoformat(),
        "duration_mins":  duration,
        "status":         "exited",
        "exit_image_url": image_url,
    }

    updated = (
        db.table("parking_sessions")
        .update(update)
        .eq("id", session_id)
        .execute()
    )
    _increment_occupied(-1)
    print(f"  [DB] EXIT recorded: {plate}  duration={duration}min")
    return updated.data[0] if updated.data else None


# ---------------------------------------------------------------------------
# parking_slots — capacity helpers
# ---------------------------------------------------------------------------

def _increment_occupied(delta: int):
    """Increment or decrement the occupied count for zone A."""
    db = get_db()
    try:
        slot = db.table("parking_slots").select("id, occupied, total").eq("zone", "A").limit(1).execute()
        if slot.data:
            row = slot.data[0]
            new_val = max(0, min(row["total"], row["occupied"] + delta))
            db.table("parking_slots").update({"occupied": new_val, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", row["id"]).execute()
    except Exception as e:
        print(f"  [DB] Slot update warning: {e}")


def get_occupancy() -> dict:
    """
    Return current occupancy stats.
    Returns {"total": int, "occupied": int, "vacant": int, "pct": float}
    """
    db = get_db()
    result = db.table("parking_slots").select("total, occupied").eq("zone", "A").limit(1).execute()
    if result.data:
        row     = result.data[0]
        total   = row["total"]
        occupied = row["occupied"]
        vacant  = max(0, total - occupied)
        pct     = round(occupied / total * 100, 1) if total else 0.0
        return {"total": total, "occupied": occupied, "vacant": vacant, "pct": pct}
    return {"total": 0, "occupied": 0, "vacant": 0, "pct": 0.0}


def get_recent_sessions(limit: int = 20) -> list:
    """Fetch the most recent parking sessions for the dashboard."""
    db = get_db()
    result = (
        db.table("parking_sessions")
        .select("plate, status, entry_time, exit_time, duration_mins, is_registered, camera_entry, camera_exit")
        .order("entry_time", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def is_plate_inside(plate: str) -> bool:
    """Quick check — is a given plate currently inside?"""
    db = get_db()
    result = (
        db.table("parking_sessions")
        .select("id")
        .eq("plate", plate.upper())
        .eq("status", "inside")
        .limit(1)
        .execute()
    )
    return bool(result.data)


# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true", help="Print setup SQL")
    parser.add_argument("--status", action="store_true", help="Show current occupancy")
    args = parser.parse_args()

    if args.setup:
        setup_schema()
    elif args.status:
        stats = get_occupancy()
        print(f"Occupancy: {stats['occupied']}/{stats['total']}  ({stats['pct']}% full, {stats['vacant']} vacant)")
    else:
        parser.print_help()
