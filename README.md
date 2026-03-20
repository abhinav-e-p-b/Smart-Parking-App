# 🅿 Parking ANPR System

Automatic Number Plate Recognition for parking lot entry/exit management, with Supabase as the live database.

---

## How it Works

```
Entry Camera                Exit Camera
     │                           │
     ▼                           ▼
  YOLO detection             YOLO detection
  + OCR (7 variants)         + OCR (7 variants)
  + Tracker (confirm 3×)     + Tracker (confirm 3×)
     │                           │
     ▼                           ▼
  record_entry()             record_exit()
     │                           │
     └─────────────┬─────────────┘
                   ▼
            Supabase DB
          (parking_sessions)
                   │
           ┌───────┴───────┐
           ▼               ▼
    registered_users   parking_slots
   (your website DB)   (occupancy count)
                   │
                   ▼
          dashboard/index.html
          (live browser view)
```

---

## Quick Start

### 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### 2 — Set up Supabase

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and paste + run the output of:
   ```bash
   python admin.py setup-schema
   ```
3. Your **registered_users** table (from your website) must have:
   - `id` (uuid)
   - `plate_number` (text, uppercase)
   - `name` (text)
   - `email` (text)
   
   If your column is named differently, edit `lookup_registered_user()` in `db/supabase_client.py`.

### 3 — Configure credentials
```bash
cp .env.example .env
# Edit .env and fill in SUPABASE_URL and SUPABASE_KEY
```

### 4 — Configure cameras
Edit `config.py` → `CameraConfig`:
```python
entry_camera = 0      # laptop webcam
exit_camera  = 1      # USB / external camera
```

### 5 — Run

**Both gates on one machine:**
```bash
python run_both_gates.py
```

**Individual gate (one machine per gate, or for testing):**
```bash
python parking_gate.py --mode entry --source 0
python parking_gate.py --mode exit  --source 1
```

**No GUI (server / Raspberry Pi):**
```bash
python run_both_gates.py --headless
```

---

## Dashboard

Open `dashboard/index.html` in a browser.
Edit the top of the file and replace:
```js
const SUPABASE_URL = "https://YOUR_PROJECT.supabase.co";
const SUPABASE_KEY = "YOUR_ANON_PUBLIC_KEY";  // anon key is fine for read-only dashboard
```

The dashboard auto-refreshes every 10 seconds and shows:
- Vacant / occupied slot counts
- Live occupancy gauge
- Session table (filterable by status / registered users)
- Entry count for today

---

## Database Tables

### `parking_sessions`
| Column | Type | Description |
|---|---|---|
| `plate` | text | Number plate (uppercase) |
| `camera_entry` | text | Camera label for entry |
| `camera_exit` | text | Camera label for exit |
| `entry_time` | timestamptz | UTC entry time |
| `exit_time` | timestamptz | UTC exit time (null while inside) |
| `duration_mins` | int | Parking duration |
| `status` | text | `inside` or `exited` |
| `is_registered` | bool | Matched to registered_users |
| `user_id` | uuid | FK to registered_users |
| `entry_image_url` | text | Path to snapshot |

### `parking_slots`
Tracks total capacity and current occupied count per zone.

### `registered_users` (your website's table, read-only)
Must have a `plate_number` column that `parking_gate.py` can query.

---

## Admin CLI

```bash
python admin.py status                   # current occupancy
python admin.py sessions                 # recent 30 sessions
python admin.py sessions --inside        # only vehicles inside now
python admin.py lookup KL07BB1234        # check a plate
python admin.py set-capacity 200         # update total slots
python admin.py manual-exit KL07BB1234   # force-exit a stuck session
```

---

## Camera Setup

### Laptop webcam + USB camera
```
entry_camera = 0   (built-in webcam at entry)
exit_camera  = 1   (USB camera at exit)
```

### Two IP cameras (RTSP)
```python
entry_camera = "rtsp://admin:pass@192.168.1.10/stream1"
exit_camera  = "rtsp://admin:pass@192.168.1.11/stream1"
```

### Two separate Raspberry Pis / PCs
Run `parking_gate.py` on each machine pointing at the same Supabase project.

---

## Why Supabase (not local SQLite)?

| | Supabase | Local SQLite |
|---|---|---|
| Shared with website | ✅ Same DB | ❌ Separate sync needed |
| Dashboard from any device | ✅ Browser, anywhere | ❌ Local only |
| Multiple cameras on separate machines | ✅ All write to same DB | ❌ Complex sync |
| Free tier | ✅ 500MB, unlimited rows | N/A |
| Backups | ✅ Automatic | Manual |
| Registered users check | ✅ Same project | ❌ Cross-DB query |

---

## Project Structure

```
parking_anpr/
├── parking_gate.py        ← main entry point (one instance per camera)
├── run_both_gates.py      ← runs both gates on one machine
├── admin.py               ← CLI admin tools
├── config.py              ← all settings
├── requirements.txt
├── .env.example           ← copy to .env and fill credentials
│
├── db/
│   ├── __init__.py
│   └── supabase_client.py ← all DB read/write operations
│
├── utils/
│   ├── preprocess.py      ← 7-variant plate image preprocessing
│   ├── ocr.py             ← EasyOCR + Indian plate validation
│   ├── visualise.py       ← OpenCV drawing helpers
│   ├── tracker.py         ← IoU tracker (prevents duplicate logs)
│   └── snapshot.py        ← saves plate crop images to disk
│
└── dashboard/
    └── index.html         ← live occupancy dashboard (open in browser)
```
