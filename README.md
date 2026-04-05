# 🅿 ParkWatch — Parking ANPR System

> **Automatic Number Plate Recognition** for parking lot entry/exit management,  
> powered by YOLOv8, EasyOCR, and Supabase as the live database.

---

## ✦ How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Entry Camera                      Exit Camera            │
│        │                                 │                  │
│        ▼                                 ▼                  │
│   YOLO detection                    YOLO detection          │
│   + OCR (7 variants)                + OCR (7 variants)      │
│   + Tracker (confirm 3×)            + Tracker (confirm 3×)  │
│        │                                 │                  │
│        ▼                                 ▼                  │
│   record_entry()                    record_exit()           │
│        │                                 │                  │
│        └──────────────┬──────────────────┘                  │
│                       ▼                                     │
│                  Supabase DB                                │
│              (parking_sessions)                             │
│                       │                                     │
│          ┌────────────┼────────────┐                        │
│          ▼            ▼            ▼                        │
│       vehicles      users    parking_slots                  │
│    (plate lookup) (profile)  (occupancy)                    │
│                       │                                     │
│                       ▼                                     │
│              dashboard/index.html                           │
│              (live browser view)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Set up Supabase

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run the schema setup in order:

```bash
python admin.py setup-schema
# Copy the printed SQL → paste into Supabase SQL Editor
# Run STEP 1 first, then STEP 2 separately
```

3. Disable Row Level Security so the ANPR system can write:

```sql
ALTER TABLE parking_sessions  DISABLE ROW LEVEL SECURITY;
ALTER TABLE parking_slots      DISABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles           DISABLE ROW LEVEL SECURITY;
ALTER TABLE users              DISABLE ROW LEVEL SECURITY;
```

### 3 — Configure credentials

```bash
cp .env.example .env
# Fill in SUPABASE_URL and SUPABASE_KEY (use the service-role key for writes)
```

### 4 — Configure cameras

Edit `config.py` → `CameraConfig`:

```python
entry_camera = 0      # built-in webcam / entry gate
exit_camera  = 1      # USB / external camera at exit
```

### 5 — Run

| Scenario | Command |
|---|---|
| Both gates, one machine | `python run_both_gates.py` |
| Entry gate only | `python parking_gate.py --mode entry --source 0` |
| Exit gate only | `python parking_gate.py --mode exit --source 1` |
| Headless / server / Pi | `python run_both_gates.py --headless` |
| Custom RTSP cameras | `python run_both_gates.py --entry rtsp://cam1/stream --exit rtsp://cam2/stream` |

> **⚠ GUI Note:** When running both gates via `run_both_gates.py`, OpenCV windows
> are not thread-safe. Use `--headless` for stability, or run each gate in a
> separate terminal.

---

## 📊 Dashboard

Open `dashboard/index.html` in a browser. Fill in your credentials at the top of the file:

```js
const SUPABASE_URL = "https://YOUR_PROJECT.supabase.co";
const SUPABASE_KEY = "YOUR_ANON_PUBLIC_KEY";  // anon key is fine — dashboard is read-only
```

**Features:**
- 🟢 Vacant / occupied slot counts with live gauge
- 📋 Session table — filterable by status and member/guest
- 📅 Entry count for today
- 🔄 Auto-refreshes every 10 seconds

---

## 🗄 Database Schema

### `users`
Linked to Supabase Auth. Stores user profile data.

| Column | Type | Description |
|---|---|---|
| `id` | uuid | Primary key (mirrors `auth.users.id`) |
| `name` | text | Full name |
| `email` | text | Email address |
| `phone` | text | Phone number |
| `role` | text | `user` or `admin` |
| `created_at` | timestamptz | Registration time |

---

### `vehicles`
One user can register multiple plates.

| Column | Type | Description |
|---|---|---|
| `id` | uuid | Primary key |
| `user_id` | uuid | FK → `users.id` |
| `plate_number` | text | Uppercase plate, e.g. `KL07BB1234` |
| `vehicle_type` | text | e.g. `car`, `bike`, `truck` |
| `is_active` | bool | Only active plates are matched |
| `owner_name` | text | Display name fallback |
| `entry_time` | timestamptz | Last recorded entry |

---

### `parking_sessions`
Written by ANPR cameras on every entry and exit event.

| Column | Type | Description |
|---|---|---|
| `plate` | text | Number plate (uppercase) |
| `camera_entry` | text | Camera label for entry |
| `camera_exit` | text | Camera label for exit |
| `entry_time` | timestamptz | UTC entry timestamp |
| `exit_time` | timestamptz | UTC exit timestamp (null while inside) |
| `duration_mins` | int | Parking duration in minutes |
| `status` | text | `inside` or `exited` |
| `is_registered` | bool | Matched to a registered vehicle |
| `user_id` | uuid | FK → `users.id` |
| `vehicle_id` | uuid | FK → `vehicles.id` |
| `entry_image_url` | text | Path to entry snapshot |
| `exit_image_url` | text | Path to exit snapshot |

---

### `parking_slots`
One row per zone — tracks capacity and live occupancy count.

| Column | Type | Description |
|---|---|---|
| `zone` | text | Zone name, e.g. `A` (unique) |
| `total` | int | Total slot capacity (default: 100) |
| `occupied` | int | Current occupied count |
| `is_active` | bool | Whether this zone is in use |
| `updated_at` | timestamptz | Last modified time |

---

### `bookings`
Pre-scheduled parking reservations.

| Column | Type | Description |
|---|---|---|
| `user_id` | uuid | FK → `users.id` |
| `vehicle_id` | uuid | FK → `vehicles.id` |
| `slot_id` | uuid | FK → `parking_slots.id` |
| `plan` | text | e.g. `hourly`, `daily` |
| `scheduled_entry` | timestamptz | Planned entry time |
| `scheduled_exit` | timestamptz | Planned exit time |
| `status` | text | `pending`, `active`, `completed`, `cancelled` |
| `amount` | numeric | Booking fee |

---

## 🛠 Admin CLI

```bash
python admin.py status                    # current occupancy stats
python admin.py sessions                  # recent 30 sessions
python admin.py sessions --inside         # only vehicles inside right now
python admin.py lookup KL07BB1234         # check a specific plate
python admin.py set-capacity 200          # update total slot count
python admin.py manual-entry KL07BB1234   # manually record an entry
python admin.py manual-exit  KL07BB1234   # force-exit a stuck session
python admin.py interactive               # interactive terminal (easiest)
python admin.py setup-schema              # print SQL to run in Supabase
```

---

## 📷 Camera Setup

### Laptop webcam + USB camera (one machine)

```python
# config.py
entry_camera = 0   # built-in webcam at entry gate
exit_camera  = 1   # USB camera at exit gate
```

### Two IP cameras (RTSP)

```python
entry_camera = "rtsp://admin:pass@192.168.1.10/stream1"
exit_camera  = "rtsp://admin:pass@192.168.1.11/stream1"
```

### Two separate machines (Raspberry Pi / PC)

Run `parking_gate.py` independently on each machine — both write to the same Supabase project:

```bash
# Machine 1 (entry gate)
python parking_gate.py --mode entry --source 0

# Machine 2 (exit gate)
python parking_gate.py --mode exit --source 0
```

---

## 🤔 Why Supabase?

| | Supabase | Local SQLite |
|---|---|---|
| Shared with website | ✅ Same DB | ❌ Separate sync needed |
| Dashboard from any device | ✅ Browser, anywhere | ❌ Local only |
| Multiple cameras on separate machines | ✅ All write to same DB | ❌ Complex sync |
| Free tier | ✅ 500 MB, unlimited rows | N/A |
| Automatic backups | ✅ | Manual |
| Registered vehicle check | ✅ Same project | ❌ Cross-DB query |

---

## 📁 Project Structure

```
parking_anpr/
│
├── parking_gate.py          ← main entry point (one instance per camera)
├── run_both_gates.py        ← runs both gates on one machine (threaded)
├── admin.py                 ← CLI admin tools
├── config.py                ← all settings (cameras, model, OCR, storage)
├── requirements.txt
├── .env.example             ← copy to .env and fill in credentials
│
├── db/
│   ├── __init__.py
│   └── supabase_client.py   ← all DB read/write operations
│
├── utils/
│   ├── preprocess.py        ← 7-variant plate image preprocessing
│   ├── ocr.py               ← EasyOCR + Indian plate validation
│   ├── visualise.py         ← OpenCV drawing helpers
│   ├── tracker.py           ← IoU tracker (prevents duplicate logs)
│   └── snapshot.py          ← saves plate crop images to disk
│
└── dashboard/
    ├── index.html           ← live occupancy dashboard
    └── manual.html          ← manual entry/exit web interface
```

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your project URL, e.g. `https://xxxx.supabase.co` |
| `SUPABASE_KEY` | Service-role key for ANPR writes; anon key for dashboard reads |

> **Security:** Never commit `.env` to version control. The service-role key bypasses Row Level Security — keep it out of any public-facing frontend.

---

## 🧩 Controls (OpenCV Window)

| Key | Action |
|---|---|
| `q` | Quit gate |
| `s` | Save current annotated frame to `outputs/` |
| `r` | Reset on-screen event log |
