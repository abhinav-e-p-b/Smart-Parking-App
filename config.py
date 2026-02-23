"""
config.py - Central configuration for the parking management system.
Edit values here or override via environment variables.
"""

import os

# ── Camera ──────────────────────────────────────────────────────────────────
# Webcam: use integer index "0", "1", etc.
# IP camera: use full RTSP URL, e.g. "rtsp://admin:pass@192.168.1.100:554/stream"
ENTRY_CAMERA_SOURCE = os.getenv("ENTRY_CAMERA", "0")
EXIT_CAMERA_SOURCE  = os.getenv("EXIT_CAMERA",  "1")

# ── Detection ────────────────────────────────────────────────────────────────
PLATE_MODEL_PATH     = os.getenv("PLATE_MODEL", "license_plate_detector.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE", "0.60"))  # OCR confidence floor
DEBOUNCE_SECONDS     = int(os.getenv("DEBOUNCE", "10"))        # seconds between same-plate logs

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "parking.db")

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE  = os.getenv("LOG_FILE", "parking.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── GPU ──────────────────────────────────────────────────────────────────────
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
