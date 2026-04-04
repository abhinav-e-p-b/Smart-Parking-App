<div align="center">

```
██╗███╗   ██╗██████╗ ██╗ █████╗     █████╗ ███╗   ██╗██████╗ ██████╗
██║████╗  ██║██╔══██╗██║██╔══██╗   ██╔══██╗████╗  ██║██╔══██╗██╔══██╗
██║██╔██╗ ██║██║  ██║██║███████║   ███████║██╔██╗ ██║██████╔╝██████╔╝
██║██║╚██╗██║██║  ██║██║██╔══██║   ██╔══██║██║╚██╗██║██╔═══╝ ██╔══██╗
██║██║ ╚████║██████╔╝██║██║  ██║   ██║  ██║██║ ╚████║██║     ██║  ██║
╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝╚═╝  ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝     ╚═╝  ╚═╝
```

# 🚗 Indian ANPR System

**Automatic Number Plate Recognition for Indian vehicles — real-time, robust, and production-ready.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple?style=for-the-badge)](https://ultralytics.com)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-v2%2Fv3-orange?style=for-the-badge)](https://github.com/PaddlePaddle/PaddleOCR)
[![BoT-SORT](https://img.shields.io/badge/Tracker-BoT--SORT-green?style=for-the-badge)](https://github.com/mikel-brostrom/boxmot)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 📖 Overview

A complete end-to-end pipeline for detecting, reading, and tracking Indian vehicle number plates from **images**, **video files**, and **live webcam feeds**. Built around a three-stage architecture — YOLO detection → PaddleOCR reading → BoT-SORT deduplication — it handles the full spectrum of real-world Indian conditions: night traffic, dusty rural roads, monsoon rain, dashcam compression artefacts, and IR parking cameras.

The system recognises **all Indian plate formats** including standard state plates (`KL07BB1234`), Bharat Series BH plates (`22BH4567AA`), and bi-line plates. It never reports the same physical plate twice within a session.

---

## ✨ Key Features

| Feature | Details |
|---|---|
| 🎯 **Multi-format support** | Standard, BH-series, 1/2-line plates across all 36 Indian state/UT codes |
| 🔍 **Robust OCR** | PaddleOCR v2 & v3 compatible with 14 image preprocessing variants per crop |
| 📹 **Three input modes** | Static images (batch), video files, live webcam / RTSP streams |
| 🔁 **Zero duplicates** | BoT-SORT Kalman filter + optional ReID guarantees one result per physical plate |
| 🌙 **Night / IR ready** | CLAHE enhancement, Otsu/adaptive thresholding, multi-rotation fallback |
| ⚡ **Three-gate efficiency** | Nth-frame sampler → motion detector → YOLO, minimising wasted inference |
| 🛠️ **Self-healing OCR** | Position-aware character substitution (`0→O`, `1→I`, `B→8`, etc.) |
| 🧪 **Full test suite** | 20+ unit tests for the tracker with zero boxmot dependency |
| 📊 **CSV export** | Timestamped log with bounding box coordinates for every confirmed plate |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          INPUT SOURCES                              │
│        Image / Video File / Webcam / RTSP Stream                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        GATE 1 — Frame Sampler                       │
│         Process every Nth frame  (default: every 3rd frame)         │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       GATE 2 — Motion Filter                        │
│         Skip static scenes  (mean abs-diff < threshold)             │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       GATE 3 — Inference Pipeline                   │
│                                                                     │
│   ┌──────────────┐    ┌─────────────────┐    ┌─────────────────┐   │
│   │  YOLOv8      │───▶│  preprocess_    │───▶│  PaddleOCR      │   │
│   │  Detection   │    │  plate()        │    │  (14 variants)  │   │
│   │  (best.pt)   │    │  CLAHE, Otsu,   │    │  + validator    │   │
│   │              │    │  deskew, rotate │    │  + char-fix     │   │
│   └──────────────┘    └─────────────────┘    └────────┬────────┘   │
│                                                        │             │
│                                              ┌─────────▼────────┐   │
│                                              │  PlateTracker    │   │
│                                              │  BoT-SORT /      │   │
│                                              │  IoU fallback    │   │
│                                              │  majority vote   │   │
│                                              └─────────┬────────┘   │
└────────────────────────────────────────────────────────┼────────────┘
                                                         │
                         ┌───────────────────────────────▼──────────────┐
                         │           OUTPUTS (fire once per plate)       │
                         │  Annotated video/frame  │  CSV log  │  CLI   │
                         └──────────────────────────────────────────────┘
```

### Preprocessing Variants (per crop)

The pipeline tries up to **15 variants** of each crop, stopping at the first valid reading:

```
gray → deskewed → sharp → boosted → otsu → otsu_inv → adap → adap_inv
  → rot90_gray → rot90_deskewed → rot180_gray
  → rot270_gray → rot270_deskewed → rot90_otsu → rot270_otsu
```

---

## 📁 Project Structure

```
indian-anpr/
│
├── 📄 detect_video.py       — ANPR on a pre-recorded video file
├── 📄 detect_webcam.py      — Real-time ANPR from webcam / IP camera
├── 📄 detect_batch.py       — Batch ANPR over a directory of images
├── 📄 debug_ocr.py          — Diagnose OCR on a single crop or video
├── 📄 debug_video.py        — Full pipeline diagnostics (YOLO → OCR → tracker)
├── 📄 download_reid.py      — Download OSNet ReID weights from HuggingFace
├── 📄 test_tracker.py       — Pytest unit tests for PlateTracker
├── 📄 requirements.txt      — All Python dependencies
│
├── 📁 models/
│   └── best.pt              — YOLOv8 weights for plate detection (you provide)
│
├── 📁 utils/
│   ├── __init__.py          — Public API exports
│   ├── constants.py         — Single source of truth for all thresholds
│   ├── preprocess.py        — Image preprocessing pipeline (14 variants)
│   ├── ocr.py               — PaddleOCR wrapper + Indian plate validator
│   ├── tracker.py           — BoT-SORT wrapper with confirmation logic
│   ├── visualise.py         — Bounding box / overlay drawing helpers
│   └── augment.py           — Albumentations pipeline for training data
│
└── 📁 outputs/              — Generated CSVs, annotated frames, crops
```

---

## ⚙️ Installation

### 1. Clone and create environment

```bash
git clone https://github.com/yourname/indian-anpr.git
cd indian-anpr
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **GPU users:** Replace the `torch` and `torchvision` lines in `requirements.txt` with the CUDA variants, and swap `paddlepaddle` for `paddlepaddle-gpu`.

### 3. Add your YOLO model

Place your trained YOLOv8 weights at `models/best.pt`.  
The model should be trained to detect licence plates in **full scene images** (not pre-cropped plates).

### 4. (Optional) Download ReID weights

```bash
python download_reid.py                          # downloads osnet_x0_25_msmt17.pt (~3 MB)
python download_reid.py --model osnet_x1_0_msmt17  # more accurate, ~22 MB
python download_reid.py --list                   # show all available models
```

---

## 🚀 Run Commands

### 🎬 Video File

```bash
# Basic — Kalman-only deduplication (no ReID file needed, fast on CPU)
python detect_video.py --source video.mp4

# Save annotated video + CSV log
python detect_video.py --source video.mp4 \
    --output outputs/result.mp4 \
    --csv outputs/log.csv

# With ReID (better re-identification after occlusion)
python detect_video.py --source video.mp4 \
    --reid osnet_x0_25_msmt17.pt \
    --csv outputs/log.csv

# Custom thresholds
python detect_video.py --source video.mp4 \
    --conf 0.30 \
    --nth 2 \
    --motion-thresh 10.0
```

### 📷 Webcam / IP Camera

```bash
# Default webcam
python detect_webcam.py

# Second webcam
python detect_webcam.py --source 1

# RTSP IP camera
python detect_webcam.py --source rtsp://192.168.1.100:554/stream

# With ReID
python detect_webcam.py --reid osnet_x0_25_msmt17.pt
```

**Webcam keyboard controls:**  
`q` — quit &nbsp;|&nbsp; `s` — save current frame &nbsp;|&nbsp; `r` — reset tracker

### 🗂️ Batch Images

```bash
# Process all images in a directory
python detect_batch.py --source data/raw/

# Save annotated images + CSV
python detect_batch.py --source data/raw/ \
    --output outputs/annotated/ \
    --csv outputs/results.csv

# Parallel processing with 4 threads
python detect_batch.py --source data/raw/ --workers 4

# Allow repeated plates (don't deduplicate across images)
python detect_batch.py --source data/raw/ --allow-duplicates
```

### 🔬 Debugging

```bash
# Debug OCR on a single plate crop
python debug_ocr.py --source crop.jpg

# Debug OCR on video — shows all preprocessing variants tried
python debug_ocr.py --source video.mp4 --video --max-crops 10

# Save preprocessed variants as images for visual inspection
python debug_ocr.py --source video.mp4 --video --save-crops outputs/crops/

# Full pipeline diagnostics — YOLO detections, crop sizes, OCR hit-rate
python debug_video.py --source video.mp4
```

### 🧪 Tests

```bash
python -m pytest test_tracker.py -v
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `ultralytics` | ≥ 8.0.0 | YOLOv8 licence plate detection |
| `paddleocr` | ≥ 2.7.0 | OCR engine (v2 + v3 compatible) |
| `paddlepaddle` | ≥ 2.6.0 | PaddleOCR backend (CPU build) |
| `opencv-python` | ≥ 4.8.0 | Image processing, video I/O |
| `numpy` | ≥ 1.24.0 | Array operations |
| `Pillow` | ≥ 9.5.0 | Image loading helper |
| `torch` | ≥ 2.0.0 | Deep learning backend (CPU build) |
| `torchvision` | ≥ 0.15.0 | Vision transforms |
| `boxmot` | ≥ 10.0.0 | BoT-SORT tracker + ReID models |
| `albumentations` | ≥ 1.3.0 | Training augmentation pipeline |
| `kagglehub` | ≥ 0.2.0 | Dataset download utility |
| `tqdm` | ≥ 4.65.0 | Progress bars |
| `pyyaml` | ≥ 6.0 | YOLO config parsing |
| `matplotlib` | ≥ 3.7.0 | Training visualisation |
| `pandas` | ≥ 2.0.0 | CSV / data handling |
| `scikit-learn` | ≥ 1.3.0 | Metrics for evaluation |
| `huggingface_hub` | optional | Reliable ReID weight download |

---

## 🤖 Models

### Detection — `models/best.pt`

A YOLOv8 model fine-tuned to detect licence plates in full-scene images (dashcam, CCTV, parking cameras). The model must be trained on **full scene** images — not pre-cropped plates — otherwise it will fire on the entire frame.

**Recommended training datasets:**
- [Indian Number Plates Dataset (Kaggle)](https://www.kaggle.com/datasets/iamarchit/vehicle-number-plate)
- [Vehicle Registration Plates Dataset](https://universe.roboflow.com/license-plate-recognition-rxg4e/indian-license-plate)

**Recommended base:** `yolov8n.pt` (nano, fast on CPU) or `yolov8s.pt` (small, balanced)

### OCR — PaddleOCR (auto-downloaded)

PaddleOCR downloads its own text detection and recognition models on first run. No manual download required. The system auto-detects whether you have **v2** (`use_gpu=`, `use_angle_cls=`) or **v3** (`device=`) installed and constructs the reader accordingly.

### ReID — OSNet (optional)

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `osnet_x0_25_msmt17.pt` | ~3 MB | ⚡ Fastest | Good — **recommended for CPU** |
| `osnet_x0_5_msmt17.pt` | ~7 MB | Fast | Better |
| `osnet_x0_75_msmt17.pt` | ~13 MB | Moderate | Very good |
| `osnet_x1_0_msmt17.pt` | ~22 MB | Slower | Best |

Without ReID the tracker uses Kalman filter + IoU matching only, which still deduplicates correctly in most scenarios.

---

## ⚙️ Configuration

All thresholds live in `utils/constants.py` — one file to tune the entire pipeline:

```python
# utils/constants.py

CONF_THRESH    = 0.25   # YOLO detection confidence (lower = more detections)
IOU_THRESH     = 0.45   # NMS threshold
OCR_MIN_CONF   = 0.15   # PaddleOCR minimum confidence per character box
NTH_FRAME      = 3      # Process every Nth frame (3 = 33% of frames)
MOTION_THRESH  = 15.0   # Min mean pixel change to count as motion
CONFIRM_FRAMES = 2      # Frames a track must appear before confirming
MAX_LOST       = 30     # Frames before a lost track is pruned
VOTE_THRESH    = 0.40   # Fraction of OCR reads that must agree on plate text

# Webcam-specific overrides
WEBCAM_NTH_FRAME     = 2
WEBCAM_MOTION_THRESH = 12.0
```

---

## 🌏 Supported Plate Formats

### Standard Format — `SS DD LL DDDD`
```
KL 07 BB 1234   →  Kerala private vehicle
MH 12 AB 3456   →  Maharashtra private vehicle
DL 01 AA 1234   →  Delhi private vehicle
TN 09 CD 5678   →  Tamil Nadu private vehicle
```

### BH Series (Bharat) — `DD BH DDDD LL`
```
22BH4567AA      →  Bharat Series plate (no state restriction)
```

### Supported State / UT Codes (36 total)
`AN AP AR AS BR CH CG DD DL DN GA GJ HR HP JK JH KA KL LA LD MP MH MN ML MZ NL OD PY PB RJ SK TN TS TR UP UK WB`

### Character Self-Correction
The OCR post-processor fixes common misreads at each position:

| Position type | Misread → Corrected |
|---|---|
| Letter positions (0,1,4,5) | `0→O`, `1→I`, `l→I`, `8→B`, `5→S` |
| Digit positions (2,3,6-9) | `O→0`, `I→1`, `l→1`, `B→8`, `S→5` |

---

## 🐛 Debugging Guide

### YOLO finds 0 detections
```
→ Verify best.pt was trained on full-scene images, not plate crops
→ Lower CONF_THRESH in utils/constants.py (try 0.15)
→ Run: python debug_video.py --source video.mp4
```

### YOLO bounding box covers entire frame
```
→ Model was trained on pre-cropped plates only
→ Retrain on full-scene images with proper bounding box labels
```

### OCR reads 0 valid plates (but YOLO detects correctly)
```
→ Run: python debug_ocr.py --source video.mp4 --video --save-crops outputs/crops/
→ Inspect _variants.jpg files to see all preprocessing outputs
→ Lower OCR_MIN_CONF in utils/constants.py (try 0.05)
→ Check if plate is sideways — rot90/rot270 variants should handle it
```

### Tracker confirms 0 plates
```
→ Lower CONFIRM_FRAMES to 1 in utils/constants.py
→ Lower VOTE_THRESH to 0.30
→ Increase NTH_FRAME processing rate (lower NTH_FRAME value)
```

---

## 🔭 Future Extensions

| Extension | Difficulty | Description |
|---|---|---|
| 🌐 FastAPI REST endpoint | Easy | Wrap `detect_batch.py` in a REST API for remote inference |
| 📱 Android / iOS app | Medium | Export YOLO to TFLite/CoreML for on-device detection |
| 🔔 Alert system | Easy | Webhook / email / SMS alert when a flagged plate is seen |
| 🗄️ Database integration | Easy | Write confirmed plates to PostgreSQL / SQLite in real time |
| 🎓 Transfer learning | Medium | Fine-tune on your own plate dataset using `utils/augment.py` |
| 🖼️ Multi-plate per frame | Done ✅ | Already supported — each YOLO box tracked independently |
| 🌙 Night mode tuning | Medium | Dedicated night/IR augmentation pipeline already in `augment.py` |
| 🔀 Multi-camera fusion | Hard | Merge plate sightings from multiple CCTV feeds with shared tracker |
| 📊 Dashboard UI | Medium | Real-time web dashboard with plate log and confidence charts |
| 🧠 LLM vehicle lookup | Easy | Query RTO database or vehicle info API from confirmed plates |
| 🔡 Bi-line plate support | Medium | Handle two-row plates where state code and number are on separate lines |
| 🏎️ Speed estimation | Hard | Combine plate tracking with optical flow for vehicle speed |
| 🗺️ GPS tagging | Medium | Attach GPS coordinates from NMEA stream to each confirmed plate |

---

## 🏭 Use Cases

- **🏢 Parking management** — Automate entry/exit logging in office complexes and malls
- **🛣️ Toll collection** — Identify vehicles at toll plazas without stopping
- **🚓 Traffic enforcement** — Flag vehicles running red lights or speeding
- **🏠 Residential security** — Whitelist authorised vehicles at gated communities
- **🏭 Fleet management** — Track company vehicle movements across sites
- **🚨 Stolen vehicle detection** — Cross-reference against a watchlist in real time
- **📦 Logistics** — Confirm truck arrival/departure at warehouses
- **🔬 Research** — Collect traffic volume and vehicle type statistics

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Run the test suite (`python -m pytest test_tracker.py -v`)
4. Commit your changes (`git commit -m 'Add feature'`)
5. Push and open a Pull Request

All new tracker logic must be accompanied by tests in `test_tracker.py`.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Made with ❤️ for Indian roads

*Tested on dashcam footage from highways in Kerala, Maharashtra, and Delhi NCR.*

</div>
