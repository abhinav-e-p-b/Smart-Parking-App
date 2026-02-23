"""
admin.py - CLI tool for parking system administration.

Usage:
    python admin.py status          # List all vehicles currently inside
    python admin.py export          # Export full log to CSV
    python admin.py manual-exit AB12CDE   # Force an exit record
    python admin.py stats           # Today's summary
"""

import argparse
import sys
from datetime import datetime, timezone, date
import sqlite3
from database import get_active_vehicles, mark_exit, export_csv, DB_PATH


def cmd_status(args):
    vehicles = get_active_vehicles()
    if not vehicles:
        print("No vehicles currently inside.")
        return
    print(f"\n{'Plate':<12}  {'Entry Time (UTC)'}")
    print("─" * 40)
    for v in vehicles:
        print(f"{v['plate_number']:<12}  {v['entry_time']}")
    print(f"\nTotal inside: {len(vehicles)}")


def cmd_export(args):
    path = args.output or "parking_log.csv"
    export_csv(path)
    print(f"Exported to {path}")


def cmd_manual_exit(args):
    plate = args.plate.upper()
    mark_exit(plate)


def cmd_stats(args):
    today = date.today().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total_entries = conn.execute(
            "SELECT COUNT(*) as c FROM parking_log WHERE entry_time LIKE ?",
            (f"{today}%",)
        ).fetchone()["c"]

        completed = conn.execute(
            "SELECT COUNT(*) as c, AVG(duration_sec) as avg_dur FROM parking_log "
            "WHERE entry_time LIKE ? AND exit_time IS NOT NULL",
            (f"{today}%",)
        ).fetchone()

    avg = completed["avg_dur"]
    avg_str = f"{int(avg)//60}m {int(avg)%60}s" if avg else "N/A"
    print(f"\n── Today's Stats ({today}) ──────────────────")
    print(f"  Total entries  : {total_entries}")
    print(f"  Completed exits: {completed['c']}")
    print(f"  Avg duration   : {avg_str}")
    print(f"  Still inside   : {total_entries - completed['c']}")


def main():
    parser = argparse.ArgumentParser(description="Parking System Admin CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="List vehicles currently inside")

    exp = sub.add_parser("export", help="Export log to CSV")
    exp.add_argument("--output", help="Output file path (default: parking_log.csv)")

    mx = sub.add_parser("manual-exit", help="Force an exit record for a plate")
    mx.add_argument("plate", help="License plate number")

    sub.add_parser("stats", help="Show today's statistics")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "export": cmd_export,
        "manual-exit": cmd_manual_exit,
        "stats": cmd_stats,
    }

    if args.command not in commands:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
