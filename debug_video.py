"""
debug_video.py — Diagnose why BoT-SORT confirms 0 plates.

Prints per-frame stats so you can see exactly where the pipeline breaks.
Run on a short clip (first 150 frames):
    python debug_video.py --source video.mp4
"""
import argparse
import cv2
import numpy as np
from ultralytics import YOLO
from utils.preprocess import preprocess_plate
from utils.ocr import PlateReader

DEFAULT_MODEL = "models/best.pt"
CONF_THRESH   = 0.25   # deliberately low for diagnosis
IOU_THRESH    = 0.45
OCR_MIN_CONF  = 0.15
NTH_FRAME     = 3
MAX_FRAMES    = 150    # only check first 150 processed frames

def debug(source, model_path=DEFAULT_MODEL):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Cannot open: {source}"); return

    fps_in = cap.get(cv2.CAP_PROP_FPS) or 30
    w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video: {w}x{h}  FPS={fps_in}  Frames={total}")

    detector = YOLO(model_path)
    reader   = PlateReader(gpu=False)

    frame_id      = 0
    processed     = 0
    total_dets    = 0
    dets_with_ocr = 0
    prev_gray     = None

    while processed < MAX_FRAMES:
        ret, frame = cap.read()
        if not ret: break
        frame_id += 1

        if frame_id % NTH_FRAME != 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray).mean()
            if diff < 15.0:
                prev_gray = gray
                continue
        prev_gray = gray

        results = detector(frame, conf=CONF_THRESH, iou=IOU_THRESH, verbose=False)
        boxes   = results[0].boxes
        processed += 1

        if len(boxes) == 0:
            if processed <= 20:
                print(f"  [frame {frame_id:05d}] YOLO: 0 detections")
            continue

        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            det_conf = float(box.conf[0])
            total_dets += 1

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            processed_crop = preprocess_plate(crop)
            plate_text     = reader.read(processed_crop, min_conf=OCR_MIN_CONF)

            if processed <= 30:
                print(f"  [frame {frame_id:05d}] det_conf={det_conf:.3f}  "
                      f"bbox=({x1},{y1},{x2},{y2})  "
                      f"crop_size={x2-x1}x{y2-y1}  "
                      f"plate={plate_text or '[unreadable]'}")

            if plate_text:
                dets_with_ocr += 1

    cap.release()

    print(f"\n{'='*55}")
    print(f"Processed frames  : {processed}")
    print(f"Total YOLO dets   : {total_dets}")
    print(f"Dets with OCR hit : {dets_with_ocr}")
    print(f"{'='*55}")

    print("\n--- DIAGNOSIS ---")
    if total_dets == 0:
        print("PROBLEM: YOLO found 0 detections even at conf=0.25")
        print("  → models/best.pt may not be detecting plates in this video")
        print("  → Try: python diagnose.py --source <first_frame.jpg>")
    elif dets_with_ocr == 0:
        print("PROBLEM: YOLO found plates but OCR read 0 valid plate strings")
        print("  → Plate crops may be too blurry / small / at bad angle")
        print("  → Try: python diagnose.py --source <frame_with_plate.jpg>")
    else:
        pct = dets_with_ocr / total_dets * 100
        print(f"YOLO+OCR is working ({pct:.0f}% of dets have valid OCR)")
        print("PROBLEM is in tracker thresholds — see fix below")
        print(f"  det_conf range seen above vs tracker new_track_thresh=0.6")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",  required=True)
    parser.add_argument("--model",   default=DEFAULT_MODEL)
    args = parser.parse_args()
    debug(args.source, args.model)
