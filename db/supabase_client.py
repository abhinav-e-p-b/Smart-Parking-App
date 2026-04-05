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
-- ============================================================
-- STEP 1 — users & vehicles (Supabase auth-linked tables)
--           Run this block first
-- ============================================================

-- 1a. users — mirrors auth.users, stores profile data
CREATE TABLE IF NOT EXISTS users (
    id         UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name       TEXT,
    email      TEXT,
    phone      TEXT,
    avatar_url TEXT,
    role       TEXT        NOT NULL DEFAULT 'user',   -- 'user' | 'admin'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1b. vehicles — one user can have multiple plates
CREATE TABLE IF NOT EXISTS vehicles (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plate_number TEXT        NOT NULL UNIQUE,
    vehicle_type TEXT,
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    owner_name   TEXT,
    entry_time   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vehicles_plate   ON vehicles(plate_number);
CREATE INDEX IF NOT EXISTS idx_vehicles_user_id ON vehicles(user_id);


-- ============================================================
-- STEP 2 — parking_slots
--           DROP first so old schema (name/capacity/is_active)
--           is replaced with the correct one (zone/total/occupied)
-- ============================================================

DROP TABLE IF EXISTS parking_slots CASCADE;

CREATE TABLE parking_slots (
    id         SERIAL      PRIMARY KEY,
    zone       TEXT        NOT NULL UNIQUE,   -- UNIQUE required for ON CONFLICT (zone)
    total      INTEGER     NOT NULL DEFAULT 100,
    occupied   INTEGER     NOT NULL DEFAULT 0,
    is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO parking_slots (zone, total, occupied)
VALUES ('A', 100, 0);


-- ============================================================
-- STEP 3 — parking_sessions (ANPR entry/exit log)
-- ============================================================

CREATE TABLE IF NOT EXISTS parking_sessions (
    id              BIGSERIAL   PRIMARY KEY,
    plate           TEXT        NOT NULL,
    camera_entry    TEXT        NOT NULL,
    camera_exit     TEXT,
    entry_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exit_time       TIMESTAMPTZ,
    duration_mins   INTEGER,
    status          TEXT        NOT NULL DEFAULT 'inside',   -- 'inside' | 'exited'
    is_registered   BOOLEAN     NOT NULL DEFAULT FALSE,
    user_id         UUID        REFERENCES users(id) ON DELETE SET NULL,
    vehicle_id      UUID        REFERENCES vehicles(id) ON DELETE SET NULL,
    entry_image_url TEXT,
    exit_image_url  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_plate  ON parking_sessions(plate);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON parking_sessions(status);


-- ============================================================
-- STEP 4 — bookings (pre-scheduled parking)
-- ============================================================

CREATE TABLE IF NOT EXISTS bookings (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vehicle_id       UUID        NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    slot_id          UUID        REFERENCES parking_slots(id) ON DELETE SET NULL,
    plan             TEXT,                                    -- e.g. 'hourly', 'daily'
    scheduled_entry  TIMESTAMPTZ,                            -- fixed: was DATE, needs time+tz
    scheduled_exit   TIMESTAMPTZ,                            -- fixed: was DATE, needs time+tz
    status           TEXT        NOT NULL DEFAULT 'pending', -- 'pending'|'active'|'completed'|'cancelled'
    amount           NUMERIC(10,2),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status  ON bookings(status);
"""


def setup_schema():
    """Print the SQL to run in Supabase SQL editor."""
    print("=" * 65)
    print("  Paste into: Supabase → SQL Editor → New query")
    print("  Run each STEP block separately in order (1 → 2 → 3 → 4).")
    print("  STEP 2 drops the old parking_slots table — this is intentional.")
    print("=" * 65)
    print(SCHEMA_SQL)


# ---------------------------------------------------------------------------
# vehicles / users — plate lookup (read-only)
# ---------------------------------------------------------------------------

def lookup_registered_user(plate: str) -> Optional[dict]:
    """
    Check if a plate is registered in the vehicles table.
    Joins to users to get name/email.
    Returns a unified dict or None.
    """
    db = get_db()
    result = (
        db.table("vehicles")
        .select("id, plate_number, vehicle_type, is_active, user_id, users(id, name, email, role)")
        .eq("plate_number", plate.upper())
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row  = result.data[0]
    user = row.get("users") or {}
    return {
        "id":           user.get("id"),
        "name":         user.get("name") or row.get("owner_name", ""),
        "email":        user.get("email", ""),
        "role":         user.get("role", "user"),
        "plate_number": row["plate_number"],
        "vehicle_type": row.get("vehicle_type"),
        "vehicle_id":   row["id"],
    }


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
        "plate":           plate.upper(),
        "camera_entry":    camera_id,
        "entry_time":      datetime.now(timezone.utc).isoformat(),
        "status":          "inside",
        "is_registered":   user is not None,
        "user_id":         user["id"]         if user else None,
        "vehicle_id":      user["vehicle_id"] if user else None,
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
        slot = (
            db.table("parking_slots")
            .select("id, occupied, total")
            .eq("zone", "A")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if slot.data:
            row     = slot.data[0]
            new_val = max(0, min(row["total"], row["occupied"] + delta))
            db.table("parking_slots").update({
                "occupied":   new_val,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", row["id"]).execute()
    except Exception as e:
        print(f"  [DB] Slot update warning: {e}")


def get_occupancy() -> dict:
    """
    Return current occupancy stats.
    Returns {"total": int, "occupied": int, "vacant": int, "pct": float}
    """
    db = get_db()
    result = (
        db.table("parking_slots")
        .select("total, occupied")
        .eq("zone", "A")
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
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
