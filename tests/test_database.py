"""
tests/test_database.py - Unit tests for database.py

Uses a temporary in-memory / temp-file SQLite database so tests
never touch the real parking.db.

Run with:
    pytest tests/test_database.py -v
"""

import os
import sys
import time
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

# Allow importing from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ─────────────────────────────────────────────
# Fixture: isolated temp database per test
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """
    Redirect DB_PATH to a fresh temp file for every test.
    Also re-runs init_db() so the schema is clean.
    """
    db_file = tmp_path / "test_parking.db"

    import database
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()

    yield db_file


# ─────────────────────────────────────────────
# init_db
# ─────────────────────────────────────────────

class TestInitDb:

    def test_creates_table(self, isolated_db):
        import sqlite3
        with sqlite3.connect(isolated_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        names = [t[0] for t in tables]
        assert "parking_log" in names

    def test_idempotent(self, isolated_db):
        """Calling init_db() twice should not raise or duplicate tables."""
        from database import init_db
        init_db()
        init_db()

        import sqlite3
        with sqlite3.connect(isolated_db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='parking_log'"
            ).fetchone()[0]
        assert count == 1


# ─────────────────────────────────────────────
# vehicle_inside
# ─────────────────────────────────────────────

class TestVehicleInside:

    def test_returns_false_for_unknown_plate(self):
        from database import vehicle_inside
        assert vehicle_inside("XX99ZZZ") is False

    def test_returns_true_after_entry(self):
        from database import mark_entry, vehicle_inside
        mark_entry("AB12CDE")
        assert vehicle_inside("AB12CDE") is True

    def test_returns_false_after_entry_and_exit(self):
        from database import mark_entry, mark_exit, vehicle_inside
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        assert vehicle_inside("AB12CDE") is False

    def test_case_sensitive(self):
        """Plate strings are stored as-is; 'ab12cde' != 'AB12CDE'."""
        from database import mark_entry, vehicle_inside
        mark_entry("AB12CDE")
        assert vehicle_inside("ab12cde") is False


# ─────────────────────────────────────────────
# mark_entry
# ─────────────────────────────────────────────

class TestMarkEntry:

    def test_creates_row(self, isolated_db):
        from database import mark_entry
        import sqlite3
        mark_entry("AB12CDE")
        with sqlite3.connect(isolated_db) as conn:
            row = conn.execute(
                "SELECT * FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchone()
        assert row is not None

    def test_exit_time_is_null_after_entry(self, isolated_db):
        from database import mark_entry
        import sqlite3
        mark_entry("AB12CDE")
        with sqlite3.connect(isolated_db) as conn:
            row = conn.execute(
                "SELECT exit_time FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchone()
        assert row[0] is None

    def test_entry_time_is_iso_utc(self, isolated_db):
        from database import mark_entry
        import sqlite3
        mark_entry("AB12CDE")
        with sqlite3.connect(isolated_db) as conn:
            row = conn.execute(
                "SELECT entry_time FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchone()
        # Should parse without error
        dt = datetime.fromisoformat(row[0])
        assert dt.tzinfo is not None  # timezone-aware

    def test_skips_duplicate_if_already_inside(self, isolated_db):
        """A second mark_entry() for the same plate should be silently skipped."""
        from database import mark_entry
        import sqlite3
        mark_entry("AB12CDE")
        mark_entry("AB12CDE")   # should warn, not raise, not insert
        with sqlite3.connect(isolated_db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchone()[0]
        assert count == 1

    def test_allows_new_entry_after_exit(self):
        """Same plate can enter again after a complete exit."""
        from database import mark_entry, mark_exit, vehicle_inside
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        mark_entry("AB12CDE")   # second visit
        assert vehicle_inside("AB12CDE") is True

    def test_multiple_different_plates(self, isolated_db):
        from database import mark_entry
        import sqlite3
        mark_entry("AB12CDE")
        mark_entry("XY99ZZZ")
        with sqlite3.connect(isolated_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM parking_log").fetchone()[0]
        assert count == 2


# ─────────────────────────────────────────────
# mark_exit
# ─────────────────────────────────────────────

class TestMarkExit:

    def test_sets_exit_time(self, isolated_db):
        from database import mark_entry, mark_exit
        import sqlite3
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        with sqlite3.connect(isolated_db) as conn:
            row = conn.execute(
                "SELECT exit_time FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchone()
        assert row[0] is not None

    def test_sets_duration_sec(self, isolated_db):
        from database import mark_entry, mark_exit
        import sqlite3
        mark_entry("AB12CDE")
        time.sleep(1)           # ensure at least 1 second passes
        mark_exit("AB12CDE")
        with sqlite3.connect(isolated_db) as conn:
            row = conn.execute(
                "SELECT duration_sec FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchone()
        assert row[0] is not None
        assert row[0] >= 1

    def test_duration_is_non_negative(self, isolated_db):
        from database import mark_entry, mark_exit
        import sqlite3
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        with sqlite3.connect(isolated_db) as conn:
            row = conn.execute(
                "SELECT duration_sec FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchone()
        assert row[0] >= 0

    def test_no_entry_record_is_safe(self):
        """mark_exit() for an unknown plate should log a warning but not raise."""
        from database import mark_exit
        mark_exit("UNKNOWN1")  # must not raise

    def test_only_updates_open_entry(self, isolated_db):
        """mark_exit() should not touch already-closed records."""
        from database import mark_entry, mark_exit
        import sqlite3

        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        # Second visit
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")

        with sqlite3.connect(isolated_db) as conn:
            rows = conn.execute(
                "SELECT exit_time FROM parking_log WHERE plate_number='AB12CDE'"
            ).fetchall()
        # Both rows should have an exit_time
        assert len(rows) == 2
        assert all(r[0] is not None for r in rows)


# ─────────────────────────────────────────────
# get_active_vehicles
# ─────────────────────────────────────────────

class TestGetActiveVehicles:

    def test_empty_when_no_entries(self):
        from database import get_active_vehicles
        assert get_active_vehicles() == []

    def test_returns_entered_vehicle(self):
        from database import mark_entry, get_active_vehicles
        mark_entry("AB12CDE")
        active = get_active_vehicles()
        plates = [v["plate_number"] for v in active]
        assert "AB12CDE" in plates

    def test_excludes_exited_vehicle(self):
        from database import mark_entry, mark_exit, get_active_vehicles
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        active = get_active_vehicles()
        plates = [v["plate_number"] for v in active]
        assert "AB12CDE" not in plates

    def test_returns_multiple_active(self):
        from database import mark_entry, get_active_vehicles
        mark_entry("AB12CDE")
        mark_entry("XY99ZZZ")
        active = get_active_vehicles()
        assert len(active) == 2

    def test_mixed_active_and_exited(self):
        from database import mark_entry, mark_exit, get_active_vehicles
        mark_entry("AB12CDE")
        mark_entry("XY99ZZZ")
        mark_exit("AB12CDE")
        active = get_active_vehicles()
        plates = [v["plate_number"] for v in active]
        assert "XY99ZZZ" in plates
        assert "AB12CDE" not in plates

    def test_result_has_required_keys(self):
        from database import mark_entry, get_active_vehicles
        mark_entry("AB12CDE")
        active = get_active_vehicles()
        assert "plate_number" in active[0]
        assert "entry_time" in active[0]


# ─────────────────────────────────────────────
# export_csv
# ─────────────────────────────────────────────

class TestExportCsv:

    def test_creates_file(self, tmp_path):
        from database import mark_entry, mark_exit, export_csv
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        out = str(tmp_path / "out.csv")
        export_csv(out)
        assert os.path.exists(out)

    def test_csv_has_header_and_row(self, tmp_path):
        from database import mark_entry, mark_exit, export_csv
        import csv
        mark_entry("AB12CDE")
        mark_exit("AB12CDE")
        out = str(tmp_path / "out.csv")
        export_csv(out)
        with open(out) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["plate_number"] == "AB12CDE"
        assert rows[0]["exit_time"] != ""

    def test_empty_db_exports_header_only(self, tmp_path):
        from database import export_csv
        import csv
        out = str(tmp_path / "out.csv")
        export_csv(out)
        with open(out) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows == []
