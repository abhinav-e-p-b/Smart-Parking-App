# 🅿 Real-Time Parking Management System
### Automatic Number Plate Recognition — Production-Grade Entry & Exit Logging

This system converts a YOLOv8 license plate detector into a live, gate-ready parking management solution. It reads a camera feed in real time, detects and OCR-reads license plates, and logs structured entry and exit records to a SQLite database — with no video files, no CSV interpolation, and no post-processing required.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [File Structure](#2-file-structure)
3. [How It Works](#3-how-it-works)
4. [Requirements](#4-requirements)
5. [Installation](#5-installation)
6. [Configuration](#6-configuration)
7. [Running the System](#7-running-the-system)
8. [Admin CLI](#8-admin-cli)
9. [Database Schema](#9-database-schema)
10. [Module Reference](#10-module-reference)
11. [Testing](#11-testing)
12. [Camera Setup Guide](#12-camera-setup-guide)
13. [Adapting the Plate Format](#13-adapting-the-plate-format)
14. [Troubleshooting](#14-troubleshooting)
15. [Next-Level Upgrades](#15-next-level-upgrades)

---

## 1. Project Overview

### What this system does

- Connects to a **live webcam or IP CCTV camera** (RTSP stream)
- Detects license plates in every video frame using a **YOLOv8 model**
- Reads the plate text using **EasyOCR** and validates it against a configurable format
- Logs an **entry timestamp** when a vehicle arrives at the entry gate
- Logs an **exit timestamp** and computes a **duration** when the same vehicle leaves
- Prevents duplicate logs using a **debounce timer** (configurable, default 10 seconds)
- Filters out low-quality readings using a **confidence threshold** (default 0.60)
- Stores all records in a **SQLite database** that survives reboots and is queryable at any time
- Provides an **operator CLI** (`admin.py`) for status checks, manual overrides, and CSV exports

### What this system does NOT do (by design)

- It does not process pre-recorded video files
- It does not track vehicle trajectories across frames (SORT tracking was removed — parking gates need plate identity, not movement paths)
- It does not require a GPU (CPU inference is fully supported for low-to-medium traffic)
- It does not save output video

---

## 2. File Structure

```
parking_system/
│
├── camera.py                  # Main entry point — camera loop and event dispatch
├── detection.py               # detect_plate() and read_plate() — YOLO + EasyOCR
├── database.py                # SQLite wrapper — mark_entry(), mark_exit(), etc.
├── config.py                  # All tunable settings in one place
├── admin.py                   # Operator CLI: status, export, manual exit, stats
├── requirements.txt           # Python dependencies
│
├── license_plate_detector.pt  # Your trained YOLOv8 plate model (not included)
├── parking.db                 # SQLite database — auto-created on first run
├── parking.log                # Log file — auto-created on first run
│
└── tests/
    ├── __init__.py
    ├── test_detection.py      # Unit tests for OCR logic and format validation
    └── test_database.py       # Unit tests for all database operations
```

### File roles at a glance

| File | Responsibility | Imports |
|---|---|---|
| `camera.py` | Opens camera, runs detection loop, calls mark_entry/mark_exit | `detection`, `database` |
| `detection.py` | Wraps YOLOv8 and EasyOCR, validates and corrects plate text | `ultralytics`, `easyocr`, `cv2` |
| `database.py` | All SQLite reads and writes, CSV export | `sqlite3`, `csv` |
| `config.py` | Central config, reads from environment variables | `os` |
| `admin.py` | CLI tool for operators, calls database functions directly | `database`, `sqlite3` |

---

## 3. How It Works

### Detection pipeline (per frame)

```
Camera Frame
    │
    ▼
detect_plate(frame)          ← YOLOv8 finds the highest-confidence plate region
    │                           Returns grayscale + threshold-processed crop, or None
    │ None → skip frame
    ▼
read_plate(crop)             ← EasyOCR reads text from crop
    │                           Validates against plate format (UK 7-char default)
    │                           Applies character correction (O↔0, I↔1, S↔5, etc.)
    │                           Returns (plate_text, confidence) or (None, 0.0)
    │
    ├── confidence < 0.60 → discard (too noisy)
    ├── plate seen < 10s ago → discard (debounce)
    │
    ▼
camera_mode == "entry"?
    ├── Yes → mark_entry(plate)   ← INSERT row with entry_time, exit_time = NULL
    └── No  → vehicle_inside(plate)?
                ├── Yes → mark_exit(plate)    ← UPDATE row: exit_time, duration_sec
                └── No  → log warning (orphan exit scan)
```

### Debounce logic

When a vehicle sits at a gate, the camera may read the same plate dozens of times per second. The debounce system records the timestamp of each successful detection in a `recent_detections` dict. Any subsequent reading of the same plate within `DEBOUNCE_SECONDS` is silently ignored. The dict is in-memory only — it resets when the process restarts, which is intentional.

### Duplicate entry protection

`mark_entry()` first calls `vehicle_inside()` before inserting. If an open entry already exists for that plate (i.e. `exit_time IS NULL`), the insert is skipped and a warning is logged. This means even if debounce fails (e.g. after a restart), the database stays clean.

---

## 4. Requirements

### Software

- Python 3.10 or higher
- CUDA 12.1 (optional, for GPU acceleration)

### Python packages

All listed in `requirements.txt`. Key dependencies:

| Package | Purpose |
|---|---|
| `ultralytics` | YOLOv8 inference for plate detection |
| `easyocr` | OCR engine for reading plate text |
| `opencv-python` | Camera access and image preprocessing |
| `torch` / `torchvision` | Deep learning backend for both YOLO and EasyOCR |
| `numpy` | Array operations for frame handling |
| `python-dotenv` | Optional: load config from `.env` file |

### Hardware

| Use Case | Minimum Spec |
|---|---|
| Development / testing | Any modern laptop with CPU |
| Single gate, moderate traffic | Intel i5 / AMD Ryzen 5, 8 GB RAM |
| Multiple gates or high throughput | NVIDIA GPU (GTX 1660+), 16 GB RAM |
| Edge / embedded deployment | NVIDIA Jetson Orin Nano 8 GB |

### Model file

You must supply `license_plate_detector.pt` — a YOLOv8 model trained on license plate images. A compatible model trained on the [Roboflow License Plate Recognition dataset](https://universe.roboflow.com/roboflow-universe-projects/license-plate-recognition-rxg4e/dataset/4) can be downloaded from the original project resources. Place the `.pt` file in the root of `parking_system/`.

---

## 5. Installation

### Step 1 — Clone or copy the project

```bash
git clone <your-repo-url> parking_system
cd parking_system
```

### Step 2 — Create a Python environment

```bash
# Using conda (recommended)
conda create --prefix ./env python=3.10 -y
conda activate ./env

# Or using venv
python3.10 -m venv env
source env/bin/activate        # Linux / macOS
env\Scripts\activate           # Windows
```

### Step 3 — Install dependencies

**CPU only (works on any machine):**
```bash
pip install -r requirements.txt
```

**GPU (CUDA 12.1) — faster inference for high-traffic deployments:**
```bash
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

**GPU (CUDA 11.8):**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Step 4 — Add your model

```bash
# Copy your trained model into the project root
cp /path/to/license_plate_detector.pt .
```

### Step 5 — Verify everything works

```bash
# Check camera connectivity (webcam)
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK:', cap.isOpened()); cap.release()"

# Check YOLO model loads
python -c "from ultralytics import YOLO; m = YOLO('license_plate_detector.pt'); print('Model OK')"

# Check database initialises
python -c "from database import init_db; init_db(); print('Database OK')"
```

---

## 6. Configuration

All settings are centralised in `config.py`. Every value can be overridden with an environment variable, making the system Docker- and `.env`-friendly.

```python
# config.py

ENTRY_CAMERA_SOURCE = os.getenv("ENTRY_CAMERA", "0")       # webcam index or RTSP URL
EXIT_CAMERA_SOURCE  = os.getenv("EXIT_CAMERA",  "1")

PLATE_MODEL_PATH     = os.getenv("PLATE_MODEL",   "license_plate_detector.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE", "0.60"))  # 0.0 – 1.0
DEBOUNCE_SECONDS     = int(os.getenv("DEBOUNCE",    "10"))      # seconds

DB_PATH   = os.getenv("DB_PATH",   "parking.db")
LOG_FILE  = os.getenv("LOG_FILE",  "parking.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
```

### Using a `.env` file

Create a `.env` file in the project root (never commit this to version control):

```dotenv
ENTRY_CAMERA=rtsp://admin:yourpassword@192.168.1.100:554/stream1
EXIT_CAMERA=rtsp://admin:yourpassword@192.168.1.101:554/stream1
CONFIDENCE=0.65
DEBOUNCE=15
LOG_LEVEL=DEBUG
USE_GPU=true
```

Then load it at the top of `camera.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

### Tuning guide

| Setting | Effect of increasing | Effect of decreasing |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | Fewer false positives, may miss some valid plates | More readings accepted, risk of OCR noise entering DB |
| `DEBOUNCE_SECONDS` | Safer against double-logging, less responsive to fast re-entry | May double-log if vehicle lingers at gate |

A confidence of **0.60–0.70** works well in good lighting. Drop to **0.50** if you're missing valid reads in low light. Raise to **0.75+** if you're getting garbage characters logged.

---

## 7. Running the System

### Single camera (entry only)

```bash
python camera.py --mode entry --source 0
```

### Single camera (exit only) with a different webcam index

```bash
python camera.py --mode exit --source 1
```

### IP camera via RTSP

```bash
python camera.py --mode entry --source "rtsp://admin:password@192.168.1.100:554/stream1"
```

### Two cameras simultaneously (separate terminals or processes)

**Terminal 1 — Entry gate:**
```bash
python camera.py --mode entry --source 0
```

**Terminal 2 — Exit gate:**
```bash
python camera.py --mode exit --source "rtsp://admin:password@192.168.1.101:554/stream1"
```

Both processes share the same `parking.db` file safely. SQLite handles concurrent reads without issue. If you run many simultaneous camera processes (more than 4–6), enable WAL mode for better write concurrency:

```bash
python -c "import sqlite3; conn = sqlite3.connect('parking.db'); conn.execute('PRAGMA journal_mode=WAL'); conn.close()"
```

### Stopping the system

Press **`q`** in the camera preview window, or send `CTRL+C` in the terminal. The camera is released cleanly either way.

### Running as a background service (Linux systemd)

Create `/etc/systemd/system/parking-entry.service`:

```ini
[Unit]
Description=Parking Entry Camera
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/parking_system
ExecStart=/home/pi/parking_system/env/bin/python camera.py --mode entry --source 0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable parking-entry
sudo systemctl start parking-entry
sudo journalctl -u parking-entry -f   # follow logs
```

---

## 8. Admin CLI

`admin.py` provides an operator interface for managing the system without touching the database directly.

### Check who is currently inside

```bash
python admin.py status
```

Output:
```
Plate           Entry Time (UTC)
────────────────────────────────────────
AB12CDE         2025-06-01T08:32:11+00:00
XY99ZZZ         2025-06-01T09:14:55+00:00

Total inside: 2
```

### View today's statistics

```bash
python admin.py stats
```

Output:
```
── Today's Stats (2025-06-01) ──────────────────
  Total entries  : 47
  Completed exits: 43
  Avg duration   : 38m 12s
  Still inside   : 4
```

### Export the full log to CSV

```bash
python admin.py export
python admin.py export --output /path/to/report_june.csv
```

The CSV has these columns: `plate_number`, `entry_time`, `exit_time`, `duration_sec`. Rows where `exit_time` is empty indicate vehicles still inside.

### Manually force an exit record

Use this when a vehicle exits without being detected (e.g. camera outage, barrier forced open):

```bash
python admin.py manual-exit AB12CDE
```

This calls `mark_exit()` directly, writing the current time as the exit timestamp.

---

## 9. Database Schema

The database is a single SQLite file (`parking.db`) created automatically on first run. It contains one table:

```sql
CREATE TABLE parking_log (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    plate_number  TEXT     NOT NULL,
    entry_time    TEXT     NOT NULL,   -- ISO-8601 UTC, e.g. 2025-06-01T08:32:11+00:00
    exit_time     TEXT,                -- NULL while vehicle is inside
    duration_sec  INTEGER             -- seconds, populated atomically on exit
);

CREATE INDEX idx_plate ON parking_log (plate_number);
```

### Querying the database directly

You can open `parking.db` in [DB Browser for SQLite](https://sqlitebrowser.org/) (free GUI) or query it with the `sqlite3` command-line tool:

```bash
sqlite3 parking.db
```

```sql
-- All vehicles currently inside
SELECT plate_number, entry_time
FROM parking_log
WHERE exit_time IS NULL;

-- Total visits per plate, all time
SELECT plate_number, COUNT(*) as visits, AVG(duration_sec) as avg_sec
FROM parking_log
WHERE exit_time IS NOT NULL
GROUP BY plate_number
ORDER BY visits DESC;

-- All sessions today
SELECT * FROM parking_log
WHERE entry_time >= date('now');

-- Delete records older than 30 days (GDPR / data retention)
DELETE FROM parking_log
WHERE entry_time < datetime('now', '-30 days');
```

### Design decisions

- **ISO-8601 TEXT for timestamps** — portable across languages, human-readable in any DB browser, and lexicographically sortable without conversion.
- **`duration_sec` computed at exit** — avoids re-computing duration on every report query; stored as an integer for simple arithmetic.
- **No hard foreign keys** — keeps the schema flexible. Vehicle registration and payment tables can be added independently.

---

## 10. Module Reference

### `camera.py`

The main process loop. Instantiate one process per physical camera.

| Function | Signature | Description |
|---|---|---|
| `open_camera` | `(source) → cv2.VideoCapture` | Opens webcam (int index) or RTSP URL. Raises `RuntimeError` if connection fails. |
| `is_debounced` | `(plate: str) → bool` | Returns `True` if this plate was processed within `DEBOUNCE_SECONDS`. Updates timestamp on first call. |
| `run` | `(camera_mode: str, camera_source) → None` | Blocking main loop. Reads frames, detects plates, dispatches to `mark_entry` or `mark_exit`. Press `q` to exit. |

---

### `detection.py`

Wraps YOLOv8 and EasyOCR. Models are loaded lazily on first use and cached as module-level singletons — they are not reloaded on every frame.

| Function | Signature | Description |
|---|---|---|
| `detect_plate` | `(frame: np.ndarray) → np.ndarray \| None` | Runs YOLOv8 on the frame. Returns the highest-confidence plate crop (grayscale + thresholded), or `None` if no plate found. |
| `read_plate` | `(plate_crop: np.ndarray) → tuple[str \| None, float]` | Runs EasyOCR on the crop. Validates format and applies character correction. Returns `(plate_text, confidence)` or `(None, 0.0)`. |
| `_complies_format` | `(text: str) → bool` | Internal. Validates the plate string against the configured format (UK 7-char by default). |
| `_format_plate` | `(text: str) → str` | Internal. Applies `CHAR_TO_INT` and `INT_TO_CHAR` substitutions to correct common OCR misreads. |

**Character correction maps:**

```python
CHAR_TO_INT = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5'}
# Applied at digit positions (2, 3) — converts look-alike letters to digits

INT_TO_CHAR = {'0': 'O', '1': 'I', '3': 'J', '4': 'A', '6': 'G', '5': 'S'}
# Applied at letter positions (0, 1, 4, 5, 6) — converts look-alike digits to letters
```

---

### `database.py`

All database interactions go through this module. It is safe to import from multiple processes simultaneously.

| Function | Signature | Description |
|---|---|---|
| `init_db` | `() → None` | Creates the `parking_log` table and index if absent. Called automatically on import. |
| `vehicle_inside` | `(plate: str) → bool` | Returns `True` if an open entry (no `exit_time`) exists for this plate. |
| `mark_entry` | `(plate: str) → None` | Inserts a new entry row. Skips with a warning if the vehicle is already inside. |
| `mark_exit` | `(plate: str) → None` | Finds the most recent open entry and updates it with `exit_time` and `duration_sec`. Safe to call if no entry exists (logs a warning, does not raise). |
| `get_active_vehicles` | `() → list[dict]` | Returns a list of `{plate_number, entry_time}` dicts for all vehicles currently inside. |
| `export_csv` | `(output_path: str) → None` | Writes the full `parking_log` table to a CSV file. |

---

### `admin.py`

CLI entry point. Run with `python admin.py <command>`.

| Command | Arguments | Description |
|---|---|---|
| `status` | — | Print all vehicles currently inside |
| `stats` | — | Print today's entry count, exit count, average duration, and occupancy |
| `export` | `--output <path>` | Export full log to CSV (default: `parking_log.csv`) |
| `manual-exit` | `<plate>` | Force an exit record for the given plate number |

---

## 11. Testing

Tests use `pytest` and require no camera or model to run. The database tests use temporary SQLite files that are created fresh per test and cleaned up automatically.

### Install pytest

```bash
pip install pytest
```

### Run all tests

```bash
pytest tests/ -v
```

### Run a specific test file

```bash
pytest tests/test_database.py -v
pytest tests/test_detection.py -v
```

### Run a specific test class or test

```bash
pytest tests/test_database.py::TestMarkExit -v
pytest tests/test_database.py::TestMarkExit::test_sets_duration_sec -v
```

### Test coverage summary

**`test_detection.py`** — 20 tests

| Class | What is tested |
|---|---|
| `TestCompliesFormat` | Valid plates, wrong length, invalid chars at each position, lowercase, spaces |
| `TestFormatPlate` | Every substitution pair (O↔0, I↔1, S↔5, etc.) at letter and digit positions |
| `TestMappingDicts` | That `CHAR_TO_INT` values are digits, `INT_TO_CHAR` values are letters, and the two maps are true inverses |
| `TestDetectPlateContract` | That `detect_plate()` returns `None` on a blank frame (auto-skipped if model absent) and that `read_plate()` always returns a 2-tuple |

**`test_database.py`** — 25 tests

| Class | What is tested |
|---|---|
| `TestInitDb` | Table created correctly, idempotent on repeated calls |
| `TestVehicleInside` | Unknown plate, after entry, after exit, case sensitivity |
| `TestMarkEntry` | Row creation, `exit_time` is NULL, ISO timestamp with timezone, duplicate skip, re-entry after exit, multiple plates |
| `TestMarkExit` | Sets `exit_time`, sets `duration_sec`, duration is non-negative, safe on unknown plate, only closes open entry |
| `TestGetActiveVehicles` | Empty DB, single active vehicle, excludes exited vehicles, multiple active, result dict keys |
| `TestExportCsv` | File is created, contains header and data row, empty DB produces header-only file |

### Notes on model-dependent tests

`TestDetectPlateContract.test_returns_none_on_blank_frame` checks whether the YOLOv8 model returns `None` on a black frame. It automatically skips with `pytest.skip` if `license_plate_detector.pt` is not present — so CI pipelines without the model file will not fail.

---

## 12. Camera Setup Guide

### Physical placement

- **Height:** Mount 1–2 metres above ground, angled 15–30° downward toward the plate zone. This minimises perspective distortion and keeps plate pixels large.
- **Distance:** Position 2–4 metres from where the vehicle stops at the gate. The vehicle should be stationary (or nearly so) when detected — motion blur is the single biggest cause of OCR failure.
- **One lane per camera:** Avoid wide-angle shots covering multiple lanes. Each camera should have exactly one lane in frame.
- **Dedicated lanes:** Physically separate entry and exit lanes so each camera only ever sees vehicles moving in one direction.

### Lighting

- **IR illumination** is strongly recommended. Infrared LEDs illuminate plates without blinding drivers and work reliably at night. Many IP CCTV cameras include built-in IR emitters.
- **Indoor/covered parking:** 500–800 lux of diffuse LED lighting is sufficient for reliable detection.
- **Avoid backlighting:** Do not position the camera facing bright outdoor light or direct sun. Use anti-glare housing or a camera with wide dynamic range (WDR) if sun exposure is unavoidable.
- **Contrast matters more than brightness:** A well-lit plate on a dark background reads better than a uniformly bright scene.

### Camera hardware recommendations

| Budget | Recommendation |
|---|---|
| Low | Any 1080p USB webcam with manual focus |
| Medium | Hikvision DS-2CD2T47G2-L (4MP, built-in white light, IP67) |
| High | Dedicated ANPR camera (Hikvision DS-2CD4A26FWD-IZHS or similar) with built-in IR and auto-exposure |

### RTSP URL formats

Different manufacturers use different RTSP path formats. Common examples:

```bash
# Hikvision
rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101

# Dahua
rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0

# Generic
rtsp://admin:password@192.168.1.100:554/stream1
rtsp://admin:password@192.168.1.100:554/live/main
```

If you are unsure of the URL, use [ONVIF Device Manager](https://sourceforge.net/projects/onvifdm/) (free) to discover the correct stream URI automatically.

---

## 13. Adapting the Plate Format

The default format validator in `detection.py` expects **UK-style 7-character plates** in the pattern `LLDDLLL` (L = letter, D = digit), for example `AB12CDE`.

To adapt for a different country, edit `_complies_format()` in `detection.py`:

### Indian plates (e.g. MH 12 AB 1234)

```python
def _complies_format(text: str) -> bool:
    # Format: 2 letters + 2 digits + 2 letters + 4 digits = 10 chars
    if len(text) != 10:
        return False
    return (
        text[0:2].isalpha() and
        text[2:4].isdigit() and
        text[4:6].isalpha() and
        text[6:10].isdigit()
    )
```

### US plates (highly variable — relaxed validator)

```python
def _complies_format(text: str) -> bool:
    # Accept 5–8 alphanumeric characters
    return 5 <= len(text) <= 8 and text.isalnum()
```

### German plates (e.g. B·AB·1234)

```python
def _complies_format(text: str) -> bool:
    # After stripping spaces/hyphens: 2-8 chars, mix of letters and digits
    return 5 <= len(text) <= 8 and text.isalnum()
```

Also update the `_format_plate()` character substitution mappings to match your format's letter and digit positions.

---

## 14. Troubleshooting

### Camera won't open

```
RuntimeError: Cannot open camera source: 0
```

- On Linux, confirm the device exists: `ls /dev/video*`
- Try a different index (`--source 1`, `--source 2`)
- For RTSP, test the URL in VLC first: **Media → Open Network Stream → paste URL**
- Ensure no other process is holding the camera open

### OCR reads nothing / always returns None

- Increase frame resolution — plates need to be at least 80–100 px wide to OCR reliably
- Check the preprocessed image by temporarily adding `cv2.imshow("crop", plate_crop)` in `camera.py` after `detect_plate()` returns
- Lower `CONFIDENCE_THRESHOLD` in `config.py` to 0.40–0.50 as a diagnostic step
- Ensure `license_plate_detector.pt` was trained on plates from your region

### Plates detected but format validation always fails

- Your plates don't match the 7-character UK format — see [Section 13](#13-adapting-the-plate-format)
- Print rejected texts to the log by temporarily adding `logger.debug(f"Rejected: {text}")` inside `read_plate()` before the `return None, 0.0` line

### Database locked errors (multiple camera processes)

Enable WAL mode once:

```bash
python -c "import sqlite3; conn = sqlite3.connect('parking.db'); conn.execute('PRAGMA journal_mode=WAL'); conn.close()"
```

### GPU not being used

- Verify CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`
- Install the CUDA-specific torch build (see [Installation, Step 3](#step-3--install-dependencies))
- Set `USE_GPU=true` in your `.env` or environment

### Exit logged but no entry exists

The log will show: `EXIT skipped — no open entry found for <plate>`

This happens when:
- The vehicle entered before the system was running
- The entry camera missed the plate (low confidence / poor angle)
- A previous session's data was cleared

Use `python admin.py manual-exit <plate>` to force a clean exit record if needed.

---

## 15. Next-Level Upgrades

### Gate barrier automation

Connect a relay module (e.g. SainSmart 5V relay) to a Raspberry Pi GPIO pin. Wire the relay's COM and NO terminals to the barrier controller's trigger input (typically 12V dry contact). Then add a GPIO trigger call after `mark_entry()` in `camera.py`:

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BARRIER_PIN, GPIO.OUT)

# After successful mark_entry():
GPIO.output(BARRIER_PIN, GPIO.HIGH)   # open gate
time.sleep(5)                          # hold open
GPIO.output(BARRIER_PIN, GPIO.LOW)    # close gate
```

### Web admin dashboard

Expose the database functions via a FastAPI REST API, then build a frontend dashboard with React or plain HTML. A minimal API layer:

```python
from fastapi import FastAPI
from database import get_active_vehicles, export_csv

app = FastAPI()

@app.get("/api/active")
def active():
    return get_active_vehicles()

@app.get("/api/stats")
def stats():
    # query today's counts from DB
    ...
```

Run with: `uvicorn api:app --host 0.0.0.0 --port 8000`

### Payment calculation

Add a `tariffs` table mapping duration bands to prices. On exit, look up the applicable tariff and insert a `payments` record:

```sql
CREATE TABLE tariffs (
    min_sec   INTEGER,
    max_sec   INTEGER,
    price_gbp REAL
);
INSERT INTO tariffs VALUES (0, 3600, 1.00);         -- 0–1 hour: £1.00
INSERT INTO tariffs VALUES (3600, 7200, 2.00);      -- 1–2 hours: £2.00
INSERT INTO tariffs VALUES (7200, 999999, 3.50);    -- 2+ hours: £3.50
```

### Occupancy counter

Query the count of open entries at any time:

```python
def current_occupancy() -> int:
    with _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM parking_log WHERE exit_time IS NULL"
        ).fetchone()[0]
```

Compare against a `TOTAL_SPACES` constant to compute percentage full, and push the value to a display sign or dashboard widget.

### Data retention automation

Add a nightly cron job to delete records beyond your retention policy:

```bash
# Delete records older than 30 days — add to crontab with: crontab -e
0 2 * * * sqlite3 /path/to/parking.db "DELETE FROM parking_log WHERE entry_time < datetime('now', '-30 days');"
```

---

## License

MIT License — see `LICENSE` file for details.

---

## Acknowledgements

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — object detection framework
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — OCR engine
- [Roboflow License Plate Recognition Dataset](https://universe.roboflow.com/roboflow-universe-projects/license-plate-recognition-rxg4e) — training data for the plate detector
- Original demo project by [Muhammad Zeerak Khan](https://github.com/Muhammad-Zeerak-Khan/Automatic-License-Plate-Recognition-using-YOLOv8)
