"""
detect_webcam.py — Real-time ANPR from webcam or IP camera.

Thresholds imported from utils/constants.py — shared with detect_video.py
so behaviour is consistent across modes.

Usage
-----
  python detect_webcam.py                           # default webcam
  python detect_webcam.py --source 1                # second webcam
  python detect_webcam.py --source rtsp://...       # IP camera
  python detect_webcam.py --reid osnet_x0_25_msmt17.pt

Controls
--------
  q — quit
  s — save frame + annotated frame to outputs/
  r — reset tracker and on-screen log
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
from utils.constants import (
    CONF_THRESH, IOU_THRESH, OCR_MIN_CONF,
    WEBCAM_NTH_FRAME, WEBCAM_MOTION_THRESH,
    CONFIRM_FRAMES, MAX_LOST,
)

DEFAULT_MODEL = "models/best.pt"
LOG_MAXLEN    = 10


def run_webcam(
    source         = 0,
    model_path:str = DEFAULT_MODEL,
    conf:    float = CONF_THRESH,
    iou:     float = IOU_THRESH,
    reid_weights:str = None,
):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera: {source}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = YOLO(model_path)
    reader   = PlateReader(gpu=False)

    tracker = PlateTracker(
        reid_weights      = reid_weights,
        confirm_frames    = CONFIRM_FRAMES,
        max_lost          = MAX_LOST,
        vote_thresh       = 0.40,
        device            = "cpu",
        track_high_thresh = conf,
        track_low_thresh  = 0.05,
        new_track_thresh  = conf,
        match_thresh      = 0.85,
        proximity_thresh  = 0.35,
        appearance_thresh = 0.30,
    )

    frame_id    = 0
    prev_gray   = None
    plate_log:  deque = deque(maxlen=LOG_MAXLEN)
    fps_display = 0.0
    fps_timer   = time.perf_counter()

    print(f"Webcam ANPR ready. Source={source}  "
          f"ReID={'on' if reid_weights else 'off'}")
    print(f"OCR min conf: {OCR_MIN_CONF}  Detection conf: {conf}")
    print("Controls: q=quit  s=save frame  r=reset")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed.")
            break

        frame_id += 1

        # Gate 1
        if frame_id % WEBCAM_NTH_FRAME != 0:
            cv2.imshow("Indian ANPR — Webcam", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        # Gate 2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray).mean()
            if diff < WEBCAM_MOTION_THRESH:
                prev_gray = gray
                cv2.imshow("Indian ANPR — Webcam", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue
        prev_gray = gray

        # Gate 3
        yolo_res = detector(frame, conf=conf, iou=iou, verbose=False)
        boxes    = yolo_res[0].boxes

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

        events = tracker.update(raw_dets, frame)

        for event in events:
            if event["type"] == "confirmed":
                ts    = datetime.now().strftime("%H:%M:%S")
                plate = event["plate"]
                cf    = event["conf"]
                tid   = event["track_id"]
                entry = f"{ts}  {plate}  ({cf:.2f})  id={tid}"
                plate_log.append(entry)
                print(f"  ✓ {entry}")

        # FPS
        now         = time.perf_counter()
        instant_fps = 1.0 / max(now - fps_timer, 1e-6)
        fps_display = 0.8 * fps_display + 0.2 * instant_fps
        fps_timer   = now

        annotated = draw_detections(frame, det_list, plate_texts)
        annotated = add_fps_overlay(annotated, fps_display)

        for idx, entry in enumerate(reversed(plate_log)):
            y_pos = annotated.shape[0] - 14 - idx * 22
            if y_pos < 10:
                break
            cv2.putText(annotated, entry, (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52,
                        (0, 255, 100), 1, cv2.LINE_AA)

        cv2.imshow("Indian ANPR — Webcam", annotated)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("s"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            Path("outputs").mkdir(exist_ok=True)
            cv2.imwrite(f"outputs/frame_{ts}.jpg",     frame)
            cv2.imwrite(f"outputs/annotated_{ts}.jpg", annotated)
            print(f"Saved outputs/frame_{ts}.jpg")
        elif key == ord("r"):
            tracker.reset()
            plate_log.clear()
            frame_id  = 0
            prev_gray = None
            print("Tracker reset.")

    cap.release()
    cv2.destroyAllWindows()
    print(f"Session ended. {len(plate_log)} plates in log.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indian ANPR — Webcam")
    parser.add_argument("--source", default=0)
    parser.add_argument("--model",  default=DEFAULT_MODEL)
    parser.add_argument("--conf",   type=float, default=CONF_THRESH)
    parser.add_argument("--iou",    type=float, default=IOU_THRESH)
    parser.add_argument("--reid",   default=None, dest="reid_weights")
    args = parser.parse_args()

    try:
        source = int(args.source)
    except (ValueError, TypeError):
        source = args.source

    run_webcam(source, args.model, args.conf, args.iou, args.reid_weights)
