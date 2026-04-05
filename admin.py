"""
admin.py — Command-line admin tools for the parking database.

Usage:
  python admin.py status                        # occupancy stats
  python admin.py sessions                      # list recent sessions
  python admin.py sessions --inside             # only vehicles currently inside
  python admin.py lookup KL07BB1234             # look up a specific plate
  python admin.py set-capacity 200              # update total slot count
  python admin.py manual-entry KL07BB1234       # manually record an entry
  python admin.py manual-exit  KL07BB1234       # manually record an exit
  python admin.py interactive                   # interactive prompt (easiest)
  python admin.py setup-schema                  # print SQL to run in Supabase
"""

import argparse
import re
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from db.supabase_client import (
    get_occupancy, get_recent_sessions,
    lookup_registered_user, is_plate_inside,
    record_entry, record_exit, get_db, setup_schema,
)

PLATE_RE = re.compile(r'^[A-Z0-9]{4,12}$')


def _normalise_plate(raw: str) -> str:
    return raw.strip().upper().replace(" ", "").replace("-", "")


def _validate_plate(plate: str) -> bool:
    return bool(PLATE_RE.match(plate))


def _print_occ():
    occ     = get_occupancy()
    bar_len = 30
    filled  = int(bar_len * occ["occupied"] / occ["total"]) if occ["total"] else 0
    bar     = "\u2588" * filled + "\u2591" * (bar_len - filled)
    print(f"\n  [{bar}] {occ['pct']}%  --  {occ['vacant']} vacant / {occ['total']} total")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_status(_args):
    occ = get_occupancy()
    print(f"\n  Occupancy Status")
    print(f"  Total slots : {occ['total']}")
    print(f"  Occupied    : {occ['occupied']}  ({occ['pct']}%)")
    print(f"  Vacant      : {occ['vacant']}\n")


def cmd_sessions(args):
    sessions = get_recent_sessions(limit=args.limit)
    if args.inside:
        sessions = [s for s in sessions if s["status"] == "inside"]
    if not sessions:
        print("No sessions found.")
        return
    print(f"\n{'─'*90}")
    print(f"  {'PLATE':<14} {'STATUS':<10} {'ENTRY':<20} {'EXIT':<20} {'DUR':>6}  REG  CAMERA")
    print(f"{'─'*90}")
    for s in sessions:
        entry = s["entry_time"][:16].replace("T", " ") if s["entry_time"] else "--"
        exit_ = s["exit_time"][:16].replace("T", " ")  if s["exit_time"]  else "--"
        dur   = f"{s['duration_mins']}m" if s["duration_mins"] else "--"
        reg   = "+" if s["is_registered"] else " "
        print(f"  {s['plate']:<14} {s['status']:<10} {entry:<20} {exit_:<20} {dur:>6}  {reg}    {s.get('camera_entry','')}")
    print(f"{'─'*90}\n")


def cmd_lookup(args):
    plate  = _normalise_plate(args.plate)
    user   = lookup_registered_user(plate)
    inside = is_plate_inside(plate)
    print(f"\n  Plate  : {plate}")
    print(f"  Inside : {'YES' if inside else 'NO'}")
    if user:
        print(f"  Member : {user.get('name','--')}  <{user.get('email','--')}>")
    else:
        print(f"  Member : NOT REGISTERED")
    print()


def cmd_manual_entry(args):
    plate = _normalise_plate(args.plate)
    if not _validate_plate(plate):
        print(f"  Invalid plate format: {plate}")
        return
    if is_plate_inside(plate):
        print(f"  {plate} is already recorded as inside.")
        return
    user   = lookup_registered_user(plate)
    record_entry(plate, "MANUAL_ENTRY")
    occ    = get_occupancy()
    print(f"\n  ENTRY recorded")
    print(f"  Plate   : {plate}")
    print(f"  Member  : {user['name'] if user else 'Guest (not registered)'}")
    print(f"  Vacant  : {occ['vacant']} slots remaining\n")


def cmd_manual_exit(args):
    plate = _normalise_plate(args.plate)
    if not _validate_plate(plate):
        print(f"  Invalid plate format: {plate}")
        return
    if not is_plate_inside(plate):
        print(f"  No active session found for {plate}.")
        print(f"  Tip: run 'python admin.py sessions --inside' to see who's currently parked.")
        return
    result = record_exit(plate, "MANUAL_EXIT")
    occ    = get_occupancy()
    if result:
        print(f"\n  EXIT recorded")
        print(f"  Plate    : {plate}")
        print(f"  Duration : {result.get('duration_mins', '--')} minutes")
        print(f"  Vacant   : {occ['vacant']} slots now available\n")
    else:
        print(f"  Could not record exit for {plate}.")


def cmd_set_capacity(args):
    db = get_db()
    db.table("parking_slots").update({"total": args.slots}).eq("zone", "A").eq("is_active", True).execute()
    print(f"  Capacity updated to {args.slots} slots.")


def cmd_setup(_args):
    setup_schema()


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def cmd_interactive(_args):
    print("\n" + "="*55)
    print("  Parking ANPR -- Manual Entry Terminal")
    print("  Type 'help' for commands, 'quit' to exit")
    print("="*55)
    _print_occ()

    while True:
        try:
            raw = input("\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.")
            break

        if not raw:
            continue

        parts = raw.upper().split()
        cmd   = parts[0]

        if cmd in ("QUIT", "Q"):
            print("  Goodbye.")
            break

        elif cmd == "HELP":
            print("""
  Commands:
    IN  <plate>       -- record a manual entry    e.g.  IN KL07BB1234
    OUT <plate>       -- record a manual exit     e.g.  OUT MH12AB3456
    CHECK <plate>     -- look up a plate          e.g.  CHECK DL01AB1234
    LIST              -- show vehicles currently inside
    STATUS            -- show occupancy stats
    QUIT              -- exit
            """)

        elif cmd == "IN" and len(parts) >= 2:
            plate = _normalise_plate(parts[1])
            if not _validate_plate(plate):
                print(f"  Invalid plate: {plate}")
                continue
            if is_plate_inside(plate):
                print(f"  {plate} is already inside.")
                continue
            user = lookup_registered_user(plate)
            record_entry(plate, "MANUAL_ENTRY")
            occ  = get_occupancy()
            print(f"  ENTRY  {plate}")
            print(f"  {'Member: ' + user['name'] if user else 'Guest: not registered'}")
            print(f"  Vacant : {occ['vacant']} slots")

        elif cmd == "OUT" and len(parts) >= 2:
            plate = _normalise_plate(parts[1])
            if not _validate_plate(plate):
                print(f"  Invalid plate: {plate}")
                continue
            if not is_plate_inside(plate):
                print(f"  {plate} has no active session.")
                continue
            result = record_exit(plate, "MANUAL_EXIT")
            occ    = get_occupancy()
            dur    = result.get("duration_mins", "--") if result else "--"
            print(f"  EXIT   {plate}  ({dur} min)")
            print(f"  Vacant : {occ['vacant']} slots")

        elif cmd == "CHECK" and len(parts) >= 2:
            plate  = _normalise_plate(parts[1])
            user   = lookup_registered_user(plate)
            inside = is_plate_inside(plate)
            print(f"  Plate  : {plate}")
            print(f"  Inside : {'YES' if inside else 'NO'}")
            print(f"  Member : {user['name'] if user else 'not registered'}")

        elif cmd == "LIST":
            sessions = get_recent_sessions(limit=200)
            inside   = [s for s in sessions if s["status"] == "inside"]
            if not inside:
                print("  No vehicles currently inside.")
            else:
                print(f"\n  {'PLATE':<14} {'ENTRY TIME':<20} TYPE")
                print(f"  {'─'*50}")
                for s in inside:
                    entry  = s["entry_time"][:16].replace("T", " ")
                    member = "Member" if s["is_registered"] else "Guest"
                    print(f"  {s['plate']:<14} {entry:<20} {member}")
                print(f"\n  Total inside: {len(inside)}")

        elif cmd == "STATUS":
            _print_occ()

        else:
            print(f"  Unknown command. Type HELP for commands.")


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Parking ANPR admin tools")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status")

    p_sess = sub.add_parser("sessions")
    p_sess.add_argument("--limit",  type=int, default=30)
    p_sess.add_argument("--inside", action="store_true")

    p_look = sub.add_parser("lookup")
    p_look.add_argument("plate")

    p_cap = sub.add_parser("set-capacity")
    p_cap.add_argument("slots", type=int)

    p_entry = sub.add_parser("manual-entry")
    p_entry.add_argument("plate", help="Number plate e.g. KL07BB1234")

    p_exit = sub.add_parser("manual-exit")
    p_exit.add_argument("plate", help="Number plate e.g. KL07BB1234")

    sub.add_parser("interactive")
    sub.add_parser("setup-schema")

    args = parser.parse_args()
    {
        "status":        cmd_status,
        "sessions":      cmd_sessions,
        "lookup":        cmd_lookup,
        "set-capacity":  cmd_set_capacity,
        "manual-entry":  cmd_manual_entry,
        "manual-exit":   cmd_manual_exit,
        "interactive":   cmd_interactive,
        "setup-schema":  cmd_setup,
    }.get(args.cmd, lambda _: parser.print_help())(args)


if __name__ == "__main__":
    main()
