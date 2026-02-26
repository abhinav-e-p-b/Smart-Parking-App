# 🅿 Real-Time Parking Management System
### Automatic Number Plate Recognition — Production-Grade Entry & Exit Logging

A computer vision–based parking management solution that uses **YOLOv8** for license plate detection and **EasyOCR** for text recognition. The system reads live camera feeds, identifies vehicles by their number plates, and maintains a structured log of entries and exits in a **SQLite** database — with no pre-recorded video, no CSV post-processing, and no manual intervention required.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [How It Works — Detailed Pipeline](#3-how-it-works--detailed-pipeline)
4. [File Structure](#4-file-structure)
5. [pip Packages Used](#5-pip-packages-used)
6. [Installation & Setup](#6-installation--setup)
7. [Configuration](#7-configuration)
8. [Running the System](#8-running-the-system)
9. [Admin CLI Reference](#9-admin-cli-reference)
10. [Database Schema](#10-database-schema)
11. [Module Reference](#11-module-reference)
12. [Testing](#12-testing)
13. [Camera Setup Guide](#13-camera-setup-guide)
14. [Adapting for Different Plate Formats](#14-adapting-for-different-plate-formats)
15. [Troubleshooting](#15-troubleshooting)
16. [Real-World Applications](#16-real-world-applications)
17. [Future Improvements & Roadmap](#17-future-improvements--roadmap)

---

## 1. Project Overview

### What the system does

- Connects to a **live webcam or IP CCTV camera** (RTSP stream)
- Detects license plates in every video frame using **YOLOv8** (fine-tuned on Indian plates)
- Reads the plate text using **EasyOCR** with multi-augmentation ensemble voting
- Validates plate text against configurable format rules (Indian 10-char default)
- Applies position-aware **character correction** (e.g., O↔0, I↔1, S↔5) to handle OCR misreads
- Logs an **entry timestamp** when a vehicle is detected at the entry gate
- Logs an **exit timestamp** and computes a **parking duration** when the vehicle departs
- Prevents duplicate logs using an in-memory **debounce timer**
- Filters noisy readings using a **confidence threshold** (default 0.60)
- Uses a **temporal consistency filter** — only confirms a plate after it appears across multiple frames
- Stores all data in **SQLite**, which survives process restarts and is queryable at any time
- Provides an **operator CLI** (`admin.py`) for live status checks, manual overrides, and CSV exports

### What the system does NOT do (by design)

- Does not process pre-recorded video files — designed for live gate operation
- Does not perform multi-object trajectory tracking — plate identity at a gate is all that's needed
- Does not require a GPU (CPU inference fully supported for low-to-moderate traffic)
- Does not save or record output video
- Does not handle payment processing or physical gate control out-of-the-box (upgrade paths documented below)

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PHYSICAL LAYER                               │
│                                                                      │
│   [Entry Camera]                          [Exit Camera]              │
│   Webcam / IP CCTV                        Webcam / IP CCTV           │
└─────────────┬─────────────────────────────────────┬──────────────────┘
              │ cv2.VideoCapture                     │ cv2.VideoCapture
              ▼                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       DETECTION LAYER (detection.py)                 │
│                                                                      │
│   ┌─────────────────────────────────────┐                           │
│   │  detect_plate(frame)                │                           │
│   │  ─ YOLOv8 inference (5 passes)      │                           │
│   │  ─ Brightness/contrast jitter       │                           │
│   │  ─ Consistency threshold filter     │                           │
│   │  ─ Returns preprocessed crop        │                           │
│   └──────────────────┬──────────────────┘                           │
│                      │                                               │
│   ┌──────────────────▼──────────────────┐                           │
│   │  read_plate(crop)                   │                           │
│   │  ─ EasyOCR (7 augmentation modes)   │                           │
│   │  ─ Majority vote across variants    │                           │
│   │  ─ Format validation                │                           │
│   │  ─ Character correction             │                           │
│   │  Returns: (plate_text, confidence)  │                           │
│   └──────────────────┬──────────────────┘                           │
└──────────────────────┼───────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────────┐
│                      LOGIC LAYER (camera.py)                         │
│                                                                      │
│   TemporalConsistencyFilter   →  plate stable across N frames?       │
│   is_debounced()              →  seen within last 10 seconds?        │
│   confidence >= threshold     →  reading reliable enough?            │
│                                                                      │
│   camera_mode == "entry"      →  mark_entry(plate)                   │
│   camera_mode == "exit"       →  vehicle_inside? → mark_exit(plate)  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────────┐
│                   PERSISTENCE LAYER (database.py)                    │
│                                                                      │
│   SQLite — parking.db                                                │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │ parking_log                                                 │    │
│   │  id | plate_number | entry_time | exit_time | duration_sec │    │
│   └────────────────────────────────────────────────────────────┘    │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────────┐
│                    ADMIN LAYER (admin.py)                            │
│                                                                      │
│   status | stats | export | manual-exit                              │
└──────────────────────────────────────────────────────────────────────┘
```

### Component interaction summary

| Component | Role | Talks to |
|---|---|---|
| `camera.py` | Orchestrates the live loop | `detection.py`, `database.py` |
| `detection.py` | Runs YOLO + EasyOCR, corrects text | `ultralytics`, `easyocr`, `cv2` |
| `database.py` | All SQLite reads and writes | `sqlite3` |
| `config.py` | Central settings, reads env vars | `os` |
| `admin.py` | Operator CLI | `database.py`, `sqlite3` |

---

## 3. How It Works — Detailed Pipeline

### Step-by-step frame processing

```
Live Camera Frame
       │
       ▼
detect_plate(frame, n_passes=5)
  ├─ Run YOLOv8 inference 5× (with brightness/contrast jitter on passes 2–5)
  ├─ Group nearby bounding boxes (quantise to 20px grid)
  ├─ Keep only boxes seen in ≥ 60% of passes (temporal consistency)
  ├─ Average coordinates of stable boxes
  ├─ Crop the plate region from the frame
  └─ Preprocess: grayscale → upscale (if small) → adaptive threshold
       │
       │ returns preprocessed crop, or None
       ▼
read_plate(crop, n_variants=5)
  ├─ Apply 5 random augmentations from: original, blur, upscale,
  │   histogram equalise, dilate, erode, median blur
  ├─ Run EasyOCR on each augmented variant
  ├─ Strip spaces/hyphens, uppercase
  ├─ Validate against Indian plate patterns (regex)
  ├─ Apply character correction (position-aware: letters vs digits)
  ├─ Collect votes: plate_text → [confidence1, confidence2, ...]
  ├─ Require majority of variants to agree (≥ floor(n/2)+1)
  └─ Returns (plate_text, avg_confidence) or (None, 0.0)
       │
       ▼
High-Specificity Gate (camera.py)
  ├─ confidence < 0.60  →  discard
  ├─ TemporalConsistencyFilter: plate must appear in ≥ 3 of last 5 frames
  ├─ is_debounced(): same plate within last 10s  →  discard
       │
       ▼
Decision
  ├─ mode == "entry"  →  mark_entry(plate)
  └─ mode == "exit"
        ├─ vehicle_inside(plate) == True  →  mark_exit(plate)
        └─ vehicle_inside(plate) == False →  log warning (orphan exit)
```

### Debounce logic

When a vehicle stops at a gate, the camera may read the same plate dozens of times per second. `recent_detections` is an in-memory dict that records the last successful detection time for each plate. Any subsequent reading within `DEBOUNCE_SECONDS` (default 10) is silently ignored. The dict resets on process restart — this is intentional, as a restart implies a system disruption, not a repeat visit.

### Temporal consistency filter

`TemporalConsistencyFilter` maintains a sliding window (default: 5 frames) for each plate seen. A plate is only passed to the database layer if it accumulated at least `min_hits` (default: 3) detections in that window. This eliminates ghost detections caused by reflections, shadows, or passing pedestrians.

### Duplicate entry protection

Even if debounce and the temporal filter both fail (e.g. after a hard restart), the database has a second line of defence: `mark_entry()` calls `vehicle_inside()` before inserting. If an open entry already exists for that plate, the insert is silently skipped and a warning is logged.

---

## 4. File Structure

```
parking_system/
│
├── camera.py                  # Main entry point — camera loop and event dispatch
├── detection.py               # detect_plate() and read_plate() — YOLO + EasyOCR
├── database.py                # SQLite wrapper — mark_entry(), mark_exit(), etc.
├── config.py                  # All tunable settings in one place
├── admin.py                   # Operator CLI: status, export, manual exit, stats
├── finetune.py                # YOLOv8 fine-tuning script for Indian plate dataset
├── audit_test.py              # Pre-training dataset audit (image/label counts)
├── data_download.py           # Roboflow dataset download script
├── requirements.txt           # Python dependencies
│
├── best.pt                    # Fine-tuned YOLOv8 model (generated by finetune.py)
├── parking.db                 # SQLite database — auto-created on first run
├── parking.log                # Log file — auto-created on first run
│
└── tests/
    ├── __init__.py
    ├── test_detection.py      # Unit tests for OCR logic and format validation
    └── test_database.py       # Unit tests for all database operations
```

---

## 5. pip Packages Used

Install all dependencies with:

```bash
pip install -r requirements.txt
```

### Core packages

| Package | Version | Purpose |
|---|---|---|
| `ultralytics` | ≥ 8.0 | YOLOv8 model loading, inference, and fine-tuning |
| `easyocr` | ≥ 1.7 | OCR engine — reads text from license plate crops |
| `opencv-python` | ≥ 4.8 | Camera capture, image preprocessing (resize, threshold, blur) |
| `torch` | ≥ 2.0 | Deep learning backend for both YOLOv8 and EasyOCR |
| `torchvision` | ≥ 0.15 | Image transforms used internally by torch models |
| `numpy` | ≥ 1.24 | Array operations on video frames |
| `pyyaml` | ≥ 6.0 | Parse `data.yaml` for dataset configuration |
| `roboflow` | ≥ 1.0 | Download training datasets from Roboflow universe |
| `python-dotenv` | ≥ 1.0 | Load configuration from `.env` files |

### Standard library modules used (no installation needed)

| Module | Used in | Purpose |
|---|---|---|
| `sqlite3` | `database.py`, `admin.py` | SQLite database access |
| `csv` | `database.py` | Export parking log to CSV |
| `logging` | `camera.py`, `detection.py`, `database.py` | Structured log output |
| `argparse` | `camera.py`, `admin.py` | Command-line argument parsing |
| `datetime` | `database.py` | ISO-8601 UTC timestamp generation |
| `pathlib` | `database.py`, `finetune.py` | Path manipulation |
| `os` | `config.py` | Read environment variables |
| `re` | `detection.py` | Regex for plate format validation |
| `collections` | `camera.py` | `defaultdict`, `deque` for temporal filter |
| `time` | `camera.py` | Debounce timer |
| `random` | `detection.py` | Random augmentation sampling |
| `string` | `detection.py` | Character utilities |

### Development / testing packages

| Package | Purpose |
|---|---|
| `pytest` | Test runner for all unit tests |

---

## 6. Installation & Setup

### Prerequisites

- Python 3.10 or higher
- A webcam (for development/testing) or an IP CCTV camera with RTSP output
- A fine-tuned `best.pt` YOLOv8 model (see Step 5 below)
- Optional: NVIDIA GPU with CUDA 12.1 (for faster inference)

---

### Step 1 — Clone the project

```bash
git clone <your-repo-url> parking_system
cd parking_system
```

---

### Step 2 — Create a Python virtual environment

**Using conda (recommended):**
```bash
conda create --prefix ./env python=3.10 -y
conda activate ./env
```

**Using venv:**
```bash
python3.10 -m venv env
source env/bin/activate        # Linux / macOS
env\Scripts\activate           # Windows
```

---

### Step 3 — Install Python dependencies

**CPU-only (works on any machine):**
```bash
pip install -r requirements.txt
```

**GPU with CUDA 12.1 (recommended for production):**
```bash
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

**GPU with CUDA 11.8:**
```bash
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

### Step 4 — Download the training dataset (for fine-tuning only)

If you want to fine-tune the model yourself, run:

```bash
python data_download.py
```

This downloads the Indian number plate dataset from Roboflow into `number-plate-1/`. To use a different dataset, edit the `api_key`, workspace, and project name inside `data_download.py`.

---

### Step 5 — Audit the dataset

Before training, verify that all images have matching label files:

```bash
python audit_test.py
```

Each split (`train`, `val`, `test`) should show:
```
✅ Perfect match — ready to train
✅ Label format looks valid (YOLO normalized coords)
```

Fix any mismatches before proceeding.

---

### Step 6 — Fine-tune the YOLOv8 model

```bash
python finetune.py
```

This trains YOLOv8s on the Indian number plate dataset for 100 epochs. Key settings:

| Parameter | Default | Notes |
|---|---|---|
| `BASE_MODEL` | `yolov8s.pt` | Downloads ~22 MB automatically |
| `epochs` | 100 | Increase for better accuracy |
| `batch` | 8 | Safe for 8 GB RAM without GPU; increase to 16–32 on Colab |
| `imgsz` | 640 | Input resolution |
| `freeze` | 10 | Freezes backbone; set to 0 to train all layers |
| `fliplr` | 0.0 | Horizontal flip disabled — plates are directional |

After training, the best weights are saved to `runs/finetune/indian_plates/weights/best.pt`. Copy this to the project root:

```bash
cp runs/finetune/indian_plates/weights/best.pt best.pt
```

---

### Step 7 — Verify the installation

```bash
# Check camera connectivity
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK:', cap.isOpened()); cap.release()"

# Check model loads
python -c "from ultralytics import YOLO; m = YOLO('best.pt'); print('Model OK')"

# Check database initialises
python -c "from database import init_db; init_db(); print('Database OK')"

# Check CUDA (optional)
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

---

## 7. Configuration

All settings live in `config.py`. Every value can be overridden with an environment variable, making the system Docker- and `.env`-friendly.

```python
# config.py

ENTRY_CAMERA_SOURCE = os.getenv("ENTRY_CAMERA", "0")       # webcam index or RTSP URL
EXIT_CAMERA_SOURCE  = os.getenv("EXIT_CAMERA",  "1")

PLATE_MODEL_PATH     = os.getenv("PLATE_MODEL",   "best.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE", "0.60"))
DEBOUNCE_SECONDS     = int(os.getenv("DEBOUNCE",    "10"))

DB_PATH   = os.getenv("DB_PATH",   "parking.db")
LOG_FILE  = os.getenv("LOG_FILE",  "parking.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
```

### Using a `.env` file

Create `.env` in the project root (never commit this file to version control):

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
| `CONFIDENCE_THRESHOLD` | Fewer false positives; may miss valid plates in poor light | More readings accepted; risk of OCR noise entering DB |
| `DEBOUNCE_SECONDS` | Safer against double-logging; less responsive after very short re-entry | May double-log if vehicle lingers at gate |
| `n_passes` (detect_plate) | More consistent detection; slower per frame | Faster; less robust against single-frame noise |
| `min_hits` (TemporalConsistencyFilter) | Fewer false triggers; needs vehicle to be stationary longer | More responsive; may trigger on reflections |

A `CONFIDENCE` of **0.60–0.70** works well in good lighting. Drop to **0.50** for low light. Raise to **0.75+** if garbage characters are being logged.

---

## 8. Running the System

### Entry gate only (single camera)

```bash
python camera.py --mode entry --source 0
```

### Exit gate only (separate webcam)

```bash
python camera.py --mode exit --source 1
```

### IP camera via RTSP

```bash
python camera.py --mode entry --source "rtsp://admin:password@192.168.1.100:554/stream1"
```

### Two cameras simultaneously (open separate terminals)

**Terminal 1 — Entry gate:**
```bash
python camera.py --mode entry --source 0
```

**Terminal 2 — Exit gate:**
```bash
python camera.py --mode exit --source "rtsp://admin:password@192.168.1.101:554/stream1"
```

Both processes share the same `parking.db` safely. For more than 4–6 simultaneous processes, enable WAL mode:

```bash
python -c "import sqlite3; conn = sqlite3.connect('parking.db'); conn.execute('PRAGMA journal_mode=WAL'); conn.close()"
```

### Stopping the system

Press **`q`** in the camera preview window, or send **CTRL+C** in the terminal. The camera is released cleanly either way.

### Running as a Linux systemd service (auto-start on boot)

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

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable parking-entry
sudo systemctl start parking-entry
sudo journalctl -u parking-entry -f    # follow live logs
```

---

## 9. Admin CLI Reference

`admin.py` is an operator interface for managing the system without touching the database directly.

### Check who is currently inside

```bash
python admin.py status
```

Output:
```
Plate           Entry Time (UTC)
─────────────────────────────────────────────
MH12AB1234      2025-06-01T08:32:11+00:00
DL05CX9876      2025-06-01T09:14:55+00:00

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

CSV columns: `plate_number`, `entry_time`, `exit_time`, `duration_sec`. Rows with empty `exit_time` are vehicles still inside.

### Force a manual exit

Use when a vehicle exits without being detected (camera outage, barrier forced open):

```bash
python admin.py manual-exit MH12AB1234
```

---

## 10. Database Schema

The database is a single SQLite file (`parking.db`) created automatically on first run.

```sql
CREATE TABLE parking_log (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    plate_number  TEXT     NOT NULL,
    entry_time    TEXT     NOT NULL,   -- ISO-8601 UTC, e.g. 2025-06-01T08:32:11+00:00
    exit_time     TEXT,                -- NULL while vehicle is inside
    duration_sec  INTEGER             -- seconds from entry to exit
);

CREATE INDEX idx_plate ON parking_log (plate_number);
```

### Useful SQL queries

```sql
-- Vehicles currently inside
SELECT plate_number, entry_time
FROM parking_log
WHERE exit_time IS NULL;

-- Total visits and average duration per plate
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

- **ISO-8601 TEXT for timestamps** — portable across languages, human-readable in any DB viewer, and lexicographically sortable without conversion.
- **`duration_sec` as INTEGER** — computed once at exit and stored; avoids repeated arithmetic on every query.
- **No foreign keys** — keeps the schema simple; payment and membership tables can be added independently.
- **Single table** — straightforward to query, export, and back up. Complex analytics can be handled downstream in pandas or a BI tool.

---

## 11. Module Reference

### `camera.py`

Main process loop — one process per physical camera.

| Function | Signature | Description |
|---|---|---|
| `open_camera` | `(source) → cv2.VideoCapture` | Opens webcam index or RTSP URL. Raises `RuntimeError` if it fails. |
| `is_debounced` | `(plate: str) → bool` | Returns `True` if this plate was processed within `DEBOUNCE_SECONDS`. |
| `TemporalConsistencyFilter` | class | Sliding window hit counter; `update()` returns `True` only when stable. |
| `run` | `(camera_mode, camera_source) → None` | Blocking main loop. Reads frames, detects, dispatches. Press `q` to exit. |

---

### `detection.py`

Wraps YOLOv8 and EasyOCR. Models are loaded lazily on first use and cached as module-level singletons.

| Function | Signature | Description |
|---|---|---|
| `detect_plate` | `(frame, n_passes=5, consistency_threshold=0.6) → np.ndarray \| None` | Multi-pass YOLO detection with jitter. Returns preprocessed crop or `None`. |
| `read_plate` | `(crop, n_variants=5) → tuple[str \| None, float]` | Multi-augmentation EasyOCR with majority voting. Returns `(text, confidence)`. |
| `_complies_format` | `(text: str) → bool` | Validates against Indian plate regex patterns. |
| `_format_plate` | `(text: str) → str` | Position-aware character correction. |
| `_apply_corrections` | `(text: str) → str` | Internal: applies CHAR_TO_INT and INT_TO_CHAR at correct positions. |
| `_clean_ocr_text` | `(text: str) → str` | Strips spaces, hyphens, dots; uppercases. |
| `_preprocess_crop` | `(crop) → np.ndarray` | Grayscale, upscale, adaptive threshold for OCR. |

**Character correction maps:**

```python
CHAR_TO_INT = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5', 'B': '8', 'Z': '2'}
# Applied at digit positions (2, 3, last 4) — converts look-alike letters to digits

INT_TO_CHAR = {'0': 'O', '1': 'I', '3': 'J', '4': 'A', '6': 'G', '5': 'S', '8': 'B', '2': 'Z'}
# Applied at letter positions (0, 1, middle) — converts look-alike digits to letters
```

---

### `database.py`

All database interactions go through this module. Safe to import from multiple processes simultaneously.

| Function | Signature | Description |
|---|---|---|
| `init_db` | `() → None` | Creates table and index if absent. Safe to call multiple times. |
| `vehicle_inside` | `(plate: str) → bool` | True if an open entry (no exit_time) exists for this plate. |
| `mark_entry` | `(plate: str) → None` | Inserts an entry row. Skips silently if already inside. |
| `mark_exit` | `(plate: str) → None` | Updates the open entry with exit time and duration. Safe if no entry exists. |
| `get_active_vehicles` | `() → list[dict]` | Returns all vehicles currently inside as dicts. |
| `export_csv` | `(output_path: str) → None` | Writes full parking_log to a CSV file. |

---

### `admin.py`

CLI entry point. Run with `python admin.py <command>`.

| Command | Arguments | Description |
|---|---|---|
| `status` | — | Print all vehicles currently inside |
| `stats` | — | Today's entry count, exit count, average duration, occupancy |
| `export` | `--output <path>` | Export full log to CSV (default: `parking_log.csv`) |
| `manual-exit` | `<plate>` | Force an exit record for the given plate |

---

## 12. Testing

Tests use `pytest` and require no camera or model to run. Database tests use temporary SQLite files created fresh per test and cleaned up automatically.

### Run all tests

```bash
pip install pytest
pytest tests/ -v
```

### Run specific files or tests

```bash
pytest tests/test_database.py -v
pytest tests/test_detection.py -v
pytest tests/test_database.py::TestMarkExit::test_sets_duration_sec -v
```

### Test coverage summary

**`test_detection.py` — 20 tests**

| Test Class | What Is Tested |
|---|---|
| `TestCompliesFormat` | Valid plates, wrong length, invalid chars at each position, lowercase, special chars |
| `TestFormatPlate` | Each substitution pair at letter and digit positions |
| `TestMappingDicts` | CHAR_TO_INT values are digits, INT_TO_CHAR values are letters, maps are inverses |
| `TestDetectPlateContract` | `detect_plate()` returns None on blank frame; `read_plate()` always returns a 2-tuple |

**`test_database.py` — 25 tests**

| Test Class | What Is Tested |
|---|---|
| `TestInitDb` | Table created correctly; idempotent on repeated calls |
| `TestVehicleInside` | Unknown plate, after entry, after exit, case sensitivity |
| `TestMarkEntry` | Row creation, exit_time is NULL, ISO timestamp with timezone, duplicate skip, re-entry after exit |
| `TestMarkExit` | Sets exit_time, sets duration_sec, duration non-negative, safe on unknown plate |
| `TestGetActiveVehicles` | Empty DB, single/multiple active, excludes exited, result dict keys |
| `TestExportCsv` | File created, header + data row present, empty DB produces header-only file |

---

## 13. Camera Setup Guide

### Physical placement

- Mount cameras **1–2 metres above ground**, angled **15–30° downward** toward the plate zone.
- Position **2–4 metres** from where the vehicle stops — the vehicle should be stationary when detected.
- **One lane per camera** — avoid wide-angle shots covering multiple lanes.
- Use physically separate entry and exit lanes so each camera only sees one direction.

### Lighting

- **IR illumination** is strongly recommended — IR LEDs illuminate plates without blinding drivers.
- Indoor parking: 500–800 lux of diffuse LED lighting is sufficient.
- Avoid backlighting or direct sun; use wide dynamic range (WDR) cameras if unavoidable.
- Contrast matters more than raw brightness: a well-lit plate on a dark background reads better.

### Recommended cameras

| Budget | Recommendation |
|---|---|
| Low | Any 1080p USB webcam with manual focus |
| Medium | Hikvision DS-2CD2T47G2-L (4MP, built-in white light, IP67) |
| High | Dedicated ANPR camera (Hikvision DS-2CD4A26FWD-IZHS) with IR and auto-exposure |
| Edge / embedded | NVIDIA Jetson Orin Nano 8 GB |

### RTSP URL formats

```bash
# Hikvision
rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101

# Dahua
rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0

# Generic
rtsp://admin:password@192.168.1.100:554/stream1
```

Use [ONVIF Device Manager](https://sourceforge.net/projects/onvifdm/) (free) to auto-discover the correct stream URI for any IP camera.

---

## 14. Adapting for Different Plate Formats

The default validator in `detection.py` targets **Indian 10-character plates** (`MH12AB1234` format). To support a different country:

### UK plates (LLDDLLL, 7 characters)

```python
def _complies_format(text: str) -> bool:
    if len(text) != 7:
        return False
    return (text[0:2].isalpha() and text[2:4].isdigit() and text[4:7].isalpha())
```

### US plates (relaxed, 5–8 alphanumeric)

```python
def _complies_format(text: str) -> bool:
    return 5 <= len(text) <= 8 and text.isalnum()
```

### Indian BH-series plates (22BH1234AA)

Already supported via the `INDIAN_PLATE_PATTERNS` list in `detection.py`. The second pattern covers BH-series plates.

Also update `_apply_corrections()` to match the letter/digit positions of your target format.

---

## 15. Troubleshooting

### Camera won't open

```
RuntimeError: Cannot open camera source: 0
```

- On Linux, confirm device exists: `ls /dev/video*`
- Try a different index: `--source 1`, `--source 2`
- For RTSP, test the URL in VLC first: **Media → Open Network Stream → paste URL**
- Ensure no other process is holding the camera

### OCR returns nothing / always None

- Plates need to be at least 80–100 px wide to OCR reliably; increase camera resolution
- Temporarily add `cv2.imshow("crop", plate_crop)` after `detect_plate()` to inspect the crop
- Lower `CONFIDENCE_THRESHOLD` to 0.40–0.50 as a diagnostic
- Ensure `best.pt` was trained on plates from your region

### Plates detected but format validation always fails

- Your plates don't match the Indian 10-char pattern — see [Section 14](#14-adapting-for-different-plate-formats)
- Temporarily add `logger.debug(f"Rejected: {text}")` inside `read_plate()` to see rejected strings

### Database locked errors (multiple camera processes)

Enable WAL mode:

```bash
python -c "import sqlite3; conn = sqlite3.connect('parking.db'); conn.execute('PRAGMA journal_mode=WAL'); conn.close()"
```

### GPU not being used

- Check CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
- Install the CUDA-specific torch build (see [Installation Step 3](#step-3--install-python-dependencies))
- Set `USE_GPU=true` in `.env` and `gpu=True` in `_get_reader()` inside `detection.py`

### Exit logged with no matching entry

Log shows: `EXIT skipped — no open entry found for <plate>`

This happens when the entry camera missed the vehicle (low confidence, bad angle) or the system was restarted after entry but before exit. Use `python admin.py manual-exit <plate>` to insert a clean exit record.

---

## 16. Real-World Applications

### 1. Commercial parking lots and malls
Fully automate entry/exit at multi-level parking structures. Replace token-based or barrier card systems with plate recognition. Integrate with billing software to compute charges based on `duration_sec`.

### 2. Residential apartment complexes
Restrict access to registered residents and authorised visitors. Automatically log every vehicle that enters the premises. Flag unregistered plates for security review.

### 3. Corporate campuses and office parks
Track employee vehicle access, automate visitor check-in, and generate occupancy reports for facilities management.

### 4. Hospital and airport short-stay drop zones
Detect when a vehicle has been in a drop zone beyond the permitted time, and trigger an alert or notification to the vehicle owner.

### 5. Toll plazas and highway checkpoints
Identify vehicles passing through a checkpoint for billing, traffic analytics, or law enforcement flagging. With sufficient hardware, support for multiple simultaneous lanes is feasible.

### 6. Fleet and logistics yards
Log all truck and delivery van entries/exits at a depot. Verify that departing vehicles match scheduled dispatch records.

### 7. Smart city traffic analytics
Aggregate anonymised entry/exit data across multiple sites to build origin–destination matrices, identify traffic bottlenecks, and support urban planning decisions.

### 8. Evidence logging for security incidents
Maintain a tamper-resistant timestamped record of all vehicles that entered and exited a premises during a specific time window, useful for post-incident investigations.

---

## 17. Future Improvements & Roadmap

### Near-term enhancements

**Gate barrier automation**
Connect a relay module (e.g. SainSmart 5V relay) to a Raspberry Pi GPIO pin. Wire the relay's COM and NO terminals to the barrier controller's trigger input. Then trigger the barrier after `mark_entry()` in `camera.py`:

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BARRIER_PIN, GPIO.OUT)

# After successful mark_entry():
GPIO.output(BARRIER_PIN, GPIO.HIGH)
time.sleep(5)
GPIO.output(BARRIER_PIN, GPIO.LOW)
```

**Payment calculation**
Add a `tariffs` table to the database and compute fees on exit:

```sql
CREATE TABLE tariffs (
    min_sec   INTEGER,
    max_sec   INTEGER,
    price_inr REAL
);
INSERT INTO tariffs VALUES (0, 3600, 20.00);       -- 0–1 hour: ₹20
INSERT INTO tariffs VALUES (3600, 7200, 40.00);    -- 1–2 hours: ₹40
INSERT INTO tariffs VALUES (7200, 999999, 60.00);  -- 2+ hours: ₹60
```

**Occupancy counter**
```python
def current_occupancy() -> int:
    with _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM parking_log WHERE exit_time IS NULL"
        ).fetchone()[0]
```

Compare against a `TOTAL_SPACES` constant to compute percentage full and push to a display board.

**Data retention automation**
Add a nightly cron job:
```bash
0 2 * * * sqlite3 /path/to/parking.db "DELETE FROM parking_log WHERE entry_time < datetime('now', '-30 days');"
```

---

### Medium-term upgrades

**REST API and web dashboard**
Expose database functions via a FastAPI REST API and build an operator dashboard:

```python
from fastapi import FastAPI
from database import get_active_vehicles

app = FastAPI()

@app.get("/api/active")
def active():
    return get_active_vehicles()
```

Run with: `uvicorn api:app --host 0.0.0.0 --port 8000`

**SMS / push alerts**
Integrate with Twilio or Firebase Cloud Messaging to send real-time alerts when a VIP vehicle arrives, when occupancy exceeds a threshold, or when a vehicle overstays its permitted duration.

**Whitelist / blacklist system**
Add a `vehicles` table with `plate_number`, `owner_name`, `status` (allowed/blocked/VIP). Check this before `mark_entry()` and deny or flag access accordingly.

**Multi-site centralised database**
Replace the local SQLite file with a PostgreSQL or MySQL instance. Multiple parking facilities can report to a single database, enabling cross-site analytics from one dashboard.

**Edge deployment on Jetson**
Run inference on an NVIDIA Jetson Orin Nano for lower power consumption at remote sites with no internet connectivity. The codebase is fully compatible; change `gpu=True` in `_get_reader()` and ensure CUDA is available on the device.

---

### Long-term vision

**LLM-powered analytics**
Connect the parking database to an LLM assistant that can answer natural language queries like "How many vehicles stayed more than 3 hours on weekends this month?" or "Which plates visited most frequently but never completed a full exit record?"

**Vehicle type classification**
Add a second YOLOv8 model trained to classify vehicle type (car, motorcycle, bus, truck). Charge different tariffs per vehicle class and report occupancy by type.

**Predictive occupancy forecasting**
Train a time-series model (e.g. LSTM or Prophet) on historical entry/exit patterns to predict peak occupancy periods. Display forecasts on the operator dashboard and pre-emptively open overflow zones.

**Automatic re-training pipeline**
Build a CI/CD loop: every week, export all logged plates as a new dataset batch, review and annotate difficult cases, and trigger a fine-tuning run to continuously improve the OCR and detection models.

**Integration with national vehicle registries**
For law enforcement or regulatory use cases, integrate with RTO (Road Transport Office) APIs to verify that detected plates are registered, valid, and not flagged as stolen or overdue for inspection.

---

## License

MIT License — see `LICENSE` file for details.

---

## Acknowledgements

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — object detection framework
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — OCR engine
- [Roboflow License Plate Recognition Dataset](https://universe.roboflow.com/roboflow-universe-projects/license-plate-recognition-rxg4e) — training data
- Original ANPR demo by [Muhammad Zeerak Khan](https://github.com/Muhammad-Zeerak-Khan/Automatic-License-Plate-Recognition-using-YOLOv8)
