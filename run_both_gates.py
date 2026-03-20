"""
run_both_gates.py — Launch entry AND exit gate cameras simultaneously.

Each gate runs in its own thread. Use this when you have two cameras
connected to the same machine (e.g. laptop webcam + USB camera).

Usage:
  python run_both_gates.py
  python run_both_gates.py --entry 0 --exit 1
  python run_both_gates.py --entry rtsp://cam1/stream --exit rtsp://cam2/stream
  python run_both_gates.py --headless          # no GUI, server mode

For two separate machines, run parking_gate.py individually on each.
"""

import argparse
import threading
import time

from config import cfg
from parking_gate import run_gate


def main():
    parser = argparse.ArgumentParser(description="Run both parking gates")
    parser.add_argument("--entry",    default=cfg.camera.entry_camera,
                        help="Entry camera source (default: 0)")
    parser.add_argument("--exit",     default=cfg.camera.exit_camera,
                        help="Exit camera source (default: 1)")
    parser.add_argument("--model",    default=str(cfg.model.best_weights))
    parser.add_argument("--headless", action="store_true",
                        help="No GUI windows — suitable for servers")
    args = parser.parse_args()

    try:
        entry_src = int(args.entry)
    except (ValueError, TypeError):
        entry_src = args.entry

    try:
        exit_src = int(args.exit)
    except (ValueError, TypeError):
        exit_src = args.exit

    print("Starting both parking gates...")
    print(f"  Entry camera : {entry_src}")
    print(f"  Exit camera  : {exit_src}")
    print(f"  Headless     : {args.headless}")

    entry_thread = threading.Thread(
        target=run_gate,
        kwargs=dict(mode="entry", source=entry_src,
                    model_path=args.model, headless=args.headless),
        daemon=True,
        name="entry-gate",
    )
    exit_thread = threading.Thread(
        target=run_gate,
        kwargs=dict(mode="exit", source=exit_src,
                    model_path=args.model, headless=args.headless),
        daemon=True,
        name="exit-gate",
    )

    entry_thread.start()
    time.sleep(2)        # stagger startup so model loads don't race
    exit_thread.start()

    print("\nBoth gates running. Press Ctrl+C to stop.")
    try:
        while entry_thread.is_alive() or exit_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
