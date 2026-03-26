"""
detect_webcam.py — Real-time ANPR from webcam or IP camera stream.

Deduplication via BoT-SORT
---------------------------
The old cooldown-counter is replaced by PlateTracker (BoT-SORT).
Each physical plate gets one stable track ID; a "confirmed" event fires
exactly once per plate per tracking session.  The on-screen log and the
printed output therefore never show the same plate twice unless the
tracker is explicitly reset (press 'r').

Usage
-----
  python detect_webcam.py                           # default webcam
  python detect_webcam.py --source 1                # second webcam
  python detect_webcam.py --source rtsp://...       # IP camera
  python detect_webcam.py --reid osnet_x0_25_msmt17.pt   # with ReID

Controls
--------
  q — quit
  s — save current frame + annotated frame to outputs/
  r — reset tracker and plate log (new session)
"""

import argparse
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
from ultralytics import YOLO

from utils.preprocess import preprocess_plate
from utils.ocr import PlateReader
from utils.tracker import PlateTracker
from utils.visualise import draw_detections, add_fps_overlay

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL  = "models/best.pt"
CONF_THRESH    = 0.50
IOU_THRESH     = 0.45
OCR_MIN_CONF   = 0.30
NTH_FRAME      = 2       # process every 2nd frame for lower latency
MOTION_THRESH  = 12.0    # slightly tighter than video mode
CONFIRM_FRAMES = 3       # BoT-SORT: frames before plate is confirmed
MAX_LOST       = 30      # BoT-SORT: frames before track is pruned
LOG_MAXLEN     = 10      # on-screen plate log length


def run_webcam(
    source         = 0,
    model_path:str = DEFAULT_MODEL,
    conf:    float = CONF_THRESH,
    iou:     float = IOU_THRESH,
    reid_weights: str = None,
):
    """
    Run real-time ANPR from a webcam or IP camera.

    Parameters
    ----------
    source        : int (camera index) or str (RTSP / HTTP URL)
    model_path    : path to YOLOv8 weights
    conf          : YOLO detection confidence threshold
    iou           : YOLO NMS IoU threshold
    reid_weights  : path to ReID model weights; None → Kalman-only mode
    """

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera source: {source}")

    # Prefer 1280×720 — good balance of quality and inference speed on CPU
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    detector = YOLO(model_path)
    reader   = PlateReader(gpu=False)   # set gpu=True if CUDA available

    # ------------------------------------------------------------------
    # BoT-SORT tracker
    # ------------------------------------------------------------------
    tracker = PlateTracker(
        reid_weights   = reid_weights,
        confirm_frames = CONFIRM_FRAMES,
        max_lost       = MAX_LOST,
        vote_thresh    = 0.5,
        device         = "cpu",
    )

    # ------------------------------------------------------------------
    # Runtime state
    # ------------------------------------------------------------------
    frame_id    = 0
    prev_gray   = None
    plate_log: deque = deque(maxlen=LOG_MAXLEN)  # on-screen log entries
    fps_display = 0.0
    fps_timer   = time.perf_counter()

    print(f"Webcam ANPR started.")
    print(f"Source: {source}  |  ReID: {'on' if reid_weights else 'off (Kalman-only)'}")
    print("Controls:  q=quit  s=save frame  r=reset tracker")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed — exiting.")
            break

        frame_id += 1

        # ----------------------------------------------------------------
        # Gate 1 — Nth-frame sampler
        # ----------------------------------------------------------------
        if frame_id % NTH_FRAME != 0:
            cv2.imshow("Indian ANPR — Webcam", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        # ----------------------------------------------------------------
        # Gate 2 — Motion check
        # ----------------------------------------------------------------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray).mean()
            if diff < MOTION_THRESH:
                prev_gray = gray
                cv2.imshow("Indian ANPR — Webcam", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue
        prev_gray = gray

        # ----------------------------------------------------------------
        # Gate 3 — YOLO + OCR
        # ----------------------------------------------------------------
        yolo_results = detector(frame, conf=conf, iou=iou, verbose=False)
        boxes        = yolo_results[0].boxes

        raw_dets:    list = []
        det_list:    list = []
        plate_texts: list = []

        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            det_conf = float(box.conf[0])
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            processed  = preprocess_plate(crop)
            plate_text = reader.read(processed, min_conf=OCR_MIN_CONF)

            raw_dets.append((x1, y1, x2, y2, det_conf, plate_text))
            det_list.append((x1, y1, x2, y2, det_conf))
            plate_texts.append(plate_text)

        # ----------------------------------------------------------------
        # BoT-SORT update — dedup happens here
        # ----------------------------------------------------------------
        events = tracker.update(raw_dets, frame)

        for event in events:
            if event["type"] == "confirmed":
                ts    = datetime.now().strftime("%H:%M:%S")
                plate = event["plate"]
                conf_ = event["conf"]
                tid   = event["track_id"]

                log_entry = f"{ts}  {plate}  ({conf_:.2f})  id={tid}"
                plate_log.append(log_entry)
                print(f"  {log_entry}")

        # ----------------------------------------------------------------
        # FPS (exponential smoothing)
        # ----------------------------------------------------------------
        now         = time.perf_counter()
        instant_fps = 1.0 / max(now - fps_timer, 1e-6)
        fps_display = 0.8 * fps_display + 0.2 * instant_fps
        fps_timer   = now

        # ----------------------------------------------------------------
        # Draw bounding boxes + FPS overlay
        # ----------------------------------------------------------------
        annotated = draw_detections(frame, det_list, plate_texts)
        annotated = add_fps_overlay(annotated, fps_display)

        # On-screen plate log — bottom-left corner
        for idx, entry in enumerate(reversed(plate_log)):
            y_pos = annotated.shape[0] - 14 - idx * 22
            if y_pos < 10:
                break
            cv2.putText(
                annotated, entry,
                (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52,
                (0, 255, 100), 1, cv2.LINE_AA,
            )

        cv2.imshow("Indian ANPR — Webcam", annotated)

        # ----------------------------------------------------------------
        # Key controls
        # ----------------------------------------------------------------
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("Quit.")
            break

        elif key == ord("s"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            Path("outputs").mkdir(exist_ok=True)
            cv2.imwrite(f"outputs/frame_{ts}.jpg",      frame)
            cv2.imwrite(f"outputs/annotated_{ts}.jpg",  annotated)
            print(f"Saved  outputs/frame_{ts}.jpg  +  annotated version.")

        elif key == ord("r"):
            tracker.reset()
            plate_log.clear()
            frame_id  = 0
            prev_gray = None
            print("Tracker and plate log reset.")

    # ------------------------------------------------------------------
    cap.release()
    cv2.destroyAllWindows()
    print(f"Session ended.  {len(plate_log)} entries in final log.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Indian ANPR — Webcam / IP Camera  (BoT-SORT deduplication)"
    )
    parser.add_argument("--source", default=0,
                        help="Camera index (0, 1, ...) or RTSP/HTTP URL")
    parser.add_argument("--model",  default=DEFAULT_MODEL)
    parser.add_argument("--conf",   type=float, default=CONF_THRESH)
    parser.add_argument("--iou",    type=float, default=IOU_THRESH)
    parser.add_argument("--reid",   default=None, dest="reid_weights",
                        help="Path to ReID weights file. "
                             "Omit for Kalman-only mode (faster on CPU).")
    args = parser.parse_args()

    # Allow integer camera index
    try:
        source = int(args.source)
    except (ValueError, TypeError):
        source = args.source

    run_webcam(
        source       = source,
        model_path   = args.model,
        conf         = args.conf,
        iou          = args.iou,
        reid_weights = args.reid_weights,
    )
