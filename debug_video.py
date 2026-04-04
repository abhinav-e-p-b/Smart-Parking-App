"""
debug_video.py — Diagnose why BoT-SORT confirms 0 plates.

Prints per-frame stats so you can see exactly where the pipeline breaks.
Run on a short clip (first 150 frames):
    python debug_video.py --source video.mp4

What this script checks
------------------------
  1. Can the video be opened?
  2. Is YOLO finding any boxes at all?
  3. Are the crop sizes reasonable (not whole-frame = wrong model)?
  4. Is OCR producing any text?
  5. Is the text passing the Indian plate validator?
"""
import argparse
import cv2
import numpy as np
from ultralytics import YOLO
from utils.preprocess import preprocess_plate
from utils.ocr import PlateReader
from utils.constants import CONF_THRESH, IOU_THRESH, OCR_MIN_CONF, NTH_FRAME, MOTION_THRESH

DEFAULT_MODEL = "models/best.pt"
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
    print(f"Using conf={CONF_THRESH}  iou={IOU_THRESH}  ocr_min_conf={OCR_MIN_CONF}")
    print(f"(All thresholds from utils/constants.py — same as detect_video.py)\n")

    detector = YOLO(model_path)
    reader   = PlateReader(gpu=False)

    frame_id      = 0
    processed     = 0
    total_dets    = 0
    dets_with_ocr = 0
    whole_frame_dets = 0   # diagnostic: how many boxes span nearly the full frame
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
            if diff < MOTION_THRESH:
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

            # Check for whole-frame bounding box (wrong model symptom)
            bw = x2 - x1
            bh = y2 - y1
            is_whole_frame = (bw > w * 0.85 and bh > h * 0.85)
            if is_whole_frame:
                whole_frame_dets += 1

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            processed_crop = preprocess_plate(crop)
            plate_text     = reader.read(processed_crop, min_conf=OCR_MIN_CONF)

            if processed <= 30:
                flag = " *** WHOLE FRAME ***" if is_whole_frame else ""
                print(f"  [frame {frame_id:05d}] det_conf={det_conf:.3f}  "
                      f"bbox=({x1},{y1},{x2},{y2})  "
                      f"crop_size={bw}x{bh}{flag}  "
                      f"plate={plate_text or '[unreadable]'}")

            if plate_text:
                dets_with_ocr += 1

    cap.release()

    print(f"\n{'='*55}")
    print(f"Processed frames  : {processed}")
    print(f"Total YOLO dets   : {total_dets}")
    print(f"Whole-frame dets  : {whole_frame_dets}  (should be 0)")
    print(f"Dets with OCR hit : {dets_with_ocr}")
    print(f"{'='*55}")

    print("\n--- DIAGNOSIS ---")
    if total_dets == 0:
        print("PROBLEM: YOLO found 0 detections even at conf=0.25")
        print("  → models/best.pt may not detect plates in this video")
        print("  → Check that best.pt was trained on full-scene images,")
        print("    not cropped plate images")

    elif whole_frame_dets > total_dets * 0.5:
        print("PROBLEM: Most bounding boxes span the whole frame")
        print("  → best.pt was likely trained on cropped plate images only")
        print("  → It fires on the entire frame because it has never seen")
        print("    a plate inside a larger scene")
        print("  → Solution: retrain on full-scene images with proper labels")

    elif dets_with_ocr == 0:
        print("PROBLEM: YOLO found plates but OCR read 0 valid plate strings")
        print("  → Plate crops may be too blurry / small / at bad angle")
        print("  → Try lowering OCR_MIN_CONF in utils/constants.py (currently",
              OCR_MIN_CONF, ")")

    else:
        pct = dets_with_ocr / total_dets * 100
        print(f"YOLO+OCR is working ({pct:.0f}% of dets have valid OCR)")
        print("If tracker is still not confirming plates, check:")
        print(f"  1. confirm_frames={2} — plate must appear in 2+ processed frames")
        print(f"  2. vote_thresh=0.40 — 40% of OCR reads must agree on plate text")
        print("  3. Run with --nth 1 to process every frame")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",  required=True)
    parser.add_argument("--model",   default=DEFAULT_MODEL)
    args = parser.parse_args()
    debug(args.source, args.model)
